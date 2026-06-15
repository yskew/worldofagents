from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import verify_agent_credentials
from app.auth.jwt_issuer import get_jwt_issuer
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.human import Human
from app.models.verification_log import VerificationLog
from app.ratelimit import rate_limit
from app.schemas.verify import (
    ActiveVerifyRequest,
    ActiveVerifyResponse,
    ChallengeRequest,
    ChallengeResponse,
    CompareRequest,
    CompareResponse,
    Probe,
    SimilarMatch,
    SimilarRequest,
    SimilarResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.services import challenge as challenge_svc
from app.services.agent_service import _current_vector_version
from app.services.challenge_bank import get_probe, select_probes
from app.services.signature_engine import compare_signatures, extract_features, features_to_vector

router = APIRouter(tags=["verify"])


@router.post("/verify", dependencies=[Depends(rate_limit)])
async def verify_agent(
    body: VerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> VerifyResponse:
    result = await db.execute(select(Agent).where(Agent.id == body.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found or revoked")

    if not verify_agent_credentials(body.agent_key, agent.key_hash):
        raise HTTPException(status_code=401, detail="Invalid agent key")

    new_features = extract_features(body.trajectory)
    new_vector = features_to_vector(new_features)
    stored_sig = agent.signature or {}
    # Recompute the stored vector from the signature JSONB (the encoding-independent
    # source of truth) rather than trusting a possibly stale persisted vector. This
    # guarantees both sides use the active encoding (RFC 0002) and is identical to
    # the persisted value under the legacy encoding.
    stored_vec = features_to_vector(stored_sig)

    comparison = compare_signatures(stored_sig, stored_vec, new_features, new_vector)
    passed = comparison["verdict"] == "pass"

    client_ip = request.client.host if request.client else None
    log = VerificationLog(
        agent_id=agent.id,
        similarity_score=comparison["overall_score"],
        passed=passed,
        score_version=2 if settings.SCORE_NORMALIZATION_V2 else 1,
        ip_address=client_ip,
    )
    db.add(log)
    await db.commit()

    token = None
    if passed:
        from app.models.human import Human
        human_result = await db.execute(select(Human).where(Human.id == agent.human_id))
        human = human_result.scalar_one()
        issuer = get_jwt_issuer()
        token = issuer.issue_token(
            human_clerk_id=human.clerk_id,
            agent_id=str(agent.id),
            agent_name=agent.name,
            similarity_score=comparison["overall_score"],
        )

    return VerifyResponse(
        verified=passed,
        similarity_score=comparison["overall_score"],
        verdict=comparison["verdict"],
        token=token,
        breakdown=comparison["breakdown"],
        confidence=comparison.get("confidence"),
    )


@router.post("/similar", dependencies=[Depends(rate_limit)])
async def find_similar_agents(
    body: SimilarRequest,
    db: AsyncSession = Depends(get_db),
) -> SimilarResponse:
    """Find active agents whose behavioral signature most resembles the supplied
    trajectory. Uses a pgvector ANN scan (cosine) for fast candidate retrieval,
    then re-ranks candidates with the full ensemble for quality. Public, no auth.

    Only agents whose stored vector matches the active encoding are searched;
    others are reported in stale_excluded (recompute with scripts/reembed.py)."""
    query_features = extract_features(body.trajectory)
    query_vector = features_to_vector(query_features)
    active_version = _current_vector_version()

    # Candidate retrieval: pull a few extra so the ensemble re-rank has room.
    pool = min(body.limit * 4, 50)
    dist = Agent.signature_vector.cosine_distance(query_vector).label("dist")
    rows = (
        await db.execute(
            select(Agent, Human.display_name, dist)
            .join(Human, Agent.human_id == Human.id)
            .where(
                Agent.status == "active",
                Agent.signature_vector.isnot(None),
                Agent.signature_version == active_version,
            )
            .order_by(dist)
            .limit(pool)
        )
    ).all()

    stale_excluded = (
        await db.execute(
            select(func.count(Agent.id)).where(
                Agent.status == "active",
                Agent.signature_vector.isnot(None),
                Agent.signature_version.is_distinct_from(active_version),
            )
        )
    ).scalar() or 0

    matches = []
    for agent, owner_name, d in rows:
        cand_vector = features_to_vector(agent.signature or {})
        comparison = compare_signatures(
            query_features, query_vector, agent.signature or {}, cand_vector
        )
        matches.append(
            SimilarMatch(
                agent_id=agent.id,
                name=agent.name,
                owner_display_name=owner_name,
                score=comparison["overall_score"],
                vector_similarity=round(1.0 - float(d), 4),
            )
        )

    matches.sort(key=lambda m: m.score, reverse=True)
    return SimilarResponse(results=matches[: body.limit], stale_excluded=int(stale_excluded))


@router.post("/challenge", dependencies=[Depends(rate_limit)])
async def issue_challenge(
    body: ChallengeRequest,
    db: AsyncSession = Depends(get_db),
) -> ChallengeResponse:
    """Issue a fresh, single-use challenge for an agent: a server-chosen set of
    probes plus a signed, nonced token. The agent must respond to *these* probes
    live, which is what defeats replay of a pre-recorded trajectory (RFC 0008)."""
    result = await db.execute(select(Agent).where(Agent.id == body.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found or revoked")
    if not agent.challenge_profile:
        raise HTTPException(
            status_code=409,
            detail="Agent has no challenge profile; submit one via /agents/{id}/challenge-profile",
        )

    available = list(agent.challenge_profile.keys())
    # Generate the nonce first, select probes seeded by it (so the selection is
    # unpredictable to the caller), then bind both into one signed token.
    nonce = challenge_svc.new_nonce()
    probe_ids = select_probes(
        str(agent.id), nonce, available, settings.CHALLENGE_NUM_PROBES
    )
    token, _ = challenge_svc.issue(str(agent.id), probe_ids, nonce=nonce)

    probes = [Probe(id=pid, stimulus=get_probe(pid)["stimulus"]) for pid in probe_ids]
    return ChallengeResponse(
        challenge_token=token,
        probes=probes,
        expires_in=settings.CHALLENGE_TTL_SECONDS,
    )


@router.post("/verify/active", dependencies=[Depends(rate_limit)])
async def verify_active(
    body: ActiveVerifyRequest,
    db: AsyncSession = Depends(get_db),
) -> ActiveVerifyResponse:
    """Active verification: validate the challenge token (signature, expiry,
    single-use), then compare the agent's live probe responses against its stored
    challenge profile. Issues a delegated JWT on success (RFC 0008)."""
    try:
        payload = challenge_svc.decode(body.challenge_token)
    except challenge_svc.ChallengeError as e:
        raise HTTPException(status_code=400, detail=f"Invalid challenge: {e}")

    if payload["agent_id"] != str(body.agent_id):
        raise HTTPException(status_code=400, detail="Challenge was not issued for this agent")

    result = await db.execute(select(Agent).where(Agent.id == body.agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise HTTPException(status_code=404, detail="Agent not found or revoked")
    if not verify_agent_credentials(body.agent_key, agent.key_hash):
        raise HTTPException(status_code=401, detail="Invalid agent key")
    if not agent.challenge_profile:
        raise HTTPException(status_code=409, detail="Agent has no challenge profile")

    # All challenged probes must be answered.
    missing = [pid for pid in payload["probe_ids"] if pid not in body.responses]
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing responses for probes: {missing}")

    # Single-use: consume the nonce only after the request is otherwise well-formed.
    if not challenge_svc.consume_nonce(payload["nonce"], payload["exp"]):
        raise HTTPException(status_code=409, detail="Challenge already used (replay rejected)")

    per_probe: dict[str, float] = {}
    for probe_id in payload["probe_ids"]:
        expected = agent.challenge_profile[probe_id]
        expected_vec = features_to_vector(expected)
        resp_features = extract_features(body.responses[probe_id])
        resp_vec = features_to_vector(resp_features)
        comparison = compare_signatures(expected, expected_vec, resp_features, resp_vec)
        per_probe[probe_id] = comparison["overall_score"]

    active_score = round(sum(per_probe.values()) / len(per_probe), 4)
    threshold = settings.ACTIVE_VERIFICATION_PASS_THRESHOLD
    passed = active_score >= threshold
    verdict = "pass" if passed else ("warning" if active_score >= threshold * 0.6 else "fail")

    token = None
    if passed:
        from app.models.human import Human as HumanModel
        human = (
            await db.execute(select(HumanModel).where(HumanModel.id == agent.human_id))
        ).scalar_one()
        issuer = get_jwt_issuer()
        token = issuer.issue_token(
            human_clerk_id=human.clerk_id,
            agent_id=str(agent.id),
            agent_name=agent.name,
            similarity_score=active_score,
        )

    return ActiveVerifyResponse(
        verified=passed,
        active_score=active_score,
        verdict=verdict,
        token=token,
        per_probe={k: round(v, 4) for k, v in per_probe.items()},
    )


@router.post("/compare", dependencies=[Depends(rate_limit)])
async def compare_trajectories(body: CompareRequest) -> CompareResponse:
    sig_a = extract_features(body.trajectory_a)
    vec_a = features_to_vector(sig_a)
    sig_b = extract_features(body.trajectory_b)
    vec_b = features_to_vector(sig_b)

    comparison = compare_signatures(sig_a, vec_a, sig_b, vec_b)

    return CompareResponse(
        similarity_score=comparison["overall_score"],
        verdict=comparison["verdict"],
        breakdown=comparison["breakdown"],
        confidence=comparison.get("confidence"),
    )

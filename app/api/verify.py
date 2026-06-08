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
from app.schemas.verify import (
    CompareRequest,
    CompareResponse,
    SimilarMatch,
    SimilarRequest,
    SimilarResponse,
    VerifyRequest,
    VerifyResponse,
)
from app.services.agent_service import _current_vector_version
from app.services.signature_engine import compare_signatures, extract_features, features_to_vector

router = APIRouter(tags=["verify"])


@router.post("/verify")
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


@router.post("/similar")
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


@router.post("/compare")
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

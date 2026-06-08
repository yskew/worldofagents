from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.agent_keys import verify_agent_credentials
from app.auth.jwt_issuer import get_jwt_issuer
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.verification_log import VerificationLog
from app.schemas.verify import CompareRequest, CompareResponse, VerifyRequest, VerifyResponse
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
    )


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
    )

"""RFC 8693 OAuth 2.0 Token Exchange broker (RFC 0009).

Exchanges a human's IdP identity (subject_token) plus the agent's behavioral
verification JWT (actor_token, issued by us) for a scoped, short-lived,
audience-bound downstream token the relying party can accept. Behavioral
verification gates issuance: the actor_token only exists if the agent passed
/verify or /verify/active.

subject_token may come from Clerk (default, unchanged) or any configured OIDC
provider (Okta/Entra/Auth0/Google) via the provider registry.
"""
from __future__ import annotations

import jwt
from fastapi import APIRouter, Depends, Form, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_issuer import get_jwt_issuer
from app.auth.providers import get_provider
from app.config import settings
from app.database import get_db
from app.models.agent import Agent
from app.models.human import Human
from app.ratelimit import rate_limit

router = APIRouter(tags=["oauth"])

TOKEN_EXCHANGE_GRANT = "urn:ietf:params:oauth:grant-type:token-exchange"
JWT_TOKEN_TYPE = "urn:ietf:params:oauth:token-type:jwt"


def _oauth_error(error: str, description: str, status: int = 400) -> HTTPException:
    # RFC 6749 §5.2 error shape
    return HTTPException(status_code=status, detail={"error": error, "error_description": description})


@router.post("/oauth/token", dependencies=[Depends(rate_limit)])
async def token_exchange(
    grant_type: str = Form(...),
    subject_token: str = Form(...),
    requested_audience: str = Form(..., alias="audience"),
    subject_token_type: str = Form("urn:ietf:params:oauth:token-type:id_token"),
    subject_token_provider: str = Form("clerk"),  # extension: which IdP validates subject_token
    actor_token: str = Form(...),
    actor_token_type: str = Form(JWT_TOKEN_TYPE),
    scope: str = Form(""),
    db: AsyncSession = Depends(get_db),
):
    if grant_type != TOKEN_EXCHANGE_GRANT:
        raise _oauth_error("unsupported_grant_type", f"expected {TOKEN_EXCHANGE_GRANT}")

    # 1. Human identity from the IdP (Clerk default, or a federated OIDC provider).
    subject = get_provider(subject_token_provider).verify(subject_token)

    # 2. Agent's verification JWT (issued by us) proves it passed behavioral checks.
    issuer = get_jwt_issuer()
    try:
        actor_claims = issuer.verify_own_token(actor_token)
    except jwt.PyJWTError as e:
        raise _oauth_error("invalid_grant", f"invalid actor_token: {e}")
    owner_sub = actor_claims.get("sub")
    agent_id = (actor_claims.get("act") or {}).get("sub")
    if not owner_sub or not agent_id:
        raise _oauth_error("invalid_grant", "actor_token missing sub/act.sub")

    # 3. The human presenting must own the agent that was verified.
    if subject.subject != owner_sub:
        raise _oauth_error(
            "invalid_grant",
            "subject_token identity does not own the agent in actor_token",
            status=403,
        )

    # 4. Load the agent; confirm active and that ownership ties back to this human.
    agent = (await db.execute(select(Agent).where(Agent.id == agent_id))).scalar_one_or_none()
    if agent is None or agent.status == "revoked":
        raise _oauth_error("invalid_grant", "agent not found or revoked")
    human = (await db.execute(select(Human).where(Human.id == agent.human_id))).scalar_one()
    if human.clerk_id != owner_sub:
        raise _oauth_error("invalid_grant", "agent ownership mismatch", status=403)

    # 5. Scope: requested must be a subset of the agent's allowed scopes.
    requested = [s for s in scope.split() if s]
    allowed = set(agent.allowed_scopes or [])
    if not requested:
        raise _oauth_error("invalid_scope", "no scope requested")
    not_allowed = [s for s in requested if s not in allowed]
    if not_allowed:
        raise _oauth_error("invalid_scope", f"scopes not permitted for this agent: {not_allowed}")

    # 6. Mint the scoped, audience-bound delegated token.
    access_token = issuer.issue_delegated_token(
        subject=subject.subject,
        agent_id=str(agent.id),
        agent_name=agent.name,
        audience=requested_audience,
        scopes=requested,
    )
    return {
        "access_token": access_token,
        "issued_token_type": JWT_TOKEN_TYPE,
        "token_type": "Bearer",
        "expires_in": settings.DOWNSTREAM_TOKEN_EXPIRY_SECONDS,
        "scope": " ".join(requested),
    }

from dataclasses import dataclass

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.human import Human
from app.services.human_service import get_or_create_human

bearer_scheme = HTTPBearer(auto_error=False)

DEMO_CLERK_ID = "demo_user_001"
DEMO_NAME = "Demo User"
DEMO_EMAIL = "demo@worldofagents.dev"

_jwk_client: PyJWKClient | None = None


def _get_jwk_client() -> PyJWKClient | None:
    global _jwk_client
    if _jwk_client is not None:
        return _jwk_client
    if settings.CLERK_JWKS_URL:
        _jwk_client = PyJWKClient(settings.CLERK_JWKS_URL, cache_keys=True)
        return _jwk_client
    # derive from CLERK_SECRET_KEY — Clerk publishable keys contain the domain
    # but we need the JWKS URL. Check if CLERK_SECRET_KEY looks real.
    if settings.CLERK_SECRET_KEY and not settings.CLERK_SECRET_KEY.startswith("sk_test_xxx"):
        return None
    return None


@dataclass
class ClerkClaims:
    sub: str
    name: str
    email: str | None


def _is_dev_mode() -> bool:
    # The demo-user bypass must never be reachable in production, regardless of
    # how Clerk is configured (RFC 0007).
    if settings.is_production:
        return False
    return not settings.CLERK_SECRET_KEY or settings.CLERK_SECRET_KEY.startswith("sk_test_xxx")


def _decode_clerk_token(token: str) -> ClerkClaims:
    jwk_client = _get_jwk_client()

    if jwk_client:
        # production: verify signature against Clerk JWKS
        try:
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                options={"verify_exp": True, "verify_aud": False},
            )
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    else:
        # No JWKS available. Decoding without signature verification is only
        # acceptable in development; in production it would accept forged tokens
        # (RFC 0007).
        if settings.is_production:
            raise HTTPException(
                status_code=401,
                detail="Token verification unavailable: CLERK_JWKS_URL not configured",
            )
        # dev/test: decode without signature verification
        try:
            payload = jwt.decode(
                token,
                options={"verify_signature": False, "verify_exp": False},
                algorithms=["RS256"],
            )
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid token: {e}")

    sub = payload.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Token missing 'sub' claim")

    name = (
        payload.get("name")
        or payload.get("full_name")
        or payload.get("email", "Unknown")
    )
    email = payload.get("email")

    return ClerkClaims(sub=sub, name=name, email=email)


async def get_current_human(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> Human:
    if credentials is not None:
        claims = _decode_clerk_token(credentials.credentials)
        return await get_or_create_human(db, claims.sub, claims.name, claims.email)

    if _is_dev_mode():
        return await get_or_create_human(db, DEMO_CLERK_ID, DEMO_NAME, DEMO_EMAIL)

    raise HTTPException(status_code=401, detail="Missing authorization header")

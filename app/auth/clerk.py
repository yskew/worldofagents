from dataclasses import dataclass

import jwt
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


@dataclass
class ClerkClaims:
    sub: str
    name: str
    email: str | None


def _decode_clerk_token(token: str) -> ClerkClaims:
    try:
        payload = jwt.decode(
            token,
            options={"verify_signature": False, "verify_exp": True},
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

    # dev mode: no Clerk key configured — fall back to demo user
    if not settings.CLERK_SECRET_KEY or settings.CLERK_SECRET_KEY.startswith("sk_test_xxx"):
        return await get_or_create_human(db, DEMO_CLERK_ID, DEMO_NAME, DEMO_EMAIL)

    raise HTTPException(status_code=401, detail="Missing authorization header")

"""Human-identity provider registry for the token-exchange broker (RFC 0009).

The broker validates a `subject_token` (the human's identity) against a pluggable
provider. Clerk is always registered and is reused READ-ONLY via the existing
clerk module — this layer never modifies the Clerk auth path. External OIDC
providers (Okta, Entra, Auth0, Google) are added alongside it from config.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from app.auth.clerk import _decode_clerk_token  # read-only reuse; Clerk untouched
from app.config import settings


@dataclass
class SubjectIdentity:
    subject: str       # the human's canonical id from the IdP (the `sub` claim)
    provider: str
    email: str | None = None


class ClerkProvider:
    id = "clerk"

    def verify(self, token: str) -> SubjectIdentity:
        claims = _decode_clerk_token(token)
        return SubjectIdentity(subject=claims.sub, provider=self.id, email=claims.email)


class OIDCProvider:
    """Generic OIDC/JWKS provider for any standards-compliant IdP."""

    def __init__(self, id: str, issuer: str, jwks_url: str, audience: str | None = None):
        self.id = id
        self.issuer = issuer
        self.audience = audience
        self._jwk_client = PyJWKClient(jwks_url, cache_keys=True)

    def verify(self, token: str) -> SubjectIdentity:
        try:
            signing_key = self._jwk_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"verify_aud": self.audience is not None},
            )
        except jwt.PyJWTError as e:
            raise HTTPException(status_code=401, detail=f"Invalid subject token: {e}")
        sub = payload.get("sub")
        if not sub:
            raise HTTPException(status_code=401, detail="Subject token missing 'sub'")
        return SubjectIdentity(subject=sub, provider=self.id, email=payload.get("email"))


_registry: dict | None = None


def _build_registry() -> dict:
    registry: dict = {"clerk": ClerkProvider()}
    if settings.OIDC_PROVIDERS_JSON:
        for cfg in json.loads(settings.OIDC_PROVIDERS_JSON):
            registry[cfg["id"]] = OIDCProvider(
                cfg["id"], cfg["issuer"], cfg["jwks_url"], cfg.get("audience")
            )
    return registry


def get_provider(provider_id: str):
    global _registry
    if _registry is None:
        _registry = _build_registry()
    provider = _registry.get(provider_id)
    if provider is None:
        raise HTTPException(status_code=400, detail=f"Unknown identity provider: {provider_id}")
    return provider


def reset_registry() -> None:
    """Force a rebuild (tests / config changes)."""
    global _registry
    _registry = None

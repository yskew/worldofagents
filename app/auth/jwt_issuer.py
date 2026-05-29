from __future__ import annotations

import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from app.config import settings


class JWTIssuer:
    def __init__(self, private_key_pem: str | None = None, public_key_pem: str | None = None):
        loaded = False
        if private_key_pem and public_key_pem:
            try:
                priv = private_key_pem.replace("\\n", "\n")
                pub = public_key_pem.replace("\\n", "\n")
                self._private_key = serialization.load_pem_private_key(
                    priv.encode(), password=None
                )
                self._public_key = serialization.load_pem_public_key(pub.encode())
                loaded = True
            except Exception:
                pass
        if not loaded:
            self._private_key = rsa.generate_private_key(
                public_exponent=65537, key_size=2048
            )
            self._public_key = self._private_key.public_key()

        self._kid = self._compute_kid()

    def _compute_kid(self) -> str:
        pub_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        return hashlib.sha256(pub_bytes).hexdigest()[:16]

    def issue_token(
        self,
        human_clerk_id: str,
        agent_id: str,
        agent_name: str,
        similarity_score: float,
        expiry_seconds: int | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        exp = expiry_seconds or settings.JWT_EXPIRY_SECONDS
        payload = {
            "iss": settings.JWT_ISSUER,
            "sub": human_clerk_id,
            "act": {"sub": agent_id},
            "agent_name": agent_name,
            "similarity_score": similarity_score,
            "iat": now,
            "exp": now + timedelta(seconds=exp),
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(
            payload, self._private_key, algorithm="RS256", headers={"kid": self._kid}
        )

    def jwks(self) -> dict:
        pub_numbers = self._public_key.public_numbers()
        n_bytes = pub_numbers.n.to_bytes((pub_numbers.n.bit_length() + 7) // 8, "big")
        e_bytes = pub_numbers.e.to_bytes((pub_numbers.e.bit_length() + 7) // 8, "big")
        return {
            "keys": [
                {
                    "kty": "RSA",
                    "use": "sig",
                    "alg": "RS256",
                    "kid": self._kid,
                    "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
                    "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
                }
            ]
        }

    @property
    def public_key(self):
        return self._public_key

    @property
    def kid(self) -> str:
        return self._kid


_issuer: JWTIssuer | None = None


def get_jwt_issuer() -> JWTIssuer:
    global _issuer
    if _issuer is None:
        _issuer = JWTIssuer(
            private_key_pem=settings.RSA_PRIVATE_KEY_PEM or None,
            public_key_pem=settings.RSA_PUBLIC_KEY_PEM or None,
        )
    return _issuer

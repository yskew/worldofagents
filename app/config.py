from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://agentverify:devpassword@postgres:5432/agentverify"
    CLERK_SECRET_KEY: str = ""
    CLERK_JWKS_URL: str = ""
    RSA_PRIVATE_KEY_PEM: str = ""
    RSA_PUBLIC_KEY_PEM: str = ""
    JWT_ISSUER: str = "agentverify"
    JWT_EXPIRY_SECONDS: int = 3600
    VERIFICATION_PASS_THRESHOLD: float = 0.7
    VERIFICATION_FAIL_THRESHOLD: float = 0.4
    SIGNATURE_VECTOR_DIM: int = 256

    # RFC 0001: when True, unmeasurable ensemble metrics abstain and their weight
    # is redistributed over the metrics that did produce a value, instead of
    # voting a neutral 0.5. Enabled by default after the RFC 0003 eval showed
    # improved separation on short/tool-only trajectories and no regression on
    # full ones. Set False to restore exact legacy scoring.
    SCORE_NORMALIZATION_V2: bool = True

    # RFC 0002: when True, features_to_vector uses the hashed-band encoding
    # (stable per-tool positions, bounded transforms, full 256-dim use) instead
    # of the legacy sort-by-magnitude layout. Enabled by default after the RFC
    # 0003 eval (cosine AUC ~0.50 -> ~0.82). Existing stored vectors should be
    # re-embedded (scripts/reembed.py); /verify and /compare recompute from the
    # JSONB signature at call time, so live verification stays correct either way.
    # Set False to restore the legacy vector exactly.
    VECTOR_ENCODING_V2: bool = True

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

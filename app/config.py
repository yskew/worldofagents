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

    # Continuous mid-session attestation (RFC 0013). CUSUM over per-window
    # similarity vs the agent's baseline; accumulates (ref - similarity) and
    # alarms on sustained downward drift (model swap / hijack).
    ATTEST_ENABLED: bool = True
    ATTEST_REF_SIMILARITY: float = 0.5
    ATTEST_WARN_THRESHOLD: float = 0.3
    ATTEST_ALARM_THRESHOLD: float = 0.6

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

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

    # Shared Signals / CAEP transmitter (RFC 0011). When enabled, behavioral-risk
    # and revocation events are emitted as signed SETs for receivers (Okta/Entra/
    # Google) to consume via poll, and optionally pushed to webhook receivers.
    SSF_ENABLED: bool = True
    SSF_RECEIVER_WEBHOOKS: str = ""  # comma-separated push delivery URLs (optional)
    SSF_AUDIENCE: str = "https://receivers.worldofagents.dev"

    @property
    def ssf_receiver_webhooks_list(self) -> list[str]:
        return [u.strip() for u in self.SSF_RECEIVER_WEBHOOKS.split(",") if u.strip()]

    @property
    def async_database_url(self) -> str:
        url = self.DATABASE_URL
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url


settings = Settings()

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

    # RFC 0004: when True, the V2 aggregator uses data-fit ensemble weights
    # (LEARNED_METRIC_WEIGHTS) instead of the hand-set base weights. Default OFF:
    # the current weights were fit on synthetic eval data and overfit toward tool
    # identity (jsd/markov), down-weighting cosine/stats for negligible gain on a
    # saturated subset. Flip only after fitting on a real labeled corpus.
    USE_LEARNED_WEIGHTS: bool = False

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

# RFC 0004: ensemble weights fit by scripts/fit_weights.py (L2-regularized
# logistic regression) on the seeded eval dataset under the V2 encoding. Used by
# the V2 aggregator only when USE_LEARNED_WEIGHTS is True. Treated as a versioned
# artifact, not env-configurable; re-fit and replace when a real corpus exists.
LEARNED_METRIC_WEIGHTS = {"jsd": 0.4786, "cosine": 0.1562, "markov": 0.3523, "stats": 0.0129}

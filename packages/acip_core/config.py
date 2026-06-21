"""Centralised, env-driven settings (REQ-M1-010: secrets come from env/secret store)."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # App
    env: str = Field(default="development", alias="ACIP_ENV")
    log_level: str = Field(default="INFO", alias="ACIP_LOG_LEVEL")
    service_name: str = Field(default="acip", alias="ACIP_SERVICE_NAME")

    # Elasticsearch (data spine)
    es_host: str = Field(default="http://elasticsearch:9200", alias="ES_HOST")
    es_username: str = Field(default="elastic", alias="ES_USERNAME")
    es_password: str = Field(default="", alias="ES_PASSWORD")
    es_verify_certs: bool = Field(default=False, alias="ES_VERIFY_CERTS")

    # PostgreSQL (control plane)
    pg_host: str = Field(default="postgres", alias="PG_HOST")
    pg_port: int = Field(default=5432, alias="PG_PORT")
    pg_db: str = Field(default="acip", alias="PG_DB")
    pg_user: str = Field(default="acip", alias="PG_USER")
    pg_password: str = Field(default="", alias="PG_PASSWORD")

    # Redis (cache + queue)
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    celery_broker_url: str = Field(default="redis://redis:6379/1", alias="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://redis:6379/2", alias="CELERY_RESULT_BACKEND"
    )

    # Inference (compose-only in Phase 0)
    embeddings_url: str = Field(default="http://embeddings:80", alias="EMBEDDINGS_URL")
    reranker_url: str = Field(default="http://reranker:80", alias="RERANKER_URL")
    llm_url: str = Field(default="http://llm:8000", alias="LLM_URL")

    # Observability
    otel_endpoint: str = Field(default="", alias="OTEL_EXPORTER_OTLP_ENDPOINT")
    metrics_enabled: bool = Field(default=True, alias="METRICS_ENABLED")
    otel_enabled: bool = Field(default=True, alias="OTEL_ENABLED")  # instrument FastAPI
    otel_console: bool = Field(default=False, alias="OTEL_CONSOLE")  # print spans (dev)

    # --- Phase 1: search / index / embedding tuning ---
    es_index_prefix: str = Field(default="acip", alias="ES_INDEX_PREFIX")
    catalogue_alias: str = Field(default="acip-products", alias="CATALOGUE_ALIAS")
    embedding_model: str = Field(default="BAAI/bge-m3", alias="EMBEDDING_MODEL")
    embedding_dims: int = Field(default=1024, alias="EMBEDDING_DIMS")
    reranker_model: str = Field(default="BAAI/bge-reranker-v2-m3", alias="RERANKER_MODEL")
    rerank_enabled: bool = Field(default=False, alias="RERANK_ENABLED")
    rerank_window: int = Field(default=50, alias="RERANK_WINDOW")
    search_default_size: int = Field(default=20, alias="SEARCH_DEFAULT_SIZE")
    rrf_rank_constant: int = Field(default=60, alias="RRF_RANK_CONSTANT")
    rrf_rank_window: int = Field(default=100, alias="RRF_RANK_WINDOW")
    knn_k: int = Field(default=100, alias="KNN_K")
    knn_num_candidates: int = Field(default=200, alias="KNN_NUM_CANDIDATES")
    semantic_cache_threshold: float = Field(default=0.92, alias="SEMANTIC_CACHE_THRESHOLD")
    index_shards: int = Field(default=1, alias="INDEX_SHARDS")
    index_replicas: int = Field(default=1, alias="INDEX_REPLICAS")

    # --- Phase 2: assistant / gateway ---
    llm_model: str = Field(default="Qwen/Qwen3-0.6B", alias="LLM_MODEL")
    frontier_enabled: bool = Field(default=False, alias="FRONTIER_ENABLED")
    frontier_url: str = Field(default="", alias="FRONTIER_URL")
    frontier_model: str = Field(default="", alias="FRONTIER_MODEL")
    frontier_api_key: str = Field(default="", alias="FRONTIER_API_KEY")
    budget_default_cap: float = Field(default=1000.0, alias="BUDGET_DEFAULT_CAP")
    chat_max_tokens: int = Field(default=512, alias="CHAT_MAX_TOKENS")
    # Operator/admin plane auth — separated from tenant API keys (REQ-M11-004).
    admin_token: str = Field(default="", alias="ADMIN_TOKEN")

    # --- Phase 5: human identity & auth (platform admins / store owners) ---
    # MUST be overridden in production with a long random value. Empty disables
    # token issuance (login returns 503) — fail closed rather than sign with "".
    auth_secret: str = Field(default="", alias="AUTH_SECRET")
    access_token_ttl: int = Field(default=900, alias="ACCESS_TOKEN_TTL")          # 15 min
    refresh_token_ttl: int = Field(default=2592000, alias="REFRESH_TOKEN_TTL")    # 30 days
    signup_enabled: bool = Field(default=True, alias="SIGNUP_ENABLED")
    login_max_attempts: int = Field(default=5, alias="LOGIN_MAX_ATTEMPTS")
    login_lockout_minutes: int = Field(default=15, alias="LOGIN_LOCKOUT_MINUTES")
    trial_plan_code: str = Field(default="free", alias="TRIAL_PLAN_CODE")

    # --- Phase 7: billing / buy-plan (provider-agnostic) ---
    # 'manual' = operator confirms payment (works out of the box). Real gateways
    # (stripe/zarinpal) plug in via the webhook + provider redirect later.
    billing_provider: str = Field(default="manual", alias="BILLING_PROVIDER")
    # HMAC-SHA256 secret the payment provider signs webhook bodies with. Empty
    # rejects all webhooks (fail closed) — only the manual/admin path works then.
    billing_webhook_secret: str = Field(default="", alias="BILLING_WEBHOOK_SECRET")
    subscription_period_days: int = Field(default=30, alias="SUBSCRIPTION_PERIOD_DAYS")
    # Credit top-up pricing: how many AI credits one currency unit buys.
    topup_credits_per_unit: int = Field(default=1000, alias="TOPUP_CREDITS_PER_UNIT")
    billing_currency: str = Field(default="USD", alias="BILLING_CURRENCY")

    # --- Phase A: notifications (email) + verification + product surfaces ---
    # 'console' logs emails (dev default); 'smtp' sends via the SMTP settings.
    email_provider: str = Field(default="console", alias="EMAIL_PROVIDER")
    email_from: str = Field(default="Vitrin <no-reply@vitrin.ai>", alias="EMAIL_FROM")
    smtp_host: str = Field(default="", alias="SMTP_HOST")
    smtp_port: int = Field(default=587, alias="SMTP_PORT")
    smtp_user: str = Field(default="", alias="SMTP_USER")
    smtp_password: str = Field(default="", alias="SMTP_PASSWORD")
    smtp_starttls: bool = Field(default=True, alias="SMTP_STARTTLS")
    # Public base URL used to build links in emails (verify, reset, invite).
    app_base_url: str = Field(default="http://localhost:3000", alias="APP_BASE_URL")
    # Where contact-form messages are delivered.
    contact_inbox: str = Field(default="hello@vitrin.ai", alias="CONTACT_INBOX")
    # Require a verified email before sensitive actions (e.g. buying a plan).
    email_verification_required: bool = Field(
        default=True, alias="EMAIL_VERIFICATION_REQUIRED"
    )

    # --- Phase D: security hardening ---
    security_headers_enabled: bool = Field(default=True, alias="SECURITY_HEADERS_ENABLED")
    hsts_enabled: bool = Field(default=False, alias="HSTS_ENABLED")  # enable behind HTTPS
    # Comma-separated CORS allowlist for browser clients (web app + store widgets).
    # Empty falls back to APP_BASE_URL.
    cors_allow_origins: str = Field(default="", alias="CORS_ALLOW_ORIGINS")
    # Cookie-based auth (dual-support alongside bearer). Secure=true in production.
    cookie_secure: bool = Field(default=False, alias="COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="COOKIE_SAMESITE")
    csrf_enabled: bool = Field(default=True, alias="CSRF_ENABLED")
    # Per-IP rate limit (per minute) on unauthenticated auth endpoints.
    auth_ip_rate_per_min: int = Field(default=10, alias="AUTH_IP_RATE_PER_MIN")

    @property
    def cors_origins_list(self) -> list[str]:
        raw = self.cors_allow_origins.strip()
        if not raw:
            return [self.app_base_url]
        return [o.strip() for o in raw.split(",") if o.strip()]
    # --- Phase 4: agent actions (money-moving tools), disabled by default ---
    agent_actions_enabled: bool = Field(default=False, alias="AGENT_ACTIONS_ENABLED")

    @property
    def pg_dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_password}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


@lru_cache
def get_settings() -> Settings:
    """Process-wide singleton settings."""
    return Settings()

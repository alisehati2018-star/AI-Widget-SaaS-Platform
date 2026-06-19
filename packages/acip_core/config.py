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

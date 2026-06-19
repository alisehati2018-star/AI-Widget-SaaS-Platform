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
    es_host: str = Field(default="https://elasticsearch:9200", alias="ES_HOST")
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

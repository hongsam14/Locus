"""Centralized configuration for Locus (pydantic-settings, NFR1-Q6=A)."""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

if TYPE_CHECKING:
    from ..session.rumor_dynamics import RumorDynamicsParams


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
    )

    # --- LLM / VLM / Embedding ---
    llm_provider: str = Field(default="openai", alias="LLM_PROVIDER")
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model_name: str = Field(default="gpt-4o", alias="OPENAI_MODEL_NAME")
    openai_vlm_model_name: str = Field(default="gpt-4o", alias="OPENAI_VLM_MODEL_NAME")
    embedding_model: str = Field(default="text-embedding-3-small", alias="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=1536, ge=1, alias="EMBEDDING_DIMENSION")
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0, alias="LLM_TEMPERATURE")

    # --- Neo4j ---
    neo4j_uri: str = Field(default="bolt://localhost:7687", alias="NEO4J_URI")
    neo4j_user: str = Field(default="neo4j", alias="NEO4J_USER")
    # No hardcoded default — set NEO4J_PASSWORD in the environment / .env.
    neo4j_password: SecretStr = Field(default=SecretStr(""), alias="NEO4J_PASSWORD")

    # --- OpenSearch ---
    opensearch_url: str = Field(default="http://localhost:9200", alias="OPENSEARCH_URL")
    opensearch_index: str = Field(default="locus_search", alias="OPENSEARCH_INDEX")

    # --- Session layer (PostgreSQL) ---
    # Either set SESSION_DB_URL directly (incl. password), or set the parts below and
    # the URL is assembled. Host defaults to localhost (host-run app); use "postgres"
    # when running inside docker-compose.
    session_db_url: str | None = Field(default=None, alias="SESSION_DB_URL")
    session_db_user: str = Field(default="locus", alias="SESSION_DB_USER")
    session_db_password: SecretStr = Field(default=SecretStr(""), alias="SESSION_DB_PASSWORD")
    session_db_name: str = Field(default="locus_session", alias="SESSION_DB_NAME")
    session_db_host: str = Field(default="localhost", alias="SESSION_DB_HOST")
    session_db_port: int = Field(default=5432, alias="SESSION_DB_PORT")

    # --- Rumor dynamics (Phase 2 hardening / U-H1, FR-H4) ---
    # Deterministic tuning knobs for support decay / prune / propagation eligibility /
    # region feedback. Assembled into RumorDynamicsParams (FD-H Q3=A defaults).
    rumor_support_decay: float = Field(default=0.05, ge=0.0, alias="RUMOR_SUPPORT_DECAY")
    rumor_prune_floor: float = Field(default=0.05, ge=0.0, le=1.0, alias="RUMOR_PRUNE_FLOOR")
    rumor_min_source_support: float = Field(
        default=0.3, ge=0.0, le=1.0, alias="RUMOR_MIN_SOURCE_SUPPORT"
    )
    rumor_feedback_weight: float = Field(default=0.1, ge=0.0, alias="RUMOR_FEEDBACK_WEIGHT")
    rumor_high_support_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, alias="RUMOR_HIGH_SUPPORT_THRESHOLD"
    )
    rumor_birth_support: float = Field(default=0.2, ge=0.0, le=1.0, alias="RUMOR_BIRTH_SUPPORT")

    # --- App ---
    debug: bool = Field(default=False, alias="LOCUS_DEBUG")

    @model_validator(mode="after")
    def _assemble_session_db_url(self) -> "Settings":
        """If SESSION_DB_URL is not given explicitly, build it from the parts
        (user[:password]@host:port/name). Password is URL-encoded."""
        if not self.session_db_url:
            pw = self.session_db_password.get_secret_value()
            auth = f"{self.session_db_user}:{quote_plus(pw)}" if pw else self.session_db_user
            self.session_db_url = (
                f"postgresql+psycopg://{auth}@{self.session_db_host}:"
                f"{self.session_db_port}/{self.session_db_name}"
            )
        return self

    def rumor_dynamics_params(self) -> "RumorDynamicsParams":
        """Assemble the deterministic rumor-dynamics knobs (FR-H4 / BR-H1-15).

        Imported locally to keep ``config`` free of a session-layer import at
        module load. Returned value is passed to the session services as-is.
        """
        from ..session.rumor_dynamics import RumorDynamicsParams

        return RumorDynamicsParams(
            support_decay=self.rumor_support_decay,
            prune_floor=self.rumor_prune_floor,
            min_source_support=self.rumor_min_source_support,
            feedback_weight=self.rumor_feedback_weight,
            high_support_threshold=self.rumor_high_support_threshold,
            birth_support=self.rumor_birth_support,
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()

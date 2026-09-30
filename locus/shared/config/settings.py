"""Centralized configuration for Locus (pydantic-settings, NFR1-Q6=A)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from locus.shared.config.tuning import KnowledgeTuning, PlayTuning


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
    # region feedback. Assembled into PlayTuning (FD-H Q3=A defaults).
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
    # U4 player mode (BR-U4-8/17/18, NFR R-05): five env knobs
    play_max_move_cost: int = Field(default=5, ge=1, alias="PLAY_MAX_MOVE_COST")
    rumor_max_new_per_region_turn: int = Field(
        default=2, ge=0, alias="RUMOR_MAX_NEW_PER_REGION_TURN"
    )
    llm_max_calls_per_turn: int = Field(default=8, ge=0, alias="LLM_MAX_CALLS_PER_TURN")
    rumor_max_active_per_region: int = Field(default=20, ge=0, alias="RUMOR_MAX_ACTIVE_PER_REGION")
    turn_shutdown_timeout_s: float = Field(default=30.0, ge=0.0, alias="TURN_SHUTDOWN_TIMEOUT_S")
    # U5 NPC dialogue (BR-U5-5/9): prompt limits and the message length cap
    npc_max_facts: int = Field(default=12, ge=0, alias="NPC_MAX_FACTS")
    npc_max_rumors: int = Field(default=8, ge=0, alias="NPC_MAX_RUMORS")
    npc_max_recent_messages: int = Field(default=10, ge=0, alias="NPC_MAX_RECENT_MESSAGES")
    npc_max_message_chars: int = Field(default=500, ge=1, alias="NPC_MAX_MESSAGE_CHARS")

    # --- Localization (UX Improvement / X1) ---
    # Translate LLM-generated session content (rumors, events) and canonical
    # Knowledge to the target language for display; results are cached in the
    # session store (BR-X1-*). Reuses the existing LLMProvider (FR-UX3.3). Reads
    # are LLM-free (cache-only); misses warm in the background (review #3).
    translation_enabled: bool = Field(default=True, alias="TRANSLATION_ENABLED")
    translation_target_lang: str = Field(default="ko", alias="TRANSLATION_TARGET_LANG")
    translation_warm_workers: int = Field(default=2, ge=1, alias="TRANSLATION_WARM_WORKERS")
    # U5 (FD-U5 Q1=A): display languages a request may ask for with ?lang=. Read as a
    # plain comma-separated string — pydantic-settings would JSON-decode a tuple field,
    # so "ko,en" would fail to load (plan review R-14).
    supported_langs_raw: str = Field(default="ko,en", alias="SUPPORTED_LANGS")

    @property
    def supported_langs(self) -> tuple[str, ...]:
        langs = tuple(part.strip().lower() for part in (self.supported_langs_raw or "").split(","))
        langs = tuple(lang for lang in langs if lang)
        return langs or ("ko", "en")

    # --- Data dir (World File backups before a replace, U2 BR-U2-11) ---
    data_dir: Path = Field(default=Path("data"), alias="LOCUS_DATA_DIR")

    @property
    def backup_dir(self) -> Path:
        return self.data_dir / "backups"

    @model_validator(mode="after")
    def _default_lang_is_supported(self) -> "Settings":
        """TRANSLATION_TARGET_LANG is the default display language, so it must be one a
        request may ask for — otherwise every request without ?lang= answers 400
        (U5 FD review R-04). Fail at startup instead."""
        if self.translation_target_lang.lower() not in self.supported_langs:
            raise ValueError(
                f"TRANSLATION_TARGET_LANG={self.translation_target_lang!r} is not in "
                f"SUPPORTED_LANGS={self.supported_langs_raw!r}"
            )
        return self

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

    def knowledge_tuning(self) -> KnowledgeTuning:
        """Consensus thresholds (FR-A7). Values are the long-standing defaults."""
        return KnowledgeTuning()

    def play_tuning(self) -> PlayTuning:
        """Assemble the deterministic rumor-dynamics knobs (FR-H4 / BR-H1-15).

        ``shared`` owns the dataclass, so no play-layer import is needed here
        (FR-A2). Returned value is passed to the play services as-is.
        """
        return PlayTuning(
            support_decay=self.rumor_support_decay,
            prune_floor=self.rumor_prune_floor,
            min_source_support=self.rumor_min_source_support,
            feedback_weight=self.rumor_feedback_weight,
            high_support_threshold=self.rumor_high_support_threshold,
            birth_support=self.rumor_birth_support,
            max_move_cost=self.play_max_move_cost,
            max_new_rumors_per_region_turn=self.rumor_max_new_per_region_turn,
            max_llm_calls_per_turn=self.llm_max_calls_per_turn,
            max_active_rumors_per_region=self.rumor_max_active_per_region,
            npc_max_facts=self.npc_max_facts,
            npc_max_rumors=self.npc_max_rumors,
            npc_max_recent_messages=self.npc_max_recent_messages,
            npc_max_message_chars=self.npc_max_message_chars,
        )


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()

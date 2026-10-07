"""PostgreSQL adapter for ``TranslationStore`` (cut from the play adapter, FR-G1).

Shares the engine with the play adapter but owns its own table / MetaData.
Upserts use ``INSERT ... ON CONFLICT`` on the unique key, so the old
SAVEPOINT + IntegrityError dance is gone.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.engine import Engine

from locus.localization.models import Translation
from locus.localization.storage.schema import ensure_localization_schema, translations
from locus.shared.storage.sql import make_engine, upsert_stmt

# Max ids per IN() chunk — keeps large reads under the DB bind-parameter limit.
_IN_CHUNK = 500


class PostgresTranslationRepository:
    """SQLAlchemy-backed ``TranslationStore``. Pass ``engine`` for tests."""

    def __init__(self, url: str | None = None, *, engine: Engine | None = None) -> None:
        self._url = url
        self._engine = engine
        self._owns_engine = engine is None  # an injected (shared) engine is never disposed here

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> None:
        if self._engine is None:
            if not self._url:
                raise RuntimeError("PostgresTranslationRepository needs a url or engine")
            self._engine = make_engine(self._url)

    def disconnect(self) -> None:
        """Dispose the engine this adapter created; an injected engine belongs to
        ``SharedContainer`` and stays usable (review U1 #14)."""
        if self._engine is not None and self._owns_engine:
            self._engine.dispose()
            self._engine = None

    def ensure_schema(self) -> None:
        ensure_localization_schema(self._require_engine())

    # -- port ------------------------------------------------------------- #
    def get_many(
        self, keys: list[tuple[str, str, str]], target_lang: str
    ) -> dict[tuple[str, str], Translation]:
        if not keys:
            return {}
        wanted = set(keys)
        ids = list({sid for _, sid, _ in keys})
        out: dict[tuple[str, str], Translation] = {}
        with self._require_engine().connect() as conn:
            # Chunk the IN() so a large region stays under the DB bind-param limit
            # (SQLite 999 / PostgreSQL cap) (review #7).
            for start in range(0, len(ids), _IN_CHUNK):
                chunk = ids[start : start + _IN_CHUNK]
                rows = (
                    conn.execute(
                        select(translations).where(
                            translations.c.target_lang == target_lang,
                            translations.c.source_id.in_(chunk),
                        )
                    )
                    .mappings()
                    .all()
                )
                for r in rows:
                    key = (r["source_kind"], r["source_id"], r["source_field"])
                    if key in wanted:
                        out[(r["source_id"], r["source_field"])] = _row_to_translation(r)
        return out

    def upsert_many(self, translations_: list[Translation]) -> list[Translation]:
        """Batch upsert in one transaction; ON CONFLICT on the unique key."""
        if not translations_:
            return []
        engine = self._require_engine()
        with engine.begin() as conn:
            for t in translations_:
                conn.execute(
                    upsert_stmt(
                        engine,
                        translations,
                        _translation_to_values(t),
                        index_elements=["source_kind", "source_id", "source_field", "target_lang"],
                    )
                )
        return [t.model_copy(deep=True) for t in translations_]

    def purge(
        self,
        *,
        kind: str | None = None,
        ids: list[str] | None = None,
        world_id: str | None = None,
        session_id: str | None = None,
    ) -> int:
        """Delete cached translations matching **every** given filter; returns the
        number of rows removed. At least one filter is required so a stray call can
        never empty the cache (BR-U5-22). An empty ``ids`` list matches nothing."""
        if kind is None and ids is None and world_id is None and session_id is None:
            raise ValueError("purge needs at least one filter (kind, ids, world_id, session_id)")
        if ids is not None and not ids:
            return 0

        def _stmt(chunk: list[str] | None):
            stmt = delete(translations)
            if kind is not None:
                stmt = stmt.where(translations.c.source_kind == kind)
            if chunk is not None:
                stmt = stmt.where(translations.c.source_id.in_(chunk))
            if world_id is not None:
                stmt = stmt.where(translations.c.world_id == world_id)
            if session_id is not None:
                stmt = stmt.where(translations.c.session_id == session_id)
            return stmt

        removed = 0
        with self._require_engine().begin() as conn:
            if ids is None:
                removed = int(conn.execute(_stmt(None)).rowcount or 0)
            else:  # chunk the IN() under the bind-parameter limit (review #7)
                for start in range(0, len(ids), _IN_CHUNK):
                    res = conn.execute(_stmt(ids[start : start + _IN_CHUNK]))
                    removed += int(res.rowcount or 0)
        return removed

    def _require_engine(self) -> Engine:
        if self._engine is None:
            self.connect()
        return self._engine  # type: ignore[return-value]


def _translation_to_values(t: Translation) -> dict:
    return {
        "id": t.id,
        "source_kind": t.source_kind,
        "source_id": t.source_id,
        "source_field": t.source_field,
        "target_lang": t.target_lang,
        "text": t.text,
        "source_hash": t.source_hash,
        "world_id": t.world_id,
        "session_id": t.session_id,
    }


def _row_to_translation(row) -> Translation:
    return Translation(
        id=row["id"],
        source_kind=row["source_kind"],
        source_id=row["source_id"],
        source_field=row["source_field"],
        target_lang=row["target_lang"],
        text=row["text"],
        source_hash=row["source_hash"],
        world_id=row["world_id"],
        session_id=row["session_id"],
        created_at=row["created_at"],
    )

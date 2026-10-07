"""SQLAlchemy engine factory shared by the SQL-backed boundaries (play, localization).

Each boundary owns its own tables and ``MetaData``; they only share the engine
(one PostgreSQL database). Dialect-aware upsert lives here too so adapters do
not repeat the PostgreSQL/SQLite branching.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Table, create_engine
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.engine import Engine


def make_engine(url: str, *, echo: bool = False) -> Engine:
    """Create a sync SQLAlchemy 2.0 engine for ``url`` (postgresql+psycopg or sqlite)."""
    return create_engine(url, future=True, echo=echo)


def upsert_stmt(
    engine: Engine, table: Table, values: dict[str, Any], *, index_elements: list[str]
) -> Any:
    """``INSERT ... ON CONFLICT (index_elements) DO UPDATE SET <non-key columns>``.

    Uses the PostgreSQL dialect on PostgreSQL and the SQLite dialect elsewhere
    (offline tests run on SQLite), so a concurrent upsert of the same key can no
    longer race a select-then-insert. Primary-key columns are never part of the
    update set, so a row keeps its id across re-upserts on a secondary unique
    key (review U1 #9).
    """
    stmt: Any
    if engine.dialect.name == "postgresql":
        stmt = postgresql.insert(table).values(**values)
    else:
        stmt = sqlite.insert(table).values(**values)
    pk = {c.name for c in table.primary_key.columns}
    update_cols = {k: stmt.excluded[k] for k in values if k not in index_elements and k not in pk}
    return stmt.on_conflict_do_update(index_elements=index_elements, set_=update_cols)

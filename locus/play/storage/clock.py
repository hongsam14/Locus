"""Strictly increasing timestamps for append-only play rows (code review U4 #1).

A whole turn's timeline entries are written inside one transaction. PostgreSQL's
``CURRENT_TIMESTAMP`` is the *transaction* start time, so every row of that turn
would carry the identical value and ``ORDER BY turn, created_at`` would leave
them tied — the turn's entries came back in arbitrary order. Stamping them in
the application with a monotonic clock keeps the order they were appended in.

Single writer process (the API runs one worker, see operations.md); rows from
another process still sort by wall clock, then by id.
"""

from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone

_lock = threading.Lock()
_last: datetime | None = None
_TICK = timedelta(microseconds=1)


def next_timestamp() -> datetime:
    """UTC now, but never equal to or before the previous value from this process."""
    global _last
    with _lock:
        now = datetime.now(timezone.utc)
        if _last is not None and now <= _last:
            now = _last + _TICK
        _last = now
        return now

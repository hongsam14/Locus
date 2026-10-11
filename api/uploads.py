"""Request-body and upload limits (U3, NFR-6, nfr-light §1.1 〔Step 1.3 정정〕 §6-4).

Two layers:
- ``BodyLimitMiddleware`` caps what the server will receive at all — 48 MiB, World File
  routes 20 MiB. A ``Content-Length`` over the limit is refused at once; a body without
  one is counted as it arrives and refused when it crosses the limit. It is a plain
  ASGI middleware: ``BaseHTTPMiddleware`` would buffer the body first.
- the router checks each multipart field after receipt (Starlette has the whole form by
  then): how many files, how large each is, a memo's length, an image's format.

The limits are constants, not env (N3-3). Error bodies are fixed text: the field, the
file name and the limit — never an exception message.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, MutableMapping
from dataclasses import dataclass
from typing import Any

from fastapi import UploadFile
from fastapi.responses import JSONResponse

from api.errors import ApiError
from locus.world.ingestion.service import (
    CONCEPT_ARTS_MAX,
    MAP_IMAGES_MAX,
    MAPS_MAX,
    MEMO_CHARS,
    MEMOS_MAX,
)

MiB = 1024 * 1024
REQUEST_MAX = 48 * MiB
WORLD_FILE_MAX = 20 * MiB
# (method, path pattern) -> byte limit; the first match wins, else REQUEST_MAX
# A World File request may be the file plus multipart framing: the request limit leaves
# 1 MiB over the field limit so a full 20 MiB file gets the field's precise 413 (S20).
PATH_LIMITS: tuple[tuple[str, re.Pattern[str], int], ...] = (
    ("POST", re.compile(r"^/api/world/worlds/[^/]+/file(/upload)?/?$"), WORLD_FILE_MAX + MiB),
)


@dataclass(frozen=True)
class FieldLimit:
    count: int
    file_bytes: int
    chars: int | None = None  # decoded text length (memos)


# counts and lengths shared with the JSON build body (U3 review S19)
MEMO = FieldLimit(count=MEMOS_MAX, file_bytes=256 * 1024, chars=MEMO_CHARS)
MAP = FieldLimit(count=MAPS_MAX, file_bytes=2 * MiB)
MAP_IMAGE = FieldLimit(count=MAP_IMAGES_MAX, file_bytes=8 * MiB)
CONCEPT_ART = FieldLimit(count=CONCEPT_ARTS_MAX, file_bytes=8 * MiB)
WORLD_FILE = FieldLimit(count=1, file_bytes=WORLD_FILE_MAX)

_IMAGE_MAGIC = (
    b"\x89PNG",  # PNG
    b"\xff\xd8\xff",  # JPEG
)


def limit_for(method: str, path: str) -> int:
    for m, pattern, limit in PATH_LIMITS:
        if method == m and pattern.match(path):
            return limit
    return REQUEST_MAX


def _too_large(limit: int) -> str:
    return f"request body too large (limit {limit // MiB} MiB)"


Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class BodyLimitMiddleware:
    """Refuse request bodies over the path's limit with 413 (NFR-6)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        root = scope.get("root_path", "")
        if root and path.startswith(root):  # behind a prefix: match the app's own path (S20)
            path = path[len(root) :]
        limit = limit_for(scope.get("method", ""), path)
        length = dict(scope.get("headers") or []).get(b"content-length")
        if length is not None and length.isdigit() and int(length) > limit:
            response = JSONResponse(
                status_code=413, content={"detail": _too_large(limit), "code": "too_large"}
            )
            await response(scope, receive, send)
            return
        seen = 0

        async def counted() -> MutableMapping[str, Any]:
            nonlocal seen
            message = await receive()
            if message["type"] == "http.request":
                seen += len(message.get("body", b""))
                if seen > limit:  # FastAPI re-raises HTTPException from body parsing
                    raise ApiError(413, _too_large(limit), "too_large")
            return message

        await self.app(scope, counted, send)


# --------------------------------------------------------------------------- #
# Field checks (after receipt)
# --------------------------------------------------------------------------- #
def check_count(field: str, files: list[UploadFile], limit: FieldLimit) -> None:
    if len(files) > limit.count:
        raise ApiError(413, f"too many {field} files (limit {limit.count})", "too_large")


def read_capped(field: str, file: UploadFile, limit: FieldLimit) -> bytes:
    """The file's bytes, reading at most one byte past the limit."""
    data = file.file.read(limit.file_bytes + 1)
    if len(data) > limit.file_bytes:
        raise ApiError(
            413,
            f"{field} file {file.filename!r} is too large (limit {limit.file_bytes // 1024} KiB)",
            "too_large",
        )
    return data


def read_memo(file: UploadFile) -> str:
    text = read_capped("memos", file, MEMO).decode("utf-8", errors="replace")
    if MEMO.chars is not None and len(text) > MEMO.chars:
        raise ApiError(
            413,
            f"memos file {file.filename!r} is too long (limit {MEMO.chars} characters)",
            "too_large",
        )
    return text


def read_image(field: str, file: UploadFile, limit: FieldLimit) -> bytes:
    """An image's bytes; PNG, JPEG or WebP by their first bytes, else 422."""
    data = read_capped(field, file, limit)
    is_webp = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if not (is_webp or any(data.startswith(m) for m in _IMAGE_MAGIC)):
        raise ApiError(
            422, f"{field} file {file.filename!r} is not a PNG, JPEG or WebP", "bad_image"
        )
    return data

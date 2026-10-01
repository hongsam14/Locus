"""U3 upload limits (NFR-6, nfr-light §1.1 and §6-4/§6-5 〔Step 1.3 정정〕)."""

from __future__ import annotations

import io

from fastapi.testclient import TestClient

from api import uploads
from api.main import create_app
from locus.shared.models import BuildReport, ImportReport
from locus.world.wiring import WorldContainer
from tests.api.play_fixtures import play_container

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 32
WEBP = b"RIFF\x00\x00\x00\x00WEBPVP8 "


class _Builder:
    def __init__(self) -> None:
        self.calls: list = []

    def build(self, world_id, inputs, *, replace=True):
        self.calls.append(inputs)
        return BuildReport(world_id=world_id)


class _Importer:
    def import_(self, world_id, file, *, replace=True, force_remap=False):
        return ImportReport(world_id=world_id, format_version=1, source_world_id="w")


def _client():
    builder = _Builder()
    world = WorldContainer(
        cache=None, editors=None, exporter=None, importer=_Importer(), demo=None, builder=builder
    )
    return TestClient(create_app(world=world, play=play_container())), builder


def _files(field: str, n: int, data: bytes, name: str = "f.txt", kind: str = "text/plain"):
    return [(field, (f"{i}-{name}", io.BytesIO(data), kind)) for i in range(n)]


def test_field_counts_and_sizes() -> None:
    client, builder = _client()
    url = "/api/world/worlds/w/build/upload"
    ok = (
        _files("memos", 20, b"a note")
        + _files("images", 4, PNG, "m.png", "image/png")
        + _files("concept_arts", 8, WEBP, "c.webp", "image/webp")
    )
    assert client.post(url, files=ok).status_code == 200
    assert len(builder.calls[-1].concept_arts) == 8 and len(builder.calls[-1].map_images) == 4
    r = client.post(url, files=_files("memos", 21, b"a note"))
    assert r.status_code == 413 and "memos" in r.json()["detail"]
    big = _files("memos", 1, b"x" * (uploads.MEMO.file_bytes + 1))
    r = client.post(url, files=big)
    assert r.status_code == 413 and "too large" in r.json()["detail"]
    long_memo = _files("memos", 1, b"x" * (uploads.MEMO.chars + 1))  # type: ignore[operator]
    assert client.post(url, files=long_memo).status_code == 413


def test_images_must_be_png_jpeg_or_webp() -> None:
    client, builder = _client()
    fake = _files("images", 1, b"just some text", "map.png", "image/png")
    r = client.post("/api/world/worlds/w/build/upload", files=fake)
    assert r.status_code == 422 and "map.png" in r.json()["detail"]
    jpeg = _files("concept_arts", 1, b"\xff\xd8\xff\xe0rest", "a.jpg", "image/jpeg")
    assert client.post("/api/world/worlds/w/build/upload", files=jpeg).status_code == 200


def test_bad_map_json_is_a_fixed_text() -> None:
    """NFR R-08: no exception text in the body."""
    client, _b = _client()
    bad = _files("maps", 1, b"{not json", "m.json", "application/json")
    r = client.post("/api/world/worlds/w/build/upload", files=bad)
    assert r.status_code == 422 and r.json()["detail"] == "map '0-m.json' is not valid JSON"


def test_a_body_over_48_mib_is_refused_before_the_route() -> None:
    client, builder = _client()
    huge = _files("memos", 1, b"x" * (uploads.REQUEST_MAX + 1024))
    r = client.post("/api/world/worlds/w/build/upload", files=huge)
    assert r.status_code == 413 and "48 MiB" in r.json()["detail"]
    assert builder.calls == []


def test_a_chunked_body_without_length_is_counted() -> None:
    client, builder = _client()

    def chunks():  # U8 intended change: U3 review S20 — the request limit is 20 + 1 MiB
        for _ in range(22):
            yield b"y" * (1024 * 1024)

    r = client.post(
        "/api/world/worlds/w/file", content=chunks(), headers={"content-type": "application/json"}
    )
    assert r.status_code == 413 and "21 MiB" in r.json()["detail"]


def test_world_file_routes_have_their_own_limit() -> None:
    client, _b = _client()
    over = _files("file", 1, b"{" + b" " * (uploads.WORLD_FILE_MAX + 10) + b"}", "w.json")
    assert client.post("/api/world/worlds/w/file/upload", files=over).status_code == 413
    # U8 intended change: U3 review S20 — 1 MiB of multipart framing over the field limit
    assert (
        uploads.limit_for("POST", "/api/world/worlds/w/file")
        == uploads.WORLD_FILE_MAX + uploads.MiB
    )
    assert uploads.limit_for("POST", "/api/world/worlds/w/build/upload") == uploads.REQUEST_MAX


def test_small_requests_pass_untouched() -> None:
    client, _b = _client()
    assert client.get("/health").status_code in (200, 503)
    assert client.post("/api/play/worlds/w/sessions").status_code == 200


# --------------------------------------------------------------------------- #
# U3 code-review-01 items closed in U8 Step 9c
# --------------------------------------------------------------------------- #
def test_s20_a_full_world_file_gets_the_fields_own_413() -> None:
    """A 20 MiB file plus framing passes the request limit and meets the field's precise
    message (it used to meet the generic request 413)."""
    client, _b = _client()
    full = _files("file", 1, b"{" + b" " * (uploads.WORLD_FILE_MAX - 1) + b"}", "w.json")
    r = client.post("/api/world/worlds/w/file/upload", files=full)
    assert r.status_code == 413 and "is too large (limit 20480 KiB)" in r.json()["detail"]


def test_s20_the_limit_is_matched_without_the_root_path() -> None:
    import asyncio

    seen: list[int] = []

    async def app(scope, receive, send):
        seen.append(1)

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        seen.append(message.get("status", 0))

    mw = uploads.BodyLimitMiddleware(app)
    big = str(uploads.WORLD_FILE_MAX + 2 * uploads.MiB).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/locus/api/world/worlds/w/file",
        "root_path": "/locus",
        "headers": [(b"content-length", big)],
    }
    asyncio.run(mw(scope, receive, send))
    assert 413 in seen  # the World File limit, not the 48 MiB one


def test_s07_a_map_that_is_not_an_object_or_too_deep_is_422() -> None:
    client, _b = _client()
    for body in (b"[1, 2]", b'"a"', b"42", b"[" * 200_000):
        r = client.post("/api/world/worlds/w/build/upload", files=_files("maps", 1, body, "m.json"))
        assert r.status_code == 422 and "is not valid JSON" in r.json()["detail"]


def test_s19_the_json_build_body_has_the_multipart_caps() -> None:
    client, _b = _client()
    many = {"memos": ["a note"] * 21}
    assert client.post("/api/world/worlds/w/build", json=many).status_code == 422
    long = {"memos": ["x" * 60_001]}
    assert client.post("/api/world/worlds/w/build", json=long).status_code == 422
    assert uploads.MEMO.count == 20 and uploads.MAP_IMAGE.count == 4


def test_s27_an_undecodable_body_is_a_422_not_a_500() -> None:
    client, _b = _client()
    r = client.post(
        "/api/world/worlds/w/build",
        content=b"\xff\xfe\x00garbage",
        headers={"content-type": "text/plain"},
    )
    assert r.status_code == 422


def test_c15_open_sessions_are_checked_before_the_files_are_read() -> None:
    """A replace that needs a yes answers 409 before any file is read or checked."""
    client, builder = _client()
    assert client.post("/api/play/worlds/w/sessions").status_code == 200  # an open session
    bad = _files("images", 1, b"not an image", "map.png", "image/png")
    r = client.post("/api/world/worlds/w/build/upload", files=bad)
    assert r.status_code == 409 and r.json()["detail"]["open_sessions"] == 1
    assert builder.calls == []

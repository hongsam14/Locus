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

    def chunks():
        for _ in range(21):
            yield b"y" * (1024 * 1024)

    r = client.post(
        "/api/world/worlds/w/file", content=chunks(), headers={"content-type": "application/json"}
    )
    assert r.status_code == 413 and "20 MiB" in r.json()["detail"]


def test_world_file_routes_have_their_own_limit() -> None:
    client, _b = _client()
    over = _files("file", 1, b"{" + b" " * (uploads.WORLD_FILE_MAX + 10) + b"}", "w.json")
    assert client.post("/api/world/worlds/w/file/upload", files=over).status_code == 413
    assert uploads.limit_for("POST", "/api/world/worlds/w/file") == uploads.WORLD_FILE_MAX
    assert uploads.limit_for("POST", "/api/world/worlds/w/build/upload") == uploads.REQUEST_MAX


def test_small_requests_pass_untouched() -> None:
    client, _b = _client()
    assert client.get("/health").status_code in (200, 503)
    assert client.post("/api/play/worlds/w/sessions").status_code == 200

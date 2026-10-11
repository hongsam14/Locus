"""Every error body carries a ``code`` (V2, FR-D9, BR-V2-15, TP-V2-8).

The ordered ``ERROR_CODES`` table maps a service error to (status, code) with the
first match winning; the app's handlers give a code to a plain ``HTTPException``, a
route 404 / 405, a validation 422 and an uncaught 500; the body-limit middleware puts
one on the 413 it writes itself. ``detail`` keeps its shape throughout.
"""

from __future__ import annotations

import asyncio
import json

import pytest
from fastapi import Depends, HTTPException
from fastapi.testclient import TestClient

from api import uploads
from api.deps import display_lang
from api.errors import DEFAULT_CODES, ERROR_CODES, ApiError, code_for, http_error
from api.main import create_app
from locus.play.base import SessionClosedError
from locus.play.errors import InvalidActionError, TurnInProgressError
from locus.play.session_service import WorldNotFoundError
from locus.world.augmentation.types import AugmentationConflict, RunFinishedError
from locus.world.worldfile.schema import UnsupportedWorldFile


@pytest.mark.parametrize(("kind", "status", "code"), ERROR_CODES, ids=lambda v: str(v))
def test_each_table_row_maps_its_own_error(kind: type[Exception], status: int, code: str) -> None:
    err = http_error(kind("why"))
    assert (err.status_code, err.code, err.detail) == (status, code, "why")


def test_a_subclass_matches_before_its_base() -> None:
    assert http_error(UnsupportedWorldFile("v9")).code == "unsupported_world_file"  # ValueError
    assert http_error(InvalidActionError("x")).code == "invalid_action"  # ValueError
    assert http_error(RunFinishedError("x")).code == "run_finished"  # AugmentationConflict
    assert http_error(AugmentationConflict("x")).code == "augmentation_conflict"
    assert http_error(WorldNotFoundError("w")).code == "not_found"  # LookupError
    # every row sits above any row of a base class it inherits from
    for i, (kind, _s, _c) in enumerate(ERROR_CODES):
        for base, _s2, _c2 in ERROR_CODES[:i]:
            assert not issubclass(kind, base), f"{kind.__name__} is shadowed by {base.__name__}"


def test_an_error_the_table_does_not_name_is_raised_again() -> None:
    assert http_error(KeyError("k")).code == "not_found"  # a KeyError is a LookupError
    with pytest.raises(RuntimeError):
        http_error(RuntimeError("boom"))


def test_default_codes() -> None:
    assert code_for(409) == "conflict" and code_for(418) == "error"
    assert set(DEFAULT_CODES) >= {400, 404, 405, 409, 413, 422, 500, 503}


def _app_client() -> TestClient:
    app = create_app(assemble_missing=False)

    @app.get("/_t/number")
    def number(n: int) -> int:
        return n

    @app.get("/_t/plain")
    def plain() -> None:
        raise HTTPException(status_code=409, detail="taken", headers={"X-Why": "test"})

    @app.get("/_t/coded")
    def coded() -> None:
        raise ApiError(409, {"message": "m", "session_ids": ["s1"]}, "sessions_open")

    @app.get("/_t/service")
    def service() -> None:
        raise http_error(SessionClosedError("session is closed"))

    @app.get("/_t/turn")
    def turn() -> None:
        raise http_error(TurnInProgressError("a turn is running"))

    @app.get("/_t/lang")
    def lang(chosen: str = Depends(display_lang)) -> str:
        return chosen

    @app.get("/_t/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    return TestClient(app, raise_server_exceptions=False)


def test_handlers_add_a_code_and_keep_the_detail() -> None:
    client = _app_client()
    r = client.get("/_t/plain")
    assert r.status_code == 409 and r.json() == {"detail": "taken", "code": "conflict"}
    assert r.headers["x-why"] == "test"
    r = client.get("/_t/coded")
    assert r.json() == {
        "detail": {"message": "m", "session_ids": ["s1"]},
        "code": "sessions_open",
    }
    assert client.get("/_t/service").json() == {
        "detail": "session is closed",
        "code": "session_closed",
    }
    assert client.get("/_t/turn").json()["code"] == "turn_running"


def test_route_404_405_422_and_500_have_codes() -> None:
    client = _app_client()
    r = client.get("/api/no-such-route")
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    r = client.post("/api/capabilities")
    assert r.status_code == 405 and r.json()["code"] == "method_not_allowed"
    r = client.get("/_t/number?n=abc")
    assert r.status_code == 422 and r.json()["code"] == "validation_failed"
    assert isinstance(r.json()["detail"], list)  # the validation errors, as before
    r = client.get("/_t/boom")
    assert r.status_code == 500
    assert r.json() == {"detail": "internal error", "code": "error"}  # never the exception text


def test_a_missing_boundary_and_a_bad_lang_have_codes() -> None:
    client = _app_client()
    r = client.get("/api/world/worlds")
    assert r.status_code == 503 and r.json()["code"] == "service_unavailable"
    r = client.get("/_t/lang?lang=xx")
    assert r.status_code == 400 and r.json()["code"] == "unsupported_lang"


def test_the_body_limit_middleware_writes_its_413_with_a_code() -> None:
    sent: list[dict] = []

    async def app(scope, receive, send):  # pragma: no cover - never reached
        raise AssertionError("the route must not run")

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        sent.append(message)

    over = str(uploads.REQUEST_MAX + 1).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/api/x",
        "headers": [(b"content-length", over)],
    }
    asyncio.run(uploads.BodyLimitMiddleware(app)(scope, receive, send))
    assert sent[0]["status"] == 413
    body = json.loads(
        b"".join(m.get("body", b"") for m in sent if m["type"] == "http.response.body")
    )
    assert body["code"] == "too_large" and "48 MiB" in body["detail"]

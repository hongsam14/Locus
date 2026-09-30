"""U2 Step 13 — `locus world ...` over in-memory fakes (EX-25): export/import round trip,
demo load, list, exit codes and the open-session guard."""

from __future__ import annotations

import json

import pytest

import locus.__main__ as cli
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


class _Session:
    def __init__(self, sid: str, status: str) -> None:
        self.id, self.status = sid, status


class _Sessions:
    def __init__(self, sessions):
        self._sessions, self.closed = sessions, []

    def list_sessions(self, world_id):
        return self._sessions

    def close_session(self, sid):
        self.closed.append(sid)


@pytest.fixture
def fake_env(monkeypatch, tmp_path):
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    settings = Settings.model_construct(data_dir=tmp_path / "data")
    shared = SharedContainer(settings=settings, graph=graph, search=search)
    shared.close = lambda: None  # type: ignore[method-assign]
    monkeypatch.setattr(cli, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "assemble_shared", lambda *a, **k: shared)
    state = {"sessions": None}
    monkeypatch.setattr(cli, "_session_service", lambda s: state["sessions"])
    return graph, state, tmp_path


def test_demo_export_import_roundtrip_and_list(fake_env, capsys) -> None:
    graph, _state, tmp = fake_env
    assert cli.main(["world", "demo", "--list"]) == 0
    assert "aldermoor" in capsys.readouterr().out
    assert cli.main(["world", "demo", "--name", "aldermoor", "--world", "w"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["counts"]["regions"] == 5

    out = tmp / "w.world.json"
    assert cli.main(["world", "export", "--world", "w", "--out", str(out)]) == 0
    data = json.loads(out.read_text())
    assert data["format_version"] == 1 and data["world"]["id"] == "w"
    capsys.readouterr()  # drop the export message

    assert cli.main(["world", "import", "--world", "w2", "--file", str(out)]) == 0
    assert json.loads(capsys.readouterr().out)["remapped"] is True
    assert graph.list_world_ids() == ["w", "w2"]

    assert cli.main(["world", "list"]) == 0
    listing = capsys.readouterr().out
    assert "w\tAldermoor" in listing and "w2\tAldermoor" in listing

    # legacy alias still works
    assert cli.main(["export", "--world", "w2", "--out", str(tmp / "legacy.json")]) == 0


def test_import_exit_codes(fake_env, capsys) -> None:
    _graph, _state, tmp = fake_env
    bad = tmp / "bad.json"
    bad.write_text(json.dumps({"format_version": 7}))
    with pytest.raises(SystemExit, match="cannot read world file"):
        cli.main(["world", "import", "--world", "w", "--file", str(bad)])

    assert cli.main(["world", "demo", "--name", "aldermoor", "--world", "w"]) == 0
    capsys.readouterr()
    good = tmp / "good.json"
    assert cli.main(["world", "export", "--world", "w", "--out", str(good)]) == 0
    with pytest.raises(SystemExit, match="pass --replace"):
        cli.main(["world", "import", "--world", "w", "--file", str(good), "--no-replace"])

    # a broken reference makes the import not ok -> exit 1
    raw = json.loads(good.read_text())
    raw["npcs"].append(dict(raw["npcs"][0], id="npc-ghost", home_region_id="nowhere"))
    broken = tmp / "broken.json"
    broken.write_text(json.dumps(raw))
    assert cli.main(["world", "import", "--world", "w3", "--file", str(broken)]) == 1


def test_open_sessions_need_force(fake_env, capsys) -> None:
    _graph, state, tmp = fake_env
    assert cli.main(["world", "demo", "--name", "aldermoor", "--world", "w"]) == 0
    state["sessions"] = _Sessions([_Session("s1", "open"), _Session("s2", "closed")])
    with pytest.raises(SystemExit, match="--force"):
        cli.main(["world", "demo", "--name", "aldermoor", "--world", "w"])
    assert state["sessions"].closed == []
    capsys.readouterr()
    assert cli.main(["world", "demo", "--name", "aldermoor", "--world", "w", "--force"]) == 0
    assert state["sessions"].closed == ["s1"]
    assert json.loads(capsys.readouterr().out)["closed_session_ids"] == ["s1"]

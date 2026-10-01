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
    # U8 intended change: BR-U8-1 — the packaged demo is the manifest's (Emberleaf Isle)
    assert cli.main(["world", "demo", "--list"]) == 0
    assert "emberleaf" in capsys.readouterr().out
    assert cli.main(["world", "demo", "--name", "emberleaf", "--world", "w"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] and report["counts"]["regions"] == 12

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
    assert "w\tEmberleaf Isle" in listing and "w2\tEmberleaf Isle" in listing

    # legacy alias still works
    assert cli.main(["export", "--world", "w2", "--out", str(tmp / "legacy.json")]) == 0


def test_import_exit_codes(fake_env, capsys) -> None:
    _graph, _state, tmp = fake_env
    bad = tmp / "bad.json"
    bad.write_text(json.dumps({"format_version": 7}))
    with pytest.raises(SystemExit, match="cannot read world file"):
        cli.main(["world", "import", "--world", "w", "--file", str(bad)])

    assert cli.main(["world", "demo", "--name", "emberleaf", "--world", "w"]) == 0
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
    assert cli.main(["world", "demo", "--name", "emberleaf", "--world", "w"]) == 0
    state["sessions"] = _Sessions([_Session("s1", "open"), _Session("s2", "closed")])
    with pytest.raises(SystemExit, match="--force"):
        cli.main(["world", "demo", "--name", "emberleaf", "--world", "w"])
    assert state["sessions"].closed == []
    capsys.readouterr()
    assert cli.main(["world", "demo", "--name", "emberleaf", "--world", "w", "--force"]) == 0
    assert state["sessions"].closed == ["s1"]
    assert json.loads(capsys.readouterr().out)["closed_session_ids"] == ["s1"]


def test_u7_review_3_the_cli_builder_uses_the_world_tuning(monkeypatch) -> None:
    """BR-U7-19: `locus world build` reads the same env knobs as the API build."""
    monkeypatch.setenv("TOPOLOGY_BASE_WEIGHTS", '{"route": 0.35}')
    monkeypatch.setenv("ONTOLOGY_DEDUP_THRESHOLD", "0.95")
    settings = Settings(_env_file=None)  # type: ignore[call-arg]

    class Factory:
        def llm(self):
            return None

        def vlm(self):
            return None

        def embedding(self):
            return None

    shared = SharedContainer(
        settings=settings,
        graph=InMemoryGraphRepository(),
        search=InMemorySearchRepository(),
        factory=Factory(),  # type: ignore[arg-type]
    )
    _exporter, _importer, _demo, builder = cli._world_services(shared, settings, with_builder=True)
    assert builder is not None
    assert builder._topology_factory(None)._tuning.base_weights["route"] == 0.35
    assert builder._ontology_factory(None, None, None)._dedup_threshold == 0.95


def test_build_reads_a_named_demo_s_sources_and_the_alias_takes_the_first() -> None:
    """U8 (BR-U8-1·4): `world build --demo <name>` reads the manifest; the one-cycle
    alias `build-world --demo` takes the first demo with sources; no name in code."""
    import argparse

    assert cli._demo_name(argparse.Namespace(demo="emberleaf")) == "emberleaf"
    assert cli._demo_name(argparse.Namespace(demo=None, demo_alias=True)) == "emberleaf"
    assert cli._demo_name(argparse.Namespace(demo=None, demo_alias=False)) is None
    inputs = cli._load_inputs(None, "emberleaf")
    assert inputs.name == "Emberleaf Isle" and inputs.memos
    with pytest.raises(SystemExit, match="demo world not found"):
        cli._load_inputs(None, "nope")

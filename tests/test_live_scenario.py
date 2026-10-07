"""U8 Step 15 (BR-U8-36): the live scenario script, without a running stack.

Two ways in:
- the real API assembled in-process without an LLM key (the TP-U8-8 assembly) behind a
  TestClient adapter: every route and payload shape the script uses, end to end;
- a small scripted server for the LLM path: verdicts, SKIP reasons and exit codes.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app
from locus.knowledge.wiring import assemble_knowledge
from locus.play import InMemoryPlayRepository
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import assemble_play
from locus.shared.config import Settings
from locus.shared.wiring import SharedContainer
from locus.world.wiring import assemble_world
from tests.api.test_keyless_api import _keyless
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("live_scenario", ROOT / "scripts/live_scenario.py")
assert _spec and _spec.loader
live = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(live)
PASS, FAIL, SKIP = live.PASS, live.FAIL, live.SKIP


class _TestClientHttp:
    def __init__(self, client) -> None:
        self.client = client

    def call(self, method, path, body=None):
        res = self.client.request(method, path, json=body)
        try:
            return res.status_code, res.json()
        except ValueError:
            return res.status_code, res.text


def _verdicts(scenario) -> dict[str, str]:
    return {key: verdict for key, verdict, _ in scenario.results}


@pytest.mark.parametrize("world", ["emberleaf", "emberleaf-live"])
def test_a_keyless_run_against_the_real_api(world) -> None:
    """Another world id remaps every id: the script finds regions by name."""
    client, _play = _keyless()
    lines: list[str] = []
    scenario = live.Scenario(_TestClientHttp(client), world, sleep=lambda s: None, out=lines.append)
    assert scenario.run() == 0, "\n".join(lines)
    assert _verdicts(scenario) == {
        "1": PASS,
        "2": PASS,
        "3": PASS,
        "4": PASS,
        "5": SKIP,
        "6": SKIP,
        "6a": SKIP,
        "7": PASS,
        "8": PASS,
        "9": SKIP,
        "9a": PASS,
        "10a": PASS,
        "10b": SKIP,
        "11": SKIP,
        "12": PASS,
    }
    reasons = {k: d for k, v, d in scenario.results if v == SKIP}
    assert "no LLM key" in reasons["5"] and "no deed was declared" in reasons["9"]
    assert lines[-1].strip() == "9 passed, 0 failed, 6 skipped"


class _WorldLLM:
    """A provider for the whole play path: lines for the NPCs, a narration, rumor drafts,
    and an appraisal that finds every deed in its prompt worth telling (salience 0.9)."""

    def complete(self, prompt, *, system=None):
        return "Folk say the mushroom fields are sick."

    def structured(self, prompt, schema, *, system=None):
        name = schema.__name__
        if name == "AppraisalDraft":
            refs = dict.fromkeys(re.findall(r"^- (d\d+) \[", prompt, re.MULTILINE))
            items = [
                {
                    "ref": r,
                    "noteworthy": True,
                    "salience": 0.9,
                    "retelling": "The traveler burned the granary.",
                }
                for r in refs
            ]
            return schema.model_validate(
                {"summary": "asked about the granary", "appraisals": items}
            )
        if name == "NarrationDraft":
            return schema(narration="The granary burns.", record="The traveler burned the granary.")
        if name == "RumorDraft":
            return schema(statement="They say the fields are cursed.")
        return schema.model_validate({})


def test_with_an_llm_the_real_api_passes_every_step_including_the_spread() -> None:
    """U8 review #3: the deed is judged when the talk ends (BR-U6-7), seeds in the meadow,
    hops to the harbor and the grove one turn later and is not in Ironcrag two turns on."""
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    shared = SharedContainer(settings=Settings(), graph=graph, search=search, llm=_WorldLLM())
    knowledge = assemble_knowledge(shared)
    world = assemble_world(shared, knowledge)
    play = assemble_play(
        shared, knowledge, repo=InMemoryPlayRepository(), executor=SyncTurnExecutor()
    )
    client = TestClient(create_app(shared=shared, world=world, play=play))
    lines: list[str] = []
    scenario = live.Scenario(
        _TestClientHttp(client), "emberleaf", sleep=lambda s: None, out=lines.append
    )
    assert scenario.run() == 0, "\n".join(lines)
    assert set(_verdicts(scenario).values()) == {PASS}, "\n".join(lines)
    assert scenario.deed_turn == 3 and scenario.seeded


# --------------------------------------------------------------------------- #
# A scripted server for the LLM path
# --------------------------------------------------------------------------- #
NAMES = ["Saltwake Harbor", "Ambermeadow", "Sylvarch", "Ironcrag", "Gutterlight"]
NAMES += [f"Filler {i}" for i in range(7)]  # twelve regions
ID = {name: f"r{i}" for i, name in enumerate(NAMES)}
H, M, G, C, L = (ID[n] for n in NAMES[:5])


class _Server:
    def __init__(
        self, *, llm=True, seeded=True, health="ok", adjacency=None, run="done", worthy=True
    ):
        self.llm, self.seeded, self.health, self.run_status = llm, seeded, health, run
        self.worthy = worthy  # the witness's judgement at end_talk
        self.adjacency = adjacency or {M: [H, G], H: [L], L: [C]}
        self.turn, self.here = 0, H
        self.reached: dict[str, int] = {}  # region -> turn the deed rumor got there
        self.deeds: list[dict] = []
        self.events: dict[str, int] = {}
        self.runs: dict[str, dict] = {}
        self.judged = False

    def _tick(self) -> None:
        self.turn += 1
        for region, at in list(self.reached.items()):
            if at < self.turn:
                for nxt in self.adjacency.get(region, []):
                    self.reached.setdefault(nxt, self.turn)

    def call(self, method, path, body=None):  # noqa: C901 — one route table
        p = path.split("?")[0]
        if p == "/health":
            return (200 if self.health == "ok" else 503), {"status": self.health}
        if p == "/api/capabilities":
            return 200, {"llm": self.llm, "vlm": self.llm, "embedding": self.llm}
        if p == "/api/world/demos":
            return 200, [{"name": "emberleaf"}]
        if re.fullmatch(r"/api/world/worlds/\w+/demo/emberleaf", p):
            return 200, {"ok": True, "warnings": []}
        if re.fullmatch(r"/api/world/worlds/\w+/export", p):
            return 200, {"regions": [{"id": ID[n], "name": n} for n in NAMES]}
        if re.fullmatch(r"/api/play/worlds/\w+/sessions", p):
            return 201, {"session": {"id": "s1"}}
        if p == "/api/play/sessions/s1":
            return 200, {"id": "s1", "turn": self.turn}
        if p == "/api/play/sessions/s1/region":
            name = next(n for n, i in ID.items() if i == self.here)
            npcs = [{"id": f"npc-{self.here}", "name": f"Npc of {name}"}]
            return 200, {
                "region_id": self.here,
                "region_name": name,
                "turn": self.turn,
                "npcs": npcs,
            }
        if p == "/api/play/sessions/s1/act":
            return self._act(body)
        if m := re.fullmatch(r"/api/play/sessions/s1/turn-runs/(\w+)", p):
            return 200, self.runs[m.group(1)]
        if re.fullmatch(r"/api/play/sessions/s1/npcs/[\w-]+/start", p):
            return (
                (200, {"messages": []}) if self.llm else (503, {"detail": "needs an LLM provider"})
            )
        if re.fullmatch(r"/api/play/sessions/s1/npcs/[\w-]+/say", p):
            return 200, {"message": {"text": "Folk whisper about the fields."}}
        if p == "/api/gm/sessions/s1/deeds":
            appraisals = [{"noteworthy": self.worthy, "salience": 0.9 if self.worthy else 0.2}]
            return 200, [
                {"deed": d, "appraisals": appraisals if self.judged else []} for d in self.deeds
            ]
        if m := re.fullmatch(r"/api/gm/sessions/s1/regions/(\w+)/rumors", p):
            deed = self.deeds[-1]["id"] if self.deeds else None
            rumor = {"origin_kind": "deed", "origin_deed_id": deed}
            return 200, [rumor] if m.group(1) in self.reached else []
        if p == "/api/gm/sessions/s1/seeds":
            return 200, [{"seed": {"id": "seed-blight", "region_id": M, "title": "Blight"}}]
        if p == "/api/gm/sessions/s1/seeds/seed-blight/start":
            self.events[M] = 1
            return 201, {"status": "active", "category": "plague", "magnitude": 0.5}
        if p == "/api/gm/sessions/s1/state":
            dist = {H: 0.6, C: 0.35}
            regions = [
                {
                    "region_name": n,
                    "distortion": dist.get(ID[n], 0.3),
                    "active_rumors": 1 if ID[n] in self.reached else 0,
                    "active_events": self.events.get(ID[n], 0),
                }
                for n in NAMES
            ]
            return 200, {"regions": regions}
        return 404, {"detail": f"no route {method} {p}"}

    def _act(self, body):
        run_id = f"run{len(self.runs)}"
        result: dict = {}
        if body["type"] == "move":
            self.here = body["to_region_id"]
            self._tick()
        elif body["type"] == "declare":  # narrated now, judged when a talk ends
            self._tick()
            self.deeds.append({"id": "deed-1", "kind": "declared_action"})
            result["declaration"] = {"text": "The granary burns."}
        elif body["type"] == "end_talk":
            self._tick()
            self.judged = True
            if self.seeded and self.deeds:
                self.reached[self.here] = self.turn
        else:
            self._tick()
        self.runs[run_id] = {
            "id": run_id,
            "status": self.run_status,
            "result": result,
            "error": "x",
        }
        return 202, {"id": run_id, "status": "running"}


def _run(server, **kw):
    lines: list[str] = []
    scenario = live.Scenario(server, sleep=lambda s: None, out=lines.append, **kw)
    return scenario.run(), _verdicts(scenario), scenario, lines


def test_with_an_llm_every_step_passes() -> None:
    code, verdicts, scenario, lines = _run(_Server())
    assert code == 0 and set(verdicts.values()) == {PASS}, "\n".join(lines)
    assert scenario.deed_turn == 3 and scenario.seeded  # judged at the end_talk turn


def test_a_deed_judged_not_worth_telling_skips_the_spread_steps() -> None:
    code, verdicts, scenario, _lines = _run(_Server(seeded=False, worthy=False))
    assert code == 0
    assert verdicts["6"] == PASS and verdicts["6a"] == PASS
    assert verdicts["9"] == SKIP and verdicts["11"] == SKIP
    reason = {k: d for k, _v, d in scenario.results}["9"]
    assert "worth telling" in reason


def test_a_noteworthy_judgement_with_no_rumor_is_a_fail() -> None:
    """U8 review #3: a broken seeding is a FAIL, not a SKIP."""
    code, verdicts, scenario, _lines = _run(_Server(seeded=False, worthy=True))
    assert code == 1 and verdicts["6a"] == FAIL
    assert "noteworthy" in {k: d for k, _v, d in scenario.results}["6a"]


def test_a_rumor_that_spreads_too_fast_fails_the_hop_steps() -> None:
    fast = {M: [H, G, C], H: [L]}  # Ironcrag one hop from the meadow
    code, verdicts, _s, _l = _run(_Server(adjacency=fast))
    assert code == 1 and verdicts["9"] == FAIL and verdicts["11"] == FAIL


def test_a_down_stack_fails_step_one_and_skips_the_rest() -> None:
    code, verdicts, scenario, lines = _run(_Server(health="unavailable"))
    assert code == 1 and verdicts["1"] == FAIL
    assert all(v == SKIP for k, v in verdicts.items() if k != "1")
    assert "step 1 failed" in scenario.results[1][2]
    assert lines[-1].strip() == "0 passed, 1 failed, 14 skipped"


def test_a_refused_connection_is_a_fail_not_a_crash() -> None:
    class _Down:
        def call(self, method, path, body=None):
            raise ConnectionRefusedError("connection refused")

    code, verdicts, scenario, _l = _run(_Down())
    assert code == 1 and verdicts["1"] == FAIL
    assert "ConnectionRefusedError" in scenario.results[0][2]


def test_a_failed_run_and_a_run_that_never_ends_are_fails() -> None:
    code, verdicts, scenario, _l = _run(_Server(run="failed"))
    assert code == 1 and verdicts["4"] == FAIL and "failed" in scenario.results[3][2]

    server = _Server(run="running")
    code, verdicts, scenario, _l = _run(server, poll_s=10, run_timeout_s=30)
    assert code == 1 and verdicts["4"] == FAIL
    assert "still running after 30s" in scenario.results[3][2]


def test_main_parses_its_options(monkeypatch) -> None:
    seen = {}

    def fake_run(self):
        seen.update(base=self.http.base, world=self.world, poll=self.poll_s)
        return 0

    monkeypatch.setattr(live.Scenario, "run", fake_run)
    assert live.main(["--base", "http://h:9/", "--world", "w2", "--poll", "0.5"]) == 0
    assert seen == {"base": "http://h:9", "world": "w2", "poll": 0.5}


def test_the_far_check_is_made_two_turns_after_the_judgement_or_fails() -> None:
    class _SlowWait(_Server):
        def _act(self, body):
            if body["type"] == "wait":
                self._tick()  # a wait that spends two turns
            return super()._act(body)

    code, verdicts, scenario, _l = _run(_SlowWait())
    assert code == 1 and verdicts["11"] == FAIL
    assert "not at T5" in {k: d for k, _v, d in scenario.results}["11"]

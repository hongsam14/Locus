#!/usr/bin/env python3
"""Live scenario against a running Locus stack (U8 BLM §7, BR-U8-36).

Walks the Emberleaf demo in the order the player can: load the demo, start a session at the
harbor, move to the meadow, talk, declare a deed, end the talk (the witness judges the deeds
then — BR-U6-7), start the blight seed, walk back to the harbor, wait, and read what each
region heard. Far regions are read through the GM routes.
Every step prints PASS, FAIL or SKIP; without an LLM key the LLM steps are SKIP with the
reason. Any FAIL makes the exit code 1.

Standard library only; not part of CI (it needs the stack: `docker compose --profile service
up -d --build`). It REPLACES the target world (closing its open sessions).

    python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from typing import Any

PASS, FAIL, SKIP = "PASS", "FAIL", "SKIP"
DEMO = "emberleaf"
# names, not ids: a world id other than the demo's own remaps every id (BR-U2-6)
HARBOR, MEADOW, GROVE, CRAG, LANES = (
    "Saltwake Harbor",
    "Ambermeadow",
    "Sylvarch",
    "Ironcrag",
    "Gutterlight",
)
SEED_REGION = MEADOW  # the mushroom-blight seed
SEED_MIN_SALIENCE = 0.5  # DEED_SEED_MIN_SALIENCE's default: a noteworthy judgement seeds
DECLARATION = (
    "In the middle of the market I set the old mushroom granary on fire and shout that the "
    "blight is a curse sent from Sylvarch."
)
GATES = ("1", "2", "3")  # without these nothing after them can run


class StepFailed(Exception):
    """The step's check did not hold."""


class StepSkipped(Exception):
    """The step cannot run here (no LLM key, nothing seeded); the reason is the message."""


class Http:
    """A tiny JSON client over urllib: ``call`` returns (status, parsed body)."""

    def __init__(self, base: str, timeout: float = 200.0) -> None:
        self.base = base.rstrip("/")
        self.timeout = timeout

    def call(self, method: str, path: str, body: Any = None) -> tuple[int, Any]:
        data = None if body is None else json.dumps(body).encode()
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as res:
                return res.status, _parse(res.read())
        except urllib.error.HTTPError as err:
            return err.code, _parse(err.read())


def _parse(raw: bytes) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except ValueError:
        return raw.decode(errors="replace")


class Scenario:
    def __init__(
        self,
        http: Any,
        world: str = DEMO,
        *,
        sleep: Callable[[float], None] = time.sleep,
        poll_s: float = 1.0,
        run_timeout_s: float = 300.0,
        out: Callable[[str], None] = print,
    ) -> None:
        self.http = http
        self.world = world
        self.sleep = sleep
        self.poll_s = poll_s
        self.run_timeout_s = run_timeout_s
        self.out = out
        self.results: list[tuple[str, str, str]] = []
        self.llm = False
        self.ids: dict[str, str] = {}
        self.sid = ""
        self.deed_id: str | None = None
        self.deed_turn: int | None = None  # the turn the deeds were judged (and seeded)
        self.seeded = False

    # -- plumbing ----------------------------------------------------------- #
    def _ok(self, method: str, path: str, body: Any = None, *, want: tuple[int, ...] = (200,)):
        status, data = self.http.call(method, path, body)
        if status not in want:
            raise StepFailed(f"{method} {path} -> {status}: {_short(data)}")
        return data

    def _turn(self) -> int:
        return int(self._ok("GET", f"/api/play/sessions/{self.sid}")["turn"])

    def _act(self, action: dict) -> dict:
        """Start an action and wait for its run; the finished run."""
        run = self._ok("POST", f"/api/play/sessions/{self.sid}/act", action, want=(202,))
        waited = 0.0
        while run.get("status") == "running":
            if waited >= self.run_timeout_s:
                raise StepFailed(f"run {run['id']} still running after {self.run_timeout_s:.0f}s")
            self.sleep(self.poll_s)
            waited += self.poll_s
            run = self._ok("GET", f"/api/play/sessions/{self.sid}/turn-runs/{run['id']}")
        if run.get("status") != "done":
            raise StepFailed(f"run {run.get('id')} {run.get('status')}: {run.get('error')}")
        return run

    def _region_here(self) -> dict:
        return self._ok("GET", f"/api/play/sessions/{self.sid}/region")

    def _rumors(self, name: str) -> list[dict]:
        rid = self.ids[name]
        return self._ok("GET", f"/api/gm/sessions/{self.sid}/regions/{rid}/rumors")

    def _deed_rumors(self, name: str) -> list[dict]:
        """The region's rumors born of the player's deeds. Any deed counts: the arrival in
        the meadow is judged with the declaration and may take the meadow's one hop of a
        turn first (U8 review #3); either way a deed rumor travels one hop per turn."""
        return [r for r in self._rumors(name) if r.get("origin_kind") == "deed"]

    def _state(self) -> dict[str, dict]:
        state = self._ok("GET", f"/api/gm/sessions/{self.sid}/state")
        return {r["region_name"]: r for r in state["regions"]}

    def _need_llm(self, what: str) -> None:
        if not self.llm:
            raise StepSkipped(f"no LLM key on the server ({what} needs one)")

    def _talk(self, line: str) -> str:
        npcs = self._region_here().get("npcs") or []
        if not npcs:
            raise StepFailed("no NPC in the player's region")
        npc = npcs[0]
        self._ok("POST", f"/api/play/sessions/{self.sid}/npcs/{npc['id']}/start")
        reply = self._ok(
            "POST", f"/api/play/sessions/{self.sid}/npcs/{npc['id']}/say", {"text": line}
        )
        text = ((reply or {}).get("message") or {}).get("text", "")
        if not text.strip():
            raise StepFailed(f"{npc['name']} answered nothing")
        return f"{npc['name']}: {_short(text, 80)}"

    # -- the steps (BLM §7) ------------------------------------------------- #
    def s1_up(self) -> str:
        health = self._ok("GET", "/health")
        if (health or {}).get("status") != "ok":
            raise StepFailed(f"/health is {_short(health)}")
        caps = self._ok("GET", "/api/capabilities")
        self.llm = bool(caps.get("llm"))
        return f"health ok; capabilities {caps}"

    def s2_demo(self) -> str:
        demos = self._ok("GET", "/api/world/demos")
        if DEMO not in [d.get("name") for d in demos]:
            raise StepFailed(f"no {DEMO!r} in /demos")
        q = urllib.parse.urlencode({"replace": "true", "confirm": "true"})
        report = self._ok("POST", f"/api/world/worlds/{self.world}/demo/{DEMO}?{q}")
        if not report.get("ok"):
            raise StepFailed(f"load not ok: {_short(report.get('warnings'))}")
        world = self._ok("GET", f"/api/world/worlds/{self.world}/export")
        self.ids = {r["name"]: r["id"] for r in world["regions"]}
        if len(world["regions"]) != 12:
            raise StepFailed(f"{len(world['regions'])} regions, not 12")
        missing = [n for n in (HARBOR, MEADOW, GROVE, CRAG, LANES) if n not in self.ids]
        if missing:
            raise StepFailed(f"regions missing: {missing}")
        return "loaded with no LLM call, 12 regions"

    def s3_session(self) -> str:
        body = {"name": "Live", "start_region_id": self.ids[HARBOR]}
        out = self._ok("POST", f"/api/play/worlds/{self.world}/sessions", body, want=(201,))
        self.sid = out["session"]["id"]
        here = self._region_here()
        if here["region_id"] != self.ids[HARBOR] or here["turn"] != 0:
            raise StepFailed(f"started in {here['region_name']} at T{here['turn']}")
        return f"session {self.sid} at {HARBOR}, T0"

    def _move(self, name: str) -> str:
        before = self._turn()
        self._act({"type": "move", "to_region_id": self.ids[name]})
        here, turn = self._region_here(), self._turn()
        if here["region_id"] != self.ids[name] or turn != before + 1:
            raise StepFailed(f"in {here['region_name']} at T{turn} (wanted {name}, T{before + 1})")
        return f"moved to {name}, T{turn}"

    def s4_move(self) -> str:
        return self._move(MEADOW)

    def s5_talk(self) -> str:
        self._need_llm("NPC dialogue")
        return self._talk("What is happening in the fields these days?")

    def s6_declare(self) -> str:
        self._need_llm("the GM's narration and the witnesses' appraisal")
        run = self._act({"type": "declare", "text": DECLARATION})
        if not ((run.get("result") or {}).get("declaration")):
            raise StepFailed("the run carries no narration")
        deeds = self._ok("GET", f"/api/gm/sessions/{self.sid}/deeds")
        declared = [d["deed"] for d in deeds if d["deed"].get("kind") == "declared_action"]
        if not declared:
            raise StepFailed("no declared deed was recorded")
        self.deed_id = declared[-1]["id"]
        return f"deed {self.deed_id} at T{self._turn()} (judged when the talk ends)"

    def s6a_end_talk(self) -> str:
        """The witness judges the deeds it saw when the talk ends (BR-U6-7): a noteworthy
        judgement seeds a deed rumor in the meadow at that turn (U8 review #3)."""
        self._need_llm("the witness's appraisal")
        if self.deed_id is None:
            raise StepSkipped("no deed was declared (step 6 did not run)")
        npc = (self._region_here().get("npcs") or [None])[0]
        if npc is None:
            raise StepFailed("no NPC in the player's region")
        self._ok("POST", f"/api/play/sessions/{self.sid}/npcs/{npc['id']}/start")
        line = {"text": "Did you see what I just did at the granary?"}
        self._ok("POST", f"/api/play/sessions/{self.sid}/npcs/{npc['id']}/say", line)
        self._act({"type": "end_talk", "npc_id": npc["id"]})
        self.deed_turn = self._turn()
        deeds = self._ok("GET", f"/api/gm/sessions/{self.sid}/deeds")
        judged = [a for d in deeds for a in d.get("appraisals") or []]
        worthy = [
            a for a in judged if a.get("noteworthy") and a.get("salience", 0) >= SEED_MIN_SALIENCE
        ]
        self.seeded = bool(self._deed_rumors(MEADOW))
        if worthy and not self.seeded:
            raise StepFailed(f"{len(worthy)} noteworthy judgement(s) but no deed rumor in {MEADOW}")
        if not self.seeded:
            return f"T{self.deed_turn}: {len(judged)} judgement(s), none worth telling — nothing to spread"
        return f"T{self.deed_turn}: {len(worthy)} noteworthy judgement(s), seeded in {MEADOW}"

    def s7_seed(self) -> str:
        before = self._turn()
        seeds = self._ok("GET", f"/api/gm/sessions/{self.sid}/seeds")
        mine = [s for s in seeds if s["seed"]["region_id"] == self.ids[SEED_REGION]]
        if not mine:
            raise StepFailed(f"no seed in {SEED_REGION}")
        seed = mine[0]["seed"]
        path = f"/api/gm/sessions/{self.sid}/seeds/{seed['id']}/start"
        event = self._ok("POST", path, want=(201,))
        if event.get("status") != "active" or self._turn() != before:
            raise StepFailed(f"event {event.get('status')}, turn {self._turn()} (was {before})")
        return f"{seed['title']}: ACTIVE {event['category']} {event['magnitude']}, no turn spent"

    def s8_move_back(self) -> str:
        return self._move(HARBOR)

    def s9_one_hop(self) -> str:
        self._need_deed()
        heard = {n: bool(self._deed_rumors(n)) for n in (HARBOR, GROVE, CRAG, LANES)}
        if not (heard[HARBOR] and heard[GROVE]) or heard[CRAG] or heard[LANES]:
            raise StepFailed(f"deed rumor by region: {heard}")
        return f"one hop at T{self._turn()}: {heard}"

    def s9a_wait(self) -> str:
        before = self._turn()
        self._act({"type": "wait"})
        if self._turn() != before + 1:
            raise StepFailed(f"T{self._turn()} after a wait from T{before}")
        return f"T{before + 1}"

    def s10a_heard_differently(self) -> str:
        state = self._state()
        near, far = state[HARBOR], state[CRAG]
        if near["distortion"] == far["distortion"]:
            raise StepFailed(f"same distortion {near['distortion']} at {HARBOR} and {CRAG}")
        return (
            f"{HARBOR}: distortion {near['distortion']:.2f}, rumors {near['active_rumors']}; "
            f"{CRAG}: distortion {far['distortion']:.2f}, rumors {far['active_rumors']}"
        )

    def s10b_ask_about_blight(self) -> str:
        self._need_llm("NPC dialogue")
        return self._talk("Have you heard anything about the blight in Ambermeadow?")

    def s11_not_yet_far(self) -> str:
        self._need_deed()
        turn = self._turn()
        # the claim is about T+2 (one hop a turn: Ironcrag is three away); first be there
        if self.deed_turn is not None and turn != self.deed_turn + 2:
            raise StepFailed(f"checked at T{turn}, not at T{self.deed_turn + 2}")
        if self._deed_rumors(CRAG):
            raise StepFailed(f"a deed rumor reached {CRAG} by T{turn}")
        return f"not in {CRAG} at T{turn} (deed at T{self.deed_turn})"

    def s12_world_state(self) -> str:
        state = self._state()
        if state[SEED_REGION]["active_events"] < 1:
            raise StepFailed(f"no active event in {SEED_REGION}")
        busy = {n: (r["active_events"], r["active_rumors"]) for n, r in state.items()}
        return f"(events, rumors) by region: {busy}"

    def _need_deed(self) -> None:
        if self.deed_id is None:
            raise StepSkipped("no deed was declared (step 6 did not run)")
        if not self.seeded:
            raise StepSkipped("no deed was judged worth telling (LLM appraisal), so none spreads")

    STEPS: tuple[tuple[str, str, str], ...] = (
        ("1", "기동", "s1_up"),
        ("2", "데모", "s2_demo"),
        ("3", "세션", "s3_session"),
        ("4", "이동", "s4_move"),
        ("5", "대화", "s5_talk"),
        ("6", "선언", "s6_declare"),
        ("6a", "대화 마침(판단)", "s6a_end_talk"),
        ("7", "씨앗", "s7_seed"),
        ("8", "이동", "s8_move_back"),
        ("9", "행적 1칸", "s9_one_hop"),
        ("9a", "기다리기", "s9a_wait"),
        ("10a", "다르게 듣기(왜곡도)", "s10a_heard_differently"),
        ("10b", "다르게 듣기(대화)", "s10b_ask_about_blight"),
        ("11", "행적 3칸 전", "s11_not_yet_far"),
        ("12", "세계 상태", "s12_world_state"),
    )

    def run(self) -> int:
        stopped: str | None = None
        for key, title, method in self.STEPS:
            if stopped:
                verdict, detail = SKIP, f"step {stopped} failed"
            else:
                try:
                    verdict, detail = PASS, getattr(self, method)()
                except StepSkipped as skip:
                    verdict, detail = SKIP, str(skip)
                except StepFailed as fail:
                    verdict, detail = FAIL, str(fail)
                except (OSError, KeyError, TypeError, ValueError) as err:  # down, bad shape
                    verdict, detail = FAIL, f"{type(err).__name__}: {err}"
                if verdict == FAIL and key in GATES:
                    stopped = key
            self.results.append((key, verdict, detail))
            self.out(f"{verdict:<4}  {key:<3} {title} — {detail}")
        failed = sum(v == FAIL for _, v, _ in self.results)
        skipped = sum(v == SKIP for _, v, _ in self.results)
        passed = len(self.results) - failed - skipped
        self.out(f"\n{passed} passed, {failed} failed, {skipped} skipped")
        return 1 if failed else 0


def _short(value: Any, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text if len(text) <= limit else text[: limit - 1] + "…"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base", default="http://localhost:8000", help="the API's base URL")
    parser.add_argument("--world", default=DEMO, help="world id to load the demo into (replaced)")
    parser.add_argument("--poll", type=float, default=1.0, help="seconds between run polls")
    parser.add_argument("--timeout", type=float, default=300.0, help="seconds one run may take")
    args = parser.parse_args(argv)
    print(f"Locus live scenario: {args.base}, world {args.world!r} (it is replaced)\n")
    scenario = Scenario(Http(args.base), args.world, poll_s=args.poll, run_timeout_s=args.timeout)
    return scenario.run()


if __name__ == "__main__":
    sys.exit(main())

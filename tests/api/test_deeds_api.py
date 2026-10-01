"""U6 API (Step 7.3): act{declare} with ?lang=, 400 not 422, GET deeds with names and
?lang=, void (idempotent, 404, the GM write lease's 409), and the no-LLM container."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.play import InMemoryPlayRepository
from locus.play.models import AppraisalDraft, AppraisalDraftItem, NarrationDraft
from locus.play.rumor.generator import RumorDraft, RumorGenerator
from tests.play.helpers import compose_play
from tests.play.strategies import build_snapshot, edge, npc

WORLD = build_snapshot(
    ["a", "b"],
    [edge("a", "b", weight=0.6)],
    npcs=[npc("n1", "a", name="Mara"), npc("n2", "b", name="Bo")],
)


class _Snap:
    def get(self, world_id):
        if world_id != "w":
            raise LookupError(f"world not found: {world_id}")
        return WORLD


class _Voice:
    def __init__(self) -> None:
        self.narration_langs: list[str] = []

    def complete(self, prompt, *, system=None):
        return "Hm."

    def structured(self, prompt, schema, *, system=None):
        if schema is NarrationDraft:
            self.narration_langs.append("English" if "in English" in system else "other")
            return NarrationDraft(narration="The square murmurs.", record="Ari caught a thief.")
        return AppraisalDraft(
            summary="Ari bragged.",
            appraisals=[
                AppraisalDraftItem(
                    ref="d2",
                    noteworthy=True,
                    salience=1.0,
                    retelling="The traveler caught a thief!",
                )
            ],
        )


class _Rumor:
    def structured(self, prompt, schema, *, system=None):
        return RumorDraft(statement="twisted")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


def _app(*, voice: bool = True):
    play = compose_play(
        InMemoryPlayRepository(),
        RumorGenerator(_Rumor()),
        _Snap(),
        dialogue_llm=_Voice() if voice else None,
    )
    client = TestClient(create_app(play=play))
    sid = client.post(
        "/api/play/worlds/w/sessions", json={"name": "Ari", "start_region_id": "a"}
    ).json()["session"]["id"]
    return client, play, sid


def _act(client, sid, body, lang=None):
    url = f"/api/play/sessions/{sid}/act" + (f"?lang={lang}" if lang else "")
    return client.post(url, json=body)


def test_a_declaration_answers_202_and_its_run_carries_the_narration_and_language():
    client, play, sid = _app()
    res = _act(client, sid, {"type": "declare", "text": "catch the thief"}, lang="en")
    assert res.status_code == 202 and res.json()["lang"] == "en"
    run = client.get(f"/api/play/sessions/{sid}/turn-runs/{res.json()['id']}").json()
    assert run["status"] == "done"
    assert run["result"]["declaration"]["text"] == "The square murmurs."
    assert run["result"]["declaration"]["record"] == "Ari caught a thief."
    region = client.get(f"/api/play/sessions/{sid}/region").json()
    assert region["declare_max_chars"] == 300


def test_an_empty_or_long_declaration_is_400_not_422_and_a_closed_session_409():
    client, play, sid = _app()
    for text in ("", "   ", "x" * 301):
        res = _act(client, sid, {"type": "declare", "text": text})
        assert res.status_code == 400, (text[:5], res.status_code)
    client.post(f"/api/play/sessions/{sid}/close")
    assert _act(client, sid, {"type": "declare", "text": "sing"}).status_code == 409


def _told(client, sid):
    _act(client, sid, {"type": "declare", "text": "catch the thief"})
    client.post(f"/api/play/sessions/{sid}/npcs/n1/say", json={"text": "Saw that?"})
    _act(client, sid, {"type": "end_talk", "npc_id": "n1"})
    _act(client, sid, {"type": "wait"})  # one hop to B


def test_get_deeds_shows_names_appraisals_and_reach():
    client, play, sid = _app()
    _told(client, sid)
    deeds = client.get(f"/api/gm/sessions/{sid}/deeds").json()
    declared = next(v for v in deeds if v["deed"]["kind"] == "declared_action")
    assert declared["deed"]["region_name"] == "A"
    assert declared["deed"]["witness_names"] == ["Mara"]
    assert [a["npc_name"] for a in declared["appraisals"]] == ["Mara"]
    assert declared["reached_region_ids"] == ["a", "b"]
    assert declared["reached_region_names"] == ["A", "B"]
    assert {r["origin_kind"] for r in declared["rumors"]} == {"deed"}
    assert "text_ko" in declared["deed"] and "retelling_ko" in declared["appraisals"][0]
    assert client.get(f"/api/gm/sessions/{sid}/deeds?lang=fr").status_code == 400


def test_void_is_idempotent_404_for_a_stranger_and_409_while_a_turn_holds_the_session():
    client, play, sid = _app()
    _told(client, sid)
    deeds = client.get(f"/api/gm/sessions/{sid}/deeds").json()
    deed_id = next(v["deed"]["id"] for v in deeds if v["deed"]["kind"] == "declared_action")
    with play.guard.hold(sid):
        assert client.post(f"/api/gm/sessions/{sid}/deeds/{deed_id}/void").status_code == 409
    first = client.post(f"/api/gm/sessions/{sid}/deeds/{deed_id}/void")
    assert first.status_code == 200 and len(first.json()["deactivated_rumor_ids"]) == 2
    again = client.post(f"/api/gm/sessions/{sid}/deeds/{deed_id}/void")
    assert again.status_code == 200 and again.json()["deactivated_rumor_ids"] == []
    assert client.post(f"/api/gm/sessions/{sid}/deeds/nope/void").status_code == 404
    client.post(f"/api/play/sessions/{sid}/close")
    assert client.post(f"/api/gm/sessions/{sid}/deeds/{deed_id}/void").status_code == 409


def test_without_an_llm_a_declaration_and_the_deed_view_still_work():
    client, play, sid = _app(voice=False)
    res = _act(client, sid, {"type": "declare", "text": "sing"})
    assert res.status_code == 202
    run = client.get(f"/api/play/sessions/{sid}/turn-runs/{res.json()['id']}").json()
    assert run["result"]["declaration"]["llm_calls"] == 0
    assert client.get(f"/api/gm/sessions/{sid}/deeds").status_code == 200

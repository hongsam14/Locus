"""S1 session model tests — validation + property-based round-trip (NFR-R5)."""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from locus.play.models import (
    DEFAULT_DISTORTION_DEGREE,
    GameSession,
    RegionDistortion,
    SessionRumor,
    SessionStatus,
    TimelineEntry,
    TimelineKind,
)
from locus.shared.models import Provenance, SourceKind


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


def test_gamesession_defaults() -> None:
    s = GameSession(world_id="w")
    assert s.status == SessionStatus.OPEN.value
    assert s.turn == 0
    assert s.created_at is None and s.closed_at is None
    assert s.id  # auto uuid


def test_default_distortion_degree_constant() -> None:
    assert DEFAULT_DISTORTION_DEGREE == 0.3
    assert RegionDistortion(session_id="s", region_id="r").distortion_degree == 0.3


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_rumor_range_validation(bad: float) -> None:
    for field in ("distortion_degree", "support", "confidence"):
        with pytest.raises(ValidationError):
            SessionRumor(
                session_id="s",
                region_id="r",
                distorted_from_id="k",
                provenance=_prov(),
                **{field: bad},
            )


def test_session_rumor_roundtrip() -> None:
    r = SessionRumor(
        session_id="s",
        region_id="r",
        distorted_from_id="k1",
        distorted_from_kind="knowledge",
        statement="a distorted tale",
        distortion_degree=0.5,
        support=0.7,
        confidence=0.5,
        promoted=True,
        provenance=_prov(),
    )
    assert SessionRumor.model_validate(r.model_dump()) == r


def test_timeline_entry_roundtrip() -> None:
    e = TimelineEntry(
        session_id="s",
        turn=2,
        kind=TimelineKind.GENERATE,
        summary="generated 3 rumors",
        payload={"rumor_ids": ["a", "b", "c"]},
    )
    assert TimelineEntry.model_validate(e.model_dump()) == e


@given(
    degree=st.floats(min_value=0.0, max_value=1.0),
    support=st.floats(min_value=0.0, max_value=1.0),
    confidence=st.floats(min_value=0.0, max_value=1.0),
)
def test_rumor_pbt_roundtrip(degree: float, support: float, confidence: float) -> None:
    r = SessionRumor(
        session_id="s",
        region_id="r",
        distorted_from_id="k",
        distortion_degree=degree,
        support=support,
        confidence=confidence,
        provenance=_prov(),
    )
    assert SessionRumor.model_validate(r.model_dump()) == r


# --------------------------------------------------------------------------- #
# U4 player mode — models (Step 2.3; BR-U4-1/29, FD domain-entities §1)
# --------------------------------------------------------------------------- #
def test_u4_player_action_is_discriminated_by_type() -> None:
    from pydantic import TypeAdapter

    from locus.play.models import EndTalkAction, MoveAction, PlayerAction, WaitAction

    adapter = TypeAdapter(PlayerAction)
    assert isinstance(adapter.validate_python({"type": "move", "to_region_id": "r2"}), MoveAction)
    assert isinstance(adapter.validate_python({"type": "wait"}), WaitAction)
    assert isinstance(adapter.validate_python({"type": "end_talk", "npc_id": "n1"}), EndTalkAction)
    with pytest.raises(ValidationError):
        adapter.validate_python({"type": "fly"})
    with pytest.raises(ValidationError):  # extra keys are forbidden (LocusModel)
        adapter.validate_python({"type": "wait", "to_region_id": "r2"})


def test_u4_player_and_create_validate_name_length() -> None:
    from locus.play.models import Player, PlayerCreate

    assert PlayerCreate(name="Ari", start_region_id="r1").name == "Ari"
    with pytest.raises(ValidationError):
        PlayerCreate(name="", start_region_id="r1")
    with pytest.raises(ValidationError):
        PlayerCreate(name="x" * 41, start_region_id="r1")
    p = Player(session_id="s", name="Ari", region_id="r1")
    assert p.turns_spent == 0 and p.id


def test_u4_turn_result_defaults_keep_existing_construction() -> None:
    """BR-U4-29: the pre-U4 constructor call still works; new fields default."""
    from locus.play.models import TurnResult
    from locus.play.turn.advancer import TurnResult as ReExported

    assert ReExported is TurnResult
    r = TurnResult(session_id="s", turn=1, promoted_ids=["a"])
    assert r.llm_calls == 0 and r.budget_exhausted is False and r.llm_failed is False
    assert r.rumors_skipped_regions == [] and r.rumors_capped_regions == []


def test_u4_turn_run_and_action_result_round_trip() -> None:
    from locus.play.models import (
        ActionResult,
        GameSession,
        MoveAction,
        RegionTurnChange,
        TurnResult,
        TurnRun,
        TurnRunStatus,
    )

    session = GameSession(world_id="w", turn=2)
    result = ActionResult(
        session=session,
        player=None,
        turns=[TurnResult(session_id=session.id, turn=2)],
        changes=[RegionTurnChange(region_id="r1", region_name="Riverton", promoted=["x"])],
        narration=["Riverton: 1 promoted"],
        llm_calls=3,
    )
    run = TurnRun(
        session_id=session.id,
        action=MoveAction(to_region_id="r2"),
        cost_turns=2,
        status=TurnRunStatus.DONE,
        result=result,
    )
    again = TurnRun.model_validate(run.model_dump())
    assert again == run and again.action.type == "move"  # type: ignore[union-attr]
    assert again.result is not None and again.result.changes[0].region_name == "Riverton"
    assert TurnRun(session_id="s").action is None and TurnRun(session_id="s").status == "running"


def test_u4_play_tuning_defaults_and_env(monkeypatch: pytest.MonkeyPatch) -> None:
    from locus.shared.config import Settings
    from locus.shared.config.tuning import PlayTuning

    t = PlayTuning()
    assert (t.max_move_cost, t.max_new_rumors_per_region_turn) == (5, 2)
    assert (t.max_llm_calls_per_turn, t.max_active_rumors_per_region) == (8, 20)
    monkeypatch.setenv("PLAY_MAX_MOVE_COST", "3")
    monkeypatch.setenv("RUMOR_MAX_NEW_PER_REGION_TURN", "1")
    monkeypatch.setenv("LLM_MAX_CALLS_PER_TURN", "4")
    monkeypatch.setenv("RUMOR_MAX_ACTIVE_PER_REGION", "9")
    monkeypatch.setenv("TURN_SHUTDOWN_TIMEOUT_S", "2.5")
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    tuned = s.play_tuning()
    assert (tuned.max_move_cost, tuned.max_new_rumors_per_region_turn) == (3, 1)
    assert (tuned.max_llm_calls_per_turn, tuned.max_active_rumors_per_region) == (4, 9)
    assert s.turn_shutdown_timeout_s == 2.5


# --------------------------------------------------------------------------- #
# U5 NPC dialogue — models (Step 2.4)
# --------------------------------------------------------------------------- #
def test_u5_message_and_conversation_round_trip() -> None:
    from locus.play.models import Conversation, Message

    conv = Conversation(session_id="s", npc_id="n1", started_turn=2)
    msg = Message(conversation_id=conv.id, role="player", text="hello", lang="ko", turn=2)
    conv.messages.append(msg)
    again = Conversation.model_validate(conv.model_dump())
    assert again == conv and again.messages[0].role == "player"
    with pytest.raises(ValidationError):
        Message(conversation_id="c", role="narrator", text="x", lang="ko")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        Message(conversation_id="c", role="npc", text="", lang="ko")


def test_u5_scope_limits_come_from_the_tuning() -> None:
    from locus.play.models import ScopeLimits
    from locus.shared.config.tuning import PlayTuning

    limits = ScopeLimits.from_tuning(PlayTuning(npc_max_facts=3, npc_max_rumors=0))
    assert (limits.facts, limits.rumors, limits.recent_messages) == (3, 0, 10)
    with pytest.raises(ValidationError):
        ScopeLimits(facts=-1)


def test_u5_regenerate_result_rumors_is_kept_plus_fresh() -> None:
    from locus.play.models import RegenerateResult, SessionRumor

    def r(i: str) -> SessionRumor:
        return SessionRumor(
            id=i, session_id="s", region_id="a", distorted_from_id="k", provenance=_prov()
        )

    res = RegenerateResult(kept=[r("k1")], fresh=[r("f1"), r("f2")], deleted_ids=["d1"])
    assert [x.id for x in res.rumors] == ["k1", "f1", "f2"]
    skipped = RegenerateResult(kept=[r("k1")], skipped_reason="llm_incomplete")
    assert skipped.deleted_ids == [] and [x.id for x in skipped.rumors] == ["k1"]
    with pytest.raises(ValidationError):
        RegenerateResult(skipped_reason="bored")  # type: ignore[arg-type]


def test_u5_npc_talked_is_appended_after_the_u4_kinds() -> None:
    """Kinds are only ever appended. (U6 appends its own after `npc_talked`, so the old
    "npc_talked is last" check now reads "U4 < U5 < U6" — NFR-1, intended change.)"""
    from locus.play.models import TimelineKind

    kinds = [k.value for k in TimelineKind]
    assert kinds.index("turn_run_failed") < kinds.index("npc_talked")
    u6 = [
        "action_declared",
        "deed_recorded",
        "deed_appraised",
        "deed_seeded",
        "rumor_spread",
        "deed_voided",
    ]
    assert kinds[-len(u6) :] == u6 and kinds.index("npc_talked") < kinds.index(u6[0])


# --- U6 models (Step 2.3) ----------------------------------------------------------- #
def test_u6_a_declaration_is_a_player_action_and_an_empty_one_passes_the_model() -> None:
    """BR-U6-5: emptiness and length are the service's 400, never a model 422."""
    from pydantic import TypeAdapter

    from locus.play.models import DeclareAction, PlayerAction

    action = TypeAdapter(PlayerAction).validate_python({"type": "declare", "text": ""})
    assert isinstance(action, DeclareAction) and action.text == ""


def test_u6_deed_models_round_trip() -> None:
    from locus.play.models import (
        Deed,
        DeedAppraisal,
        DeedKind,
        DeedView,
        SessionRumor,
        SpreadTarget,
        TurnRun,
    )

    deed = Deed(
        session_id="s",
        player_id="p",
        region_id="a",
        kind=DeedKind.DECLARED_ACTION,
        text="Ari caught a thief.",
        declaration="도둑을 잡았다",
        witnessed_npc_ids=["n1"],
        run_id="run1",
    )
    ap = DeedAppraisal(
        session_id="s",
        deed_id=deed.id,
        npc_id="n1",
        noteworthy=True,
        salience=0.8,
        slant="admiring",
        retelling="The traveler caught a thief!",
    )
    rumor = SessionRumor(
        session_id="s",
        region_id="a",
        distorted_from_id=deed.id,
        distorted_from_kind="deed",
        statement=ap.retelling,
        origin_kind="deed",
        origin_deed_id=deed.id,
        origin_appraisal_id=ap.id,
        provenance=Provenance(source=SourceKind.SIMULATION),
    )
    view = DeedView(deed=deed, appraisals=[ap], rumors=[rumor], reached_region_ids=["a"])
    assert DeedView.model_validate_json(view.model_dump_json()) == view
    assert (
        SessionRumor(
            session_id="s",
            region_id="a",
            distorted_from_id="k",
            provenance=Provenance(source=SourceKind.SIMULATION),
        ).origin_kind
        == "canonical"
    )
    run = TurnRun(session_id="s", lang="en", turns_charged=1, from_region_id="a")
    assert TurnRun.model_validate_json(run.model_dump_json()).lang == "en"
    with pytest.raises(ValidationError):
        SpreadTarget(region_id="b", from_region_id="a", weight=1.2, degree=0.4, support=0.3)

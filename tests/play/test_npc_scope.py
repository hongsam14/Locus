"""U5 NPC scope — the pure `build_context` and the prompt it feeds (Step 3.4).

Function-level properties live here (TP-U5-1a/2/3/4, EX-5/7, the rumor-first
ordering of plan review R-12). The composed invariant over `region_sources` with an
independent oracle (TP-U5-1b) needs the Step 4 service and lives in test_dialogue.py.
"""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from locus.knowledge.consensus import ConsensusEngine
from locus.knowledge.query import region_known
from locus.play.models import Message, ScopeLimits, SessionRumor
from locus.play.npc.prompts import rumor_tone, system_prompt, user_prompt
from locus.play.npc.scope import build_context, is_known_scope
from locus.shared.models import KnowledgeView, Provenance, SourceKind
from tests.play.strategies import GLOBAL_MARKER, chain_roots, npc, regional_worlds, rumors_from

NPC_A = npc("n1", "r0", name="Mara")
LIMITS = ScopeLimits()


def _prov() -> Provenance:
    return Provenance(source=SourceKind.SIMULATION)


def _fact(kid: str, scope: str = "direct", confidence: float = 0.8, statement: str | None = None):
    return KnowledgeView(
        knowledge_id=kid,
        statement=statement or f"fact {kid}",
        scope_type=scope,
        is_hearsay=scope == "hearsay",
        confidence=confidence,
    )


def _rumor(rid: str, source: str, *, promoted=False, support=0.5, distortion=0.3) -> SessionRumor:
    return SessionRumor(
        id=rid,
        session_id="s",
        region_id="r0",
        distorted_from_id=source,
        distorted_from_kind="knowledge",
        statement=f"twisted {source}",
        distortion_degree=distortion,
        support=support,
        promoted=promoted,
        provenance=_prov(),
    )


scopes = st.sampled_from(["direct", "inherited", "global", "propagated", "hearsay"])


@st.composite
def fact_lists(draw) -> list[KnowledgeView]:
    n = draw(st.integers(min_value=0, max_value=25))
    return [
        _fact(f"k{i}", draw(scopes), draw(st.floats(min_value=0.0, max_value=1.0, allow_nan=False)))
        for i in range(n)
    ]


@st.composite
def rumor_lists(draw, fact_ids: list[str]) -> list[SessionRumor]:
    return draw(rumors_from("s", "r0", fact_ids, max_count=14))


@settings(max_examples=80)
@given(
    data=st.data(),
    limits=st.builds(
        ScopeLimits,
        facts=st.integers(0, 15),
        rumors=st.integers(0, 10),
        recent_messages=st.integers(0, 12),
    ),
)
def test_tp_u5_1a_the_context_only_holds_known_scope_minus_hidden_sources(data, limits) -> None:
    facts = data.draw(fact_lists())
    every = data.draw(rumor_lists([f.knowledge_id for f in facts]))
    active = [r for r in every if r.active]
    ctx = build_context(
        npc=NPC_A, facts=facts, rumors=active, recent=[], limits=limits, lineage=every
    )
    # only the *selected* rumors hide their sources — the root of each chain (review #1)
    hidden = chain_roots(ctx.rumors, every)
    allowed_facts = {f.knowledge_id for f in facts if is_known_scope(f)} - hidden
    assert {k.knowledge_id for k in ctx.facts} <= allowed_facts
    assert all(str(k.scope_type) in ("direct", "inherited", "global") for k in ctx.facts)
    assert {r.id for r in ctx.rumors} <= {r.id for r in active}
    assert ctx.allowed_ids == {k.knowledge_id for k in ctx.facts} | {r.id for r in ctx.rumors}


@settings(max_examples=80)
@given(
    data=st.data(),
    limits=st.builds(
        ScopeLimits,
        facts=st.integers(0, 15),
        rumors=st.integers(0, 10),
        recent_messages=st.integers(0, 12),
    ),
)
def test_tp_u5_2_limits_and_priority_order_hold(data, limits) -> None:
    facts = data.draw(fact_lists())
    rumors = data.draw(rumor_lists([f.knowledge_id for f in facts]))
    recent = [
        Message(
            conversation_id="c", role="player" if i % 2 else "npc", text=f"m{i}", lang="ko", turn=0
        )
        for i in range(data.draw(st.integers(0, 20)))
    ]
    ctx = build_context(npc=NPC_A, facts=facts, rumors=rumors, recent=recent, limits=limits)
    assert len(ctx.facts) <= limits.facts and len(ctx.rumors) <= limits.rumors
    assert len(ctx.recent) <= limits.recent_messages
    assert ctx.recent == recent[len(recent) - len(ctx.recent) :]  # the newest ones, in order
    ranks = {"direct": 0, "inherited": 1, "global": 2}
    assert [ranks[str(k.scope_type)] for k in ctx.facts] == sorted(
        ranks[str(k.scope_type)] for k in ctx.facts
    )
    promoted = [r.promoted for r in ctx.rumors]
    assert promoted == sorted(promoted, reverse=True)  # promoted first
    if limits.facts == 0:
        assert ctx.facts == []
    if limits.recent_messages == 0:
        assert ctx.recent == []  # not recent[-0:], which is everything


@settings(max_examples=40)
@given(data=st.data())
def test_tp_u5_3_same_inputs_same_context_even_shuffled(data) -> None:
    facts = data.draw(fact_lists())
    rumors = data.draw(rumor_lists([f.knowledge_id for f in facts]))
    first = build_context(npc=NPC_A, facts=facts, rumors=rumors, recent=[], limits=LIMITS)
    rng = random.Random(data.draw(st.integers(0, 10_000)))
    shuffled_f, shuffled_r = facts[:], rumors[:]
    rng.shuffle(shuffled_f)
    rng.shuffle(shuffled_r)
    again = build_context(npc=NPC_A, facts=shuffled_f, rumors=shuffled_r, recent=[], limits=LIMITS)
    assert again == first


def test_r12_a_rumor_cut_by_the_limit_does_not_hide_its_source() -> None:
    """Plan review R-12: with the old order the NPC forgot the event altogether."""
    facts = [_fact("k1"), _fact("k2")]
    rumors = [
        _rumor("ra", "k1", promoted=True),  # picked: hides k1
        _rumor("rb", "k2", support=0.01),  # cut by limits.rumors=1: must NOT hide k2
    ]
    ctx = build_context(
        npc=NPC_A, facts=facts, rumors=rumors, recent=[], limits=ScopeLimits(rumors=1)
    )
    assert [r.id for r in ctx.rumors] == ["ra"]
    assert [k.knowledge_id for k in ctx.facts] == ["k2"]


def test_ex5_twenty_facts_and_twelve_rumors_are_cut_to_twelve_and_eight() -> None:
    facts = [_fact(f"g{i}", "global") for i in range(8)] + [_fact(f"d{i}") for i in range(12)]
    rumors = [_rumor(f"r{i:02d}", f"elsewhere{i}", support=i / 12) for i in range(12)]
    ctx = build_context(npc=NPC_A, facts=facts, rumors=rumors, recent=[], limits=LIMITS)
    assert len(ctx.facts) == 12 and len(ctx.rumors) == 8
    assert all(str(k.scope_type) == "direct" for k in ctx.facts)  # direct beats global
    assert [r.id for r in ctx.rumors] == [f"r{i:02d}" for i in range(11, 3, -1)]  # support desc


def test_ex7_the_prompt_tells_the_distortion_not_the_original() -> None:
    """US-4.3: the market burned → the NPC only knows 'a riot tore the market down'."""
    original = _fact("k-fire", statement="The market burned.")
    other = _fact("k-well", statement="The well is dry.")
    rumor = _rumor("r1", "k-fire", distortion=0.7)
    rumor.statement = "A riot tore the market down."
    known = _rumor("r2", "k-elsewhere", promoted=True)
    known.statement = "The mayor fled."
    ctx = build_context(
        npc=NPC_A, facts=[original, other], rumors=[rumor, known], recent=[], limits=LIMITS
    )
    prompt = user_prompt(ctx, "What happened to the market?", "ko")
    assert "The market burned." not in prompt  # the original is hidden
    assert "[uncertain rumor] A riot tore the market down." in prompt
    assert "[known] The mayor fled." in prompt
    assert "The well is dry." in prompt
    assert rumor_tone(_rumor("x", "k", distortion=0.2)) == "rumor"
    assert "k-fire" not in prompt and "r1" not in prompt  # no ids leak


def test_the_system_prompt_carries_persona_language_and_guard() -> None:
    ko = system_prompt(NPC_A, "ko")
    assert "Mara" in ko and "Korean" in ko and "say you do not know" in ko
    assert "never invent" in ko
    assert "English" in system_prompt(NPC_A, "en")


@settings(max_examples=60)
@given(world=regional_worlds(), data=st.data())
def test_tp_u5_4_a_prompt_never_carries_another_regions_knowledge(world, data) -> None:
    """TP-U5-4: for every region, the rendered prompt holds only that region's own
    statements (and global ones) — no other region's marker, whatever the path weights."""
    region_id = data.draw(st.sampled_from(sorted(world.regions_by_id)))
    view = ConsensusEngine.from_snapshot(world).resolve(region_id)
    facts = region_known(view) + list(view.hearsay) + list(view.propagated)  # try to smuggle
    ctx = build_context(npc=npc("n", region_id), facts=facts, rumors=[], recent=[], limits=LIMITS)
    prompt = user_prompt(ctx, "tell me everything", "en")
    others = [rid for rid in world.regions_by_id if rid != region_id]
    for other in others:
        assert f"only-in-{other}-#" not in prompt
    for k in world.kg.knowledge:
        if k.is_global:
            assert GLOBAL_MARKER in prompt or len(ctx.facts) == LIMITS.facts


def test_known_scope_rejects_propagated_and_hearsay() -> None:
    assert is_known_scope(_fact("a", "direct")) and is_known_scope(_fact("b", "global"))
    assert not is_known_scope(_fact("c", "propagated"))
    assert not is_known_scope(_fact("d", "hearsay"))


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_the_question_line_names_the_language(lang: str) -> None:
    ctx = build_context(npc=NPC_A, facts=[], rumors=[], recent=[], limits=LIMITS)
    prompt = user_prompt(ctx, "hi", lang)
    assert prompt.endswith("hi") and "(nothing in particular)" in prompt


# --- review U5 #1: a chain's later links hide the chain's canonical root ------------ #
def _link(rid: str, parent: str, *, support=0.5, distortion=0.5, active=True) -> SessionRumor:
    r = _rumor(rid, parent, support=support, distortion=distortion)
    return r.model_copy(update={"distorted_from_kind": "rumor", "active": active})


def test_review_1_second_and_third_links_hide_the_original() -> None:
    """The demo case: a regenerate makes 3-link chains with equal support; the limit
    keeps the most distorted links, so only 2nd/3rd links are picked."""
    facts = [_fact("k1", statement="The mill burned."), _fact("k2")]
    first = _rumor("r1", "k1", distortion=0.2)
    second = _link("r2", "r1", distortion=0.4)
    third = _link("r3", "r2", distortion=0.6)
    ctx = build_context(
        npc=NPC_A,
        facts=facts,
        rumors=[first, second, third],
        recent=[],
        limits=ScopeLimits(facts=12, rumors=2, recent_messages=0),
    )
    assert [r.id for r in ctx.rumors] == ["r3", "r2"]
    assert "k1" not in {k.knowledge_id for k in ctx.facts}  # the original is hidden
    assert "k2" in {k.knowledge_id for k in ctx.facts}


def test_review_1_a_pruned_middle_link_still_leads_to_the_root() -> None:
    facts = [_fact("k1")]
    first = _rumor("r1", "k1").model_copy(update={"active": False})
    third = _link("r3", "r2")
    ctx = build_context(
        npc=NPC_A,
        facts=facts,
        rumors=[third],
        recent=[],
        limits=LIMITS,
        lineage=[first, _link("r2", "r1", active=False), third],
    )
    assert ctx.facts == []  # k1 hidden through two pruned links


def test_review_14_a_rumor_with_no_words_is_never_picked() -> None:
    facts = [_fact("k1")]
    empty = _rumor("r1", "k1").model_copy(update={"statement": "  "})
    ctx = build_context(npc=NPC_A, facts=facts, rumors=[empty], recent=[], limits=LIMITS)
    assert ctx.rumors == [] and [k.knowledge_id for k in ctx.facts] == ["k1"]

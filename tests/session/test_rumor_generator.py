"""S2 RumorGenerator tests — chain, lineage, confidence, graceful (mock LLM)."""

from __future__ import annotations

import pytest

from locus.session.rumor_generator import RumorDraft, RumorGenerator


class _FakeLLM:
    """Returns a deterministic distorted statement; optionally fails after N calls."""

    def __init__(self, fail_after: int | None = None) -> None:
        self.calls = 0
        self._fail_after = fail_after

    def structured(self, prompt, schema, *, system=None):
        self.calls += 1
        if self._fail_after is not None and self.calls > self._fail_after:
            raise RuntimeError("LLM down")
        return RumorDraft(statement=f"distorted#{self.calls}")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""


def _gen(fail_after=None) -> RumorGenerator:
    return RumorGenerator(_FakeLLM(fail_after))


def test_chain_length_and_lineage() -> None:
    rumors = _gen().generate_chain(
        source_text="The king is wise.",
        source_id="k1",
        source_kind="knowledge",
        source_confidence=1.0,
        region_id="r",
        session_id="s",
        degrees=[0.1, 0.2, 0.3],
    )
    assert len(rumors) == 3
    # step 0 distorts the source knowledge
    assert rumors[0].distorted_from_id == "k1" and rumors[0].distorted_from_kind == "knowledge"
    # steps 1,2 re-distort the previous rumor (lineage, Q3=A)
    assert rumors[1].distorted_from_id == rumors[0].id and rumors[1].distorted_from_kind == "rumor"
    assert rumors[2].distorted_from_id == rumors[1].id and rumors[2].distorted_from_kind == "rumor"
    assert [r.distortion_degree for r in rumors] == [0.1, 0.2, 0.3]
    assert all(r.session_id == "s" and r.region_id == "r" for r in rumors)
    assert all(r.support == 0.0 and r.promoted is False for r in rumors)


def test_confidence_decays_with_degree() -> None:
    rumors = _gen().generate_chain(
        source_text="x",
        source_id="k1",
        source_kind="knowledge",
        source_confidence=0.8,
        region_id="r",
        session_id="s",
        degrees=[0.25, 0.5],
    )
    assert rumors[0].confidence == pytest.approx(0.8 * 0.75)
    assert rumors[1].confidence == pytest.approx(0.8 * 0.5)


def test_graceful_stops_chain_on_llm_failure() -> None:
    gen = _gen(fail_after=2)  # 3rd structured() call raises
    rumors = gen.generate_chain(
        source_text="x",
        source_id="k1",
        source_kind="knowledge",
        source_confidence=1.0,
        region_id="r",
        session_id="s",
        degrees=[0.1, 0.2, 0.3],
    )
    assert len(rumors) == 2  # successful prefix kept


def test_chain_from_existing_rumor_source() -> None:
    rumors = _gen().generate_chain(
        source_text="a prior rumor",
        source_id="ru0",
        source_kind="rumor",
        source_confidence=0.5,
        region_id="r",
        session_id="s",
        degrees=[0.3],
    )
    assert rumors[0].distorted_from_id == "ru0" and rumors[0].distorted_from_kind == "rumor"

"""S2 PromotionPolicy tests — transitions + PBT (NFR-R5)."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.models import Provenance, SourceKind
from locus.session.models import SessionRumor
from locus.session.promotion import DEFAULT_PROMOTION_THRESHOLD, evaluate


def _rumor(support: float, promoted: bool) -> SessionRumor:
    return SessionRumor(
        session_id="s",
        region_id="r",
        distorted_from_id="k",
        support=support,
        promoted=promoted,
        provenance=Provenance(source=SourceKind.SESSION_RUMOR),
    )


def test_promote_when_above_threshold_and_not_promoted() -> None:
    r = _rumor(0.7, promoted=False)
    res = evaluate([r], threshold=0.6)
    assert res.promoted_ids == [r.id] and res.demoted_ids == []


def test_demote_when_below_threshold_and_promoted() -> None:
    r = _rumor(0.3, promoted=True)
    res = evaluate([r], threshold=0.6)
    assert res.demoted_ids == [r.id] and res.promoted_ids == []


def test_no_transition_when_already_consistent() -> None:
    already = _rumor(0.9, promoted=True)  # promoted + still above
    low = _rumor(0.1, promoted=False)  # below + not promoted
    res = evaluate([already, low], threshold=0.6)
    assert res.promoted_ids == [] and res.demoted_ids == []


def test_threshold_boundary_is_inclusive() -> None:
    r = _rumor(0.6, promoted=False)
    assert evaluate([r], threshold=0.6).promoted_ids == [r.id]


@given(
    support=st.floats(min_value=0.0, max_value=1.0),
    promoted=st.booleans(),
    threshold=st.floats(min_value=0.0, max_value=1.0),
)
def test_pbt_transition_is_consistent(support: float, promoted: bool, threshold: float) -> None:
    r = _rumor(support, promoted)
    res = evaluate([r], threshold=threshold)
    should_promote = support >= threshold and not promoted
    should_demote = support < threshold and promoted
    assert (r.id in res.promoted_ids) == should_promote
    assert (r.id in res.demoted_ids) == should_demote
    # never both
    assert not (res.promoted_ids and res.demoted_ids)


def test_default_threshold() -> None:
    assert DEFAULT_PROMOTION_THRESHOLD == 0.6

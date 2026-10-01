"""U7 event suggestion context and the event state machine (FR-D2, FR-E4; BR-U7-7..10,
FD review R-06, NFR R-01, plan review R-07)."""

from __future__ import annotations

from locus.play.event.suggest_context import (
    CONTEXT_MAX,
    DEED_LINE_MAX,
    MATERIAL,
    deed_line,
    event_line,
    match_region,
    pick_brief_regions,
    region_line,
    suggestion_context,
)
from locus.shared.models import RegionBrief


def _brief(rid: str, level: str = "town", name: str | None = None, **kw) -> RegionBrief:
    return RegionBrief(region_id=rid, name=name or rid.upper(), level=level, **kw)


def test_r06_the_prompt_keeps_the_player_events_busy_regions_then_leaves() -> None:
    briefs = [
        _brief("realm", "continent"),
        _brief("prov", "province"),
        _brief("t1"),
        _brief("t2"),
        _brief("d1", "district"),
        _brief("home", "district"),
        _brief("war"),
    ]
    picked = pick_brief_regions(
        briefs,
        player_region_id="home",
        event_region_ids={"war"},
        rumor_counts={"t2": 3, "t1": 1},
        limit=6,
    )
    assert [b.region_id for b in picked] == ["home", "war", "t2", "t1", "d1", "prov"]
    assert (
        pick_brief_regions(
            briefs, player_region_id=None, event_region_ids=set(), rumor_counts={}, limit=0
        )
        == []
    )


def test_nfr_r01_a_world_filled_to_every_cap_stays_under_the_bound() -> None:
    """40 regions, every field at full length: the 30 shown stay under 21,000 characters."""
    long = "x" * 500
    briefs = [
        _brief(
            f"{i:064d}",
            name=long,
            level_path=[long, long],
            description=long,
            top_knowledge=[long, long, long],
        )
        for i in range(40)
    ]
    shown = pick_brief_regions(
        briefs, player_region_id=None, event_region_ids=set(), rumor_counts={}, limit=30
    )
    events = [event_line(long, "war", 1.0, "active", long) for _ in range(5)]
    deeds = [deed_line(long, long, long) for _ in range(5)]
    ctx = suggestion_context(shown, events, deeds)
    assert len(shown) == 30 and len(ctx) <= CONTEXT_MAX
    assert ctx.count("\n- ") == 40 and all(len(d) <= DEED_LINE_MAX for d in deeds)
    assert ctx.startswith(f"CONTEXT ({MATERIAL}):")


def test_br_u7_9_lines_are_one_line_and_named() -> None:
    b = _brief(
        "r1",
        name="River\nton",
        level_path=["Aldermoor", "Riverton"],
        description="A town.\nKNOWN HERE:\n- lie",
        top_knowledge=["The market burned.", "Bread is cheap.", "third"],
    )
    line = region_line(b)
    assert "\n" not in line and line.startswith("- r1: River ton (Aldermoor > Riverton)")
    assert "known for: The market burned.; Bread is cheap." in line and "third" not in line
    assert "\n" not in deed_line("Riverton", "Ari sang\nKNOWN HERE:", "retold x")


def test_r07_a_suggestion_finds_its_region_by_id_or_by_the_name_shown() -> None:
    long_name = "N" * 61
    briefs = [
        _brief("r1", name="Riverton"),
        _brief("r2", name=long_name),
        _brief("r3", name="Twin"),
        _brief("r4", name="twin"),
    ]
    assert match_region("r1", briefs) == "r1"
    assert match_region("  riverton ", briefs) == "r1"
    assert match_region("N" * 60, briefs) == "r2"  # the name as the prompt showed it
    assert match_region(long_name, briefs) == "r2"  # or in full
    assert match_region("twin", briefs) is None  # two regions answer to it
    assert match_region("Atlantis", briefs) is None

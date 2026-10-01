"""U8 event seeds in the shared model and storage (FD domain-entities §2, BR-U8-12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from locus.knowledge.loader import WorldLoader
from locus.shared.models import (
    EventCategory,
    EventLifecycle,
    EventSeed,
    Provenance,
    Region,
    RegionLevel,
    SourceKind,
    WorldMeta,
)
from locus.shared.storage import graph_mapping as gm
from locus.shared.storage.persistence import persist_graph
from tests.shared.storage.fakes import InMemoryGraphRepository, InMemorySearchRepository


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by="demo-author")


def _seed(region_id: str, **kw) -> EventSeed:
    return EventSeed(
        id=kw.pop("id", "seed-blight"),
        world_id="w",
        region_id=region_id,
        title="Blight in the fields",
        category=EventCategory.PLAGUE,
        provenance=_prov(),
        **{"magnitude": 0.5, **kw},
    )


def test_a_seed_maps_to_a_node_and_back() -> None:
    seed = _seed("r1", description="spots on the caps", lifecycle=EventLifecycle.ONE_SHOT)
    node = gm.seed_to_node(seed)
    assert node.label == "EventSeed" and node.id == "seed-blight"
    assert gm.node_to_seed(node) == seed
    bare = _seed("r1")  # no lifecycle: the category default applies at start
    assert gm.node_to_seed(gm.seed_to_node(bare)) == bare


def test_a_seed_keeps_its_bounds() -> None:
    with pytest.raises(ValidationError):
        _seed("r1", magnitude=1.5)
    with pytest.raises(ValidationError):
        EventSeed(
            world_id="w",
            region_id="r1",
            title="",
            category="plague",
            magnitude=0.1,
            provenance=_prov(),
        )


def test_the_loader_carries_seeds_and_drops_one_whose_region_is_gone() -> None:
    graph, search = InMemoryGraphRepository(), InMemorySearchRepository()
    town = Region(id="r1", world_id="w", name="Town", level=RegionLevel.TOWN, provenance=_prov())
    persist_graph(
        graph,
        search,
        None,
        "w",
        regions=[town],
        seeds=[_seed("r1"), _seed("gone", id="seed-lost")],
        meta=WorldMeta(id="w", name="W"),
    )
    snap = WorldLoader(graph).load("w")
    assert [s.id for s in snap.event_seeds] == ["seed-blight"]
    assert any(w.item_id == "seed-lost" for w in snap.load_warnings)


def test_the_event_vocabulary_is_shared_and_play_reexports_it() -> None:
    from locus.play import models as play_models
    from locus.shared.models import enums

    assert play_models.EventCategory is enums.EventCategory
    assert play_models.EventLifecycle is enums.EventLifecycle
    assert play_models.default_lifecycle(EventCategory.PLAGUE) == EventLifecycle.PERSISTENT

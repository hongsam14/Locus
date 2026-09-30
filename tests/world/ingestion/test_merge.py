"""U2 Step 6 — merge preserves hints (TP-U2-3), references stay resolvable (TP-U2-4),
scalar conflicts warn (EX-6), dangling relations are dropped with a warning (EX-7),
bad base64 is an error that does not stop the other inputs (EX-9)."""

from __future__ import annotations

import base64

from hypothesis import given

from locus.shared.models import Entity, EntityType, Provenance, Region, RegionLevel, SourceKind
from locus.world.ingestion import IngestionService, StructuredMapIngestor, WorldInputs
from locus.world.ingestion.mapping import merge_entities, merge_regions, remap_entity_refs
from locus.world.ingestion.schemas import TextExtraction
from locus.world.ingestion.text_ingestor import TextIngestor
from tests.world.ingestion.test_ingestion import _FakeLLM, _FakeVLM
from tests.world.strategies import entities_with_refs, region_hints


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


@given(region_hints())
def test_merge_regions_keeps_every_hint(hints: list[Region]) -> None:  # TP-U2-3 / BR-U2-6
    merged, _warnings = merge_regions([h.model_copy(deep=True) for h in hints])
    for h in hints:
        same = [
            m
            for m in merged
            if m.name.strip().lower() == h.name.strip().lower() and str(m.level) == str(h.level)
        ]
        assert len(same) == 1
        m = same[0]
        for hint in h.attributes.get("connection_hints", []):
            assert hint in m.attributes.get("connection_hints", [])
        for adj in h.attributes.get("adjacent_names", []):
            assert adj in m.attributes.get("adjacent_names", [])
        if "parent_name" in h.attributes:
            assert "parent_name" in m.attributes  # first value kept, never dropped


@given(entities_with_refs())
def test_remapped_references_resolve(data) -> None:  # TP-U2-4 / BR-U2-7
    entities, relations, knowledge = data
    merged, id_map = merge_entities([e.model_copy(deep=True) for e in entities])
    kept, knowledge2, warnings = remap_entity_refs(relations, knowledge, merged, id_map)
    known = {e.id for e in merged}
    assert all(r.source_id in known and r.target_id in known for r in kept)
    assert all(eid in known for k in knowledge2 for eid in k.about_entity_ids)
    assert len(kept) == len(relations) and warnings == []  # nothing dangling after remap
    assert set(id_map) | known >= {e.id for e in entities}


def test_scalar_attribute_conflict_keeps_first_and_warns() -> None:  # EX-6
    a = Region(
        world_id="w",
        name="Riverton",
        level=RegionLevel.TOWN,
        attributes={"parent_name": "Greenvale", "terrain_kind": "river"},
        provenance=_prov(),
    )
    b = Region(
        world_id="w",
        name="riverton",
        level=RegionLevel.TOWN,
        attributes={"parent_name": "Frostreach", "adjacent_names": ["Highcrag"]},
        provenance=_prov(),
    )
    merged, warnings = merge_regions([a, b])
    assert len(merged) == 1 and merged[0].attributes["parent_name"] == "Greenvale"
    assert merged[0].attributes["adjacent_names"] == ["Highcrag"]
    assert len(warnings) == 1 and "parent_name" in warnings[0].message


def test_dangling_relation_is_dropped_with_warning() -> None:  # EX-7
    e = Entity(world_id="w", name="Keep", entity_type=EntityType.PLACE, provenance=_prov())
    from locus.shared.models import Relation

    rel = Relation(
        world_id="w", source_id=e.id, target_id="ghost", relation_type="near", provenance=_prov()
    )
    kept, _k, warnings = remap_entity_refs([rel], [], [e], {})
    assert kept == [] and warnings and "dangling" in warnings[0].message


def test_bad_base64_is_an_error_but_other_inputs_proceed() -> None:  # EX-9 / BR-U2-10
    from locus.world.ingestion.concept_art_ingestor import ConceptArtIngestor
    from locus.world.ingestion.map_image_ingestor import MapImageIngestor
    from locus.world.ingestion.schemas import ArtExtraction, MapExtraction

    svc = IngestionService(
        text=TextIngestor(_FakeLLM(TextExtraction())),
        map_image=MapImageIngestor(_FakeVLM(), _FakeLLM(MapExtraction())),
        structured_map=StructuredMapIngestor(),
        concept_art=ConceptArtIngestor(_FakeVLM(), _FakeLLM(ArtExtraction())),
    )
    good = base64.b64encode(b"png-bytes").decode("ascii")
    inputs = WorldInputs(
        map_images=["%%%not-base64%%%", good],
        structured_maps=[{"regions": [{"name": "Z", "level": "town"}]}],
    )
    res = svc.ingest_all("w", inputs)
    errors = [w for w in res.warnings if w.severity == "error"]
    assert len(errors) == 1 and "map image #0" in errors[0].message
    assert [r.name for r in res.region_hints] == ["Z"]  # the structured map was processed


def test_level_less_structured_map_infers_a_hierarchy() -> None:  # review #5
    from locus.world.topology.hierarchy import assign_hierarchy

    doc = {
        "regions": [
            {"name": "Kingdom"},
            {"name": "Shire", "parent": "Kingdom"},
            {"name": "Riverton", "parent": "Shire"},
        ]
    }
    res = StructuredMapIngestor().parse(doc, world_id="w")
    levels = {r.name: str(r.level) for r in res.region_hints}
    assert levels == {"Kingdom": "continent", "Shire": "province", "Riverton": "town"}
    assert sum("inferred" in w.message for w in res.warnings) == 3
    regions, warnings = assign_hierarchy(res.region_hints)
    by_name = {r.name: r for r in regions}
    assert by_name["Riverton"].parent_id == by_name["Shire"].id
    assert by_name["Shire"].parent_id == by_name["Kingdom"].id and not warnings

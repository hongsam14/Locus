"""U2 Ingestion tests — pure mapping/parsing + mocked LLM/VLM ingestors."""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from locus.ingestion import (
    IngestionService,
    StructuredMapIngestor,
    TextIngestor,
    WorldInputs,
    merge_results,
)
from locus.ingestion.concept_art_ingestor import ConceptArtIngestor
from locus.ingestion.map_image_ingestor import MapImageIngestor
from locus.ingestion.mapping import (
    CONCEPT_ART_CONFIDENCE_CAP,
    merge_entities,
    normalize_name,
)
from locus.ingestion.schemas import (
    ArtExtraction,
    ExtractedEntity,
    ExtractedRelation,
    MapExtraction,
    TextExtraction,
)
from locus.models import Entity, EntityType, IngestionResult, Provenance, SourceKind


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


# --------------------------------------------------------------------------- #
# Fakes
# --------------------------------------------------------------------------- #
class _FakeLLM:
    def __init__(self, structured_return) -> None:
        self._ret = structured_return

    def complete(self, prompt, *, system=None):  # pragma: no cover
        return ""

    def structured(self, prompt, schema, *, system=None):
        return self._ret


class _FakeVLM:
    def analyze_image(self, image, prompt, *, system=None):
        return "a description"


# --------------------------------------------------------------------------- #
# Pure mapping / merge
# --------------------------------------------------------------------------- #
@given(st.text())
def test_normalize_name_idempotent(s: str) -> None:
    assert normalize_name(normalize_name(s)) == normalize_name(s)


def test_normalize_name_collapses() -> None:
    assert normalize_name("  Old   Town ") == "old town"


def test_merge_entities_dedup_keeps_max_confidence() -> None:
    a = Entity(
        world_id="w",
        name="Old Town",
        entity_type=EntityType.PLACE,
        confidence=0.4,
        provenance=_prov(),
    )
    b = Entity(
        world_id="w",
        name="old  town",
        entity_type=EntityType.PLACE,
        confidence=0.9,
        provenance=_prov(),
    )
    merged = merge_entities([a, b])
    assert len(merged) == 1
    assert merged[0].confidence == 0.9


def test_merge_entities_distinct_types_not_merged() -> None:
    a = Entity(
        world_id="w", name="Sage", entity_type=EntityType.PERSON, confidence=0.8, provenance=_prov()
    )
    b = Entity(
        world_id="w", name="Sage", entity_type=EntityType.OBJECT, confidence=0.8, provenance=_prov()
    )
    assert len(merge_entities([a, b])) == 2


# --------------------------------------------------------------------------- #
# Structured map parsing (pure)
# --------------------------------------------------------------------------- #
def test_locus_map_json_parsed() -> None:
    doc = {
        "regions": [
            {"name": "Northland", "level": "continent"},
            {"name": "Rivertown", "level": "town", "parent": "Northland"},
        ],
        "connections": [{"from": "Rivertown", "to": "Northland", "kind": "route"}],
    }
    res = StructuredMapIngestor().parse(doc, world_id="w")
    assert len(res.region_hints) == 2
    assert not res.errors
    # connection hints preserved (edges built later in U3)
    assert any("connection_hints" in r.attributes for r in res.region_hints)


def test_locus_map_invalid_items_reported_but_others_kept() -> None:
    doc = {
        "regions": [
            {"level": "town"},  # missing name
            {"name": "Goodtown", "level": "bogus"},  # invalid level
            {"name": "Valid", "level": "district"},
        ]
    }
    res = StructuredMapIngestor().parse(doc, world_id="w")
    assert len(res.region_hints) == 1
    assert res.region_hints[0].name == "Valid"
    assert len(res.errors) == 2


def test_geojson_parsed() -> None:
    doc = {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {"name": "Hillvale", "level": "province"},
                "geometry": {"type": "Polygon", "coordinates": []},
            },
        ],
    }
    res = StructuredMapIngestor().parse(doc, world_id="w")
    assert len(res.region_hints) == 1
    assert res.region_hints[0].name == "Hillvale"


# --------------------------------------------------------------------------- #
# Ingestors (mocked providers)
# --------------------------------------------------------------------------- #
def test_text_ingestor_maps_and_resolves_relations() -> None:
    extraction = TextExtraction(
        entities=[
            ExtractedEntity(name="Mara", entity_type=EntityType.PERSON, confidence=0.9),
            ExtractedEntity(name="Rivertown", entity_type=EntityType.PLACE, confidence=0.3),
        ],
        relations=[
            ExtractedRelation(source_name="Mara", target_name="Rivertown", relation_type="lives_in")
        ],
    )
    res = TextIngestor(_FakeLLM(extraction)).extract("note", world_id="w")
    assert len(res.entities) == 2
    assert len(res.relations) == 1  # both endpoints resolved
    # low-confidence Rivertown (0.3 < 0.5) flagged
    assert len(res.low_confidence_item_ids) == 1


def test_text_ingestor_empty_memo() -> None:
    res = TextIngestor(_FakeLLM(TextExtraction())).extract("   ", world_id="w")
    assert res.errors and "empty" in res.errors[0]


def test_text_ingestor_graceful_on_provider_error() -> None:
    class _BoomLLM:
        def structured(self, *a, **k):
            raise RuntimeError("api down")

    res = TextIngestor(_BoomLLM()).extract("note", world_id="w")
    assert res.errors and "failed" in res.errors[0]
    assert res.entities == []


def test_concept_art_confidence_capped() -> None:
    art = ArtExtraction(clues=[ExtractedEntity(name="Ruined Tower", confidence=0.95)])
    res = ConceptArtIngestor(_FakeVLM(), _FakeLLM(art)).extract(b"img", world_id="w")
    assert res.entities[0].confidence <= CONCEPT_ART_CONFIDENCE_CAP
    assert res.entities[0].id in res.low_confidence_item_ids


def test_map_image_ingestor_barrier_hint_and_area_promotion() -> None:
    from locus.ingestion.schemas import ExtractedRegion, ExtractedTerrain
    from locus.models import RegionLevel

    mp = MapExtraction(
        regions=[
            ExtractedRegion(name="East Reach", level=RegionLevel.PROVINCE, x=0.8, y=0.5),
            ExtractedRegion(name="West Reach", level=RegionLevel.PROVINCE, x=0.2, y=0.5),
        ],
        terrain=[
            # barrier kind -> A-B connection hint, NOT promoted (no entity, no region)
            ExtractedTerrain(
                name="Spine Mts",
                kind="mountain",
                between=["East Reach", "West Reach"],
                confidence=0.7,
            ),
            # area kind -> promoted to a Region(level=TERRAIN) with position (FR-IM4.1)
            ExtractedTerrain(
                name="Mire Swamp",
                kind="swamp",
                between=["East Reach"],
                x=0.6,
                y=0.6,
                confidence=0.7,
            ),
        ],
    )
    res = MapImageIngestor(_FakeVLM(), _FakeLLM(mp)).extract(b"img", world_id="w")
    # no orphan terrain entities anymore (BR-B4)
    assert res.entities == []
    # 2 named regions + 1 promoted terrain region
    levels = {r.name: r.level for r in res.region_hints}
    assert levels["Mire Swamp"] == RegionLevel.TERRAIN.value
    swamp = next(r for r in res.region_hints if r.name == "Mire Swamp")
    assert swamp.position is not None and swamp.attributes["terrain_kind"] == "swamp"
    # connection hints: mountain barrier (East-West) + swamp adjacency (Mire Swamp-East Reach)
    hints = res.region_hints[0].attributes.get("connection_hints", [])
    assert any(h.get("terrain_kind") == "mountain" for h in hints)
    assert any(h.get("from") == "Mire Swamp" for h in hints)


def test_map_image_ingestor_barrier_wrong_arity_surfaced() -> None:
    """FR-H8 / BR-H2-3: a barrier terrain not bordering exactly 2 regions is
    reported in errors instead of being silently dropped."""
    from locus.ingestion.schemas import ExtractedRegion, ExtractedTerrain
    from locus.models import RegionLevel

    mp = MapExtraction(
        regions=[
            ExtractedRegion(name="East Reach", level=RegionLevel.PROVINCE, x=0.8, y=0.5),
            ExtractedRegion(name="West Reach", level=RegionLevel.PROVINCE, x=0.2, y=0.5),
            ExtractedRegion(name="North Reach", level=RegionLevel.PROVINCE, x=0.5, y=0.1),
        ],
        terrain=[
            # barrier bordering 3 regions -> not a 2-region connection -> surfaced
            ExtractedTerrain(
                name="Great Range",
                kind="mountain",
                between=["East Reach", "West Reach", "North Reach"],
                confidence=0.7,
            ),
            # barrier bordering 1 region -> also surfaced
            ExtractedTerrain(
                name="Lone Ridge", kind="mountain", between=["East Reach"], confidence=0.7
            ),
        ],
    )
    res = MapImageIngestor(_FakeVLM(), _FakeLLM(mp)).extract(b"img", world_id="w")
    assert len(res.errors) == 2
    assert all("skipped" in e for e in res.errors)
    # no barrier connection hints generated for the wrong-arity terrain
    hints = res.region_hints[0].attributes.get("connection_hints", []) if res.region_hints else []
    assert not any(h.get("terrain_kind") == "mountain" for h in hints)


# --------------------------------------------------------------------------- #
# Service merge
# --------------------------------------------------------------------------- #
def test_merge_results_dedup_across_inputs() -> None:
    e1 = Entity(
        world_id="w", name="Keep", entity_type=EntityType.PLACE, confidence=0.5, provenance=_prov()
    )
    e2 = Entity(
        world_id="w", name="keep", entity_type=EntityType.PLACE, confidence=0.8, provenance=_prov()
    )
    r1 = IngestionResult(world_id="w", entities=[e1], errors=["x"])
    r2 = IngestionResult(world_id="w", entities=[e2])
    merged = merge_results("w", [r1, r2])
    assert len(merged.entities) == 1
    assert merged.entities[0].confidence == 0.8
    assert merged.errors == ["x"]


def test_ingestion_service_routes_structured_map() -> None:
    svc = IngestionService(
        text=TextIngestor(_FakeLLM(TextExtraction())),
        map_image=MapImageIngestor(_FakeVLM(), _FakeLLM(MapExtraction())),
        structured_map=StructuredMapIngestor(),
        concept_art=ConceptArtIngestor(_FakeVLM(), _FakeLLM(ArtExtraction())),
    )
    inputs = WorldInputs(structured_maps=[{"regions": [{"name": "Z", "level": "town"}]}])
    res = svc.ingest_all("w", inputs)
    assert len(res.region_hints) == 1 and res.region_hints[0].name == "Z"

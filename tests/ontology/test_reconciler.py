"""Unit-B EntityReconciler tests — cross-source merge + orphan connect (mocked)."""

from __future__ import annotations

from locus.models import Entity, EntityType, Provenance, Region, RegionLevel, Relation, SourceKind
from locus.ontology.reconciler import EntityReconciler
from locus.ontology.schemas import EntityMatchVerdict, RegionPickVerdict


def _prov(by: str) -> Provenance:
    return Provenance(source=SourceKind.INPUT, generated_by=by)


def _entity(name, by="llm", located_in=None) -> Entity:
    return Entity(
        world_id="w",
        name=name,
        entity_type=EntityType.PLACE,
        located_in=located_in,
        provenance=_prov(by),
    )


def _region(name) -> Region:
    return Region(world_id="w", name=name, level=RegionLevel.TOWN, provenance=_prov("llm"))


class _Embed:
    def embed(self, texts):
        # deterministic 2-d vectors keyed by first token; unknown -> [0,0]
        table = {
            "Rivertown": [1.0, 0.0],
            "Rivrton": [0.98, 0.02],
            "Keep": [0.0, 1.0],
        }
        return [table.get(t.split()[0], [0.5, 0.5]) for t in texts]


class _LLM:
    def __init__(self, *, same=False, region_name=None) -> None:
        self._same = same
        self._region_name = region_name

    def structured(self, prompt, schema, *, system=None):
        if schema is EntityMatchVerdict:
            return EntityMatchVerdict(same_entity=self._same)
        if schema is RegionPickVerdict:
            return RegionPickVerdict(region_name=self._region_name)
        raise AssertionError("unexpected schema")


def test_merge_vlm_into_non_vlm_canonical() -> None:
    # VLM mis-spelled "Rivrton" should merge into text-source "Rivertown" (non-VLM wins, BR-B6)
    canonical = _entity("Rivertown", by="llm")
    vlm = _entity("Rivrton", by="vlm")
    rec = EntityReconciler(_Embed(), _LLM(same=True)).reconcile(
        [canonical, vlm], [], [], about_entity_ids=set()
    )
    ids = {e.id for e in rec.entities}
    assert canonical.id in ids and vlm.id not in ids  # VLM absorbed
    assert rec.remap[vlm.id] == canonical.id


def test_relations_remapped_after_merge() -> None:
    canonical = _entity("Rivertown", by="llm")
    vlm = _entity("Rivrton", by="vlm")
    other = _entity("Keep", by="llm")
    rel = Relation(
        world_id="w",
        source_id=other.id,
        target_id=vlm.id,
        relation_type="near",
        provenance=_prov("llm"),
    )
    rec = EntityReconciler(_Embed(), _LLM(same=True)).reconcile(
        [canonical, vlm, other], [], [rel], about_entity_ids=set()
    )
    assert rec.relations[0].target_id == canonical.id  # remapped


def test_orphan_attached_to_region_via_llm() -> None:
    orphan = _entity("Ruined Tower", by="vlm")
    region = _region("East Reach")
    rec = EntityReconciler(_Embed(), _LLM(same=False, region_name="East Reach")).reconcile(
        [orphan], [region], [], about_entity_ids=set()
    )
    assert orphan.located_in == region.id  # LOCATED_IN assigned (BR-B8)
    assert rec.unconnected_entity_ids == []


def test_orphan_unconnected_when_no_provider() -> None:
    orphan = _entity("Mystery", by="vlm")
    region = _region("East Reach")
    rec = EntityReconciler(embedding=None, llm=None).reconcile(
        [orphan], [region], [], about_entity_ids=set()
    )
    assert rec.unconnected_entity_ids == [orphan.id]  # graceful -> augmentation candidate
    assert orphan.located_in is None


def test_already_connected_entity_left_alone() -> None:
    e = _entity("Keep", by="vlm", located_in="r1")
    rec = EntityReconciler(_Embed(), _LLM()).reconcile([e], [], [], about_entity_ids=set())
    assert rec.unconnected_entity_ids == []
    assert e.located_in == "r1"

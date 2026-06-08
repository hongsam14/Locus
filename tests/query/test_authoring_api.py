"""U9 authoring API tests — FastAPI TestClient with mocked services."""

from __future__ import annotations

from fastapi.testclient import TestClient

from api.main import create_app
from locus.models import BuildReport, Knowledge, Provenance, Region, RegionLevel, SourceKind
from locus.storage.base import Node


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


class _Orchestrator:
    def build_world(self, world_id, inputs):
        return BuildReport(world_id=world_id, regions_created=2, knowledge_created=3)


class _Editor:
    def __init__(self) -> None:
        self.deleted: list = []

    def upsert_region(self, region):
        return region

    def upsert_knowledge(self, knowledge):
        return knowledge

    def delete_node(self, world_id, node_id):
        self.deleted.append(node_id)


class _GraphRepo:
    def find_nodes(self, world_id, label, filters=None):
        if label == "Region":
            return [Node(id="r1", label="Region", world_id=world_id, properties={})]
        return []


def _client(editor=None) -> TestClient:
    return TestClient(
        create_app(
            orchestrator=_Orchestrator(),
            graph_editor=editor or _Editor(),
            graph_repo=_GraphRepo(),
        )
    )


def test_build_world_endpoint() -> None:
    body = {"memos": ["a note"], "structured_maps": [], "map_images": [], "concept_arts": []}
    r = _client().post("/api/authoring/worlds/w/build", json=body)
    assert r.status_code == 200
    assert r.json()["regions_created"] == 2


def test_graph_summary_endpoint() -> None:
    r = _client().get("/api/authoring/worlds/w/graph")
    assert r.status_code == 200
    assert r.json()["region_count"] == 1
    assert r.json()["region_ids"] == ["r1"]


def test_upsert_region_endpoint() -> None:
    region = Region(world_id="w", name="Town", level=RegionLevel.TOWN, provenance=_prov())
    r = _client().put(f"/api/authoring/worlds/w/regions/{region.id}", json=region.model_dump())
    assert r.status_code == 200
    assert r.json()["name"] == "Town"


def test_delete_node_endpoint() -> None:
    editor = _Editor()
    r = _client(editor).delete("/api/authoring/worlds/w/nodes/n9")
    assert r.status_code == 204
    assert editor.deleted == ["n9"]


def test_upsert_knowledge_endpoint() -> None:
    k = Knowledge(world_id="w", statement="fact", provenance=_prov())
    r = _client().put(f"/api/authoring/worlds/w/knowledge/{k.id}", json=k.model_dump())
    assert r.status_code == 200
    assert r.json()["statement"] == "fact"

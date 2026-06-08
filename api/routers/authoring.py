"""Internal authoring router — build / edit / wiki (U9, Q2=C). No auth (MVP)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response

from locus.augmentation.types import AugmentationAnswer, AugmentationSession, ChangeSet
from locus.commonsense_wiki import load_bundled_realworld
from locus.demo import load_demo_world
from locus.ingestion.service import WorldInputs
from locus.models import (
    BuildReport,
    GraphSummary,
    Knowledge,
    Region,
    WikiBuildReport,
    WikiPrior,
)

router = APIRouter(prefix="/api/authoring", tags=["authoring"])


def _svc(request: Request, name: str):
    svc = getattr(request.app.state, name, None)
    if svc is None:
        raise HTTPException(status_code=503, detail=f"{name} not configured")
    return svc


@router.post("/worlds/{world_id}/build", response_model=BuildReport)
def build_world(world_id: str, inputs: WorldInputs, request: Request) -> BuildReport:
    return _svc(request, "orchestrator").build_world(world_id, inputs)


@router.post("/worlds/{world_id}/build/demo", response_model=BuildReport)
def build_demo_world(world_id: str, request: Request, with_map: bool = True) -> BuildReport:
    """Build the bundled demo world (memo + structured map [+ map image for VLM])."""
    return _svc(request, "orchestrator").build_world(
        world_id, load_demo_world(include_map=with_map)
    )


@router.post("/wiki/build", response_model=WikiBuildReport)
def build_wiki(request: Request, inputs: WorldInputs | None = None) -> WikiBuildReport:
    return _svc(request, "wiki_builder").build_wiki(inputs or load_bundled_realworld())


@router.get("/worlds/{world_id}/graph", response_model=GraphSummary)
def graph_summary(world_id: str, request: Request) -> GraphSummary:
    graph = _svc(request, "graph_repo")
    regions = graph.find_nodes(world_id, "Region")
    return GraphSummary(
        world_id=world_id,
        region_count=len(regions),
        entity_count=len(graph.find_nodes(world_id, "Entity")),
        knowledge_count=len(graph.find_nodes(world_id, "Knowledge")),
        prior_count=len(graph.find_nodes(world_id, "WikiPrior")),
        region_ids=[n.id for n in regions],
    )


@router.get("/worlds/{world_id}/export")
def export_world(world_id: str, request: Request) -> dict:
    """Full world graph (regions+connections+knowledge+scopes) for the UI overlay."""
    return _svc(request, "exporter").export_world(world_id)


@router.post("/wiki/priors", response_model=WikiPrior)
def upsert_prior(prior: WikiPrior, request: Request) -> WikiPrior:
    return _svc(request, "wiki_admin").upsert_prior(prior)


@router.put("/worlds/{world_id}/regions/{region_id}", response_model=Region)
def upsert_region(world_id: str, region_id: str, region: Region, request: Request) -> Region:
    return _svc(request, "graph_editor").upsert_region(region)


@router.put("/worlds/{world_id}/knowledge/{knowledge_id}", response_model=Knowledge)
def upsert_knowledge(
    world_id: str, knowledge_id: str, knowledge: Knowledge, request: Request
) -> Knowledge:
    return _svc(request, "graph_editor").upsert_knowledge(knowledge)


@router.delete("/worlds/{world_id}/nodes/{node_id}", status_code=204)
def delete_node(world_id: str, node_id: str, request: Request) -> Response:
    _svc(request, "graph_editor").delete_node(world_id, node_id)
    return Response(status_code=204)


# --- Knowledge augmentation Q&A (U7) ---------------------------------------- #
@router.post("/worlds/{world_id}/augment/session", response_model=AugmentationSession)
def start_augmentation(world_id: str, request: Request) -> AugmentationSession:
    return _svc(request, "augmentation_service").start_session(world_id)


@router.post("/augment/{session_id}/answer", response_model=ChangeSet)
def submit_augmentation_answer(
    session_id: str, answer: AugmentationAnswer, request: Request
) -> ChangeSet:
    try:
        return _svc(request, "augmentation_service").submit_answer(session_id, answer)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/augment/{session_id}/revert", status_code=204)
def revert_augmentation(session_id: str, change_id: str, request: Request) -> Response:
    try:
        _svc(request, "augmentation_service").revert(session_id, change_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(status_code=204)

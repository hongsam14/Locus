"""STATUS: in-progress — LangGraph view of the detect/ask/apply loop; not wired into any service yet.

LangGraph representation of the augmentation loop (U7, AD-CL1=A).

The human-in-the-loop loop is driven by AugmentationService; this builds an
optional LangGraph view (detect -> generate) over the same engine. LangGraph is
imported lazily so the module/tests work without it installed.
"""

from __future__ import annotations

from typing import TypedDict

from locus.shared.models import WorldSnapshot
from locus.world.augmentation.engine import AugmentationEngine
from locus.world.augmentation.run_store import RunState
from locus.world.augmentation.types import AugmentationRun


class AugState(TypedDict, total=False):
    world_id: str
    issues: list
    questions: list
    snapshot: WorldSnapshot
    run: RunState


def build_detection_graph(engine: AugmentationEngine):
    """Compile a LangGraph: detect -> generate. Raises ImportError if langgraph absent."""
    from langgraph.graph import END, StateGraph

    def _detect(state: AugState) -> AugState:
        run = RunState(run=AugmentationRun(world_id=state["world_id"]))
        issues, snapshot = engine.detect(state["world_id"], run, lambda: False)
        return {**state, "issues": issues, "snapshot": snapshot, "run": run}

    def _generate(state: AugState) -> AugState:
        questions = engine.questions(
            state.get("issues", []), state["snapshot"], state["run"], lambda: False
        )
        return {**state, "questions": questions}

    graph = StateGraph(AugState)
    graph.add_node("detect", _detect)
    graph.add_node("generate", _generate)
    graph.set_entry_point("detect")
    graph.add_edge("detect", "generate")
    graph.add_edge("generate", END)
    return graph.compile()

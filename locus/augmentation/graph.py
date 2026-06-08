"""LangGraph representation of the augmentation loop (U7, AD-CL1=A).

The human-in-the-loop loop is driven by AugmentationService; this builds an
optional LangGraph view (detect -> generate) over the same engine. LangGraph is
imported lazily so the module/tests work without it installed.
"""

from __future__ import annotations

from typing import TypedDict

from .engine import AugmentationEngine


class AugState(TypedDict, total=False):
    world_id: str
    issues: list
    questions: list


def build_detection_graph(engine: AugmentationEngine):
    """Compile a LangGraph: detect -> generate. Raises ImportError if langgraph absent."""
    from langgraph.graph import END, StateGraph

    def _detect(state: AugState) -> AugState:
        return {**state, "issues": engine.detect_issues(state["world_id"])}

    def _generate(state: AugState) -> AugState:
        return {**state, "questions": engine.generate_questions(state.get("issues", []))}

    graph = StateGraph(AugState)
    graph.add_node("detect", _detect)
    graph.add_node("generate", _generate)
    graph.set_entry_point("detect")
    graph.add_edge("detect", "generate")
    graph.add_edge("generate", END)
    return graph.compile()

"""Test composition of the play services through the production root (review U1 #15).

``compose_play`` wraps ``locus.play.wiring.assemble_play`` with the fakes the tests
already build (in-memory repo, fake loader, fake LLM generator), so a wiring
regression in the composition root shows up offline.
"""

from __future__ import annotations

from locus.knowledge.consensus import DEFAULT_PARAMS, ConsensusParams
from locus.knowledge.query import QueryEngine
from locus.knowledge.wiring import KnowledgeContainer
from locus.play.event.suggester import EventSuggester
from locus.play.rumor.dynamics import DEFAULT_RUMOR_DYNAMICS
from locus.play.rumor.generator import RumorGenerator
from locus.play.turn.executor import SyncTurnExecutor
from locus.play.wiring import PlayContainer, assemble_play
from locus.shared.config import Settings
from locus.shared.config.tuning import PlayTuning
from locus.shared.wiring import SharedContainer


class _NoSuggestLLM:
    """Stands in for the LLM when a test passes no suggester: suggesting is not exercised."""

    def structured(self, prompt, schema, *, system=None):  # pragma: no cover
        raise AssertionError("event suggestion is not wired in this test")

    def complete(self, prompt, *, system=None):  # pragma: no cover
        raise AssertionError("LLM completion is not wired in this test")


def compose_play(
    repo,
    generator: RumorGenerator,
    loader,
    params: ConsensusParams = DEFAULT_PARAMS,
    *,
    suggester: EventSuggester | None = None,
    tuning: PlayTuning = DEFAULT_RUMOR_DYNAMICS,
    executor=None,
) -> PlayContainer:
    # Default to the inline executor: letting `assemble_play` start its daemon thread
    # leaked one per composition across the suite (code review U4-2).
    shared = SharedContainer(settings=Settings.model_construct(), graph=None, llm=None)
    knowledge = KnowledgeContainer(
        loader=None, cache=loader, query=QueryEngine(loader, params), params=params
    )
    return assemble_play(
        shared,
        knowledge,
        repo=repo,
        generator=generator,
        suggester=suggester or EventSuggester(_NoSuggestLLM()),
        tuning=tuning,
        executor=executor or SyncTurnExecutor(),
    )

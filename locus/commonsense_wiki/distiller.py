"""PriorDistiller — distill real-world ingestion into WikiPriors (U6, Q3=A)."""

from __future__ import annotations

from ..llm.base import LLMProvider
from ..models import (
    EntityType,
    IngestionResult,
    Provenance,
    RegionTopology,
    SourceKind,
    WikiPrior,
)
from .schemas import PriorBatch

_SYSTEM = (
    "You distill general, reusable real-world common-sense priors (geography, "
    "geology, climate, logistics) as condition->effect rules, plus salient facts. "
    "Keep each prior general enough to apply to fictional worlds."
)


class PriorDistiller:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def distill(
        self, ingestion: IngestionResult, topology: RegionTopology, *, world_id: str
    ) -> list[WikiPrior]:
        context = self._context(ingestion, topology)
        try:
            batch = self._llm.structured(self._prompt(context), PriorBatch, system=_SYSTEM)
        except Exception:
            return []  # graceful (BR-U6-8)

        priors: list[WikiPrior] = []
        for s in batch.items:
            if not s.condition or not s.effect:
                continue  # BR-U6-4
            priors.append(
                WikiPrior(
                    prior_type=s.prior_type,
                    condition=s.condition,
                    effect=s.effect,
                    description=s.description,
                    confidence=s.confidence,
                    provenance=Provenance(source=SourceKind.INFERRED_WIKI, generated_by="llm"),
                )
            )
        return priors

    @staticmethod
    def _context(ingestion: IngestionResult, topology: RegionTopology) -> str:
        terrains = [e.name for e in ingestion.entities if e.entity_type == EntityType.TERRAIN]
        regions = [r.name for r in topology.regions]
        facts = [k.statement for k in ingestion.knowledge[:20]]
        return f"regions={regions[:30]}; terrain={terrains[:30]}; " f"facts={facts}"

    @staticmethod
    def _prompt(context: str) -> str:
        return (
            "From the following real-world reference material, produce reusable priors "
            "(condition->effect rules + key facts).\n\n" + context
        )

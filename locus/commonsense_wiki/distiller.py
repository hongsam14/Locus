"""PriorDistiller — distill a world's ingestion into WikiPriors (FR-IM1.3).

Generalized from the old real-world-only distiller: applies to any world and
classifies each prior into the shared ``WikiDomain`` taxonomy in the same call.
"""

from __future__ import annotations

from ..llm.base import LLMProvider
from ..models import (
    EntityType,
    IngestionResult,
    Provenance,
    RegionTopology,
    SourceKind,
    WikiDomain,
    WikiPrior,
)
from .schemas import PriorBatch

_SYSTEM = (
    "You distill general, reusable common-sense priors (geography, geology, "
    "climate, ecology, economy, logistics, culture, history, politics, religion, "
    "military, technology) as condition->effect rules, plus salient facts. Keep "
    "each prior general enough to apply across worlds, and tag each with one or "
    "more domains from the shared taxonomy."
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
                    world_id=world_id,
                    prior_type=s.prior_type,
                    condition=s.condition,
                    effect=s.effect,
                    domains=s.domains or [WikiDomain.OTHER],  # BR-A5
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

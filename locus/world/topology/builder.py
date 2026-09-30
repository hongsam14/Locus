"""TopologyBuilder — IngestionResult -> RegionTopology (U3, FR-B)."""

from __future__ import annotations

from dataclasses import dataclass, field

from locus.shared.models import (
    BuildWarning,
    ConnectionEdge,
    ConnectionKind,
    IngestionResult,
    Provenance,
    Region,
    RegionTopology,
    SourceKind,
)
from locus.world.topology.hierarchy import assign_hierarchy
from locus.world.topology.naming import index_by_name, resolve_region
from locus.world.topology.weights import compute_weight
from locus.world.wiki.base import CommonsenseWiki


def _coerce_kind(value: str | None) -> str:
    try:
        return ConnectionKind(str(value)).value
    except ValueError:
        return ConnectionKind.ADJACENT.value


@dataclass
class TopologyBuild:
    """What the topology stage hands the builder: the topology plus every warning it
    raised (hierarchy, unresolved or ambiguous hints) — RE A13 / BR-U2-13."""

    topology: RegionTopology
    warnings: list[BuildWarning] = field(default_factory=list)


def collect_connection_candidates(
    regions: list[Region],
) -> tuple[list[dict], list[BuildWarning]]:
    """Gather connection hints from region attributes; resolve names -> ids
    (deterministically, BR-U2-8).

    Returns (candidates, warnings). Each candidate:
    ``{a_id, b_id, kind, terrain_kinds: [..]}`` (unordered pair, deduped).
    """
    warnings: list[BuildWarning] = []
    by_name = index_by_name(regions)
    candidates: dict[frozenset, dict] = {}

    def resolve(name: str | None, level: str | None) -> str | None:
        if not name:
            return None
        region, warning = resolve_region(name, by_name, role="hint", level=level)
        if warning is not None:
            warnings.append(warning)
        return region.id if region else None

    for region in regions:
        for hint in region.attributes.get("connection_hints", []) or []:
            frm, to = hint.get("from"), hint.get("to")
            a_id = resolve(frm, hint.get("from_level"))
            b_id = resolve(to, hint.get("to_level"))
            if a_id is None or b_id is None or a_id == b_id:
                warnings.append(
                    BuildWarning(
                        stage="topology",
                        item_id=region.id,
                        message=f"connection hint unresolved/self: {frm!r}->{to!r}",
                    )
                )
                continue
            key = frozenset((a_id, b_id))
            kind = _coerce_kind(hint.get("kind"))
            terrain_kind = hint.get("terrain_kind")
            if key in candidates:
                cand = candidates[key]
                # stronger constraint wins for kind ordering blocked<river<route<adjacent
                cand["kind"] = _stronger(cand["kind"], kind)
                if terrain_kind:
                    cand["terrain_kinds"].append(terrain_kind)
            else:
                candidates[key] = {
                    "a_id": a_id,
                    "b_id": b_id,
                    "kind": kind,
                    "terrain_kinds": [terrain_kind] if terrain_kind else [],
                }
    return list(candidates.values()), warnings


_KIND_STRENGTH = {"blocked": 0, "river": 1, "route": 2, "adjacent": 3}


def _stronger(a: str, b: str) -> str:
    """Pick the more restrictive (lower-strength) connection kind."""
    return a if _KIND_STRENGTH.get(a, 9) <= _KIND_STRENGTH.get(b, 9) else b


class TopologyBuilder:
    def __init__(self, wiki: CommonsenseWiki | None = None) -> None:
        self._wiki = wiki

    def set_wiki(self, wiki: CommonsenseWiki | None) -> None:
        """Inject the world-scoped wiki at build time (single-world, BR-A9)."""
        self._wiki = wiki

    def build(self, ingestion: IngestionResult, *, world_id: str) -> TopologyBuild:
        regions = list(ingestion.region_hints)
        _, warnings = assign_hierarchy(regions)
        candidates, hint_warnings = collect_connection_candidates(regions)
        warnings = warnings + hint_warnings

        connections: list[ConnectionEdge] = []
        for cand in candidates:
            weight = compute_weight(cand["kind"], cand["terrain_kinds"])
            rationale, prior_ref, used_wiki = self._wiki_rationale(cand["terrain_kinds"])
            source = SourceKind.INFERRED if used_wiki else SourceKind.INPUT
            prov = Provenance(source=source, generated_by="topology", note=rationale)
            for a, b in ((cand["a_id"], cand["b_id"]), (cand["b_id"], cand["a_id"])):
                connections.append(
                    ConnectionEdge(
                        world_id=world_id,
                        source_region_id=a,
                        target_region_id=b,
                        kind=cand["kind"],
                        weight=weight,
                        rationale=rationale,
                        wiki_prior_ref=prior_ref,
                        provenance=prov,
                    )
                )
        return TopologyBuild(
            topology=RegionTopology(world_id=world_id, regions=regions, connections=connections),
            warnings=warnings,
        )

    def _wiki_rationale(self, terrain_kinds: list[str]) -> tuple[str | None, str | None, bool]:
        if not self._wiki or not terrain_kinds:
            return None, None, False
        notes: list[str] = []
        prior_ref: str | None = None
        for tk in terrain_kinds:
            try:
                priors = self._wiki.lookup_terrain_rule(tk)
            except Exception:  # graceful degrade (BR-U3-13)
                continue
            for p in priors:
                notes.append(p.effect)
                prior_ref = prior_ref or p.id
        if not notes:
            return None, None, False
        return "; ".join(notes), prior_ref, True

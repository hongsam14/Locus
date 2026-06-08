"""Issue detectors (U7, CL5=A/B/C). Pure where possible; wiki_conflict uses LLM."""

from __future__ import annotations

from ..models import KnowledgeGraph, RegionTopology, ScopeType
from .types import Issue, IssueType

LOW_CONFIDENCE_THRESHOLD = 0.5


def detect_gaps(kg: KnowledgeGraph, topo: RegionTopology) -> list[Issue]:
    """Empty regions (no direct knowledge) + dangling relations. Pure."""
    issues: list[Issue] = []

    direct_regions = {s.region_id for s in kg.scopes if str(s.scope_type) == ScopeType.DIRECT.value}
    for region in topo.regions:
        if region.id not in direct_regions:
            issues.append(
                Issue(
                    type=IssueType.GAP,
                    description=f"Region '{region.name}' has no direct knowledge.",
                    target_ids=[region.id],
                    region_id=region.id,
                    severity=0.6,
                )
            )

    entity_ids = {e.id for e in kg.entities}
    for rel in kg.relations:
        missing = [x for x in (rel.source_id, rel.target_id) if x not in entity_ids]
        if missing:
            issues.append(
                Issue(
                    type=IssueType.DANGLING,
                    description=f"Relation '{rel.relation_type}' references missing entity.",
                    target_ids=[rel.id, *missing],
                    severity=0.5,
                )
            )
    return issues


def detect_low_confidence(
    kg: KnowledgeGraph, threshold: float = LOW_CONFIDENCE_THRESHOLD
) -> list[Issue]:
    """Knowledge/entities below the confidence threshold. Pure."""
    issues: list[Issue] = []
    for k in kg.knowledge:
        if k.confidence < threshold:
            issues.append(
                Issue(
                    type=IssueType.LOW_CONFIDENCE,
                    description=f"Low-confidence knowledge: {k.statement!r} ({k.confidence:.2f}).",
                    target_ids=[k.id],
                    severity=1.0 - k.confidence,
                )
            )
    for e in kg.entities:
        if e.confidence < threshold:
            issues.append(
                Issue(
                    type=IssueType.LOW_CONFIDENCE,
                    description=f"Low-confidence entity: {e.name!r} ({e.confidence:.2f}).",
                    target_ids=[e.id],
                    severity=1.0 - e.confidence,
                )
            )
    return issues


def detect_wiki_conflicts(kg: KnowledgeGraph, topo: RegionTopology, wiki, llm) -> list[Issue]:
    """LLM-judged contradictions vs real-world priors (graceful; [] on failure)."""
    if wiki is None or llm is None:
        return []
    from pydantic import BaseModel

    class _ConflictVerdict(BaseModel):
        conflicts: bool
        reason: str = ""

    issues: list[Issue] = []
    region_by_id = {r.id: r for r in topo.regions}
    scoped = [s for s in kg.scopes if str(s.scope_type) == ScopeType.DIRECT.value]
    kbi = {k.id: k for k in kg.knowledge}
    for s in scoped:
        region = region_by_id.get(s.region_id)
        k = kbi.get(s.knowledge_id)
        if region is None or k is None or not region.attributes:
            continue
        terrain = region.attributes.get("terrain")
        if not terrain:
            continue
        try:
            priors = wiki.lookup_similar(f"{terrain} {region.name}", k=2)
            prior_text = "; ".join(p.effect for p in priors) or "(none)"
            verdict = llm.structured(
                f"Real-world priors: {prior_text}\nStatement about a {terrain} region: "
                f"{k.statement!r}\nDoes the statement contradict the priors?",
                _ConflictVerdict,
            )
        except Exception:
            continue
        if verdict.conflicts:
            issues.append(
                Issue(
                    type=IssueType.WIKI_CONFLICT,
                    description=f"Possible conflict with real-world priors: {verdict.reason}",
                    target_ids=[k.id],
                    region_id=region.id,
                    severity=0.7,
                )
            )
    return issues


def detect_all(kg, topo, *, wiki=None, llm=None, threshold=LOW_CONFIDENCE_THRESHOLD) -> list[Issue]:
    issues = (
        detect_gaps(kg, topo)
        + detect_low_confidence(kg, threshold)
        + detect_wiki_conflicts(kg, topo, wiki, llm)
    )
    # dedup by (type, sorted target_ids)
    seen: set = set()
    out: list[Issue] = []
    for i in issues:
        key = (str(i.type), tuple(sorted(i.target_ids)))
        if key not in seen:
            seen.add(key)
            out.append(i)
    return out

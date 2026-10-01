"""Issue detectors (U7 CL5; U3 Q3=A, BR-U3-22/23). Pure over a world snapshot.

Six kinds: gap, low_confidence, wiki_conflict, orphan, dangling, unscoped. The five
structural ones are here; wiki_conflict needs the wiki and an LLM, so this module only
lists the (knowledge, terrain) pairs to judge and the engine judges them under the
run's cache and budget (BR-U3-41).

Dangling (Q3=A) is an id property that points at no node of the world: a region's
``parent_id``, an entity's ``located_in``, a connection's ``wiki_prior_ref`` and each
id in a knowledge item's ``derived_from_prior_ids`` / ``about_entity_ids`` — one issue
per broken id (FD 검토 02 R-11). NPC homes are left out: the loader already drops an
NPC whose region is gone (FD 검토 01 R-06).
"""

from __future__ import annotations

from collections.abc import Iterable

from locus.shared.models import Knowledge, Region, WorldSnapshot
from locus.shared.text import one_line
from locus.world.augmentation.types import Issue, IssueType
from locus.world.refs import ConnectionKey

LOW_CONFIDENCE_THRESHOLD = 0.5
QUESTIONS_MAX = 20  # questions per detection, by severity (BR-U3-28)


def connection_id(key: ConnectionKey) -> str:
    """A connection target's id: ``a|b|kind`` with the smaller region id first."""
    k = key.normalized()
    return f"{k.a_region_id}|{k.b_region_id}|{k.kind}"


def _first_scope(snapshot: WorldSnapshot) -> dict[str, str]:
    out: dict[str, str] = {}
    for s in snapshot.kg.scopes:
        out.setdefault(s.knowledge_id, s.region_id)
    return out


def detect_gaps(snapshot: WorldSnapshot) -> list[Issue]:
    direct = {s.region_id for s in snapshot.kg.scopes}
    return [
        Issue(
            type=IssueType.GAP,
            description=f"Region '{r.name}' has no direct knowledge.",
            target_kind="region",
            target_ids=[r.id],
            region_id=r.id,
            severity=0.6,
        )
        for r in snapshot.topo.regions
        if r.id not in direct
    ]


def detect_low_confidence(
    snapshot: WorldSnapshot, threshold: float = LOW_CONFIDENCE_THRESHOLD
) -> list[Issue]:
    where = _first_scope(snapshot)
    issues = [
        Issue(
            type=IssueType.LOW_CONFIDENCE,
            description=f"Low-confidence knowledge: {one_line(k.statement, 200)!r}"
            f" ({k.confidence:.2f}).",
            target_kind="knowledge",
            target_ids=[k.id],
            region_id=where.get(k.id),
            severity=round(1.0 - k.confidence, 6),
        )
        for k in snapshot.kg.knowledge
        if k.confidence < threshold
    ]
    issues += [
        Issue(
            type=IssueType.LOW_CONFIDENCE,
            description=f"Low-confidence entity: {e.name!r} ({e.confidence:.2f}).",
            target_kind="entity",
            target_ids=[e.id],
            region_id=e.located_in,
            severity=round(1.0 - e.confidence, 6),
        )
        for e in snapshot.kg.entities
        if e.confidence < threshold
    ]
    return issues


def detect_orphans(snapshot: WorldSnapshot) -> list[Issue]:
    """Entities with no LOCATED_IN / RELATED_TO / ABOUT edge (FR-IM4.3)."""
    linked: set[str] = set()
    for r in snapshot.kg.relations:
        linked.update((r.source_id, r.target_id))
    for k in snapshot.kg.knowledge:
        linked.update(k.about_entity_ids)
    return [
        Issue(
            type=IssueType.ORPHAN,
            description=f"Entity '{e.name}' is not connected to any region or entity.",
            target_kind="entity",
            target_ids=[e.id],
            severity=0.5,
        )
        for e in snapshot.kg.entities
        if not e.located_in and e.id not in linked
    ]


def detect_dangling(snapshot: WorldSnapshot, prior_ids: set[str]) -> list[Issue]:
    regions = set(snapshot.regions_by_id)
    entities = {e.id for e in snapshot.kg.entities}

    def issue(kind, target, field, broken, what, region_id=None) -> Issue:
        return Issue(
            type=IssueType.DANGLING,
            description=f"{what}: {field} points at a missing {broken}.",
            target_kind=kind,
            target_ids=[target],
            region_id=region_id,
            field=field,
            broken_id=broken,
            severity=0.8,
        )

    out = [
        issue("region", r.id, "parent_id", r.parent_id, f"Region '{r.name}'", r.id)
        for r in snapshot.topo.regions
        if r.parent_id and r.parent_id not in regions
    ]
    out += [
        issue("entity", e.id, "located_in", e.located_in, f"Entity '{e.name}'")
        for e in snapshot.kg.entities
        if e.located_in and e.located_in not in regions
    ]
    seen: set[str] = set()
    for c in snapshot.topo.connections:
        cid = connection_id(ConnectionKey.of(c))
        if c.wiki_prior_ref and c.wiki_prior_ref not in prior_ids and cid not in seen:
            seen.add(cid)
            out.append(
                issue(
                    "connection",
                    cid,
                    "wiki_prior_ref",
                    c.wiki_prior_ref,
                    "A connection",
                    c.source_region_id,
                )
            )
    for k in snapshot.kg.knowledge:
        for field, held in (("derived_from_prior_ids", prior_ids), ("about_entity_ids", entities)):
            for broken in dict.fromkeys(getattr(k, field)):
                if broken not in held:
                    out.append(issue("knowledge", k.id, field, broken, f"Knowledge '{k.title}'"))
    return out


def detect_unscoped(snapshot: WorldSnapshot) -> list[Issue]:
    unscoped = set(snapshot.unscoped_knowledge_ids)  # the snapshot's rule (U3 review C5)
    return [
        Issue(
            type=IssueType.UNSCOPED,
            description=f"Knowledge '{k.title}' is known nowhere (no region, not global).",
            target_kind="knowledge",
            target_ids=[k.id],
            severity=0.65,
        )
        for k in snapshot.kg.knowledge
        if k.id in unscoped
    ]


def detect_structural(snapshot: WorldSnapshot, prior_ids: set[str]) -> list[Issue]:
    """Every detector but wiki_conflict."""
    return (
        detect_dangling(snapshot, prior_ids)
        + detect_unscoped(snapshot)
        + detect_gaps(snapshot)
        + detect_low_confidence(snapshot)
        + detect_orphans(snapshot)
    )


def conflict_pairs(snapshot: WorldSnapshot) -> list[tuple[Knowledge, str, Region]]:
    """(knowledge, terrain_kind, a region with that terrain) — one pair per knowledge and
    terrain however many such regions it is scoped to (NFR R-03, 〔Step 1.3 정정〕)."""
    kbi = {k.id: k for k in snapshot.kg.knowledge}
    pairs: dict[tuple[str, str], tuple[Knowledge, str, Region]] = {}
    for s in snapshot.kg.scopes:
        region = snapshot.regions_by_id.get(s.region_id)
        k = kbi.get(s.knowledge_id)
        terrain = region.attributes.get("terrain_kind") if region else None
        if k is None or region is None or not terrain:
            continue
        pairs.setdefault((k.id, str(terrain)), (k, str(terrain), region))
    return [pairs[key] for key in sorted(pairs)]


def select(
    issues: Iterable[Issue], ignored: Iterable[str], limit: int = QUESTIONS_MAX
) -> list[Issue]:
    """One issue per key, ignored keys out, the most severe ``limit`` (stable order)."""
    skip = set(ignored)
    unique: dict[str, Issue] = {}
    for i in issues:
        if i.key not in skip:
            unique.setdefault(i.key, i)
    ranked = sorted(unique.values(), key=lambda i: (-i.severity, i.key))
    return ranked[:limit]

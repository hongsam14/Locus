"""Domain generators shared by the world-boundary property tests (PBT-07).

Reused by U3/U4/U8: region hints with connection attributes, entities with
relation/ABOUT references, and (Step 9) whole World Files with consistent ids.
"""

from __future__ import annotations

from hypothesis import strategies as st

from locus.shared.models import (
    Entity,
    EntityType,
    Knowledge,
    Provenance,
    Region,
    RegionLevel,
    Relation,
    SourceKind,
)

names = st.text(alphabet="abcdefghij ", min_size=1, max_size=8).map(str.strip).filter(bool)
levels = st.sampled_from([RegionLevel.CONTINENT, RegionLevel.PROVINCE, RegionLevel.TOWN])


def _prov() -> Provenance:
    return Provenance(source=SourceKind.INPUT)


@st.composite
def region_hints(draw) -> list[Region]:
    """Region hints as ingestors produce them: same names may repeat across inputs and
    carry connection hints / adjacent names / a parent name (TP-U2-3)."""
    n = draw(st.integers(min_value=1, max_value=6))
    pool = draw(st.lists(names, min_size=1, max_size=4, unique=True))
    out: list[Region] = []
    for _ in range(n):
        name = draw(st.sampled_from(pool))
        attrs: dict = {}
        if draw(st.booleans()):
            attrs["connection_hints"] = [
                {"from": name, "to": draw(st.sampled_from(pool)), "kind": "route"}
                for _ in range(draw(st.integers(min_value=1, max_value=2)))
            ]
        if draw(st.booleans()):
            attrs["adjacent_names"] = draw(st.lists(st.sampled_from(pool), max_size=2))
        if draw(st.booleans()):
            attrs["parent_name"] = draw(st.sampled_from(pool))
        out.append(
            Region(
                world_id="w",
                name=name,
                level=draw(levels),
                attributes=attrs,
                provenance=_prov(),
            )
        )
    return out


@st.composite
def entities_with_refs(draw) -> tuple[list[Entity], list[Relation], list[Knowledge]]:
    """Entities (with duplicates by normalized name) plus relations and knowledge that
    reference them by id — before merging (TP-U2-4)."""
    pool = draw(st.lists(names, min_size=1, max_size=4, unique=True))
    entities = [
        Entity(
            world_id="w",
            name=draw(st.sampled_from(pool)) + ("  " if draw(st.booleans()) else ""),
            entity_type=EntityType.PLACE,
            confidence=draw(st.floats(min_value=0.0, max_value=1.0)),
            provenance=_prov(),
        )
        for _ in range(draw(st.integers(min_value=1, max_value=6)))
    ]
    ids = [e.id for e in entities]
    relations = [
        Relation(
            world_id="w",
            source_id=draw(st.sampled_from(ids)),
            target_id=draw(st.sampled_from(ids)),
            relation_type="near",
            provenance=_prov(),
        )
        for _ in range(draw(st.integers(min_value=0, max_value=4)))
    ]
    knowledge = [
        Knowledge(
            world_id="w",
            statement="s",
            title="t",
            about_entity_ids=draw(st.lists(st.sampled_from(ids), max_size=3)),
            provenance=_prov(),
        )
        for _ in range(draw(st.integers(min_value=0, max_value=3)))
    ]
    return entities, relations, knowledge


@st.composite
def same_name_regions(draw) -> tuple[str, list[Region]]:
    """A name plus 1..4 regions sharing it (case/whitespace variants) at distinct or
    repeated levels, terrain included (TP-U2-5)."""
    name = draw(names)
    n = draw(st.integers(min_value=1, max_value=4))
    all_levels = list(RegionLevel)
    regions = [
        Region(
            world_id="w",
            name=draw(st.sampled_from([name, name.upper(), f" {name} "])),
            level=draw(st.sampled_from(all_levels)),
            provenance=_prov(),
        )
        for _ in range(n)
    ]
    return name, regions


# --------------------------------------------------------------------------- #
# Whole World Files with consistent references (TP-U2-1/2/6)
# --------------------------------------------------------------------------- #
from locus.shared.models import (  # noqa: E402
    NPC,
    ConnectionEdge,
    ConnectionKind,
    Coord,
    PriorType,
    ScopeLink,
    ScopeType,
    WikiDomain,
    WikiPrior,
    WikiPriorLink,
)
from locus.world.worldfile.schema import FORMAT_VERSION, WorldFile, WorldFileMeta  # noqa: E402

_unit = st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
_text = st.text(alphabet="abcdefghijklmnop ", min_size=1, max_size=12).map(str.strip).filter(bool)


@st.composite
def world_files(draw, world_id: str = "src") -> WorldFile:
    def prov(known_ids: list[str]) -> Provenance:
        refs = (
            draw(st.lists(st.sampled_from(known_ids + ["chg-external"]), max_size=2))
            if known_ids
            else []
        )
        return Provenance(
            source=draw(st.sampled_from([SourceKind.INPUT, SourceKind.INFERRED])),
            generated_by=draw(st.sampled_from([None, "llm", "user"])),
            refs=refs,
            note=draw(st.sampled_from([None, "n"])),
        )

    priors = [
        WikiPrior(
            world_id=world_id,
            prior_type=PriorType.TERRAIN_RULE,
            condition=draw(_text),
            effect=draw(_text),
            domains=draw(st.lists(st.sampled_from(list(WikiDomain)), max_size=2, unique=True)),
            confidence=draw(_unit),
            provenance=prov([]),
        )
        for _ in range(draw(st.integers(min_value=0, max_value=2)))
    ]
    prior_ids = [p.id for p in priors]
    regions: list[Region] = []
    for i in range(draw(st.integers(min_value=1, max_value=4))):
        parent = draw(st.sampled_from(regions)).id if regions and draw(st.booleans()) else None
        regions.append(
            Region(
                world_id=world_id,
                name=f"{draw(_text)} {i}",
                level=draw(levels),
                parent_id=parent,
                description=draw(st.sampled_from([None, "desc"])),
                attributes=draw(
                    st.sampled_from([{}, {"terrain_kind": "river"}, {"adjacent_names": ["x"]}])
                ),
                position=Coord(x=draw(_unit), y=draw(_unit)) if draw(st.booleans()) else None,
                provenance=prov(prior_ids),
            )
        )
    region_ids = [r.id for r in regions]
    connections: list[ConnectionEdge] = []
    seen: set[tuple[str, str]] = set()
    for _ in range(draw(st.integers(min_value=0, max_value=3))):
        a, b = draw(st.sampled_from(region_ids)), draw(st.sampled_from(region_ids))
        if a == b or (a, b) in seen:
            continue
        seen.add((a, b))
        connections.append(
            ConnectionEdge(
                world_id=world_id,
                source_region_id=a,
                target_region_id=b,
                kind=draw(st.sampled_from(list(ConnectionKind))),
                weight=draw(_unit),
                rationale=draw(st.sampled_from([None, "why"])),
                wiki_prior_ref=(
                    draw(st.sampled_from(prior_ids)) if prior_ids and draw(st.booleans()) else None
                ),
                provenance=prov(prior_ids),
            )
        )
    entities = [
        Entity(
            world_id=world_id,
            name=f"{draw(_text)} {i}",
            entity_type=EntityType.PLACE,
            description=draw(st.sampled_from([None, "d"])),
            confidence=draw(_unit),
            located_in=draw(st.sampled_from(region_ids)) if draw(st.booleans()) else None,
            provenance=prov([]),
        )
        for i in range(draw(st.integers(min_value=0, max_value=3)))
    ]
    entity_ids = [e.id for e in entities]
    relations: list[Relation] = []
    seen_r: set[tuple[str, str]] = set()  # the graph keys RELATED_TO by (source, target)
    for _ in range(draw(st.integers(min_value=0, max_value=2)) if entity_ids else 0):
        a, b = draw(st.sampled_from(entity_ids)), draw(st.sampled_from(entity_ids))
        if (a, b) in seen_r:
            continue
        seen_r.add((a, b))
        relations.append(
            Relation(
                world_id=world_id,
                source_id=a,
                target_id=b,
                relation_type="near",
                confidence=draw(_unit),
                provenance=prov([]),
            )
        )
    knowledge = [
        Knowledge(
            world_id=world_id,
            statement=f"{draw(_text)} {i}",
            title=f"t{i}",
            topic=draw(st.sampled_from([None, "topic"])),
            confidence=draw(_unit),
            is_global=draw(st.booleans()),
            region_hint=draw(st.sampled_from([None, "hint"])),
            about_entity_ids=(
                draw(st.lists(st.sampled_from(entity_ids), max_size=2, unique=True))
                if entity_ids
                else []
            ),
            derived_from_prior_ids=(
                draw(st.lists(st.sampled_from(prior_ids), max_size=1)) if prior_ids else []
            ),
            provenance=prov(prior_ids),
        )
        for i in range(draw(st.integers(min_value=0, max_value=3)))
    ]
    scopes: list[ScopeLink] = []
    seen_s: set[tuple[str, str]] = set()
    for k in knowledge:
        if draw(st.booleans()):
            rid = draw(st.sampled_from(region_ids))
            if (k.id, rid) not in seen_s:
                seen_s.add((k.id, rid))
                scopes.append(
                    ScopeLink(
                        world_id=world_id,
                        knowledge_id=k.id,
                        region_id=rid,
                        scope_type=ScopeType.DIRECT,
                        confidence=draw(_unit),
                    )
                )
    prior_links = []
    if len(prior_ids) == 2 and draw(st.booleans()):
        prior_links.append(
            WikiPriorLink(
                world_id=world_id,
                source_id=prior_ids[0],
                target_id=prior_ids[1],
                relation="implies",
                weight=draw(_unit),
                provenance=prov([]),
            )
        )
    npcs = [
        NPC(
            world_id=world_id,
            name=f"{draw(_text)} {i}",
            role="villager",
            description="d",
            home_region_id=draw(st.sampled_from(region_ids)),
            traits=draw(st.lists(st.sampled_from(["kind", "gruff"]), max_size=2)),
            provenance=prov([]),
        )
        for i in range(draw(st.integers(min_value=0, max_value=2)))
    ]
    return WorldFile(
        format_version=FORMAT_VERSION,
        world=WorldFileMeta(
            id=world_id, name=draw(_text), description=draw(st.sampled_from([None, "about"]))
        ),
        regions=regions,
        connections=connections,
        entities=entities,
        relations=relations,
        knowledge=knowledge,
        scopes=scopes,
        priors=priors,
        prior_links=prior_links,
        npcs=npcs,
    )


# --------------------------------------------------------------------------- #
# U3 editor generators (TP-U3-1·2·2a·6)
# --------------------------------------------------------------------------- #
@st.composite
def editable_worlds(draw, world_id: str = "w") -> WorldFile:
    """A World File whose knowledge may sit in 0–3 regions (``world_files`` gives at
    most one scope each), so a region delete meets both "becomes unscoped" and "keeps
    its other scopes" (TP-U3-2)."""
    file = draw(world_files(world_id=world_id))
    region_ids = [r.id for r in file.regions]
    scopes = list(file.scopes)
    seen = {(s.knowledge_id, s.region_id) for s in scopes}
    for k in file.knowledge:
        for rid in draw(st.lists(st.sampled_from(region_ids), max_size=2, unique=True)):
            if (k.id, rid) not in seen:
                seen.add((k.id, rid))
                scopes.append(
                    ScopeLink(
                        world_id=world_id,
                        knowledge_id=k.id,
                        region_id=rid,
                        scope_type=ScopeType.DIRECT,
                        confidence=draw(_unit),
                    )
                )
    return file.model_copy(update={"scopes": scopes})


EDIT_OPS = (
    "describe_region",
    "set_scopes",
    "save_connection",
    "delete_connection",
    "delete_knowledge",
    "delete_region",
    "move_npc",
)


@st.composite
def edit_ops(draw) -> list[tuple]:
    """A short list of editor operations, each an (op, ints...) tuple the test maps onto
    whatever the world holds at that moment (TP-U3-6)."""
    picks = st.integers(min_value=0, max_value=50)
    return draw(
        st.lists(
            st.tuples(st.sampled_from(EDIT_OPS), picks, picks, picks, _unit),
            min_size=1,
            max_size=5,
        )
    )

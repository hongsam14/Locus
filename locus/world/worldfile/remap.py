"""Deterministic id remapping and reference validation for World Files (U2 BR-U2-4/5).

``remap_ids`` has no identity shortcut: the caller (``WorldFileImporter``) decides
whether to remap (``force_remap or source != target``). Only ids that exist in the
file are rewritten; ``provenance.refs`` entries that point outside the file (change
sets, inputs) are left alone.
"""

from __future__ import annotations

import uuid
from collections.abc import Callable

from locus.shared.models import BuildWarning
from locus.world.worldfile.schema import NAMESPACE_LOCUS, WorldFile, WorldFileMeta


def file_ids(file: WorldFile) -> set[str]:
    ids: set[str] = set()
    for section in (
        "regions",
        "entities",
        "relations",
        "knowledge",
        "priors",
        "npcs",
        "event_seeds",
    ):
        ids.update(item.id for item in getattr(file, section))
    return ids


def remap_ids(file: WorldFile, target_world_id: str) -> WorldFile:
    """Rewrite every id and reference to ``uuid5(NAMESPACE_LOCUS, f"{target}:{old}")``
    and every ``world_id`` (and ``world.id``) to ``target_world_id``. Deterministic."""
    known = file_ids(file)

    def new(old: str | None) -> str | None:
        if old is None or old not in known:
            return old
        return str(uuid.uuid5(NAMESPACE_LOCUS, f"{target_world_id}:{old}"))

    def new_list(ids: list[str]) -> list[str]:
        return [new(i) or i for i in ids]

    def prov(p):
        refs = new_list(list(p.refs))
        return p if refs == list(p.refs) else p.model_copy(update={"refs": refs})

    def upd(item, **fields):
        fields["world_id"] = target_world_id
        fields["provenance"] = prov(item.provenance)
        return item.model_copy(update=fields)

    return file.model_copy(
        update={
            "world": WorldFileMeta(
                id=target_world_id, name=file.world.name, description=file.world.description
            ),
            "regions": [upd(r, id=new(r.id), parent_id=new(r.parent_id)) for r in file.regions],
            "connections": [
                upd(
                    c,
                    source_region_id=new(c.source_region_id),
                    target_region_id=new(c.target_region_id),
                    wiki_prior_ref=new(c.wiki_prior_ref),
                )
                for c in file.connections
            ],
            "entities": [upd(e, id=new(e.id), located_in=new(e.located_in)) for e in file.entities],
            "relations": [
                upd(r, id=new(r.id), source_id=new(r.source_id), target_id=new(r.target_id))
                for r in file.relations
            ],
            "knowledge": [
                upd(
                    k,
                    id=new(k.id),
                    about_entity_ids=new_list(k.about_entity_ids),
                    derived_from_prior_ids=new_list(k.derived_from_prior_ids),
                )
                for k in file.knowledge
            ],
            "scopes": [
                s.model_copy(
                    update={
                        "world_id": target_world_id,
                        "knowledge_id": new(s.knowledge_id),
                        "region_id": new(s.region_id),
                    }
                )
                for s in file.scopes
            ],
            "priors": [upd(p, id=new(p.id)) for p in file.priors],
            "prior_links": [
                upd(link, source_id=new(link.source_id), target_id=new(link.target_id))
                for link in file.prior_links
            ],
            "npcs": [upd(n, id=new(n.id), home_region_id=new(n.home_region_id)) for n in file.npcs],
            "event_seeds": [  # U8: a seed follows its region (TP-U8-2)
                upd(s, id=new(s.id), region_id=new(s.region_id)) for s in file.event_seeds
            ],
        }
    )


def set_world_id(file: WorldFile, world_id: str) -> WorldFile:
    """Stamp ``world_id`` on every item and ``world.id`` without touching ids (used when
    a same-world file is imported as-is, so nodes land in the target partition)."""

    def stamp(items):
        return [item.model_copy(update={"world_id": world_id}) for item in items]

    return file.model_copy(
        update={
            "world": WorldFileMeta(
                id=world_id, name=file.world.name, description=file.world.description
            ),
            **{
                name: stamp(getattr(file, name))
                for name in (
                    "regions",
                    "connections",
                    "entities",
                    "relations",
                    "knowledge",
                    "scopes",
                    "priors",
                    "prior_links",
                    "npcs",
                    "event_seeds",
                )
            },
        }
    )


def validate_references(file: WorldFile) -> tuple[WorldFile, list[BuildWarning]]:
    """Drop items whose references point nowhere in the file; each drop is an
    ``error`` warning so the import reports ``ok=False`` (BR-U2-5)."""
    region_ids = {r.id for r in file.regions}
    entity_ids = {e.id for e in file.entities}
    knowledge_ids = {k.id for k in file.knowledge}
    prior_ids = {p.id for p in file.priors}
    warnings: list[BuildWarning] = []

    def err(message: str, item_id: str | None = None) -> None:
        warnings.append(
            BuildWarning(stage="import", item_id=item_id, message=message, severity="error")
        )

    def keep(items, pred: Callable, what: str, ident: Callable):
        out = []
        for item in items:
            if pred(item):
                out.append(item)
            else:
                err(f"{what} {ident(item)} dropped: broken reference", ident(item))
        return out

    regions = []
    for r in file.regions:
        if r.parent_id and r.parent_id not in region_ids:
            err(f"region {r.id} parent {r.parent_id} not in file; parent cleared", r.id)
            r = r.model_copy(update={"parent_id": None})
        regions.append(r)
    connections = keep(
        file.connections,
        lambda c: c.source_region_id in region_ids and c.target_region_id in region_ids,
        "connection",
        lambda c: f"{c.source_region_id}->{c.target_region_id}",
    )
    relations = keep(
        file.relations,
        lambda r: r.source_id in entity_ids and r.target_id in entity_ids,
        "relation",
        lambda r: r.id,
    )
    scopes = keep(
        file.scopes,
        lambda s: s.knowledge_id in knowledge_ids and s.region_id in region_ids,
        "scope",
        lambda s: f"{s.knowledge_id}@{s.region_id}",
    )
    prior_links = keep(
        file.prior_links,
        lambda link: link.source_id in prior_ids and link.target_id in prior_ids,
        "prior_link",
        lambda link: f"{link.source_id}->{link.target_id}",
    )
    npcs = keep(file.npcs, lambda n: n.home_region_id in region_ids, "npc", lambda n: n.id)
    seeds = keep(  # U8 (BR-U8-13): a seed in a region the file lacks is dropped, an error
        file.event_seeds, lambda s: s.region_id in region_ids, "event_seed", lambda s: s.id
    )

    def soft(message: str, item_id: str) -> None:  # optional refs: clear, warn (not an error)
        warnings.append(BuildWarning(stage="import", item_id=item_id, message=message))

    entities = []
    for e in file.entities:
        if e.located_in and e.located_in not in region_ids:
            soft(f"entity {e.id}: located_in {e.located_in} not in file; cleared", e.id)
            e = e.model_copy(update={"located_in": None})
        entities.append(e)
    fixed_connections = []
    for c in connections:
        if c.wiki_prior_ref and c.wiki_prior_ref not in prior_ids:
            soft(f"connection {c.source_region_id}->{c.target_region_id}: prior ref dropped", None)  # type: ignore[arg-type]
            c = c.model_copy(update={"wiki_prior_ref": None})
        fixed_connections.append(c)
    knowledge = []
    for k in file.knowledge:
        about = [i for i in k.about_entity_ids if i in entity_ids]
        derived = [i for i in k.derived_from_prior_ids if i in prior_ids]
        if about != k.about_entity_ids or derived != k.derived_from_prior_ids:
            soft(f"knowledge {k.id}: unknown entity/prior references dropped", k.id)
            k = k.model_copy(update={"about_entity_ids": about, "derived_from_prior_ids": derived})
        knowledge.append(k)
    return (
        file.model_copy(
            update={
                "regions": regions,
                "connections": fixed_connections,
                "entities": entities,
                "relations": relations,
                "knowledge": knowledge,
                "scopes": scopes,
                "prior_links": prior_links,
                "npcs": npcs,
                "event_seeds": seeds,
            }
        ),
        warnings,
    )

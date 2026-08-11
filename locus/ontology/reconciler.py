"""EntityReconciler — cross-source merge + orphan connection (U-B, FR-IM4.2/4.3/4.4).

Two jobs after multimodal ingestion:
1. **case1 merge**: a VLM-origin entity whose name was mis-extracted but denotes a
   node already found by text/structured sources is merged into that node
   (fuzzy -> embedding -> LLM; non-VLM is canonical, BR-B6).
2. **orphan connect**: any entity still unconnected (no LOCATED_IN / RELATED_TO /
   ABOUT) is attached to the most plausible region (LOCATED_IN); leftovers become
   augmentation candidates (``unconnected_entity_ids``, BR-B8). Nothing is dropped.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from pydantic import BaseModel

from ..llm.base import EmbeddingProvider, LLMProvider
from ..models import Entity, Region, Relation
from .schemas import EntityMatchVerdict, RegionPickVerdict
from .similarity import cosine

FUZZY_THRESHOLD = 0.6


def _norm(name: str) -> str:
    return " ".join(name.strip().lower().split())


def _is_vlm(e: Entity) -> bool:
    return (e.provenance.generated_by or "") == "vlm"


def _entity_text(e: Entity) -> str:
    return f"{e.name} {e.description or ''}".strip()


def _region_text(r: Region) -> str:
    return f"{r.name} {r.description or ''}".strip()


class Reconciled(BaseModel):
    entities: list[Entity]
    relations: list[Relation]
    remap: dict[str, str]  # old entity id -> canonical id
    unconnected_entity_ids: list[str]


class EntityReconciler:
    def __init__(
        self,
        embedding: EmbeddingProvider | None = None,
        llm: LLMProvider | None = None,
    ) -> None:
        self._embedding = embedding
        self._llm = llm

    def reconcile(
        self,
        entities: list[Entity],
        regions: list[Region],
        relations: list[Relation],
        about_entity_ids: set[str],
    ) -> Reconciled:
        remap = self._merge_cross_source(entities)
        # keep only canonical entities (drop absorbed VLM nodes)
        kept = [e for e in entities if remap.get(e.id, e.id) == e.id]
        relations = self._remap_relations(relations, remap)
        about = {remap.get(i, i) for i in about_entity_ids}

        connected = self._connected_ids(kept, relations, about)
        unconnected: list[str] = []
        for e in kept:
            if e.id in connected or e.located_in:
                continue
            region = self._pick_region(e, regions)
            if region is not None:
                e.located_in = region.id  # -> LOCATED_IN edge (BR-B5)
            else:
                unconnected.append(e.id)  # augmentation candidate (BR-B8)
        return Reconciled(
            entities=kept, relations=relations, remap=remap, unconnected_entity_ids=unconnected
        )

    # -- case1 cross-source merge ---------------------------------------- #
    def _merge_cross_source(self, entities: list[Entity]) -> dict[str, str]:
        remap: dict[str, str] = {}
        vlm = [e for e in entities if _is_vlm(e)]
        others = [e for e in entities if not _is_vlm(e)]
        if not vlm or not others or self._llm is None:
            return remap  # graceful: need an LLM to confirm a sensitive merge (BR-B6/B10)

        emb = self._embeddings(vlm + others)
        for v in vlm:
            cands = self._fuzzy_candidates(v, others)
            if emb is not None:
                cands = self._rank_by_embedding(v, cands, emb)
            for c in cands[:3]:
                verdict = self._judge_same(v, c)
                if verdict is not None and verdict.same_entity:
                    remap[v.id] = c.id  # non-VLM canonical (BR-B6)
                    break
        return remap

    def _fuzzy_candidates(self, v: Entity, others: list[Entity]) -> list[Entity]:
        scored = [(SequenceMatcher(None, _norm(v.name), _norm(o.name)).ratio(), o) for o in others]
        scored = [(s, o) for s, o in scored if s >= FUZZY_THRESHOLD]
        scored.sort(key=lambda t: t[0], reverse=True)
        return [o for _s, o in scored]

    def _rank_by_embedding(
        self, v: Entity, cands: list[Entity], emb: dict[str, list[float]]
    ) -> list[Entity]:
        vv = emb.get(v.id)
        if vv is None:
            return cands
        return sorted(cands, key=lambda o: cosine(vv, emb.get(o.id, [])), reverse=True)

    def _judge_same(self, v: Entity, c: Entity) -> EntityMatchVerdict | None:
        prompt = (
            "Do these two refer to the SAME world entity (one name may be a "
            "mis-spelling/variant)?\n\n"
            f"A (from image): {_entity_text(v)}\nB (from text/map): {_entity_text(c)}"
        )
        try:
            return self._llm.structured(prompt, EntityMatchVerdict)
        except Exception:
            return None

    # -- orphan connection ------------------------------------------------ #
    def _connected_ids(
        self, entities: list[Entity], relations: list[Relation], about: set[str]
    ) -> set[str]:
        connected = set(about)
        for r in relations:
            connected.add(r.source_id)
            connected.add(r.target_id)
        for e in entities:
            if e.located_in:
                connected.add(e.id)
        return connected

    def _pick_region(self, e: Entity, regions: list[Region]) -> Region | None:
        if not regions or self._llm is None:
            return None
        candidates = regions
        emb = self._embeddings_regions(e, regions)
        if emb is not None:
            ev = emb["__entity__"]
            candidates = sorted(regions, key=lambda r: cosine(ev, emb.get(r.id, [])), reverse=True)
        names = [r.name for r in candidates[:5]]
        prompt = (
            "Which region is this map/art feature located in? Choose one name from "
            f"the list or null if none fits.\nFeature: {_entity_text(e)}\nRegions: {names}"
        )
        try:
            verdict: RegionPickVerdict = self._llm.structured(prompt, RegionPickVerdict)
        except Exception:
            return None
        if not verdict.region_name:
            return None
        target = _norm(verdict.region_name)
        for r in candidates:
            if _norm(r.name) == target:
                return r
        return None

    # -- embeddings (graceful) ------------------------------------------- #
    def _embeddings(self, entities: list[Entity]) -> dict[str, list[float]] | None:
        if self._embedding is None:
            return None
        try:
            vecs = self._embedding.embed([_entity_text(e) for e in entities])
        except Exception:
            return None
        return {e.id: v for e, v in zip(entities, vecs, strict=True)}

    def _embeddings_regions(
        self, e: Entity, regions: list[Region]
    ) -> dict[str, list[float]] | None:
        if self._embedding is None:
            return None
        try:
            texts = [_entity_text(e)] + [_region_text(r) for r in regions]
            vecs = self._embedding.embed(texts)
        except Exception:
            return None
        out = {"__entity__": vecs[0]}
        for r, v in zip(regions, vecs[1:], strict=True):
            out[r.id] = v
        return out

    @staticmethod
    def _remap_relations(relations: list[Relation], remap: dict[str, str]) -> list[Relation]:
        if not remap:
            return relations
        out: list[Relation] = []
        for r in relations:
            s = remap.get(r.source_id, r.source_id)
            t = remap.get(r.target_id, r.target_id)
            if s == t:
                continue  # self-loop after merge -> drop
            out.append(r.model_copy(update={"source_id": s, "target_id": t}))
        return out

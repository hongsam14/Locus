# U4 Ontology — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-3.1 (knowledge graph + ABOUT), US-3.2 (region scoping + global), US-3.3 (corroboration / SC-4); dedup (CL2=C).
**Verification**: 58 tests PASS (48 prior + 10 U4, incl. PBT cosine bound); ruff + black clean. Offline (LLM/Embedding/Wiki mocked).

## Created files (`locus/ontology/`)
- `schemas.py` — `CorroborationSuggestion`, `CorroborationBatch`, `DuplicateVerdict`.
- `similarity.py` — deterministic measurement: `cosine`, `candidate_pairs` (pure; extension point for structural/terrain similarity per user note).
- `dedup.py` — `Deduplicator` (embed → similarity candidates → LLM verdict → merge; exact fallback) + pure `cosine`-driven `merge_duplicates`, union-find.
- `corroboration.py` — `CorroborationGenerator` (region context + Wiki grounding → LLM `CorroborationBatch` → region-scoped Knowledge, confidence ×0.8).
- `builder.py` — `OntologyBuilder.build` + pure `scope_knowledge` (direct/global/unscoped) + `remap_scopes`.
- `__init__.py` — re-exports.

## Modified files (additive)
- `locus/models/enums.py` — `ScopeType.GLOBAL`.
- `locus/models/graph.py` — `Knowledge.is_global`, `Knowledge.region_hint` (transient scope hint).
- `locus/ingestion/schemas.py` — `ExtractedKnowledge.is_global`.
- `locus/ingestion/mapping.py` — `to_knowledge` carries `is_global`, `region_hint`, `about_entity_ids`.
- `locus/ingestion/text_ingestor.py` — resolves ABOUT (about_names→entity ids) where data is local.

## Key realizations
- **measurement (similarity) vs policy (dedup)** kept separate per user guidance — similarity is the deterministic, extensible home; dedup adds LLM judgment (high cosine alone never auto-merges, CL2=C).
- **Global knowledge** (`is_global`) has no SCOPED_TO and is included for every region at query time (CL1=A).
- **Scoping** uses a transient `region_hint` resolved against the full merged region set in U4; unresolved non-global → augmentation candidate.
- **Corroboration** is LLM-generated (Q3=B), grounded on Wiki priors, discounted ×0.8 (Q5=A), with `DERIVED_FROM` provenance — drives SC-4.
- All external calls graceful (exact-merge / skip on failure).

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U4 (inherits U1 + shared infra).
- Persistence (KnowledgeGraph → Neo4j/OpenSearch) handled by U9 orchestrator.

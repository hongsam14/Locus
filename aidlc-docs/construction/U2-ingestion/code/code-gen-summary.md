# U2 Ingestion — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-1.1 (text), US-1.2 (map image/VLM), US-1.3 (structured map), US-1.4 (concept art).
**Verification**: 38 tests PASS (24 U1 + 14 U2, incl. hypothesis PBT); ruff + black clean. External LLM/VLM calls mocked → fully offline.

## Created files (`locus/ingestion/`)
- `schemas.py` — extraction DTOs: `Extracted{Entity,Relation,Region,Terrain,Knowledge}`, `TextExtraction`, `MapExtraction`, `ArtExtraction`.
- `mapping.py` — pure helpers: `normalize_name`, `to_entity/to_region/to_terrain_entity/to_relation/to_knowledge`, `merge_entities`, `merge_regions`, `flag_low_confidence`; constants `LOW_CONFIDENCE_THRESHOLD=0.5`, `CONCEPT_ART_CONFIDENCE_CAP=0.4`.
- `text_ingestor.py` — `TextIngestor` (US-1.1): structured extraction → map/merge/relations/low-conf; graceful on provider error.
- `map_image_ingestor.py` — `MapImageIngestor` (US-1.2): VLM describe → structured `MapExtraction` → region_hints + terrain entities + connection_hints (on attributes; edges deferred to U3).
- `structured_map_ingestor.py` — `StructuredMapIngestor` (US-1.3): pure parsing of Locus Map JSON + GeoJSON; invalid items rejected to `errors`, valid ones kept.
- `concept_art_ingestor.py` — `ConceptArtIngestor` (US-1.4): VLM → `ArtExtraction`; clues capped at 0.4 confidence, all flagged low-confidence.
- `service.py` — `IngestionService` (routing + merge), `WorldInputs`, `merge_results`; `from_factory(ProviderFactory)` wiring.
- `__init__.py` — re-exports.

## Created tests (`tests/ingestion/test_ingestion.py`)
normalize idempotence (PBT), merge dedup/type-distinction, Locus JSON + GeoJSON parsing + partial-reject, Text ingestor mapping/relations/low-conf/empty/graceful-error, concept-art confidence cap, map-image terrain/regions, service merge + routing.

## Key realizations
- **Single structured-output call per modality** (FD2-Q1=A); LLM/VLM injected (mockable).
- **Pure logic separated** from provider calls (mapping/merge/parse) → PBT-friendly (BR-U2-12).
- **U2 produces region_hints + terrain only**; topology edges/hierarchy built in U3 (FD2-Q5=A). Connection hints carried on region `attributes`.
- **Graceful degradation**: provider failure / invalid items never abort — recorded in `errors`, other inputs continue.

## Stage notes
- NFR Requirements / NFR Design / Infrastructure Design SKIPPED for U2 (no new NFRs/infra; inherits U1 provider abstraction/retry/graceful-degrade + shared infra).

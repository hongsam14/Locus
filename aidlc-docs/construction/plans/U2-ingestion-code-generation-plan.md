# U2 Ingestion — Code Generation Plan

Code 위치 = `locus/ingestion/`. U1 모델·provider 사용. Stories US-1.1~1.4.

## Steps  (ALL DONE — 38 tests pass, ruff/black clean)
- [x] **Step 1 — schemas** (`locus/ingestion/schemas.py`): Extracted{Entity,Relation,Region,Terrain,Knowledge} + TextExtraction/MapExtraction/ArtExtraction (Pydantic, confidence 0~1).
- [ ] **Step 2 — mapping/merge** (`locus/ingestion/mapping.py`): `normalize_name`, `to_entity/to_region/to_relation/to_knowledge`, `merge_entities`, `merge_regions`, `flag_low_confidence`. 순수 함수.
- [ ] **Step 3 — TextIngestor** (`text_ingestor.py`): llm.structured(TextExtraction) → 매핑·병합·저신뢰·errors(graceful).
- [ ] **Step 4 — MapImageIngestor** (`map_image_ingestor.py`): vlm + llm.structured(MapExtraction) → region_hints + terrain entities + connection_hints(attributes).
- [ ] **Step 5 — StructuredMapIngestor** (`structured_map_ingestor.py`): Locus Map JSON + GeoJSON 파싱, 검증·부분거부(errors).
- [ ] **Step 6 — ConceptArtIngestor** (`concept_art_ingestor.py`): vlm + llm.structured(ArtExtraction) → 낮은 confidence clues.
- [ ] **Step 7 — IngestionService** (`service.py` + `WorldInputs`): 라우팅 + 결과 병합 → 단일 IngestionResult.
- [ ] **Step 8 — `__init__.py`** 재노출.
- [ ] **Step 9 — Tests** (`tests/ingestion/`): mapping/merge/normalize(순수, +PBT), structured-map 파싱(Locus JSON + GeoJSON + 부분거부), TextIngestor(mock LLM) 매핑·저신뢰, IngestionService 병합, concept-art confidence 상한.
- [ ] **Step 10 — Docs**: `construction/U2-ingestion/code/code-gen-summary.md`.

## Story Coverage
US-1.1→Step3 · US-1.2→Step4 · US-1.3→Step5 · US-1.4→Step6 · (병합/서비스)→Step2,7.

## Notes
- LLM/VLM provider는 생성자 주입(ProviderFactory) → 테스트 mock. 순수 로직(매핑/병합/파싱) LLM 비의존.
- 테스트는 작성만(실행 검증은 본 단계에서 pytest로 확인). 외부 호출 mock, 오프라인.

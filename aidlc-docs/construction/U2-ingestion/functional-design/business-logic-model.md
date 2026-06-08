# U2 Ingestion — Business Logic Model

## Ingestor 별 흐름 (단일 구조화 호출, FD2-Q1=A)

### TextIngestor.extract(memo, world_id) -> IngestionResult
1. `llm.structured(prompt(memo), TextExtraction)` 호출(retry/graceful degrade는 U1 provider가 처리).
2. ExtractedEntity/Relation/Region/Knowledge → U1 도메인 모델로 매핑(UUID, provenance.source=input, generated_by="llm").
3. 이름 정규화 병합(FD2-Q2=A): `normalize(name)=lower+collapse_ws`; 동일 키 병합, confidence=max.
4. confidence < THRESHOLD(기본 0.5) → `low_confidence_item_ids`에 추가.
5. 실패 시(provider 예외 소진) → `errors`에 기록하고 빈 결과 반환(빌드 미중단).

### MapImageIngestor.extract(image, world_id) -> IngestionResult
1. `vlm.analyze_image(image, prompt)` → 텍스트, 이어 `llm.structured(text, MapExtraction)` 로 구조화
   (또는 VLM이 구조화 지원 시 직접). regions/terrain/connections_hint 산출.
2. regions → `region_hints`(Region, source=input), terrain → `Entity(entity_type=terrain)`.
3. connections_hint → region attributes에 보존(엣지는 U3).
4. 저신뢰·실패 처리는 Text와 동일.

### StructuredMapIngestor.parse(doc, world_id) -> IngestionResult
1. 포맷 감지: `type=="FeatureCollection"` → GeoJSON, else Locus Map JSON(FD2-Q3=A).
2. 스키마 검증 → 위반 항목은 `errors`에 사유와 함께(나머지는 계속).
3. regions → `region_hints`(confidence=1.0), connections → attributes 힌트.

### ConceptArtIngestor.extract(image, world_id) -> IngestionResult (FD2-Q6=A)
1. `vlm.analyze_image` → `llm.structured(text, ArtExtraction)`.
2. clues → `Entity`(낮은 confidence, 상한 0.4), 모두 `low_confidence_item_ids`.

## IngestionService.ingest_all(inputs) -> IngestionResult
- 입력 종류별 Ingestor로 라우팅 → 각 결과를 **병합**(엔티티 이름 정규화 병합, region_hints 이름 병합, errors/low_conf 누적).
- 단일 `IngestionResult`(world_id) 반환. (서비스 계층은 U9에서 PipelineOrchestrator와 연결; U2는 IngestionService까지 제공.)

## 매핑/병합 유틸 (`locus/ingestion/mapping.py`)
- `to_entity / to_region / to_relation / to_knowledge` (Extracted* → 도메인 모델).
- `merge_entities(list)` 이름 정규화 병합.
- `normalize_name(s)`.

## Provider 사용
- LLM/VLM는 U1 `ProviderFactory`로 주입(생성자 인자) → 테스트에서 mock. 임베딩은 U2 단계 불필요(색인은 저장 시점/후속 Unit).

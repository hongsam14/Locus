# U2 Ingestion — Domain Entities & Extraction Schemas

U2는 U1의 도메인 모델을 사용하고, **LLM/VLM 구조화 출력용 추출 스키마**를 추가로 정의합니다. 결정: FD2-Q1=A(단일 구조화 호출)·Q2=A(이름 정규화 병합)·Q3=A(Locus맵JSON+GeoJSON)·Q4=A(self-report+모달리티 기본값)·Q5=A(region_hints+terrain만)·Q6=A(컨셉아트 포함).

## 출력 (U1 모델 재사용)
- `IngestionResult { world_id, entities[], relations[], region_hints[], knowledge[], low_confidence_item_ids[], errors[] }`
- 구성 요소: `Entity`, `Relation`, `Region`(힌트), `Knowledge` (U1 `locus/models`).

## 추출 스키마 (LLM 구조화 출력 전용 — `locus/ingestion/schemas.py`)
LLM/VLM가 채우는 경량 Pydantic 모델(도메인 모델로 매핑 전 단계):

```text
ExtractedEntity   { name, entity_type, description?, confidence(0~1) }
ExtractedRelation { source_name, target_name, relation_type, confidence(0~1) }
ExtractedRegion   { name, level?, description?, parent_name?, confidence(0~1) }
ExtractedTerrain  { name, kind, between?:[region_name,region_name], note?, confidence }
ExtractedKnowledge{ statement, topic?, about_names:[...], region_name?, confidence }
TextExtraction    { entities[], relations[], regions[], knowledge[] }
MapExtraction     { regions[], terrain[], connections_hint?[] }   # VLM
ArtExtraction     { clues:[ExtractedEntity], mood? }              # 낮은 confidence
```
- 매핑 단계에서 `ExtractedRegion`→`Region`(provenance.source=input), terrain→`Entity(entity_type=terrain)`, 등으로 변환하며 UUID 부여.

## 구조화 맵 입력 스키마 (FD2-Q3=A)
- **Locus Map JSON**:
  ```json
  {"regions":[{"name":"...","level":"town","parent":"...","attributes":{}}],
   "connections":[{"from":"...","to":"...","kind":"route"}]}
  ```
- **GeoJSON**: `FeatureCollection`; `Feature.properties.name/level` → Region; `geometry` 보존은 attributes에 요약(MVP는 좌표 상세 미사용).
- 파싱 결과는 `IngestionResult.region_hints`(+ connections는 attributes 힌트로 보존; 실제 엣지는 U3).

## 비고
- U2는 **토폴로지 그래프를 만들지 않음**(FD2-Q5=A) — region_hints와 terrain 엔티티, 연결 "힌트"만.
- confidence 기본값(FD2-Q4=A): 구조화 맵=1.0, 텍스트/이미지=모델 self-report, 컨셉아트=0.4(상한).

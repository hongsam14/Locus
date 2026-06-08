# U2 Ingestion — Business Rules

## 추출 / 매핑
- BR-U2-1: 모든 추출 항목은 `provenance.source=input`, `generated_by="llm"|"vlm"|"structured-map"`.
- BR-U2-2: confidence ∈ [0,1]; 모달리티 기본값 — 구조화 맵=1.0, 텍스트/이미지=모델 self-report(없으면 0.7), 컨셉아트 상한 0.4 (FD2-Q4=A).
- BR-U2-3: confidence < `LOW_CONFIDENCE_THRESHOLD`(기본 0.5) → `low_confidence_item_ids`에 등록(보강 대상, FR-A5).

## 병합 (FD2-Q2=A)
- BR-U2-4: 단일 ingestion 내 엔티티는 `normalize_name`(소문자+공백 축약) + `entity_type` 동일 시 병합; confidence=최댓값, description은 비어있지 않은 것 우선.
- BR-U2-5: region_hints도 `normalize_name`+level 기준 병합.

## 구조화 맵 (FD2-Q3=A)
- BR-U2-6: `type=="FeatureCollection"`이면 GeoJSON, 아니면 Locus Map JSON으로 해석.
- BR-U2-7: 필수 필드 누락/타입 오류 항목은 거부하고 `errors`에 `"<위치>: <사유>"` 기록(나머지는 계속 — graceful).
- BR-U2-8: connections는 U2에서 엣지로 만들지 않음 — region attributes의 `connection_hints`로 보존(U3가 소비, FD2-Q5=A).

## 경계 / 실패
- BR-U2-9: U2는 토폴로지(CONTAINS/CONNECTED_TO) 엣지·계층을 확정하지 않는다(U3 책임).
- BR-U2-10: provider 호출 실패가 재시도 소진되면 해당 입력은 빈 결과 + `errors` 기록, 다른 입력 처리는 계속(빌드 미중단, NFR graceful degrade).
- BR-U2-11: 빈/공백 입력 텍스트·0바이트 이미지는 검증 거부(`errors`).

## 결정성/테스트
- BR-U2-12: 매핑·병합·정규화·포맷 파싱은 순수 함수로 분리(LLM 비의존) → 단위 테스트/PBT 대상. LLM/VLM 경로는 mock.

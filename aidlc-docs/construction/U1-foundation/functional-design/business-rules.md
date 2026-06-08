# U1 Foundation — Business Rules & Invariants

## 식별 / 유니크
- BR-1: 모든 노드는 `world_id`와 불변 `id`(UUID)를 가진다. (FD1-Q2=A)
- BR-2: 유니크 제약 — Region `(world_id, level, natural_key)`, Entity `(world_id, entity_type, natural_key)`. 위반 시 upsert는 기존 노드 병합.
- BR-3: world_id `__realworld__`는 Wiki 예약. 가상 세계가 사용 불가.

## 값 범위
- BR-4: `confidence` ∈ [0.0, 1.0]. 범위 밖 → 검증 오류.
- BR-5: `CONNECTED_TO.weight` ∈ [0.0, 1.0]. (0=단절, 1=완전 연결)
- BR-6: `DISTORTED_FROM.distortion_degree` ∈ [0.0, 1.0].

## Provenance / 출처 (Q6=A)
- BR-7: 모든 Knowledge/Rumor/Entity/WikiPrior와 생성된 관계는 `source` ∈ {input, inferred-wiki, augmentation} 필수.
- BR-8: `source=inferred-wiki` 항목은 `DERIVED_FROM`으로 최소 1개 WikiPrior 근거(또는 LLM 폴백 note) 보유.
- BR-9: `source=augmentation` 항목은 변경 추적 ChangeSet 참조 보유.

## 스코핑 / 상속 (FD1-Q3=A)
- BR-10: Knowledge는 최소 1개 `SCOPED_TO`(scope_type=direct) Region 보유.
- BR-11: 상속 지식은 저장하지 않고, 조회 시 `CONTAINS` 조상 경로로 동적 계산(scope_type=inherited).
- BR-12: 동일 (Knowledge, Region) 쌍에 direct가 있으면 inherited는 중복 표기하지 않음(direct 우선).

## 왜곡 / 소문 (FD1-Q4=B)
- BR-13: `:Rumor`는 정확히 1개의 `DISTORTED_FROM`(→ :Knowledge 또는 :Rumor)을 가진다(고아 금지).
- BR-14: Rumor의 confidence ≤ 원본 confidence (전파·왜곡으로 신뢰 감소).
- BR-15: `DISTORTED_FROM` 체인은 순환 금지.

## 토폴로지
- BR-16: `CONTAINS`는 비순환 트리(각 Region 부모 ≤ 1).
- BR-17: `CONNECTED_TO`는 같은 world_id 내에서만.

## 검색 / 임베딩
- BR-18: 색인 대상(Knowledge/Entity/WikiPrior/Rumor) 생성·수정 시 `SearchDoc` 동기화. 텍스트 비어있으면 색인 제외.
- BR-19: `hybrid_search`는 world_id 필터 필수(교차 세계 누출 방지). Wiki 검색만 `__realworld__` 허용.

## 직렬화 (PBT Partial 대상)
- BR-20: 모든 Pydantic 모델은 `model_dump()` → `model_validate()` round-trip 동일성 보장. (NFR-C2)
- BR-21: Enum 값은 직렬화 안정(문자열 고정).

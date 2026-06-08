# U3 Topology — Business Rules

## 계층 (CONTAINS)
- BR-U3-1: parent_id는 같은 world_id 내 Region만 참조.
- BR-U3-2: 부모 미지정/미발견 Region은 최상위(parent_id=None) (FD3-Q1=A). 합성 루트 생성 안 함.
- BR-U3-3: 계층은 비순환(부모 체인에 자기 자신 금지) — 위반 시 해당 parent_id 무시 + 경고.
- BR-U3-4: 각 Region의 부모는 ≤ 1 (트리).

## 연결 (CONNECTED_TO)
- BR-U3-5: 엣지는 connection_hints + terrain.between 에서만 생성(FD3-Q2=A) — 무근거 자동 인접 금지.
- BR-U3-6: from/to가 모두 region으로 해소될 때만 엣지 생성(미해소 → skip + 경고).
- BR-U3-7: 같은 world_id 내에서만 연결(BR-17).
- BR-U3-8: 무방향 의미 — 쌍마다 양방향 2개(A→B, B→A), 동일 kind/weight (FD3-Q5=A).
- BR-U3-9: 동일 무방향 쌍 중복 입력은 1쌍으로 병합(더 강한 제약 kind 우선: blocked>river>route>adjacent? — MVP: 마지막 명시 우선, terrain이 hint를 덮어씀).

## Weight
- BR-U3-10: weight ∈ [0,1]; `clamp(base × Π modifiers)`.
- BR-U3-11: base는 kind 표, modifier는 terrain kind 휴리스틱 표(FD3-Q3/Q4=A) — 결정적.
- BR-U3-12: Wiki 기여 시 rationale + wiki_prior_ref + DERIVED_FROM 기록; provenance.source=inferred-wiki.
- BR-U3-13: Wiki lookup 실패/공백 → base weight 사용, 경고만(graceful, 빌드 미중단).

## 테스트/결정성
- BR-U3-14: 계층·엣지 수집·weight 계산은 순수 함수(LLM/IO 비의존) → 단위 테스트/PBT. Wiki만 mock.

# U4 Ontology — Business Rules

## 스코핑
- BR-U4-1: 비글로벌 Knowledge가 region_name 해소되면 정확히 그 지역에 `SCOPED_TO(scope_type=direct)`.
- BR-U4-2: `is_global=True` 지식은 SCOPED_TO 없음 — 쿼리 시 모든 지역에 포함(CL1=A).
- BR-U4-3: 미해소 & 비글로벌 지식은 미귀속 + low_confidence(보강 대상). 폐기하지 않음.
- BR-U4-4: inherited 스코프는 저장하지 않음(쿼리 시 CONTAINS 순회).

## ABOUT
- BR-U4-5: about_names는 같은 world_id 엔티티로만 해소; 미해소는 무시(에러 아님).

## 고증 (Q3=B)
- BR-U4-6: 고증 Knowledge는 `source=inferred-wiki`, `generated_by=llm`, confidence = suggestion×0.8(BR Q5=A), 해당 지역 direct 스코프.
- BR-U4-7: 매칭 Wiki prior가 있으면 `derived_from_prior_ids`에 기록(DERIVED_FROM 근거).
- BR-U4-8: 지역당 고증 ≤ N(기본 2). 생성 실패는 graceful(경고), 빌드 미중단.

## Dedup (CL2=C)
- BR-U4-9: 중복 후보 = 배치 내 코사인 유사도 ≥ SIM_THRESHOLD(기본 0.86).
- BR-U4-10: 후보 쌍은 LLM 판정(DuplicateVerdict)으로만 병합 확정 — 임계만으로 자동 병합하지 않음(병합은 민감).
- BR-U4-11: 병합 시 confidence=max, about/derived/refs 합집합, canonical 유지; 병합된 쪽의 SCOPED_TO는 canonical로 이전.
- BR-U4-12: 임베딩/LLM 실패 시 exact 정규화 병합으로 폴백(graceful).

## 일반
- BR-U4-13: U4는 Rumor를 만들지 않음(왜곡=U5).
- BR-U4-14: 순수 로직(코사인·후보·병합·스코프·about 해소)은 LLM/IO 비의존 → 단위 테스트/PBT.

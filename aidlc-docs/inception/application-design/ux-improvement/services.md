# UX Improvement — Services & Orchestration

## S1 — TranslationService (신규, X1)
- **책임**: 캐시 우선 로컬라이제이션. `LLMProvider`(Translator) + `SessionRepository`(번역 캐시) 조합.
- **오케스트레이션**:
  1. `localize(kind,id,text)` → repo에서 `(kind,id,lang)` 조회.
  2. hit & `source_hash` 일치 → 캐시 반환.
  3. miss/hash 불일치 → `Translator.translate` → `upsert_translation` → 반환(FR-UX3.5 재사용).
  4. `localize_many` → 미스만 모아 배치 번역(SEC-E 상한).
- **회복력**: 번역 실패 시 원문 폴백(뷰는 깨지지 않음, SEC-C).

## S2 — 생성 파이프라인 통합 (기존 RumorService/EventService/TurnAdvancer 확장, X1)
- **책임**: 콘텐츠 생성 직후 TranslationService로 ko 캐시 워밍(Q3=A).
- **DI**: 각 서비스 생성자에 `translation: TranslationService | None` 주입(옵션 — 미주입 시 조회 시 지연 번역).

## S3 — 세션 조회 로컬라이제이션 (SessionQuery/session router, X1)
- **책임**: 응답 조립 시 en+ko 동봉. 소문/이벤트/타임라인은 캐시 히트, 캐노니컬 `Knowledge`는 조회 시 지연 번역·캐시(Q4=B).
- **성능**: `localize_many`로 N+1 방지(NFR-UX2).

## S4 — TurnAdvancer 변동 셰이핑 (기존 확장, X1)
- **책임**: `advance_turn` 결과의 promoted/demoted/pruned/events_applied/events_resolved/rumors_added를 **지역별로 그룹핑**해 `region_changes` 생성(Q5=A). 지역 귀속은 소문/이벤트 `region_id` + `feedback_regions`.
- **불변**: 기존 top-level id 리스트는 후방호환 유지(가산).

## S5 — 프론트 전체 생성 오케스트레이션 (SessionPanel, X3)
- **책임**: 빈 지역 판정(distortions+listRumors, Q6=B) → 병렬 생성(Promise.all) + 진행률(N/M) + 부분 실패 개별 표기. 덮어쓰기(전체 재생성)는 확인 모달 게이트(FR-UX2.2).
- **SEC-E**: 병렬 상한(과도한 동시 호출 방지).

## S6 — 프론트 알림 오케스트레이션 (NotificationCenter, X3)
- **책임**: advance-turn 응답의 `region_changes` 소비 → 변동 있는 지역마다 알림 1건 생성(그 지역 변동 병합), 무변동 지역 무알림(FR-UX2.6).

## 오케스트레이션 흐름 (요약)
```
[생성] rumor/event/timeline 생성 → S2 → TranslationService.localize(캐시 워밍)
[조회] session knowledge/list → S3 → localize_many(소문/이벤트/타임라인 hit; knowledge 지연) → en+ko DTO
[턴]   advance_turn → (기존 룰) → S4 region_changes 셰이핑 → 응답
[UI]   turn 응답 → S6 지역별 알림 ; 전체생성 버튼 → S5 병렬+진행률
```

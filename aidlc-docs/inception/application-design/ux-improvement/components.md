# UX Improvement — Components

설계 결정: AD-UX Q1=A / Q2=**C**(별도 번역 테이블) / Q3=A / Q4=B / Q5=A / Q6=B / Q7=A / Q8=A / Q9=C.

핵심 통찰: **Q2=C + Q4=B → 단일 번역 캐시 테이블**이 세션 콘텐츠(생성 시 채움)와 캐노니컬 지식(조회 시 지연 채움)을 모두 수용. 저장은 정규화(캐시), 응답은 비정규화(en+ko 동봉).

---

## Backend Components

### C1 — Translator (`locus/translation/translator.py`) [X1]
- **책임**: 텍스트를 대상 언어(기본 `ko`)로 번역. 기존 `LLMProvider` 포트 재사용, 오프라인 목킹 가능(Q1=A).
- **인터페이스**: `translate(text, target_lang="ko") -> str`, `translate_many(texts, target_lang="ko") -> list[str]`. 빈/공백 입력은 무번역 통과(그대로 반환).
- **NFR/SEC**: LLM 호출 명시적 에러 처리(SEC-C, fail-safe: 실패 시 원문 폴백 + 경고 로그), API 키 미로깅(SEC-A).

### C2 — Translation 엔티티 + 저장 (`locus/session/models.py`, `repository.py`, `postgres_session_repo.py`, `memory_repo.py`) [X1]
- **책임**: 번역 캐시를 영속화(Q2=C). 신규 엔티티 `Translation` + `translations` 테이블.
- **필드**: `source_kind`(`rumor|event|timeline|knowledge`), `source_id`, `target_lang`, `text`(번역문), `source_hash`(원문 해시 — 변경 감지/무효화, FR-UX3.5), `world_id`(knowledge 캐시 파티션), `session_id`(nullable — 세션 콘텐츠), `created_at`.
- **키/유니크**: `(source_kind, source_id, target_lang)`.
- **Repo 메서드**: `get_translation(kind, id, lang)`, `get_translations_many([(kind,id)], lang)`, `upsert_translation(...)`. 후방호환 가산 테이블(ensure_schema idempotent).

### C3 — TranslationService (`locus/translation/service.py`) [X1]
- **책임**: 캐시 우선 번역 오케스트레이션. miss → Translator → 저장 → 반환. `source_hash` 불일치 시 재번역(FR-UX3.5). 배치 지원(전 지역/타임라인 렌더용).
- **인터페이스**: `localize(kind, id, source_text, *, world_id=None, session_id=None, lang="ko") -> str`, `localize_many([(kind,id,source_text)], ...) -> dict[id,str]`.
- **SEC-E**: 배치 크기·병렬 상한 존중(남용/비용 폭주 방지).

### C4 — Session content generation hooks (`rumor_generator.py`, `event_service.py`, `turn.py`) [X1]
- **책임**: 생성 시점(Q3=A)에 소문 `statement`, 이벤트 `description`, 타임라인 `summary`의 ko를 TranslationService로 미리 채움(캐시 워밍). 생성 실패해도 원문은 저장되고 ko는 조회 시 지연 생성 가능(회복력).

### C5 — Read-path enrichment (`query.py` 세션 쿼리 + `api/routers/session.py` 응답 DTO) [X1]
- **책임**: 세션 조회/목록 응답에 ko를 동봉(en+ko). 캐노니컬 `Knowledge`는 이 경로에서 지연 번역·캐시(Q4=B, 캐노니컬 그래프 불변). 반환 DTO는 `*_ko` 또는 `translation` 서브필드로 en·ko 모두 제공(FR-UX3.4/Q8=A 원문 토글 지원).

### C6 — RegionTurnChange 셰이핑 (`turn.py`, `models.py`) [X1]
- **책임**: `advance_turn`이 지역별 구조화 변동 요약을 생성(Q5=A). 신규 모델 `RegionTurnChange{region_id, promoted[], demoted[], pruned[], events_applied[], events_resolved[], rumors_added[]}`; `TurnResult.region_changes: list[RegionTurnChange]` 추가(가산). 지역 귀속: 소문/이벤트 `region_id` + `feedback_regions`.

### C7 — API surface (`api/routers/session.py`) [X1]
- **책임**: 응답 모델에 ko 동봉(C5), advance-turn 응답에 `region_changes`(C6). 전체 생성 신규 엔드포인트 없음(Q6=B, 프론트 병렬). 입력 검증 유지(SEC-A).

### C8 — Wiring/Config (`api/main.py`, `locus/config/settings.py`, `locus/translation/__init__.py`) [X1]
- **책임**: Translator/TranslationService DI 주입. 설정: `translation_target_lang="ko"`, `translation_enabled`, 번역 모델(기존 OpenAI 재사용). 미구성 시 graceful(원문 폴백).

---

## Frontend Components

### C9 — Design System: Tailwind + "Doodly" (`web/tailwind.config`, `web/src/index.css`, `web/src/ui/*`) [X2]
- **책임**: Tailwind 도입 + 디자인 토큰(색·간격·타이포·라운드·그림자) + "Doodly" 스타일(로컬 번들 손글씨 폰트 + CSS 스케치 요소, Q9=C, 외부 CDN 없음 SEC-B/D). 공용 프리미티브: `Button`, `Panel`, `Card`, `Badge`, `Toast`, `Modal(confirm)`.
- **제약**: 동작·`data-testid` 계약 보존(FR-UX1.5), 라이트 단일 테마.

### C10 — i18n 사전 (`web/src/i18n.ts`) [X3]
- **책임**: 한국어 UI 라벨 중앙 사전 + `t(key)` 헬퍼(Q7=A, 의존성 없음). 한국어 고정(Q12=A).

### C11 — Localized content + 원문 토글 (`web/src/ui/LocalizedText.tsx`, `types.ts`) [X3]
- **책임**: ko 기본 표시 + 항목별 "원문 보기" 토글(Q8=A). `types.ts`에 콘텐츠 ko 필드 추가.

### C12 — 전체 루머 생성 (`web/src/SessionPanel.tsx`, `api.ts`) [X3]
- **책임**: "전체 생성" 버튼 — 빈 지역 판정(distortions+listRumors, Q6=B) → 병렬 생성(Promise.all) + 진행률 + 부분 실패 표시(FR-UX2.1/2.3). 전체 재생성(덮어쓰기)은 확인 모달 후 실행(FR-UX2.2).

### C13 — 지역 상세 재생성 개선 (`web/src/RegionPanel.tsx` / `SessionPanel.tsx`) [X3]
- **책임**: 재설계된 지역 상세 뷰에 재생성 버튼 강조 배치 + 확인 모달 + 승격 소문 보존 노출(FR-UX2.4/2.5).

### C14 — 턴 변동 알림 (`web/src/ui/NotificationCenter.tsx`) [X3]
- **책임**: `TurnResult.region_changes` 소비 → **지역마다 알림 1건**(그 지역 변동 병합), 변동 없는 지역 무알림(FR-UX2.6). 토스트/배너 스택.

### C15 — api.ts/types.ts 갱신 [X3]
- **책임**: 신규 필드(ko, region_changes) 타입, 응답 매핑.

---

## Unit Mapping (제안)
- **X1 Localization Backend**: C1–C8
- **X2 Frontend Design System**: C9
- **X3 Frontend UX Features**: C10–C15 (+ C9 프리미티브 사용)

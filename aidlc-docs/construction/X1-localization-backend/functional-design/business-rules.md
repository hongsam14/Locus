# X1 Localization Backend — Business Rules

## Translator (BR-X1-1..4)
- **BR-X1-1** 빈/공백 텍스트는 번역하지 않고 그대로 반환.
- **BR-X1-2** 번역은 기존 `LLMProvider.complete`로 수행(별도 서비스/키 없음, FR-UX3.3). 목킹 가능(NFR-UX3).
- **BR-X1-3** LLM 실패는 예외를 전파하지 않고 원문 반환 + 경고 로그(SEC-C fail-safe). API 키/시크릿 미로깅(SEC-A).
- **BR-X1-4** `translate_many`는 각 항목 독립 처리 — 일부 실패가 나머지를 막지 않음.

## 캐시/무효화 (BR-X1-5..9)
- **BR-X1-5** 캐시 키 = `(source_kind, source_id, source_field, target_lang)` 유니크.
- **BR-X1-6** 조회 시 캐시의 `source_hash`가 현재 원문 해시와 **일치할 때만** 히트로 인정(불일치→재번역, FR-UX3.5/Q1=A).
- **BR-X1-7** 번역 성공분만 캐시에 저장. 폴백(번역=원문)은 저장하지 않음 → 다음 조회 재시도(Q4=A).
- **BR-X1-8** 캐노니컬 `Knowledge` 번역 캐시는 **world 범위**(`world_id` 파티션, `session_id=null`), 세션 간 재사용(Q3=A).
- **BR-X1-9** 세션 콘텐츠(rumor/event/timeline) 캐시는 `session_id` 스코프.

## 번역 대상 (BR-X1-10..12, 25)
- **BR-X1-10** 세션 콘텐츠 LLM 번역 대상 필드: 소문 `statement`, 이벤트 `description`. (타임라인 `summary`는 제외 — BR-X1-25.)
- **BR-X1-11** 캐노니컬 `Knowledge`는 `title` + `statement` 둘 다 번역(Q2=A), 각각 별도 캐시 행.
- **BR-X1-12** 대상 언어는 `ko` 고정(Q12=A); `target_lang`는 확장 여지로 파라미터화하되 기본 ko.
- **BR-X1-25 (F2a)** `TimelineEntry.summary`는 코드 템플릿 문자열이므로 LLM 번역/캐시 대상이 **아니다**. 타임라인 현지화는 X3에서 `kind`+`payload` 기반 UI i18n으로 처리한다(FR-UX3.2의 "타임라인 메시지"는 UI 현지화로 충족). `source_kind`에 `timeline` 없음.

## 생성 시점 워밍 (BR-X1-13..14, 26)
- **BR-X1-13** 소문/이벤트 생성 직후 번역 캐시를 워밍할 수 있다(Q3=A). 워밍은 best-effort — 실패해도 콘텐츠 생성/커밋에 영향 없음(Q6=A, SEC-C).
- **BR-X1-14** `translation` 미주입 또는 `translation_enabled=False`면 워밍 스킵, 조회 시 지연 번역 또는 원문 표시(graceful).
- **BR-X1-26 (F4, NFR-UX1)** 워밍은 선택적 최적화다. `translation_warm_on_generate`(기본 **False**)로 제어하며, 기본값에서 `advance_turn` 등 다지역 경로는 워밍하지 않고 조회 경로의 지연 번역을 안전망으로 삼아 턴 임계경로를 보호한다.

## 조회 로컬라이제이션 (BR-X1-15..17, 27)
- **BR-X1-15** 세션 조회/목록 응답은 원문 + ko를 함께 반환(원문 토글 지원, FR-UX3.4/Q8=A). ko 미해결 시 해당 ko 필드는 `None`.
- **BR-X1-27 (F3)** ko는 **응답 전용 표현**으로만 노출하며 저장 스키마에 영속하지 않는다(Q2=C 유지). (i) 세션 knowledge 경로는 `KnowledgeView`에 응답 전용 옵션 필드 `statement_ko`/`title_ko` 추가(`is_rumor`로 rumor/knowledge 키잉 구분). (ii) `list_rumors`/`list_events` 직접 반환 경로는 `SessionRumor.statement_ko`/`SessionEvent.description_ko`를 기본 `None`·비영속 응답 전용 필드로 채운다(영속 컬럼 아님을 주석·테스트로 고정).
- **BR-X1-16** 다건 조회는 `localize_many`로 처리해 N+1 번역 호출을 피함(NFR-UX2).
- **BR-X1-17** 캐노니컬 Knowledge는 조회 시 지연 번역 후 world 캐시에 저장(Q4=B). 캐노니컬 그래프(Neo4j/OpenSearch)는 불변(NFR-UX5).

## 턴 변동 셰이핑 (BR-X1-18..21)
- **BR-X1-18** `advance_turn`은 기존 top-level id 리스트를 유지하고 `region_changes`를 추가로 셰이핑(가산, 후방호환).
- **BR-X1-19** `region_changes` 각 원소는 지역 하나의 변동 병합. 소문/이벤트는 각자의 `region_id`로 그룹핑, 피드백 이동 지역은 `feedback_regions`로 귀속.
- **BR-X1-20** `rumors_added`는 이번 턴 새로 생성/추가된 소문 id(Q5=A). **(F1)** 데이터는 `advance_turn` 2단계에서 `append_for_region(...) -> list[SessionRumor]`의 반환을 지역별로 수집해 확보한다(현재 코드는 이 반환을 버리므로 수집 추가 필요). 미수집 시 신규 소문이 알림에서 누락되므로 이는 필수 구현 사항이다.
- **BR-X1-21** 6개 변동 리스트가 모두 빈 지역은 `region_changes`에서 제외(무변동 무알림, FR-UX2.6).

## 남용 방지/성능 (BR-X1-22..23)
- **BR-X1-22** `localize_many` 배치 크기는 `translation_batch_size`(기본 20)로 제한, 초과분은 소배치 순차 처리(SEC-E).
- **BR-X1-23** 캐시 우선으로 반복 조회 시 LLM 재호출을 하지 않음(NFR-UX2 비용 최소화).

## 스키마/후방호환 (BR-X1-24)
- **BR-X1-24** `translations` 테이블·`TurnResult.region_changes`는 가산 도입. `ensure_schema`는 idempotent하며 기존 세션 데이터와 후방호환(NFR-UX5).

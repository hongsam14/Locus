# X1 Localization Backend — Domain Entities

결정: FD-X1 Q1=A(source_hash 무효화)/Q2=A(title+statement)/Q3=A(world 범위 캐시)/Q4=A(조용한 원문 폴백)/Q5=A(신규 소문 포함)/Q6=A(best-effort)/Q7=A(배치 상한 settings).

## Translation (신규 엔티티 — 번역 캐시)
번역 캐시 1행 = 한 소스 텍스트의 한 언어 번역.

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | str | `new_id()` |
| `source_kind` | str | `rumor` \| `event` \| `knowledge` (타임라인 제외 — F2(a), X3 UI i18n 처리) |
| `source_id` | str | 원 엔티티 id (SessionRumor.id / SessionEvent.id / Knowledge.id) |
| `source_field` | str | 번역된 원 필드명 (`statement` \| `description` \| `title`) — Knowledge는 title/statement 2행 |
| `target_lang` | str | 기본 `"ko"` |
| `text` | str | 번역문 |
| `source_hash` | str | 원문 텍스트 해시(sha256 등) — 무효화 판정(Q1=A) |
| `world_id` | str \| None | knowledge 캐시 파티션(Q3=A); 세션 콘텐츠는 None 가능 |
| `session_id` | str \| None | 세션 콘텐츠 캐시(rumor/event/timeline); knowledge는 None(world 범위, Q3=A) |
| `created_at` | datetime \| None | DB now |

- **유니크 키**: `(source_kind, source_id, source_field, target_lang)`.
- **저장소**: 세션 PostgreSQL 레이어의 신규 가산 테이블 `translations` (ensure_schema idempotent, 후방호환).

## RegionTurnChange (신규 값 객체 — 턴 변동 지역별 요약)
`TurnResult.region_changes`의 원소. 한 지역에서 이번 턴 발생한 변동의 병합(FR-UX2.6).

| 필드 | 타입 | 설명 |
|---|---|---|
| `region_id` | str | 지역(캐노니컬 id) |
| `promoted` | list[str] | 승격된 소문 id |
| `demoted` | list[str] | 강등된 소문 id |
| `pruned` | list[str] | 프룬(소멸)된 소문 id |
| `events_applied` | list[str] | 이번 턴 적용된 이벤트 id |
| `events_resolved` | list[str] | 이번 턴 해소된 이벤트 id |
| `rumors_added` | list[str] | 이번 턴 새로 생성/추가된 소문 id(Q5=A) |

- **불변식**: 6개 리스트가 모두 비면 그 지역은 `region_changes`에 포함되지 않음(무변동 무알림).
- **`rumors_added` 데이터 확보(F1)**: `advance_turn` 2단계 `append_for_region(...) -> list[SessionRumor]`의 **반환을 지역별로 수집**해 채운다. 현재 코드는 이 반환을 버리므로(turn.py) 수집 로직 추가가 필요하다(변경 작음 — 반환 타입 이미 적합). 미수집 시 신규 소문이 알림에서 누락됨.

## TurnResult (가산 확장)
- 기존 필드(promoted_ids/demoted_ids/pruned_rumor_ids/applied_event_ids/resolved_event_ids/feedback_regions) **유지**.
- **추가**: `region_changes: list[RegionTurnChange] = []` (기존 필드로부터 파생 셰이핑, 후방호환).

## 기존 엔티티 (불변 — 참조만)
- `SessionRumor.statement` / `SessionEvent.description` / `Knowledge.title`·`Knowledge.statement` = 번역 소스(영어). 저장 모델엔 ko 필드 추가하지 않음(Q2=C 별도 테이블). ko는 **응답 표현**에서 동봉.
- `TimelineEntry.summary`는 **코드 템플릿 문자열**(예: `"pruned <id>"`)이므로 LLM 번역 대상이 아니다(F2(a)). 타임라인 현지화는 X3에서 `kind`+`payload` 기반 UI i18n으로 처리(FR-UX3.2 재해석: "타임라인 메시지"는 UI 현지화로 충족).

## 응답 표현 (API — en+ko) — F3 명시
Q2=C(저장에 ko 없음)와 응답 표현을 구분한다. 저장은 정규화 캐시, **응답 전용**으로 ko를 동봉(원문 토글 지원, FR-UX3.4/Q8=A):
- **세션 knowledge 경로(`QueryResult.items` = `KnowledgeView`)**: `KnowledgeView`는 이미 뷰/투영이며 `title` 옵션을 보유 → 여기에 **응답 전용 옵션 필드** `statement_ko: str|None`, `title_ko: str|None`을 추가(저장 모델 아님 → Q2=C 무위배). 항목 구분은 `is_rumor`로: rumor 뷰 → `localize("rumor", knowledge_id, "statement", …)`, 캐노니컬 → `localize("knowledge", knowledge_id, "title"/"statement", …, world_id)`.
- **`list_rumors` / `list_events` 직접 반환 경로**: 저장 모델을 그대로 반환하므로, **응답 전용 nullable 필드**(`SessionRumor.statement_ko`, `SessionEvent.description_ko`, 기본 None·비저장/미영속) 또는 별도 응답 DTO 중 택일. 본 유닛은 **응답 전용 nullable 필드** 방식을 채택(직렬화 단순·프론트 계약 최소 변경; 영속 컬럼 아님을 코드 주석·테스트로 고정).
- ko 미해결(폴백) 시 해당 ko 필드는 `None` → 프론트는 원문 표시.

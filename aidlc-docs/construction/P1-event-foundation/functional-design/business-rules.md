# P1 Event Foundation — Business Rules

> BR-P1-*. additive; 캐노니컬 불변; Phase 1(BR-S1-*) 규약 계승.

| ID | 규칙 |
|---|---|
| **BR-P1-1** | `magnitude`는 [0,1]. 모델 직접 생성 시 범위 밖은 거부(Pydantic Field ge/le); **서비스 경로(create_event)는 클램프**(adjust_support/set_distortion 컨벤션 일치). |
| **BR-P1-2** | `create_event`의 `region_id`는 그 world 캐노니컬 토폴로지에 존재해야 함. 없으면 LookupError→404 (FD-P1 Q2=A). |
| **BR-P1-3** | `lifecycle` 미지정 시 `CATEGORY_DEFAULT_LIFECYCLE[category]` 적용. 명시 시 override (CL1.3). |
| **BR-P1-4** | 수동 생성 Event는 `status=ACTIVE`, `provenance.generated_by="gm:event"`. (제안 경로 SUGGESTED/llm은 P2.) |
| **BR-P1-5** | `created_turn` = 생성 시점 세션 `turn`. `id`는 앱 생성(new_id). (Phase 1 규약.) |
| **BR-P1-6** | `resolve_event`는 idempotent — 이미 RESOLVED면 그대로 반환(중복 타임라인 없음). |
| **BR-P1-7** | 쓰기 동작(create/resolve/discard)은 OPEN 세션만. CLOSED면 SessionClosedError→409. 읽기(list/get)는 닫힌 세션에도 허용. |
| **BR-P1-8** | `discard_event`는 `SUGGESTED` 상태만 삭제 가능. ACTIVE/RESOLVED 폐기 시도는 거부(ValueError). |
| **BR-P1-9** | 모든 Event 동작은 `session_id` 스코프 — 세션 간 격리(다른 세션 event 접근 불가). (BR-S1-15 계승) |
| **BR-P1-10** | `session_events` 스키마 생성은 idempotent `CREATE TABLE IF NOT EXISTS`(ensure_schema). `init-schema` + 앱 부팅 둘 다 안전. (BR-S1-17 계승) |
| **BR-P1-11** | Event는 캐노니컬 노드를 `region_id` 문자열로 **참조만**(복사/스냅샷 없음). 세션 쓰기가 캐노니컬을 변경하지 않음(NFR-P2). |
| **BR-P1-12** | `contributions`는 P1에서 항상 `{}`(빈 맵). 값 채움/복원은 P2 dynamics 책임. |
| **BR-P1-13** | TimelineKind enum에 `EVENT_CREATED/EVENT_APPLIED/EVENT_RESOLVED` 추가 — 기존 값/순서 불변(additive). |
| **BR-P1-14** | 기존 SessionRepository 시그니처·라우트·모델 불변. P1은 신규 메서드/필드/라우트/테이블만 추가(NFR-P5). |

## 검증/에러 시나리오
- 존재하지 않는 session → LookupError→404.
- 존재하지 않는 region(create) → LookupError→404 (BR-P1-2).
- magnitude 범위 밖 → 422(Pydantic).
- 닫힌 세션 쓰기 → 409 (BR-P1-7).
- ACTIVE/RESOLVED discard → 400/409 (BR-P1-8).

## 테스트 포인트 (P1)
- Event CRUD round-trip(in-memory + postgres/SQLite).
- region 검증(존재/부재).
- lifecycle 기본 매핑 + override.
- resolve idempotent / 닫힌 세션 가드 / discard 상태 제약.
- ensure_schema 멱등.
- Phase 1 회귀(기존 세션 동작 불변).

# Rumor / Game-Session **Phase 2** — 요구사항 (Requirements)

> 완료된 Locus + **Rumor/Game-Session Phase 1**(S1+S2+S3, PostgreSQL 세션 레이어) 위 **brownfield 신규 기능 사이클**.
> Phase 1에서 deferred 된 **Event + Event 상호작용 → 동적 distortion 진화**를 구현한다.
> 참조: `rumor-distortion-requirements.md` §7(Out of Scope: Event+interaction, support auto-increase), §4 FR-R4.3(Event=Phase 2).

## 1. Intent Analysis Summary
- **Request**: "ai-dlc를 사용해서 Phase 2를 구현하고 싶어." → 정적/수동이던 per-region `distortion_degree`를 **Event 기반으로 동적 진화**시키고, support 자동 진화 + 이벤트→소문 자동 갱신을 추가.
- **Request Type**: New Feature (세션 레이어 위 신규 동적 메커니즘 + UI).
- **Scope**: Multiple Components (세션 백엔드 신규 엔티티/엔진/서비스 + API + 웹). 인프라 변화 없음(기존 PostgreSQL 재사용).
- **Complexity**: Complex. **Depth**: Comprehensive. **Workspace**: Brownfield resume.
- **호환 정책(불변식)**: 캐노니컬 레이어(Neo4j/OpenSearch)는 **불변 참조만**. 세션 레이어(PostgreSQL)에 **additive**. 기존 **177 backend + 14 frontend 테스트 GREEN** 유지, ruff/black/tsc 클린.

## 2. 용어 (Glossary) — Phase 2 추가/정제
| 용어 | 정의 |
|---|---|
| **Event (SessionEvent)** | 한 리전에 영향을 주는 사건. 세션 레이어(PostgreSQL)에 저장되는 신규 엔티티. `category`·`magnitude`·`description`·대상 region·lifecycle·status를 가짐. GameMaster 또는 LLM이 생성. |
| **category** | Event의 사전 정의 분류(enum: 예 war/disaster/festival/plague…). 카테고리별 **기본 lifecycle**을 결정(override 가능). |
| **magnitude** | Event 강도(0~1). distortion delta 계산의 입력. |
| **lifecycle** | `one_shot`(1회 적용 후 해소) / `persistent`(해소 전까지 매 턴 적용). 카테고리 기본값 + 생성 시 override. |
| **resolve(해소)** | persistent Event를 끝내는 행위. **그 자체가 하나의 Event/액션**(GM 또는 LLM이 동일 방식으로 생성). 해소 시 그 Event가 누적시킨 distortion 기여분을 복원/감쇠. |
| **distortion delta** | Event가 리전 `distortion_degree`에 가하는 변화량(결정론적 공식, magnitude 기반). 토폴로지 거리로 이웃에 감쇠 전파. |
| **accumulated_delta** | 한 Event가 활성 동안 누적 적용한 총 기여분(해소 시 복원에 사용). |
| **support 자동 진화** | advance_turn마다 support가 자동 증감(이벤트 영향 리전=강화↑, 그 외=감쇠↓). Phase 1의 수동 조정과 공존. |

## 3. 아키텍처 원칙 (Phase 1 계승)
- **2-레이어 분리**: 캐노니컬(Neo4j, 정적·읽기 참조) / 세션(PostgreSQL, 동적·휘발). Event는 세션 레이어 전용.
- 세션 레코드는 캐노니컬 노드를 **id로 참조만**. 세션 쓰기가 캐노니컬을 변경하지 않는다(불변식 NFR-P2).
- 세션 저장은 기존 **`SessionRepository` 포트** 뒤. Event CRUD는 **additive 확장**(PostgreSQL 어댑터 + in-memory mock). 기존 시그니처 불변.
- **턴 기반 시뮬레이션**: 모든 동적 진화(Event 적용·distortion 갱신·소문 갱신·support 진화·승격/강등)는 **`advance_turn`에서 일괄** 수행되고 Timeline에 기록.

---

## 4. Functional Requirements (Phase 2)

### 영역 P1 — Event 엔티티 & 영속화
- **FR-P1.1**: 세션 레이어 PostgreSQL에 **신규 `SessionEvent` 엔티티/테이블**을 additive로 추가. 캐노니컬 불변. (Q1=A)
- **FR-P1.2**: Event 속성(최종 필드는 Functional Design 확정): `id`, `session_id`, `region_id`(주 대상), `category`(enum), `description`(자유 텍스트), `magnitude`(0~1), `lifecycle`(one_shot|persistent), `status`(active|resolved), `created_turn`, `resolved_turn`, **`accumulated_delta`**(복원용), `provenance`(생성자: gm|llm). (Q2=B, CL1)
- **FR-P1.3**: `SessionRepository` 포트에 Event CRUD(create/get/list/update-status) 추가 — PostgreSQL 어댑터 + in-memory mock 둘 다, 기존 시그니처 불변. `init-schema`에 `session_events` 테이블 생성(ensure_schema 확장). (Q13=A)

### 영역 P2 — Event 생성
- **FR-P2.1 (수동)**: GameMaster가 웹에서 Event 수동 생성(category/description/magnitude/대상 리전 입력). (Q4=C)
- **FR-P2.2 (LLM 자동 제안)**: **매 `advance_turn`마다** LLM이 현재 세션 상태(리전·소문·진행 턴)를 기반으로 1건 이상의 Event를 **제안**한다. (Q4=C, CL2.2=B)
- **FR-P2.3 (suggest-then-approve)**: LLM 제안 Event는 곧바로 활성화되지 않는다. **GameMaster가 채택/수정/폐기**한 것만 active Event로 커밋된다. (CL2.1=A)
- **FR-P2.4 (카테고리 기본 lifecycle)**: 각 category는 기본 lifecycle을 가진다(예: disaster/festival=one_shot, war/plague=persistent). 생성 시 사용자가 override 가능. 구체 매핑은 Functional Design. (CL1.3=A)

### 영역 P3 — Event → 동적 distortion 진화 (핵심)
- **FR-P3.1 (결정론적 delta)**: Event가 리전 `distortion_degree`에 가하는 변화는 **결정론적 공식**(magnitude → delta)으로 산출하고 [0,1]로 clamp. 순수 로직(테스트 용이). (Q5=C)
- **FR-P3.2 (토폴로지 전파)**: delta는 주 대상 리전 + **이웃 리전에 거리 감쇠**로 전파된다. consensus의 거리 기반 전파 메커니즘을 재사용. (Q3=C, Q5=C)
- **FR-P3.3 (적용 시점=advance_turn 일괄)**: Event 효과는 `advance_turn`에서 일괄 처리된다. 처리 순서: **(1) 활성 Event 수집 → (2) distortion 갱신(주 대상+전파) → (3) 소문 갱신 → (4) support 자동 진화 → (5) 승격/강등 재평가 → (6) Timeline 기록**. (Q6=A, Q7=B)
- **FR-P3.4 (persistent 누적)**: `persistent` Event는 active인 동안 **매 턴 동일 delta를 재적용**(누적 상승, clamp). 누적분은 `accumulated_delta`에 기록. (CL1.2=A)
- **FR-P3.5 (one_shot)**: `one_shot` Event는 적용 턴에 1회 효과 적용 후 `resolved`로 전이. (Q10=X via category)
- **FR-P3.6 (해소=이벤트)**: persistent Event의 해소(resolve)는 **그 자체가 하나의 Event/액션**(GM 또는 LLM이 동일 방식으로 생성). 해소 적용 시 해당 Event의 `accumulated_delta`를 **복원/감쇠**(distortion에서 차감)하고 status=resolved. (CL1.1=X, CL1.2=A)

### 영역 P4 — Event → Rumor 처리
- **FR-P4.1 (주 대상 리전 갱신)**: Event 영향을 받은 **주 대상 리전**의 소문은 새 distortion 기반으로 **add/update** 하되 **기존 소문과 support를 보존**한다(전체 wipe 아님 — 수동 `regenerate_region`과 구분). (Q7=B, CL3.1=B)
- **FR-P4.2 (전파 이웃)**: 전파(거리 감쇠)만 받은 이웃 리전은 **distortion 수치만 갱신**하고 소문은 재생성하지 않는다. (CL4.1=A)
- **FR-P4.3 (시점)**: 소문 갱신은 `advance_turn` 처리 시퀀스(FR-P3.3) 안에서 수행. (Q7=B note)
- **FR-P4.4 (수동 경로 유지)**: 기존 수동 `generate_rumors`/`regenerate_region`(전체 wipe) 동작은 그대로 유지(회귀 없음).

### 영역 P5 — support 자동 진화
- **FR-P5.1 (자동 증감)**: `advance_turn`마다 support 자동 진화 — **그 턴 Event 영향 리전(주 대상 + 전파 이웃)의 소문 = 강화(support↑)**, 영향 없는 리전 소문 = **감쇠(support↓)**. 증감폭은 결정론적(공식은 Functional Design). (Q9=B, CL3.2=A)
- **FR-P5.2 (승격/강등 재평가)**: support 진화 후 기존 `promotion.evaluate(threshold)`로 승격/강등을 재평가 — threshold 교차 시 자동 승격/강등 + Timeline 기록. (Phase 1 메커니즘 재사용)
- **FR-P5.3 (수동 공존)**: Phase 1의 수동 support 조정(`adjust_support`)은 유지되며 자동 진화와 공존.

### 영역 P6 — Timeline & GameMaster 턴
- **FR-P6.1 (TimelineKind 확장)**: Event 라이프사이클용 새 `TimelineKind`를 additive 추가(예: `EVENT_CREATED` / `EVENT_APPLIED` / `EVENT_RESOLVED`). 기존 enum 값 불변. (Q6, Timeline)
- **FR-P6.2 (턴 결과 확장)**: `advance_turn`은 단일 시퀀스로 처리되고 `TurnResult`를 확장(예: `applied_event_ids`, `created_event_ids`, `promoted_ids`, `demoted_ids`). 각 하위 변경은 Timeline 엔트리로 기록.

### 영역 P7 — NPC 쿼리 (불변)
- **FR-P7.1**: NPC 쿼리 노출 규칙은 **Phase 1 그대로 유지** — direct + inherited + global Knowledge + 승격된 Rumor + Rumor; propagated/자동-rumor view는 비노출. Phase 2는 distortion/소문/ support **값만** 동적으로 진화시킨다. (Q11=A)
- **FR-P7.2**: 세션 미지정(캐노니컬) 쿼리는 기존 동작 유지(회귀 없음).

### 영역 P8 — 웹 UI (풀)
- **FR-P8.1 (Event 생성 폼)**: SessionPanel에 Event 수동 생성 폼(category / description / magnitude / 대상 리전 = 지도 선택). (Q12=A)
- **FR-P8.2 (LLM 제안 승인 UI)**: 턴 진행 시 제시되는 LLM 제안 Event를 표시하고 **채택/수정/폐기** UI 제공. (CL2)
- **FR-P8.3 (Event 목록 & 해소)**: 활성/해소 Event 목록 표시 + 해소(resolve) 액션 트리거.
- **FR-P8.4 (Timeline)**: Timeline에 Event 관련 항목(생성/적용/해소) 표시.
- **FR-P8.5 (distortion 시각화)**: 턴 진행에 따른 per-region `distortion_degree` 변화 표시(기존 distortion 슬라이더/표시 확장).

---

## 5. Non-Functional Requirements (Phase 2)
- **NFR-P1 (포트 추상화)**: Event 저장은 `SessionRepository` 포트의 additive 확장. PostgreSQL 어댑터 + in-memory mock(오프라인 테스트).
- **NFR-P2 (레이어 격리)**: 세션 레이어는 캐노니컬(Neo4j)을 **읽기 참조만**. Event/턴 처리가 캐노니컬을 변경하지 않는다(불변식).
- **NFR-P3 (LLM graceful)**: LLM Event 제안 실패 시 그 제안만 생략하고 턴 진행은 계속. **distortion delta·전파·support 진화는 LLM 비의존(결정론적)** — LLM 장애와 무관하게 동작.
- **NFR-P4 (결정론/테스트)**: distortion delta·토폴로지 전파·support 진화·lifecycle 판정·accumulated 복원은 **순수 함수**로 분리. PBT(Partial) 적용 대상.
- **NFR-P5 (회귀)**: 기존 177 backend + 14 frontend 테스트 GREEN 유지. Phase 1 NPC 쿼리/수동 소문 경로 불변. ruff/black/tsc 클린.
- **NFR-P6 (인프라 무변경)**: 기존 PostgreSQL 세션 스택 재사용. **신규 인프라 컴포넌트 없음** — `session_events` 테이블만 additive(ensure_schema). docker-compose 변화 없음.

## 6. Data Model (확정은 Functional/Application Design)
- **신규** (PostgreSQL): `SessionEvent`(FR-P1.2 필드). `init-schema`에 `session_events` 테이블.
- **재사용/mutate**: `RegionDistortion`(Event가 동적으로 갱신; accumulated 추적은 SessionEvent 측). `SessionRumor`(support 자동 진화; 주 대상 리전 add/update).
- **additive 확장**: `TimelineKind`(EVENT_* 추가), `TurnResult`(event id 필드 추가), `SessionRepository`(Event CRUD).
- **캐노니컬 모델 변경 없음**(참조만).

## 7. Out of Scope (Phase 3+)
- **루머 피드백 루프** — 소문 자체가 리전 distortion을 끌어올리는 메커니즘. (Q8=B; Phase 3)
- **Event 간 상호작용/연쇄** — 복수 Event의 조합·연쇄 효과 시뮬레이션(Phase 2는 개별 Event 적용까지).
- Event/세션 데이터 검색 인덱싱(세션은 PostgreSQL 전용, 비인덱싱 — Phase 1 결정 계승).

## 8. 확정 가정 (Answer 기반)
1. Event = 세션 PostgreSQL 신규 엔티티(category enum + magnitude + lifecycle), `SessionRepository` additive. (Q1/Q2/Q13)
2. Event 효과는 **결정론적 distortion delta + 토폴로지 전파**, `advance_turn`에서 일괄 적용. (Q3/Q5/Q6)
3. 생성 = GM 수동 + 매 턴 LLM 제안(suggest-then-approve). (Q4/CL2)
4. persistent = 매 턴 누적 delta, 해소(=이벤트)까지 지속; one_shot = 1회; 카테고리 기본값 override 가능. (Q10/CL1)
5. 주 대상 리전 소문 = 기존 보존+add/update(support 유지); 전파 이웃 = distortion+support만; support 자동 진화(영향=강화/그 외=감쇠) + 승격/강등 재평가. (Q7/Q9/CL3/CL4)
6. NPC 쿼리 규칙 불변; 웹 풀 UI; 인프라 무변경. (Q11/Q12/NFR-P6)

## 9. Trigger 평가 (다음 스테이지)
- **User Stories**: SKIP 후보 — 기존 persona/스토리(P2 월드/레벨 디자이너, GameMaster)가 actor 커버. (Workflow Planning에서 확정)
- **Application Design**: **EXECUTE 후보** — 신규 컴포넌트/서비스(EventEngine·distortion 진화·support 진화·LLM EventSuggester·GameMasterService 확장).
- **Units Generation**: **EXECUTE 후보** — 백엔드 엔진/서비스 → API → 웹으로 단위 분할(Phase 1처럼 S-단위).
- **Infrastructure Design**: **SKIP 후보** — 신규 인프라 없음(NFR-P6), 테이블만 additive.
- **NFR (light)**: Phase 1처럼 단일 light 노트 후보.

## 10. Extension Configuration (이번 사이클)
| Extension | Enabled | Decided At |
|---|---|---|
| Security Baseline | No | Phase 2 Requirements Analysis (Security=B) |
| Property-Based Testing | Yes (Partial — pure functions & serialization round-trips only) | Phase 2 Requirements Analysis (PBT=B) |

## 11. Key Requirements 요약
- **SessionEvent**(category·magnitude·lifecycle, PostgreSQL additive) + `SessionRepository` Event CRUD.
- **Event 생성**: GM 수동 + 매 턴 LLM 제안(승인 게이트).
- **동적 distortion**: 결정론적 delta + 토폴로지 전파, `advance_turn` 일괄; persistent=누적/해소까지, one_shot=1회.
- **이벤트→소문**: 주 대상 리전 보존+갱신(support 유지), 전파 이웃은 distortion만.
- **support 자동 진화**: 영향 리전 강화/그 외 감쇠 + 승격/강등 재평가; 수동 조정 공존.
- **Timeline/TurnResult** additive 확장; **NPC 규칙 불변**; **웹 풀 UI**; **인프라 무변경**.
- **루머 피드백 루프·Event 간 상호작용은 Phase 3**.

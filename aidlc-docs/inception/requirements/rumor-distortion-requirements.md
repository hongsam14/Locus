# 소문 내용 실제 왜곡 + 게임 세션 레이어 — 요구사항 (Requirements)

> 완료된 Locus 위 **brownfield 신규 기능 사이클**. 단순 "소문 텍스트 왜곡"을 넘어, **동적 게임 세션 레이어**를 도입한다.
> 본 사이클은 **Phase 1** (세션 골격 + 소문 생성/지지도/승격 + 턴/타임라인 + NPC 규칙 + 웹). **Event 상호작용은 Phase 2(다음 사이클)**.

## 1. Intent Analysis Summary
- **Request**: Knowledge/Rumor 내용을 LLM이 실제 왜곡해 Rumor로 생성(웹 버튼 트리거). 답변 과정에서 게임 세션·턴·GameMaster·타임라인·지지도·승격 개념이 추가됨.
- **Request Type**: New Feature (신규 레이어 + UI).
- **Scope**: Cross-system (신규 PostgreSQL 인프라 + 백엔드 서비스/포트 + API + 웹).
- **Complexity**: Complex. **Depth**: Comprehensive.
- **호환 정책**: 캐노니컬 레이어(Neo4j/OpenSearch, world별 정적)는 **불변 유지**. 세션 레이어는 **추가(additive)**. 기존 117/133 테스트 GREEN 유지.

## 2. 용어 (Glossary)
| 용어 | 정의 |
|---|---|
| **캐노니컬 레이어** | world별 정적 데이터(Region/토폴로지/Entity/Knowledge/WikiPrior). Neo4j+OpenSearch. 게임이 바뀌어도 유지. |
| **게임 세션 레이어** | 한 world 위 한 판(play-through)의 동적·휘발 상태. **PostgreSQL**. 신규. |
| **GameSession** | world 위에서 시작/종료되는 한 판. world당 여러 이력 보관. |
| **턴(turn)** | GameMaster가 세션을 한 단계 진행시키는 단위. 각 턴은 타임라인에 기록. |
| **GameMaster** | 매 턴 세션을 변화시키는 주체. Phase 1: **Rumor 생성/재생성/승격·강등** + 리전별 `distortion_degree` 보유/설정. Phase 2: Event 상호작용으로 동적 진화. |
| **Rumor** | Knowledge(또는 Rumor)를 LLM이 **실제 왜곡한 텍스트**. `distortion_degree`·`support`(지지도)·`distorted_from_id`·region scope·confidence. 세션 레이어에 저장. 세션마다 재생성. |
| **support(지지도)** | Rumor가 얼마나 받아들여지는지. threshold 초과 시 승격. Phase 1: 수동 설정/조정. |
| **승격/강등** | support ≥ threshold → 세션 내 그 리전의 **direct Knowledge처럼** 노출(캐노니컬엔 안 씀). threshold 미만으로 떨어지면 **강등**(되돌림). |
| **Timeline** | 세션에서 GameMaster가 턴마다 한 변경(생성/재생성/승격/강등 등)의 시간순 기록. |
| **Event** | (Phase 2) 리전에 영향을 주는 사건. GameMaster가 해석해 distortion/소문을 동적으로 바꿈. |
| **자동 소문(propagated)** | consensus의 거리 기반 전파 분류(텍스트 불변). 세션과 무관, 재생성 안 됨. 기획자용. |

## 3. 아키텍처 원칙
- **2-레이어 분리**: 캐노니컬(Neo4j)=정적·참조 대상 / 세션(PostgreSQL)=동적·휘발. (CL-A/B)
- 세션 레코드는 캐노니컬 노드를 **id로 참조만** 함(복사·스냅샷 없음). `distorted_from_id`는 Neo4j Knowledge/Rumor id 또는 세션 내 Rumor id를 가리킴. (CL-C2=A)
- 세션 저장은 신규 **`SessionRepository` 포트**(PostgreSQL 어댑터) 뒤. 오프라인 테스트는 in-memory mock. (CL-F2=A)
- 새 게임(세션) 시작 시 이전 세션의 Rumor/Timeline/승격은 그 세션에 귀속될 뿐, 캐노니컬엔 영향 없음. 과거 세션은 이력으로 열람 가능. (CL-C1=A)

---

## 4. Functional Requirements (Phase 1)

### 영역 R1 — Game Session 생애주기
- **FR-R1.1**: world별로 **GameSession 시작**(생성) / **종료**(close) / **목록·조회**. world당 여러 세션 이력 보관. (CL-C1=A)
- **FR-R1.2**: 세션은 `world_id` + 캐노니컬 노드 id 참조만 유지(복사 없음). (CL-C2=A)
- **FR-R1.3**: 세션 상태(Rumor/Timeline/per-region distortion/승격)는 **PostgreSQL**에 저장. 캐노니컬 그래프는 불변. (CL-F1=A)

### 영역 R2 — Rumor 생성(실제 왜곡)
- **FR-R2.1 (리전별 생성)**: 한 리전을 대상으로 그 리전의 지식들에서 Rumor를 생성한다(웹 버튼). (Q1=B)
- **FR-R2.2 (원본)**: Rumor의 원본(`distorted_from_id`)은 Knowledge **또는 기존 Rumor**(연쇄 왜곡). (Q2=B)
- **FR-R2.3 (강도별 체인)**: 한 번 생성 시 **왜곡 강도별 다단계 체인**(예: 약→중→강)으로 여러 Rumor 생성. 각 단계는 이전 단계를 원본으로 가리킬 수 있다. (Q3=C)
- **FR-R2.4 (LLM 실제 왜곡)**: `distortion_degree`↑ = 사실에서 점점 벗어남(세부 변경→과장→부분 오류→거의 허구). degree를 프롬프트에 명시해 LLM이 statement를 실제로 변형. (Q5=A)
- **FR-R2.5 (강도 출처)**: 생성 시 사용하는 강도는 **그 리전의 `distortion_degree`**(GameMaster가 보유; Phase 1은 수동/기본값). (Q4=X→GameMaster, CL-G=A)
- **FR-R2.6 (confidence)**: 생성 Rumor의 confidence = 원본 confidence × (1 − distortion_degree). (Q6=A)
- **FR-R2.7 (재생성)**: 리전의 Rumor를 재생성(re-roll)할 수 있다(GameMaster 턴 동작). (A의 "재생성")

### 영역 R3 — 지지도(support) & 승격/강등
- **FR-R3.1 (support 필드)**: Rumor는 `support`(지지도)를 가진다. Phase 1: 생성 시 초기값 + 사용자/GameMaster 수동 조정. (CL-D1=A)
- **FR-R3.2 (승격)**: support ≥ threshold인 Rumor는 그 리전의 **direct Knowledge처럼** NPC 쿼리에 노출(세션 한정, 캐노니컬 Neo4j엔 미기록). (Q5, CL-D2=A)
- **FR-R3.3 (강등)**: support가 threshold 미만으로 내려가면 승격 해제(강등). 승격은 영속적이지 않다. (CL-D2=A)
- **FR-R3.4 (평가 시점)**: 승격/강등은 GameMaster 턴 진행 시 재평가되고 타임라인에 기록된다.

### 영역 R4 — GameMaster & 턴 & Timeline
- **FR-R4.1 (GameMaster 동작)**: Phase 1 GameMaster는 턴 단위로 **Rumor 생성/재생성/승격/강등**을 수행하고 리전별 `distortion_degree`를 보유/설정한다. (A, CL-G=A)
- **FR-R4.2 (Timeline 기록)**: 각 턴의 변경(무엇이 생성/재생성/승격/강등됐는지)을 **시간순 Timeline**으로 기록·조회. (A)
- **FR-R4.3 (Event 제외)**: Event 상호작용 및 그에 따른 동적 distortion 진화는 **Phase 2**. Phase 1은 타임라인 구조와 GameMaster 골격만 갖춘다. (CL-B 정제)

### 영역 R5 — NPC 쿼리 규칙 변경
- **FR-R5.1**: 세션 컨텍스트의 NPC 쿼리 결과 = **direct + inherited + global Knowledge + (승격된 Rumor) + Rumor**. 거리 기반 `propagated` 사실과 자동-rumor view는 **NPC에 직접 노출하지 않는다**(기획자용으로만). (Q7, CL-E=A)
- **FR-R5.2**: 세션이 지정되지 않은(캐노니컬) 쿼리는 기존 동작 유지(회귀 없음).

### 영역 R6 — 웹 UI (Phase 1)
- **FR-R6.1**: 세션 **생성/선택/종료** UI.
- **FR-R6.2**: 리전 패널에 **"소문 생성" 버튼**(강도별 체인 생성 트리거) + 생성된 Rumor·`support`·`distortion_degree` 표시.
- **FR-R6.3**: support 수동 조정 + 승격/강등 상태 표시.
- **FR-R6.4**: **과거 Game Session 열람**(세션 이력 + Timeline 조회). (Q11=A)
- **FR-R6.5 (정리)**: 지난 사이클에 제거된 `wiki/build`를 호출하는 dead `buildWiki()`(web/src/api.ts)와 관련 UI를 제거. (Q12=A)

---

## 5. Non-Functional Requirements
- **NFR-R1 (포트 추상화)**: 세션 저장은 `SessionRepository` 포트 뒤. PostgreSQL 어댑터 + in-memory mock(오프라인 테스트). (CL-F2=A, 기존 컨벤션)
- **NFR-R2 (레이어 격리)**: 세션 레이어는 캐노니컬(Neo4j)을 **읽기 참조만**. 세션 쓰기가 캐노니컬을 변경하지 않는다(불변식).
- **NFR-R3 (인프라)**: docker-compose에 PostgreSQL 추가(세션 전용). 기존 Neo4j/OpenSearch 스택 유지. (Infrastructure Design 필요)
- **NFR-R4 (LLM graceful)**: Rumor 생성 LLM 실패 시 해당 단계 생략, 세션/턴 진행은 계속.
- **NFR-R5 (결정론/테스트)**: 순수 로직(승격/강등 판정, confidence 계산, 타임라인 구성)과 LLM/DB 포트 분리. PBT(Partial) 적용 대상.
- **NFR-R6 (회귀)**: 캐노니컬 경로/기존 테스트 GREEN 유지. ruff/black/tsc 클린.

## 6. Data Model (확정은 Functional/Infra Design에서)
- 세션 레이어(PostgreSQL): `GameSession`(id, world_id, status, created/closed), `SessionRumor`(id, session_id, distorted_from_id, statement, distortion_degree, support, confidence, region_id, promoted: bool, provenance), `RegionDistortion`(session_id, region_id, distortion_degree), `TimelineEntry`(session_id, turn, kind, payload, ts).
- 기존 `Rumor`(Neo4j) 모델과의 관계: 세션 Rumor는 PostgreSQL 전용 표현(캐노니컬 Neo4j Rumor 노드는 사용하지 않거나 별개). Functional Design에서 정리.
- 캐노니컬 모델 변경 **없음**(참조만).

## 7. Out of Scope (Phase 2+)
- **Event + Event 상호작용**, Event 기반 GameMaster 자동 distortion 진화/시뮬레이션.
- support 자동 증가(NPC 상호작용/전파 기반).
- 세션 데이터의 검색 인덱싱(현 결정: 세션은 PostgreSQL, 검색 인덱싱 안 함 — Q9=X).

## 8. 확정 가정
1. 캐노니컬=Neo4j 정적 / 세션=PostgreSQL 동적, 참조만(복사 없음). (A/C2)
2. GameMaster=턴 기반 Rumor 라이프사이클 + per-region distortion(수동); Event는 Phase 2. (A/G)
3. 승격=세션 내 한정·강등 가능·캐노니컬 미기록. (D2)
4. NPC=Knowledge(+승격)+Rumor만; propagated/자동-rumor는 기획자용. (E)
5. 신규 `SessionRepository` 포트 + PostgreSQL + in-memory mock. (F)

## 9. Key Requirements 요약
- **GameSession**(world별·이력) + **PostgreSQL 세션 레이어**(SessionRepository 포트) 도입, 캐노니컬은 불변 참조.
- **리전별 LLM 소문 생성**(강도별 체인, Knowledge/Rumor 원본, degree↑→실제 왜곡, confidence 감쇠).
- **support + 승격/강등**(세션 한정, 비영속) + **GameMaster 턴** + **Timeline 기록**.
- **NPC 쿼리 규칙**: Knowledge(+승격)+Rumor만; propagated 비노출.
- **웹**: 세션 생성/선택/종료, 리전 소문 생성 버튼·support·distortion 표시, 과거 세션·타임라인 열람, dead buildWiki 정리.
- **Event/타임라인 동적 진화는 Phase 2**.

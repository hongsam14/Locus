# 소문 왜곡 — 개념 모델 확인 & 범위 클러스터링 (후속)

답변에 **여러 새 개념**(Game/Game Session, PostgreSQL 세션 DB, Event·Rumor 타임라인, GameMaster, Rumor 지지도·승격, NPC 접근 규칙)이 등장했습니다. 단순 기능이 아니라 **동적 게임 세션 레이어** 도입입니다. 요구사항을 정확히 쓰기 전에 (1) 제가 이해한 개념 모델이 맞는지, (2) 이번 사이클 범위(phasing)를 확정하겠습니다.

---

## A. 제가 이해한 개념 모델 (틀린 부분 지적해 주세요)

**두 레이어로 나뉩니다:**

### 캐노니컬 레이어 — 정적, world별 (현재 Neo4j + OpenSearch)
- Region/토폴로지/Entity/**Knowledge(사실)**/WikiPrior. `build-world`로 생성. 게임이 바뀌어도 유지.

### 게임 세션 레이어 — 동적, 휘발성, **Game Session별** (신규, PostgreSQL)
- **Game Session**: 한 world 위에서 진행되는 한 판(play-through) 인스턴스.
- **Rumor**: Knowledge(또는 Rumor)를 LLM이 **실제 왜곡한 텍스트** 노드. 필드: `distortion_degree`, **`support`(지지도)**, `distorted_from_id`(Knowledge/Rumor), region scope, confidence.
- **per-region `distortion_degree`**: 리전마다 다른 왜곡 강도(동적 상태). **GameMaster**가 Event/Rumor 영향으로 시간에 따라 바꿈.
- **Event**: 리전에 영향을 주는 사건. distortion_degree·소문 생성에 영향. **타임라인**으로 관리.
- **승격(promotion)**: Rumor의 `support`가 threshold 초과 → 그 리전의 **direct Knowledge로 승격**(세션 한정, 영속 아님).
- **세션 리셋**: 새 Game이 시작되면 이전 Rumor/Event/승격Knowledge는 사라짐(캐노니컬 world는 유지).

**쿼리/NPC 규칙 변화:**
- NPC는 **propagated knowledge(자동 소문, 거리 기반)에 직접 접근 불가** — 오직 **Rumor 노드를 통해서만** 접근.
- 자동 소문 분류(consensus, 텍스트 안 바뀜)와 명시적 Rumor(왜곡 텍스트)는 **독립**으로 공존. 자동 소문은 세션마다 재생성되지 않음, Rumor는 재생성됨.

### Clarification A — 위 2-레이어 개념 모델이 맞나요?
A) 맞음 (캐노니컬=Neo4j 정적 / 게임 세션=PostgreSQL 동적·휘발)
B) 대체로 맞으나 수정 필요(아래 [Answer] 옆에 무엇이 틀렸는지)
X) Other (please describe after [Answer]: tag below)

[Answer]: B. 개념 모델은 맞음. 하지만 **타임라인**과 **GameMaster** 개념은 다음과 같음. **GameMaster**는 매턴마다 게임 세션을 변화시킴. 1: **Event** 상호작용(추후 설계) 2: **Rumor**를 생성, 재생성, 승격/소멸 시킴. 그것을 기록하는게 **타임라인**임.

---

## B. 이번 사이클 범위 (phasing) — 가장 중요

개념이 크므로 한 번에 다 만들지, 단계로 나눌지 정해야 합니다. 제안:

- **Phase 1 (이번 사이클 권장)**: Game Session 기반 골격 + 소문 생성 핵심
  - PostgreSQL 세션 DB + `GameSession` 생성/종료/조회.
  - 리전별 소문 생성(Q1=B): Knowledge/Rumor에서 **강도별 체인 Rumor**(Q3=C) LLM 왜곡 생성, 세션 DB에 저장.
  - Rumor `support` 필드 + threshold 승격(세션 내 direct Knowledge처럼 취급).
  - NPC 쿼리 규칙: propagated는 Rumor로만 노출.
  - per-region `distortion_degree`는 **이번엔 GameMaster가 단순 규칙/수동 설정**(동적 Event 연동은 Phase 2).
  - 웹: 세션 생성/선택 + 리전별 "소문 생성" 버튼 + 소문/지지도/distortion 표시 + 과거 세션 열람. dead `buildWiki` 정리.
- **Phase 2 (다음 사이클)**: **Event + Rumor 타임라인**, GameMaster가 Event로 distortion_degree를 동적으로 진화, 시간축 시뮬레이션.

### Clarification B — 이 phasing에 동의하시나요?
A) 동의 — Phase 1만 이번에(Event/타임라인은 Phase 2)
B) Event/타임라인까지 이번 사이클에 포함(더 큼)
C) 더 좁게 — Phase 1에서도 일부 제외(아래에 무엇을 뺄지)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 내가 A에서 서술한 개념을 반영해서 다시 작성해줘.

---

## C. Game Session 라이프사이클

### Clarification C1 — 세션 생성/종료 트리거 & 단위
A) world별로 사용자가 "새 게임 시작" → 세션 생성, "종료"로 닫음. world당 여러 세션 이력 보관
B) 세션은 자동(빌드 시 1개) — 명시적 시작/종료 없음
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification C2 — 세션이 캐노니컬 world를 참조하는 방식
A) 세션 레코드가 `world_id` + 캐노니컬 노드 id(예: distorted_from = Neo4j Knowledge id)를 **참조**만 함(캐노니컬은 Neo4j 유지, 복사 안 함)
B) 세션 시작 시 필요한 캐노니컬 데이터를 PostgreSQL로 스냅샷 복사
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## D. 지지도(support) & 승격 메커니즘

### Clarification D1 — support는 어떻게 증가/변하나?
A) 이번엔 **수동/단순**: 생성 시 초기값 + 사용자(또는 GameMaster)가 조정. 자동 증가 로직은 Phase 2
B) NPC 상호작용/전파로 자동 증가(이번 사이클에 로직 포함)
C) Event에 의해 변동(Phase 2 의존)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification D2 — 승격된 Knowledge의 동작
A) 세션 내에서만 그 리전의 direct knowledge처럼 쿼리에 노출(캐노니컬 Neo4j엔 안 씀). support가 threshold 아래로 내려가면 강등(되돌림)
B) 승격되면 세션 동안 고정(강등 없음)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## E. NPC 접근 규칙 (consensus 변경)

### Clarification E — "NPC는 propagated를 Rumor로만 접근"의 정확한 의미
A) consensus의 `propagated`(weight≥0.5 자동 전파 사실)도 NPC 쿼리에선 **그대로 노출하지 않고**, 세션의 Rumor(있으면)로 치환해 반환. 즉 NPC view = direct/inherited/global Knowledge(+승격) + Rumor. propagated/자동-rumor는 기획자용으로만.
B) propagated 개념 자체를 NPC 쿼리에서 제거하고, 거리 기반 정보는 전부 Rumor 생성으로만 표현
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## F. 저장소 경계 & 인프라

### Clarification F1 — PostgreSQL 도입(신규 인프라)
A) 예 — docker-compose에 PostgreSQL 추가, 세션 레이어 전용. 캐노니컬은 Neo4j/OpenSearch 유지
B) PostgreSQL 대신 다른 것(아래 명시)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### Clarification F2 — 세션 데이터 접근 포트
A) 기존 포트 패턴 따라 신규 `SessionRepository` 포트 추가(PostgreSQL 어댑터), 오프라인 테스트는 in-memory mock. (기존 Graph/Search와 동일 컨벤션)
B) 직접 ORM/SQL(포트 추상화 없이)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## G. GameMaster (이번 사이클 한정)

### Clarification G — 이번 사이클의 GameMaster 역할
A) 최소: 리전별 `distortion_degree`를 보유/설정하는 주체(수동 또는 단순 기본값). 소문 생성 시 그 리전 degree를 사용. 동적 진화·자동 의사결정은 Phase 2
B) 이번부터 LLM 기반 자동 GameMaster(Event 해석→degree 조정)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 위 개념을 필수로 고려.

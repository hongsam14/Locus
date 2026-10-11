# V7 월드·지식 정확성 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V7(실행 7/9), Code Generation Part 1. 승인된 FD를 코드로 옮길 순서, 커밋 단위, 시험을 정한다. 다시 빌드하거나 월드를 불러와도 지식·NPC·사건 씨앗이 틀어지지 않게 하는 일이다. 백엔드만 바뀐다(`locus/knowledge`, `locus/shared/{storage,models}`, `locus/world`, `tests`, README, 운영 문서). 이 계획이 Part 2의 유일한 기준이다.

**입력**
- FD(승인 2026-10-11): `construction/V7-world-knowledge/functional-design/{domain-entities,business-logic-model,business-rules}.md` — BR-V7-01~22, TP-V7-1~14, PBT-V7-1~5. 리뷰 02의 R-09·R-10과 세션 확인 S-1은 Accepted risk → § 1.1
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V7(완료 조건 여섯, NFR SKIP)
- Application Design `component-methods.md`, `components.md`
- 요구 `inception/requirements/follow-up-requirements.md` FR-C6~C10, FR-C12, NFR-6

**기준선**(Step 1에서 잰다): pytest 1138, ruff·black clean, mypy 11. 웹은 바뀌지 않는다(vitest 664 그대로).

---

## 1. 실행 메모

### 1.1 FD 리뷰 02와 세션 확인 (승인 때 Accepted risk, 게이트에서 보인 결정)

- **〔FD R-09〕 아무것도 바꾸지 않는 확인**
  - 확인 답의 새 확신도가 지금 값과 같으면 `apply_answer`는 아무것도 쓰지 않고 `None`을 돌려준다. 변경 기록이 없으므로 되돌리기 목록에 빈 항목이 생기지 않는다. 색인 쓰기와 `touch_world_meta`도 없다.
  - 서비스는 그 질문의 열쇠를 run의 새 목록 `kept_keys`에 넣는다. 그래서 질문이 닫힌다(아래 S-1과 같은 길).
  - TP-V7-13에 단언을 더한다: 확신 0.95 지식에 확인 → 변경 기록 없음, 그래프 쓰기 없음, 질문 닫힘.
- **〔세션 S-1〕 위키 충돌의 확인이 질문을 닫지 못함**
  - 지금은 판정 캐시의 열쇠가 (id, 문장, 지형)이다. 확인은 문장을 바꾸지 않으므로 다음 탐지가 같은 질문을 다시 낸다. `ignored_keys`에 들어가는 것은 [두기]뿐이다.
  - 고침: 확인 답이 WIKI_CONFLICT이거나 값을 바꾸지 않았으면, 서비스가 그 열쇠를 `kept_keys`에 넣는다. 탐지 뒤 고르기(`select`)는 `ignored_keys`와 `kept_keys`를 함께 뺀다.
  - `kept_keys`는 `ignored_keys`와 따로 둔다. 화면의 "무시한 질문" 목록이 `ignored_keys`를 그대로 그리므로, 같은 목록에 넣으면 "이대로 둔다"고 확인한 것이 "무시"로 보인다.
  - 되살리기는 없다. 같은 run 동안만 다시 묻지 않고, 새 run은 다시 탐지한다. 화면에서 `kept_keys`를 보일지는 V8 몫이다.
  - AugmentationRun 모델에 `kept_keys: list[str] = []`를 더한다. 기본값이 있으므로 저장된 옛 run도 읽힌다.
- **〔FD R-10〕 로더가 버린 NPC·씨앗**
  - 로더는 집 지역이 없는 NPC와 지역이 없는 씨앗을 스냅샷에서 빼고 `load_warnings`(stage `load`)에만 적는다. 그래서 `carry_over`가 받는 옛 스냅샷에는 그것들이 없다.
  - 고침: 로더의 두 문장 앞머리를 상수로 둔다(`NPC_HOME_DANGLING = "NPC home region"`, `SEED_REGION_DANGLING = "EventSeed region"`, `locus/knowledge/loader.py`). `carry_over`는 `old.load_warnings`에서 그 상수로 시작하는 경고를 찾아 하나마다 이어 붙이기 경고를 낸다: `"NPC {id} was not carried over: its region is not in the old world"`(씨앗도 같은 꼴).
  - 그래서 FD domain-entities § 4의 마지막 경고 갈래가 이 경로로 쓰인다. 이름은 버려진 항목에 없으므로 id를 쓴다.
  - PBT-V7-4는 "붙인 수 + 경고 수 = 옛 NPC 수 + 옛 씨앗 수 + 로더가 버린 NPC·씨앗 수"로 센다.
  - 경계: world는 knowledge를 가져다 쓸 수 있다(shared ← knowledge ← world). `test_boundaries.py`가 지킨다.

### 1.2 코드를 읽고 정한 것 (FD에 없던 사실)

- **테스트 대역이 셋이다.** FD는 둘(`tests/shared/storage/fakes.py`, `tests/world/services/test_services.py`)이라 했다. `tests/world/editor/helpers.py`의 `MeteredGraph`가 `delete_node`를 덮어쓰므로 셋째다. 셋 다 `label` 키워드를 받는다.
- **인메모리 그래프는 노드를 (월드, id)로 둔다.** 같은 id의 지역과 씨앗이 함께 있을 수 없어 TP-V7-11을 재현하지 못한다. Neo4j는 `MERGE (n:Label {id, world_id})`라 라벨마다 따로 둔다.
  - 고침: `InMemoryGraphRepository._nodes`의 열쇠를 (월드, 라벨, id)로 바꾼다. `upsert_nodes`, `replace_nodes`, `get_node`, `find_nodes`, `delete_node`, `delete_world`, `list_world_ids`가 따른다.
  - 다른 월드의 같은 id를 막는 검사(`ConstraintViolation`)는 지금처럼 라벨을 가리지 않는다. 대역이 Neo4j보다 엄격한 쪽이고, 기존 시험이 그 동작에 기댄다.
  - 라벨 없는 `get_node`는 그 id의 노드 가운데 처음 넣은 것을 돌려준다. 라벨 없는 `delete_node`는 그 id의 모든 노드를 지운다(Neo4j의 라벨 없는 `MATCH … DETACH DELETE`와 같음).
  - 엣지는 라벨이 없다. 그래서 대역의 라벨 있는 삭제는 그 id를 쓰는 노드가 하나도 남지 않을 때만 그 id에 닿는 엣지를 지운다. Neo4j보다 느슨하다(지운 쪽 노드의 엣지도 남을 수 있다). 대역 docstring에 적는다.
  - `tests/world/editor/helpers.py`는 `self.graph._nodes.values()`만 읽는다. 열쇠를 바꿔도 그대로 돈다.
- **캐시 hit의 버전 읽기 예외**가 지금 호출자에게 그대로 간다(`cache.py` hit 갈래의 `_current_version` 호출에 try가 없다). FD § 2.2 1항대로 잡는다.
- **빌더 시험의 캐시 대역 둘**은 `get`에서 던진다(`test_services.py` `_NoCache`, `test_wiki_evidence.py` `_Cache`). 거기 빌드는 모두 첫 빌드(월드 없음)라서 옛 스냅샷을 읽지 않는다. Step 7 게이트에서 실제로 돌려 확인한다. 교체 빌드가 있으면 그 대역의 `get`이 빈 스냅샷을 돌려주게 고친다.
- **빌드 리포트를 받는 화면**(`BuildReportPanel`)은 경고를 `[stage] message`로 그린다. 새 stage(`backup`, `carry-over`, `duplicate-ids`, `persist-meta`)도 그대로 보인다. 이어 붙인 수의 표시와 stage 이름의 한국어는 V8로 넘긴다(§ 4).

### 1.3 이 계획이 정한 것

- **커밋**: 단계마다 하나다. 게이트가 GREEN일 때만 커밋한다. 게이트는 ruff·black(`locus api tests`), mypy ≤ 11, pytest(pipefail)이다. scratchpad의 `v5gate.sh`를 `v7gate.sh`로 복사해 쓴다.
- **돌연변이 확인**: 고친 곳마다 고치기 전 동작으로 되돌린 코드에서 새 시험이 실패하는지 본다. 단계마다 적은 돌연변이를 돌리고 결과를 code-summary에 적는다.
- **웹**: 바뀌지 않는다. Step 10에서 `git diff --stat -- web`가 비어 있는지 본다.
- **푸시·PR**: 하지 않는다(사람의 일).

### 1.4 실행 메모 (코드 계획 리뷰 01, 승인 2026-10-11 때 Accepted risk)

- 〔실행 메모 R-01〕 Step 3.3: `tests/knowledge/test_cache.py::test_hit_is_refreshed_when_the_world_version_changes`의 끝부분(버전 `None` → 무효화 → 캐시됨)을 새 규칙으로 고친다. 버전 `None`이면 두 번째 `get`도 새로 불러오고, 버전 없는 로더(`UNVERSIONED`)면 캐시된다. "메타 없는 월드는 무효화만"이 "메타 없는 월드는 캐시하지 않음"으로 바뀌었다고 code-summary § 4에 적는다.
- 〔실행 메모 R-02〕 Step 3.2: `check_version`이 꺼져 있으면 저장할 버전은 `UNVERSIONED`다. Step 3.3에 `check_version=False` 캐시가 캐시하는 시험을 하나 더한다.
- 〔실행 메모 R-03〕 Step 8.2·8.3
  - `_confirm_or_edit`는 썼는지(bool)를 돌려주고, `_write`는 확인이 아무것도 바꾸지 않았으면 표식 `UNCHANGED`를 돌려준다. `apply_answer`는 그때 `None`이다.
  - 서비스 조건: `action == CONFIRM and (issue.type == WIKI_CONFLICT or change is None)`이면 `kept_keys`에 넣는다. [두기]는 `ignored_keys`에만 들어간다는 시험을 더한다.
- 〔실행 메모 R-04〕 게이트 명령(Step 1.2에서 scratchpad `v7gate.sh`로 새로 만든다):
  - `.venv/bin/ruff check locus api tests && .venv/bin/black --check locus api tests`
  - `.venv/bin/mypy locus api` → 오류 수 ≤ 11
  - `set -o pipefail; .venv/bin/pytest -q -p no:cacheprovider --no-cov | tail -3`
- 〔실행 메모 R-05〕 Step 4.4: `MeteredGraph`가 `get_node`·`delete_node`의 `(node_id, label)`을 `calls_with`에 기록한다. TP-V7-12는 그것을 단언한다. `test_port_contract.py`에 Neo4j 어댑터의 질의 모양 시험(라벨 있음 → `MATCH (n:Label {…})`, 없음 → 지금 질의)을 더하고 돌연변이 목록에 넣는다.
- 〔실행 메모 R-06〕 Step 6.4·7.6의 `tests/api/test_world_api.py` 시험은 스텁 리포트로 라우터 규칙(`replaced=false`면 세션을 닫지 않음)을 고정하는 시험이다. V7 동작의 증거는 `test_build.py`·`test_worldfile.py`의 실제 빌더·불러오기 시험이다.
- 〔실행 메모 R-07〕 Step 6.2·6.3·7.4: 백업 실패와 옛 월드 읽기 실패는 커밋 블록의 일반 `except Exception`보다 먼저 잡는다. 지우기 전이므로 `replaced=false`, 각 stage(`backup`, `carry-over`)의 error 경고를 담은 리포트를 돌려준다. `finally`의 캐시 무효화는 그대로 돈다.
- 〔실행 메모 R-08〕 Step 10.1: pytest 수 ≥ 기준선 + 새 시험 수이고 줄어든 시험이 없는지 본다. `cd web && npx vitest run`이 664 그대로인지 본다.

---

## 2. 단계

### Step 1 — 진행 기록과 기준선
- [x] 1.1 진행 기록을 커밋한다: audit, state, FD 계획(체크), FD 산출물과 리뷰 01·02, 이 계획과 그 리뷰(`docs(aidlc): V7 functional design approved; V7 code plan`).
- [x] 1.2 기준선을 잰다(2026-10-11: pytest 1138, ruff·black clean, mypy 11). `v7gate.sh`를 새로 만들었다(§ 1.4 R-04).

### Step 2 — 합의: 가장 강한 출처, 한 번 세기, 확실한 것부터 (BLM § 1, BR-V7-01~05)
- [x] 2.1 `locus/knowledge/consensus.py`
  - `region_direct`를 만들 때 같은 (지역, 지식)은 확신이 가장 높은 하나만 둔다(R-07).
  - 순수 함수 `best_origins(pw, region_direct, exclude)`를 더한다(domain-entities § 1.1). 가중이 가장 큰 출처, 동률이면 지역 id가 작은 쪽, `pw`에 없는 지역과 `exclude`는 빠진다.
  - 4단계: `origins`를 지식 id 순으로 돌며 전파·전언·모름을 나눈다. 모름은 지식마다 한 번 센다.
  - 반환 전에 다섯 목록을 각각 `(-confidence, knowledge_id)`로 정렬한다.
- [x] 2.2 시험
  - `tests/knowledge/test_consensus.py`: TP-V7-1(약한 출처가 dict에서 먼저 나와도 0.9 출처로 전파, 동률은 id 작은 지역), TP-V7-2(약한 출처 둘 → 1, 강한 출처가 있으면 0, 겹친 스코프 0.4·0.8 → 어느 순서로든 0.8), TP-V7-3 앞부분(직접 셋 → 내림차순).
  - 새 `tests/knowledge/test_consensus_props.py`: PBT-V7-1~3. 생성기는 이 모듈 안에 둔다. 지역 2~8개, 연결 가중 0~1, 겹치는 직접 스코프, 일부 전역 지식이다. 두 순열을 만들어 결과(다섯 목록의 id 차례, confidence, `unknown_count`)를 비교한다.
  - 새 `tests/play/test_v7_order.py`: TP-V7-3 뒷부분(플레이 지역 보기 `facts`의 첫 셋이 합의 차례)과 BR-V7-05의 소문 씨앗 차례(`_collect_sources`가 확실한 것부터).
  - 합의 차례에 기대던 기존 단언이 깨지면 새 차례로 고치고, 고친 수와 까닭을 code-summary § 4에 적는다(`test_consensus.py`, `test_npc_scope.py`, `test_dialogue.py`, `test_demo.py`, 소문 시험).
  - 돌연변이: (a) 처음 만난 출처를 고르기, (b) 쌍마다 세기, (c) 정렬 빼기, (d) 겹친 스코프에서 먼저 온 것 두기.
- [x] 2.3 커밋: `fix(knowledge): a region's knowledge comes from its strongest source, unknowns count once, each list confident first (V7, FR-C6, RE-W01)`

### Step 3 — 저장 순서와 캐시 (BLM § 2, BR-V7-06~09)
- [x] 3.1 `locus/shared/storage/persistence.py` `persist_graph`
  - 노드 목록에서 WorldMeta를 뺀다. 노드 → 엣지 → 임베딩 → 색인 → WorldMeta upsert 차례다.
  - 노드·엣지 실패는 지금처럼 돌아가고 WorldMeta를 쓰지 않는다.
  - 색인 실패 뒤에도 WorldMeta를 쓴다. WorldMeta 쓰기 실패는 `stage="persist-meta"`, severity error다.
- [x] 3.2 `locus/knowledge/cache.py` `WorldCache`
  - 모듈 상수 `UNVERSIONED`(표식 객체)를 둔다. `_current_version`은 로더에 `version`이 없으면 `UNVERSIONED`를 돌려준다.
  - hit: `check_version`이 꺼져 있거나 캐시한 버전이 `UNVERSIONED`면 hit다. 버전 읽기를 try로 감싼다. 예외면 invalidate하고 miss로 가되 캐시하지 않는다.
  - miss: 버전이 `None`(이 월드에 WorldMeta 없음)이면 캐시하지 않는다. `UNVERSIONED`나 문자열이면 지금처럼 generation을 보고 캐시한다.
  - 모듈 docstring과 `__init__` 주석의 "Worlds without meta rely on explicit invalidation only"를 새 규칙으로 고친다.
- [x] 3.3 시험
  - `tests/knowledge/test_cache.py`: TP-V7-4(인메모리 그래프 + `WorldLoader`로 다른 "프로세스"의 교체를 흉내: 옛 월드 지우기 → 노드만 쓰기 → `get` → `is_cached` 거짓 → 엣지와 메타 쓰기 → `get` → 연결·스코프가 있는 스냅샷, 캐시됨), TP-V7-5(hit의 `version()` 예외 → 오류 없이 새 스냅샷, 캐시 안 됨; `version` 없는 로더 → 캐시). EX-18·EX-19는 손대지 않는다.
  - 새 `tests/shared/storage/test_persist_order.py`: TP-V7-6(쓰기를 기록하는 대역: WorldMeta upsert가 엣지·색인 뒤; 엣지 실패 → WorldMeta upsert 없음; 색인 실패 → WorldMeta 있음; 메타 실패 → `persist-meta` error).
  - 돌연변이: (a) WorldMeta를 노드 묶음에 되돌림 → TP-V7-4·6 실패, (b) `None` 캐시 → TP-V7-4 실패, (c) hit의 try 빼기 → TP-V7-5 실패.
- [x] 3.4 커밋: `fix(knowledge): the world's version mark is written last and a world without one is never cached, so a half-replaced world is not served twice (V7, FR-C7, RE-W02, RE-W03)`

### Step 4 — 라벨 있는 읽기·삭제 (BLM § 6, BR-V7-19·20)
- [x] 4.1 포트와 어댑터
  - `locus/shared/storage/base.py`: `get_node(…, *, label: str | None = None)`, `delete_node(…, *, label: str | None = None)`.
  - `locus/shared/storage/neo4j_repo.py`: 라벨이 있으면 `MATCH (n:{_safe_ident(label)} {id, world_id})`로 읽고 지운다. 없으면 지금 질의다.
- [x] 4.2 대역 셋(§ 1.2)
  - `tests/shared/storage/fakes.py`: (월드, 라벨, id) 열쇠, 라벨 인자, 남은 노드가 없을 때만 엣지 지우기.
  - `tests/world/services/test_services.py` `_GraphRepo`, `tests/world/editor/helpers.py` `MeteredGraph`: 라벨 인자를 받아 넘긴다.
- [x] 4.3 호출부 9곳
  - `editor/writes.py`: `node()` → `get_node(label=label)`. `delete_held`는 FD R-02 흐름이다(라벨 읽기 → 있으면 라벨 삭제와 문서 지우기 → 없으면 라벨 없는 읽기 → 노드가 아예 없으면 문서만 → 다른 라벨이면 False, 문서 그대로).
  - `editor/regions.py`: 씨앗 `EventSeed`, NPC `NPC`, 지역 `Region`.
  - `augmentation/apply.py`: 다시 가리키기 `label=_REF_KIND.get(field)`, 되돌리기 검사 `label=snap.label`, 더한 노드 삭제는 `nodes_after`의 라벨(스냅숏이 없는 id는 라벨 없이).
  - 그대로 두는 셋: `own_label`, `bundle.delete_any`, `apply._nodes`. 셋에 "이 id의 아무 노드를 묻는다" 주석을 한 줄 단다.
- [x] 4.4 시험
  - `tests/shared/storage/test_port_contract.py`: 대역의 라벨 계약(같은 id의 두 라벨, 라벨 있는 읽기·삭제가 다른 라벨을 건드리지 않음, 라벨 없는 삭제는 둘 다 지움).
  - `tests/world/editor/test_region_delete.py`: TP-V7-11(같은 id의 지역 Y와 다른 지역 X의 씨앗 Y → X 삭제가 지역 Y와 그 연결을 남김).
  - `tests/world/editor/test_editors.py`: `delete_held(label=X)`가 다른 라벨 노드와 그 검색 문서를 남김(R-02), 노드가 없으면 문서만 지움(지금 규칙 유지).
  - TP-V7-12: 대역이 받은 `label` 인자를 9곳에서 단언한다(지역 삭제 경로, 다시 가리키기, 되돌리기).
  - 돌연변이: 각 호출부의 `label=` 빼기 → 해당 시험 실패.
- [x] 4.5 커밋: `fix(world): reads and deletes name the node's kind, so a seed sharing a region's id no longer takes the region with it (V7, FR-C10, U8 #10)`

### Step 5 — 중복 id 거절 (BLM § 5, BR-V7-17·18)
- [x] 5.1 `locus/world/worldfile/remap.py`: `duplicate_ids(file) -> list[str]`(정렬; 절 `regions, entities, relations, knowledge, priors, npcs, event_seeds`, 절 안과 절 사이).
- [x] 5.2 `locus/world/worldfile/import_.py`: 재매핑 뒤, `validate_references` 앞에 검사한다. 있으면 아무것도 쓰지 않고 `replaced=false`, 경고 `stage="duplicate-ids"`, severity error, `"duplicate ids in the World File: a, b, …"`(10개까지와 `and N more`)인 리포트를 돌려준다.
- [x] 5.3 시험(`tests/world/worldfile/test_worldfile.py`): TP-V7-10(씨앗 id = 지역 id, 같은 id 지식 둘 → 거절, 그래프 쓰기 없음, 옛 월드 그대로), PBT-V7-5(절과 항목 순서를 섞어도 같은 결과, 결과의 id는 실제로 두 번 이상). 데모 불러오기(`tests/world/test_demo.py`)는 그대로 통과한다.
  - 돌연변이: 검사 빼기 → TP-V7-10 실패.
- [x] 5.4 커밋: `fix(world): a World File with duplicate ids is refused before anything is written (V7, FR-C10)`

### Step 6 — 백업 게이트 (BLM § 3, BR-V7-10·11)
- [x] 6.1 `locus/world/build.py`: `BackupFailedError(RuntimeError)`를 `WorldExistsError` 곁에 둔다. `_backup(world_id) -> Path | None`은 미설정이면 `None`, 성공이면 경로, 실패면 `BackupFailedError`다(경고 목록을 받지 않는다).
- [x] 6.2 빌더 커밋 단계: `_backup`이 던지면 지우기 전에 멈춘다. 리포트는 `replaced=false`, `backup_path=None`, `BuildWarning(stage="backup", severity="error", message="backup failed; the world was not replaced: …")`다.
- [x] 6.3 `locus/world/worldfile/import_.py`: `_backup`을 같은 계약으로 바꾸고, 같은 자리에서 멈춘다. `BackupFailedError`는 `locus.world.build`에서 가져온다(지금 `WorldExistsError`와 같음).
- [x] 6.4 시험: TP-V7-7을 빌드(`tests/world/services/test_build.py`)와 불러오기(`tests/world/worldfile/test_worldfile.py`)에 각각 둔다. exporter가 던짐 → `delete_world` 안 불림, 옛 노드 그대로, `ok=false`, stage `backup`. 미설정이면 교체(BR-V7-11). API 경로의 세션은 닫히지 않음(`replaced=false`, `tests/api/test_world_api.py`에 하나).
  - 돌연변이: 실패를 삼키고 진행 → TP-V7-7 실패.
- [x] 6.5 커밋: `fix(world): a failed backup stops the replace before anything is deleted (V7, FR-C8, RE-W04)`

### Step 7 — 이어 붙이기 (BLM § 4, BR-V7-12~16, § 1.1 R-10)
- [x] 7.1 `locus/knowledge/loader.py`: 버리는 문장의 앞머리를 상수 `NPC_HOME_DANGLING`, `SEED_REGION_DANGLING`으로 둔다(문장은 그대로).
- [x] 7.2 새 `locus/world/carry_over.py`(순수): `CarryOver`, `region_key`, `carry_over(old, new_regions, world_id)`. 맞추기는 domain-entities § 4다. 로더가 버린 것의 경고는 § 1.1 R-10이다.
- [x] 7.3 `locus/shared/models/reports.py` `BuildReport`: `carried_npcs: int = 0`, `carried_seeds: int = 0`. `BuildWarning.stage` 주석에 새 stage 넷을 더한다.
- [x] 7.4 `locus/world/build.py` 커밋 단계(교체일 때)
  - ① `self._cache.invalidate(world_id)` 다음 `old = self._cache.get(world_id)`. 던지면 멈춘다: `stage="carry-over"`, severity error, `"the old world could not be read; it was not replaced: …"`, `replaced=false`.
  - ② 백업(Step 6) ③ 지우기 ④ 사전·온톨로지(지금과 같음)
  - ⑤ `carry = carry_over(old, topology.regions, world_id)`
  - ⑥ 본체 `persist_graph`에 `npcs=carry.npcs`, `seeds=carry.seeds`를 싣는다. WorldMeta는 Step 3대로 마지막이다.
  - ⑦ 리포트에 `carried_npcs`, `carried_seeds`, `carry.warnings`를 싣는다. 첫 빌드(월드 없음)는 0이다.
- [x] 7.5 `README.md` 7행: "NPC가 만들어집니다"를 FD § 4 문장으로 고친다.
- [x] 7.6 시험
  - 새 `tests/world/test_carry_over.py`: 맞추기 규칙(정규화한 이름·단계, 부모로 가르기, 못 가르면 경고, 없으면 경고, 로더가 버린 것 경고), PBT-V7-4.
  - `tests/world/services/test_build.py`: TP-V7-8(NPC 둘·씨앗 하나 → 다시 빌드 → 새 지역 id로 셋, 리포트 수; 이름 바뀐 지역의 NPC → 경고), TP-V7-9(캐시에 낡은 스냅샷, 그래프에 막 더한 NPC → 이어 붙음; 캐시 `get`이 던지면 교체 안 함).
  - `tests/api/test_world_api.py`: TP-V7-9의 세션 쪽(옛 월드 읽기 실패 → `replaced=false`, 열린 세션 그대로).
  - TP-V7-14: README에 옛 문장이 없고 새 문장이 있다(README를 읽는 기존 `tests/test_packaging.py`에 둔다).
  - PBT-02: `BuildReport`의 JSON 왕복(새 두 칸).
  - 돌연변이: (a) 캐시 `get`만 하고 무효화 빼기 → TP-V7-9 실패, (b) 부모 가르기 빼기 → 시험 실패, (c) 로더가 버린 것 경고 빼기 → PBT-V7-4 실패.
- [x] 7.7 커밋: `fix(world): a rebuild keeps the world's NPCs and event seeds on the regions of the same name, and says which it could not place (V7, FR-C9, RE-W18)`

### Step 8 — 보강 질문의 입력 칸과 무변경 답 (BLM § 7, BR-V7-21·22, § 1.1 R-09·S-1)
- [x] 8.1 `locus/world/augmentation/questions.py`: `NEEDS`를 (이슈 종류, 대상 종류) 열쇠로 바꾼다(domain-entities § 8 표). `generate`는 `NEEDS.get((issue.type, issue.target_kind), {})`로 찾는다. DANGLING은 대상 넷 모두 같은 칸이다.
- [x] 8.2 `locus/world/augmentation/apply.py`
  - `_confirm_or_edit` 고치기: 바꿀 칸을 먼저 계산하고 지금 값과 같은 칸은 뺀다. 비면 아무것도 쓰기 전에 `ValueError("the answer changes nothing")`이다. 엔티티는 설명(statement 칸)과 확신만 본다.
  - `_confirm_or_edit` 확인: 새 확신도가 지금 값과 같으면 쓰지 않고 "바뀐 것 없음"을 알린다. `apply_answer`는 그때 `None`을 돌려준다(R-09).
  - 더하기·다시 가리키기·자리 정하기는 지금 검사(빈 문장, 빈 지역, 없는 참조)로 이미 쓰기 전에 거절된다. 이 단계의 시험이 그것을 확인한다.
- [x] 8.3 `locus/world/augmentation/types.py` `AugmentationRun.kept_keys: list[str] = []`. `locus/world/augmentation/service.py` `answer`: 확인 답이 WIKI_CONFLICT이거나 `change is None`이면 `kept_keys`에 열쇠를 넣는다. `_refresh`는 `select(found, run.ignored_keys + run.kept_keys)`다.
- [x] 8.4 시험(`tests/world/augmentation/test_augmentation.py`)
  - TP-V7-13: LOW_CONFIDENCE·entity 질문의 `needs`에 title이 없음; 제목만 보낸 엔티티 답 → 400(API 경로 하나는 `tests/api/test_world_editor_api.py`), 그래프 쓰기 없음(Meter), 변경 기록 없음, 질문 열림; 지금 값과 같은 지식 답 → 같음.
  - R-09: 확신 0.95 지식에 확인 → 받음, 변경 기록 없음, 그래프 쓰기 없음, 질문 닫힘.
  - S-1: 위키 충돌 판정이 캐시된 지식에 확인 → 다음 탐지에 같은 질문이 없음, "무시한 질문"(`ignored_keys`)에도 없음.
  - 돌연변이: (a) 무변경 검사를 쓰기 뒤로 → 쓰기 단언 실패, (b) `kept_keys` 빼기 → S-1 실패, (c) 엔티티에 title 칸 되돌림 → `needs` 단언 실패.
- [x] 8.5 커밋: `fix(world): augmentation answers ask only for what they can change, refuse an answer that changes nothing, and a kept wiki conflict stays answered (V7, FR-C12, U8 #13)`

### Step 9 — 운영 문서
- [x] 9.1 `aidlc-docs/operations/operations.md`
  - WorldMeta가 없는 옛 월드는 캐시되지 않아 읽을 때마다 불러온다. 다시 빌드하거나 다시 불러오면 생긴다.
  - 백업이 설정되어 있고 실패하면 교체가 멈춘다(stage `backup`). 디스크·권한을 고치고 다시 한다.
  - 다시 빌드는 NPC·씨앗을 이름이 같은 지역에 이어 붙인다. 못 붙인 것은 리포트 경고(stage `carry-over`)와 백업에 있다.
  - 중복 id World File은 거절된다(stage `duplicate-ids`). 파일을 고친다.
- [x] 9.2 커밋: `docs: rebuilds keep NPCs and seeds, a failed backup stops a replace, meta-less worlds are read fresh (V7)`

### Step 10 — 게이트와 요약
- [x] 10.1 게이트: ruff·black, mypy ≤ 11, pytest 두 번(hypothesis 시드 둘), `git diff --stat -- web` 비어 있음.
- [x] 10.2 `construction/V7-world-knowledge/code/code-summary.md`
  - § 1 기준선과 결과
  - § 2 파일
  - § 3 BR·TP·PBT 대응
  - § 4 바뀐 기존 시험(수와 까닭)
  - § 5 이탈(대역 셋, 인메모리 열쇠, `kept_keys`)
  - § 6 알려진 한계(FD의 셋, 대역 엣지의 느슨함, 옛 스냅샷 읽기와 백업 사이의 편집)
  - § 7 돌연변이 결과
  - § 8 다음에 넘김(§ 4)
- [x] 10.3 커밋: `docs(aidlc): V7 code summary`

---

## 3. 요구 대응

| 요구 | 단계 | 규칙·시험 |
|---|---|---|
| FR-C6 합의 출처·순서 무관 | 2 | BR-V7-01~05, TP-V7-1~3, PBT-V7-1~3 |
| FR-C7 교체 중 캐시 | 3 | BR-V7-06~09, TP-V7-4~6 |
| FR-C8 백업 실패 | 6 | BR-V7-10·11, TP-V7-7 |
| FR-C9 다시 빌드 뒤 NPC·씨앗 | 7 | BR-V7-12~16, TP-V7-8·9·14, PBT-V7-4 |
| FR-C10 중복 id·라벨 | 4·5 | BR-V7-17~20, TP-V7-10~12, PBT-V7-5 |
| FR-C12 보강 입력 칸 | 8 | BR-V7-21·22, TP-V7-13, § 1.1 R-09·S-1 |
| NFR-6 순서 무관 | 2·5 | PBT-V7-1·5 |

유닛 완료 조건: 연결 순서와 무관한 합의(Step 2) · 교체 중 캐시(Step 3) · 백업 실패 뒤 옛 월드(Step 6) · 다시 빌드 뒤 NPC·씨앗(Step 7) · 중복 id 거절과 라벨 있는 삭제(Step 4·5) · 엔티티 질문의 제목 칸 없음(Step 8).

## 4. 다음에 넘김

- **V8 에디터**: 빌드 리포트에 이어 붙인 수(`carried_npcs`, `carried_seeds`) 보이기와 `web/src/types.ts`의 두 칸. 경고 stage(`backup`, `carry-over`, `duplicate-ids`, `persist-meta`)의 한국어 이름. 보강 패널에서 `kept_keys`를 보일지.
- **B&T 운영자 확인**: 실제 Neo4j에서 라벨 있는 삭제(같은 id의 지역과 씨앗을 손으로 만든 뒤 씨앗만 지워짐), CLI 다시 빌드 중 API 읽기가 반쪽 월드를 캐시하지 않음.

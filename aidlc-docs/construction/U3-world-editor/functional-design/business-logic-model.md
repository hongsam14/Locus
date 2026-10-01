# U3 월드 에디터 — Business Logic Model

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3 기능 설계 중 흐름입니다. 다음을 어떤 순서로 처리하는지 고정합니다.
- 편집 연산(지역·연결·지식·스코프·NPC)과 지역 삭제 정리
- 열린 세션 확인
- NPC 초안
- 보강 Q&A의 탐지·질문·적용·되돌리기
- wiki 근거, 빌드·불러오기·목록 화면

규칙 번호(BR-U3-n)는 business-rules.md, 데이터는 domain-entities.md를 따른다.

## 0. 한눈에
| 흐름 | 주인 | 스토리 |
|---|---|---|
| 지역·연결·지식·스코프·NPC 편집 | `RegionEditor`·`ConnectionEditor`·`KnowledgeEditor`·`NpcEditor`·`EntityEditor`·`WorldCatalog`(`locus/world/editor/`, domain-entities §2.0) | US-2.2·2.3·2.4 |
| 지역 삭제 정리 | `RegionEditor.plan_region_delete` / `delete_region` | US-2.2 넷째 |
| 열린 세션 확인 | `api/routers/world.py` + `SessionService.open_player_regions` | Q2=A |
| NPC 초안 | `NpcDraftService`(`locus/world/npc_drafts.py`) | US-2.5 |
| 보강 Q&A | `AugmentationService`·`detectors`·`apply`(`locus/world/augmentation/`) | US-2.6 |
| wiki 근거 | 빌드(`build.py`·`wiki/base.py`) + `WikiAdmin` | US-2.8 |
| 빌드·World File·월드 목록 화면 | 기존 경로 + `web/src/features/editor/`, `routes/HomePage.tsx` | US-2.1·2.7·6.2·6.3·6.4 |
| U7 이월 | `DistortionService.set_region_distortion` | Q6=A |

## 1. 편집 연산 (W7)
아래 절의 연산은 domain-entities §2.0의 클래스에 나뉜다(1.2·1.3 = `RegionEditor`, 1.4 = `ConnectionEditor`, 1.5 = `KnowledgeEditor`, 1.6 = `NpcEditor`, 1.7 = `EntityEditor`, 1.8 = `WorldCatalog`). 공통 쓰기는 `EditorWrites`가 한다.

### 1.1 공통
- **쓰기**
  - 노드는 `replace_nodes`로 쓴다(속성 교체, BR-U3-1).
  - 검색 문서가 있는 종류(지식·NPC·엔티티·prior)는 같은 연산에서 다시 색인하거나 지운다.
- **끝**: 연산마다 `_written(world_id)`이 `finally`에서 캐시를 무효화하고 `WorldMeta.updated_at`을 고친다(지금 그대로).
- **검사**
  - 경로의 `world_id`·id와 본문이 다르면 400이다(A3-13).
  - 참조하는 지역·엔티티는 스냅샷에 있어야 한다. 없으면 404다.
- **원자성**: 그래프 포트에는 트랜잭션이 없다. 한 연산 안의 여러 쓰기는 "중간에 끊겨도 끊긴 참조가 남지 않는 순서"로 둔다(§1.3, BR-U3-8). 끊겨 남은 것은 보강 DANGLING이 찾는다.

### 1.2 지역 (`upsert_region(region)`)
1. 부모 검사
   - `parent_id`가 있으면 그 지역이 있어야 한다.
   - 자기 자신이거나 자기 자손이면 400이다(순환).
2. `replace_nodes([region_to_node(region)])`
3. 부모가 바뀌었으면 옛 `CONTAINS`(옛 부모 → 이 지역)를 지우고 새 것을 만든다. 부모가 없어졌으면 지우기만 한다.
4. 위치(`position`)만 바뀌는 끌기도 같은 경로다. 화면은 실제로 끌었을 때만 보낸다(BR-U3-30).

### 1.3 지역 삭제 (Q1=A, Q2=A)
**`plan_region_delete(world_id, region_id) -> RegionDeletePlan`** (쓰기 없음, 확인 대화용)
- 스냅샷에서 다음을 모은다.
  - 자식 지역: `parent_id == region_id`
  - 연결: 이 지역이 끝점인 `CONNECTED_TO`, 키로 짝지음
  - NPC: `home_region_id == region_id`
  - 지식
    - 이 지역에 SCOPED_TO가 있는 지식을 모은다.
    - 다른 DIRECT 스코프가 없고 `is_global`이 아니면 `knowledge_to_unscope`로 간다.
    - 다른 스코프가 있으면 `knowledge_scope_removed`로 간다.
  - 엔티티: `located_in == region_id`
- `new_parent_id`는 지운 지역의 `parent_id`다.
- `blocked_by_sessions`는 라우터가 채운다(§2).

**`delete_region(world_id, region_id, *, protected: set[str]) -> RegionDeleteReport`**
1. `region_id in protected`이면 `RegionInUseError`(409)다. 쓰지 않는다.
2. 계획을 다시 만든다(확인 대화 뒤 바뀌었을 수 있다).
3. 쓰기 순서(BR-U3-8)
   1. 자식 지역 다시 붙이기: 각 자식의 `parent_id = new_parent_id`로 `replace_nodes`, 옛 `CONTAINS` 지우기, 새 `CONTAINS` 만들기
   2. 엔티티의 `located_in = None`(교체)과 `LOCATED_IN` 지우기
   3. 이 지역으로 가는 `SCOPED_TO` 지우기. 지식 노드는 그대로다.
   4. NPC 삭제: 노드, `LIVES_IN`, 검색 문서
   5. 연결 삭제: 두 방향 모두
   6. 지역 노드 삭제(`delete_node`, DETACH)
4. 보고를 돌려준다. 지식 노드는 지우지 않으므로 번역 정리는 없다. NPC 글은 번역 캐시가 없다.

### 1.4 연결 (US-2.2 둘째, B9)
- **`upsert_connection(conn: ConnectionEdge) -> list[ConnectionEdge]`**
  - 두 지역이 있어야 하고 서로 달라야 한다. 가중치는 [0,1]이다.
  - 같은 키(두 지역 + 종류)의 엣지 두 개를 지운 뒤, a→b와 b→a를 같은 종류·가중치·근거로 만든다(BR-U3-10).
  - 종류를 바꾸는 편집은 화면이 "옛 키 삭제 + 새 키 추가"로 보낸다.
- **`change_connection_kind(key: ConnectionKey, new_kind) -> list[ConnectionEdge]`** (검토 01 R-09)
  - 한 연산이다. 옛 쌍을 읽어 가중치·근거(`rationale`)·`wiki_prior_ref`·`provenance`를 그대로 옮긴 새 쌍을 쓰고, 옛 쌍을 지운다(새 쌍 먼저).
  - 같은 두 지역에 새 종류의 쌍이 이미 있으면 400이다.
  - `PUT connections` 본문에 `previous_kind`가 있으면 이 연산이다.
- **`delete_connection(key: ConnectionKey) -> int`**: 두 방향을 지운다. 없으면 404다.
- 연결은 검색 문서가 없다. 캐시 무효화만 한다.

### 1.5 지식과 스코프 (US-2.3, FR-B5)
- **`upsert_knowledge(k)`**
  - 노드를 교체하고 검색 문서를 다시 색인한다.
  - 스코프 엣지는 건드리지 않는다(US-2.3 셋째 "스코프는 유지된다").
  - `region_hint`는 저장하지 않는다(일시 값).
- **`create_knowledge(k, region_id)`**: 지역 화면의 "지식 추가"다. `upsert_knowledge` 뒤에 DIRECT 스코프 하나를 만든다(US-2.3 첫째).
- **`set_scopes(world_id, knowledge_id, region_ids: list[str])`**
  - 그 지식의 DIRECT 스코프를 주어진 지역들로 바꾼다. 빠진 것은 지우고 새것은 만든다.
  - 빈 목록이면 스코프 없음이 된다.
  - INHERITED·GLOBAL 스코프는 계산값이라 저장하지 않는다. 지금처럼 DIRECT만 저장한다.
- **`delete_knowledge(world_id, knowledge_id)`**: 노드(DETACH)와 검색 문서를 지운다. 라우터는 번역을 정리한다.
- **`list_unscoped(world_id) -> list[Knowledge]`**: 스냅샷에서 전역이 아니고 SCOPED_TO가 하나도 없는 지식이다. 빌드 리포트의 `unscoped_knowledge_ids`와 지역 삭제가 남긴 것을 함께 담는다.

### 1.6 NPC (US-2.4)
- **`upsert_npc(npc)`**
  - `home_region_id`의 지역이 있어야 한다.
  - 노드를 교체하고, `LIVES_IN`은 옛 것을 지우고 새것을 만든다. 검색 문서도 다시 색인한다.
- **`delete_npc(world_id, npc_id)`**: 노드, `LIVES_IN`, 검색 문서를 지운다. NPC 글은 번역 캐시가 없다(검토 01 R-02).
  - 세션에 그 NPC와의 대화가 있어도 지울 수 있다(Q2=A는 지역 삭제만 막는다). 플레이 화면은 그 NPC를 더는 보이지 않고, 대화 기록은 세션에 남는다.

### 1.7 엔티티 (보강 대상, B3)
- **`update_entity(entity)`**: 노드를 교체하고, `located_in`이 바뀌면 `LOCATED_IN`을 다시 쓴다. 검색 문서도 다시 색인한다.
- **`delete_entity(world_id, entity_id)`**: 노드와 검색 문서를 지운다.
- 에디터 화면에서 엔티티를 직접 편집하는 일은 없다(스토리에 없다). 보강 Q&A가 쓴다.

### 1.8 월드 목록 (US-6.4)
- **`list_worlds() -> list[WorldSummary]`**: `graph.list_world_ids()`, `WorldMeta`, 지역 수다. 지금 라우터 계산을 옮긴 것이다.
- 라우터가 열린 세션 수를 붙인다.

## 2. 열린 세션 확인 (Q2=A)
- `SessionService.open_player_regions(world_id) -> dict[str, list[str]]`(play, 새로)는 열린 세션마다 플레이어의 `region_id`를 모은다. 결과는 `region_id → [session_id]`다.
- `DELETE /api/world/worlds/{w}/regions/{r}` (검토 01 R-09: 확인과 삭제 사이의 경합)
  1. 라우터가 그 월드의 열린 세션마다 GM 리스(`play.guard.hold`)를 잡는다. 턴이 돌고 있는 세션이 있으면 409("turn in progress")이고 아무것도 지우지 않는다(교체 경로의 사전 확인과 같다).
  2. 리스를 쥔 채로 `open_player_regions`를 읽어 `protected = {r} ∩ keys`를 만든다. 리스가 이동(턴)을 막으므로, 확인과 삭제 사이에 플레이어가 그 지역에 들어올 수 없다.
  3. `RegionEditor.delete_region(..., protected=...)`를 부르고 리스를 놓는다.
  4. 409면 본문에 세션 id 목록을 싣는다.
  - play가 조립되지 않았으면(세션 DB 없음) 빈 보호 집합이고 리스도 없다.
- `GET .../regions/{r}/delete-plan`은 같은 함수로 `blocked_by_sessions`를 채운다. 그러면 확인 대화가 "지울 수 없음"을 미리 보인다.
- 그 밖의 편집은 열린 세션과 상관없이 된다. 에디터는 `GET /worlds`의 `open_sessions`로 "열린 세션 N개" 띠를 보인다(BR-U3-15).

## 3. NPC 초안 (W8, US-2.5)
`NpcDraftService(llm, snapshots).suggest(world_id, region_id, *, n=3) -> NpcDraftResult`
1. 지역이 있어야 한다(404).
2. 프롬프트에 넣는 것
   - 지역 이름·계층·설명
   - 그 지역의 DIRECT 지식 상위 8개(제목 + 진술, `one_line`)
   - 이미 있는 NPC 이름(겹치지 않게)
3. 구조화 출력 한 번이다. 최대 3명이고, 이름·역할·설명·traits는 상한으로 자른다(BR-U3-21).
4. LLM이 실패하거나 없으면 `drafts=[]`, `failed=true`다(LLM이 없으면 라우터가 503).
5. 저장은 하지 않는다. 화면의 "받아들이기"가 `POST .../npcs`로 하나만 저장한다(US-2.5 둘째).

## 4. 보강 Q&A (W5, Q3=A)

### 4.1 탐지 (스냅샷 위, 순수)
| 탐지기 | 대상 | 질문 대상 | 고정 선택지 |
|---|---|---|---|
| `gap` | 직접 지식이 없는 지역 | region | add / ignore |
| `low_confidence` | 신뢰도 < 0.5인 지식·엔티티 | knowledge·entity | confirm / edit / remove / ignore |
| `wiki_conflict` | 지역 `attributes.terrain_kind`와 맞지 않는 지식(LLM + wiki) | knowledge | confirm / edit / remove / ignore |
| `orphan` | `located_in`·RELATED_TO·ABOUT 어느 것도 없는 엔티티 | entity | edit(지역 지정) / remove / ignore |
| `dangling` | id 속성이 없는 노드를 가리킴(domain-entities §4.1) | 그 속성을 가진 노드 | edit(다른 대상으로) / remove(속성 비우기·참조 지우기) / ignore |
| `unscoped` | 전역이 아니고 스코프가 없는 지식 | knowledge | edit(지역 지정) / remove(지식 지우기) / ignore |

- 질문 텍스트는 템플릿으로 만들고, LLM이 있으면 다듬는다. 선택지(`actions`)는 바꾸지 않는다(B4).
- 이슈 키(유형 + 대상 + 속성)가 같으면 같은 이슈다. 한 노드의 끊긴 속성 둘은 이슈 둘이다(검토 01 R-03).
- 한 탐지의 질문은 최대 20개다(심각도 순). `ignored_keys`에 있는 이슈는 뺀다.
- **LLM 호출 상한** (검토 01 R-05, BR-U3-41)
  - 질문 다듬기: 탐지마다 아직 다듬지 않은 질문 5개까지만 다듬는다. 다듬은 문장은 run 안에 이슈 키로 보관하고 다시 쓴다.
  - wiki_conflict 판정: 탐지마다 20개 지식까지만 보고, 판정 결과를 run 안에 `(지식 id, 지역 terrain_kind)`로 보관한다. 편집으로 바뀐 지식은 다시 본다.
  - 그래서 답·되돌리기마다 다시 탐지해도 새로 바뀐 것만 LLM을 부른다.

### 4.2 답 적용 (`apply_answer`) — 대상은 서버가 질문에서 읽는다(B1)
| 이슈 / 선택 | 쓰기 | `ChangeSet`에 남는 것 |
|---|---|---|
| gap / add | 지식 노드(진술 필수, 비면 400) + 그 지역 DIRECT 스코프 | `added_ids`, `edges_added` |
| low_confidence·wiki_conflict / confirm | 지식이면 신뢰도 `max(현재, 0.9)`, 엔티티면 신뢰도(B3) | `nodes_before` |
| … / edit | 지식이면 진술·제목·신뢰도, 엔티티면 설명·신뢰도 | `nodes_before` |
| … / remove | 지식·엔티티 삭제. 붙은 엣지를 미리 읽어 둔다 | `nodes_before`, `edges_removed` |
| orphan / edit(region) | 엔티티 `located_in` + `LOCATED_IN` | `nodes_before`, `edges_added` |
| dangling / edit(`ref_id`) | 그 속성을 새 id로 바꾸고, 해당 엣지(CONTAINS·LOCATED_IN·ABOUT·DERIVED_FROM)도 다시 쓴다. `ref_id`의 노드가 그 속성에 맞는 종류로 있어야 한다(지역·엔티티·prior). 아니면 400 | `nodes_before`, `edges_*` |
| dangling / remove | 속성을 비운다(`parent_id`·`located_in`·`wiki_prior_ref`는 None, 목록은 그 id만 뺌) | `nodes_before`, `edges_removed` |
| unscoped / edit(region) | DIRECT 스코프 하나 | `edges_added` |
| unscoped / remove | 지식 삭제 | `nodes_before`, `edges_removed` |
| * / ignore | 쓰지 않는다. 그 이슈는 이 run에서 다시 묻지 않는다 | 빈 변경 |

- 쓰기는 `WorldEditor`의 같은 연산을 쓴다. 검색 색인·캐시 무효화도 같다.

### 4.3 run (검토 01 R-04·R-08)
- **시작**: `start_run(world_id)`은 탐지와 질문으로 run을 만든다. 이슈는 run 안에 둔다(지금은 버린다).
- **답**: `answer(run_id, answer) -> AnswerResult`
  - 질문이 그 run에 있어야 하고 run이 열려 있어야 한다. 아니면 404·409다.
  - 적용 → `answers += 1` → 다시 탐지 → 다음 질문 순서다. ignore는 그 이슈 키를 `ignored_keys`에 넣는다.
  - 한 run의 답은 최대 30개다(`MAX_ANSWERS`). 지금의 "5라운드"는 답 5개였는데, run을 유지하면 질문 20개 중 5개밖에 답할 수 없어서 넓힌다.
  - 화면은 run을 유지한다(B2).
- **상태 전이**
  | 지금 | 사건 | 다음 |
  |---|---|---|
  | open | 답, 남은 이슈 있음, `answers < 30` | open |
  | open | 답, 남은 이슈 없음 | converged |
  | open | 답, `answers == 30` | stopped |
  | open·converged·stopped | 되돌리기 | 다시 탐지: 이슈가 있고 `answers < 30`이면 open, 이슈가 없으면 converged, `answers == 30`이면 stopped |
  | converged·stopped | 답 | 409(새 run을 연다) |
- **되돌리기**: `revert(run_id, change_id)`
  - 그 run의 기록에서 찾는다. `reverted`면 409다.
  - **나중 것부터**다. 아직 되돌리지 않은 변경 중 가장 나중 것이 아니면 409("먼저 나중 변경을 되돌리세요")다. 그래서 앞선 되돌리기가 나중 변경을 덮어쓰지 않는다.
  - 순서
    1. `edges_added` 지우기
    2. `added_ids` 노드 지우기
    3. `nodes_before`를 `replace_nodes`로 되돌리기
    4. `edges_removed` 되살리기
    5. 검색 문서 다시 색인(지운 것은 다시 만들고 추가한 것은 지운다)
  - 다시 탐지해 질문을 고친다.
- `GET /augmentation/runs/{id}`: run을 다시 읽는다(화면 새로고침용).
- **run 수명**: run은 프로세스 메모리에만 있다(`InMemoryRunStore`). 서버를 다시 켜면 사라지고, 화면은 404를 받으면 "새로 찾기"를 보인다. 월드마다 최근 20개만 두고 오래된 것부터 버린다(BR-U3-42).

## 5. wiki 근거 (Q4=A, US-2.8)

### 5.1 빌드가 근거를 저장한다 (검토 01 R-01)
빌드는 준비 단계(그래프를 건드리지 않음)와 커밋 단계로 나뉜다. 토폴로지는 준비 단계에서, 온톨로지(보강·dedup)는 커밋 단계에서 wiki를 찾는다. 그래서 폴백 prior는 두 번에 나눠 저장한다.

1. **만들기**: `CommonsenseWiki`(한 빌드에 인스턴스 하나)가 검색에서 못 찾아 LLM으로 만든 prior를 `created_priors`에 모은다.
   - **중복 키**: 정규화한 질의(`casefold` + 공백 접기)다. 같은 질의는 LLM을 다시 부르지 않고 처음 만든 prior를 돌려준다. 연결 후보마다 새 prior가 생기던 문제를 막는다.
   - **상한**: 빌드당 폴백 prior 40개(`WIKI_FALLBACK_MAX`, 상수)다. 넘으면 LLM을 부르지 않고 빈 결과를 돌려준다. 그 연결은 근거 문구 없이 계산 가중치만 갖는다. 리포트에 경고 한 줄을 남긴다.
2. **참조 정리** (커밋 전): 연결의 `wiki_prior_ref`는 `증류 prior id ∪ created id`에 있을 때만 남긴다. 그 밖(검색이 찾은 옛 월드의 prior, 교체로 지워질 것)은 지금처럼 버리고 경고한다.
3. **커밋 순서**
   1. 옛 월드 삭제
   2. 증류 prior + 토폴로지 단계의 `created_priors` 저장
   3. 온톨로지(보강이 더 만들 수 있다)
   4. 온톨로지 단계에서 새로 생긴 `created_priors` 저장
   5. 나머지(지식과 `DERIVED_FROM` 엣지 포함) 저장
   - 그래서 `DERIVED_FROM`의 MATCH가 늘 끝점을 찾는다.
4. 리포트에 `priors_created`(증류 + 폴백)를 더한다.

### 5.2 읽기
- `WikiAdmin.list_priors(world_id) -> list[WikiPrior]`
- `WikiAdmin.prior_refs(world_id) -> list[PriorUsage]`: 스냅샷의 연결(`wiki_prior_ref`)과 지식(`derived_from_prior_ids`)을 prior별로 묶는다.
- 끊긴 참조는 `broken_refs`로 따로 준다. 연결 상세의 `PriorRefView.broken`도 같은 계산이다.
- `delete_prior(world_id, prior_id)`: 노드와 검색 문서를 지운다. 참조하는 연결·지식은 그대로 두고, 이후 DANGLING이 찾는다.

## 6. 빌드·World File·월드 목록 (화면만 새로)
- **빌드(US-2.1)**
  - `POST /worlds/{w}/build/upload`에 `concept_arts` 칸을 더한다. 그 밖은 그대로다.
  - 같은 world_id가 있으면 화면이 교체 확인을 받는다(`replace=true`). 열린 세션이 있으면 `confirm=true`를 받는다(지금 409 규칙).
  - 리포트는 다음을 그대로 보인다: 수, 경고(severity별), 스코프 없음 수, LLM·임베딩 호출 수, 교체 여부, 닫힌 세션, 백업 경로, `priors_created`.
- **World File(US-6.2·6.3)**
  - 저장은 `GET /worlds/{w}/file`을 내려받기로 한다.
  - 불러오기는 `POST /worlds/{w}/file/upload`다. 열린 세션이 있으면 "교체하고 N개 닫는다" 확인을 받은 뒤 `confirm=true`로 보낸다.
  - 지원하지 않는 버전은 422 문구를 그대로 보인다.
- **월드 목록(US-6.4)**
  - `/`는 `GET /worlds`의 이름·지역 수·마지막 수정·열린 세션 수를 보인다.
  - 각 줄의 [편집]은 `/editor/:w`다.
  - [세션 시작] (검토 01 R-10)
    1. `GET /api/world/worlds/{w}/export`로 지역 목록을 읽는다(누를 때 한 번).
    2. `NewSessionForm`(U4)에 그 지역을 넘긴다.
    3. 시작은 U4의 `POST /api/play/worlds/{w}/sessions`(본문 이름·시작 지역) → `/play/:sid`다.

## 7. API (A4, `/api/world`)
| 메서드·경로 | 동작 |
|---|---|
| `GET /worlds/{w}/regions/{r}/editor` | `EditorRegionView`(+`*_ko`) |
| `PUT /worlds/{w}/regions/{r}` | 지역 교체 저장(부모 다시 붙이기) |
| `POST /worlds/{w}/regions` | 지역 추가 |
| `GET /worlds/{w}/regions/{r}/delete-plan` | `RegionDeletePlan`(+ `blocked_by_sessions`) |
| `DELETE /worlds/{w}/regions/{r}` | `RegionDeleteReport` / 409 |
| `PUT /worlds/{w}/connections` | 본문 `ConnectionEdge`(+ 선택 `previous_kind`) → 두 방향 저장 또는 종류 바꾸기 |
| `DELETE /worlds/{w}/connections?a=&b=&kind=` | 두 방향 삭제 |
| `POST /worlds/{w}/regions/{r}/knowledge` | 지식 추가 + DIRECT 스코프 |
| `PUT /worlds/{w}/knowledge/{k}` | 지식 교체(스코프 유지) |
| `PUT /worlds/{w}/knowledge/{k}/scopes` | 본문 `{region_ids}` |
| `DELETE /worlds/{w}/knowledge/{k}` | 지식 삭제(검색·번역 정리) |
| `GET /worlds/{w}/knowledge/unscoped` | 스코프 없는 지식 목록 |
| `POST /worlds/{w}/npcs` · `PUT …/npcs/{n}` · `DELETE …/npcs/{n}` | NPC |
| `POST /worlds/{w}/regions/{r}/npc-drafts` | `NpcDraftResult`(저장 없음) |
| `GET /worlds/{w}/priors` · `GET /worlds/{w}/prior-refs` · `DELETE /worlds/{w}/priors/{p}` | wiki |
| `POST /worlds/{w}/augmentation/runs` · `GET /augmentation/runs/{id}` · `POST …/answer`(→`AnswerResult`) · `POST …/revert` | 보강 |
| `POST /worlds/{w}/build/upload` | `concept_arts` 칸 추가 |
| `DELETE /worlds/{w}/nodes/{n}` | **없앤다**(이탈 2) |

## 8. U7 이월 (Q6=A)
`DistortionService.set_region_distortion`의 같은 UoW 안에서 다음을 한다.
1. ACTIVE 사건마다 `contributions.get(region_id)`이 있으면 그 키를 지우고 `update_event`로 저장한다.
2. 지운 합계를 타임라인 페이로드 `event_contributions_cleared`에 넣는다.

그 뒤 해소는 남은 기여만 되돌린다. 다음 턴부터 사건은 다시 쌓는다. 지금은 몫 지우기와 타임라인이 같은 UoW가 아니므로, 이것도 하나의 UoW로 묶는다.

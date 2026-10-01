# U3 월드 에디터 — Domain Entities

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3 기능 설계 중 데이터 정의입니다. 다음을 고정합니다.
- 편집 연산이 쓰는 값: 삭제 보고, 연결 키, 에디터 읽기 모델
- 보강 Q&A의 질문 대상과 변경 기록
- wiki 참조
- 포트 확장(엣지 삭제, 문서 삭제, 속성 교체)

근거
- 답: FD-U3 Q1=A(정리해서 지운다), Q2=A(편집 자유, 플레이어 지역 삭제만 막음), Q3=A(끊긴 id 참조 + 스코프 없는 지식), Q4=A(빌드가 근거를 저장), Q5=A(도구 모드), Q6=A(GM 설정이 사건 몫도 지운다, U7 이월)
- 가정: 플랜 A3-1~15
- 캐노니컬 모델(`Region`, `ConnectionEdge`, `Knowledge`, `ScopeLink`, `Entity`, `NPC`, `WikiPrior`)은 필드를 바꾸지 않는다. 바뀌는 것은 저장 방식(교체)과 새 값 객체다.

## 1. 저장 포트 확장 (A3-1, A3-2)

### 1.1 `GraphRepository` (shared/storage/base.py)
| 메서드 | 뜻 |
|---|---|
| `replace_nodes(nodes: list[Node]) -> None` | **새로**. 노드의 속성을 통째로 바꾼다. 없던 속성은 생기고 빠진 속성은 사라진다(`SET n = $props`, id·라벨·world_id 유지). 노드가 없으면 만든다 |
| `delete_edges(world_id, edges: list[EdgeKey]) -> int` | **새로**. 지운 수를 돌려준다. 없는 엣지는 조용히 넘긴다 |
| `upsert_nodes` | 그대로(병합). 빌드·불러오기는 계속 이것을 쓴다 |

```python
class EdgeKey(BaseModel):           # 엣지 하나를 가리키는 키 (edge_identity_field와 같은 규칙)
    type: str                       # "CONNECTED_TO", "SCOPED_TO", "CONTAINS", "LIVES_IN", "LOCATED_IN", "ABOUT", ...
    source_id: str
    target_id: str
    identity: dict = {}             # CONNECTED_TO는 {"kind": ...}, RELATED_TO는 {"id": ...}
```

### 1.2 `SearchRepository`
| 메서드 | 뜻 |
|---|---|
| `delete(world_id, doc_ids: list[str]) -> int` | **새로**. 문서를 지운다. 없는 id는 넘긴다 |

- Neo4j·OpenSearch 어댑터와 인메모리 가짜를 함께 바꾸고, 포트 계약 테스트를 더한다.

## 2. 편집 값 (W7)

### 2.0 편집 서비스 나누기 (검토 01 제안 채택)
`WorldEditor` 한 클래스에 연산 20여 개가 몰리지 않게 한다. 책임별 클래스로 나누고 생성자로 주입한다(파사드 없음, play의 서비스 배치와 같다).

| 클래스 | 책임 |
|---|---|
| `EditorWrites` | 공통: 그래프·검색·임베딩 포트, 캐시 무효화, `WorldMeta` 갱신, 교체 쓰기·문서 색인·삭제 도우미 |
| `RegionEditor` | 지역 추가·교체·부모 다시 붙이기, 삭제 계획·삭제(정리) |
| `ConnectionEditor` | 연결 쌍 저장·종류 바꾸기·삭제 |
| `KnowledgeEditor` | 지식 추가·교체·삭제, 스코프 지정, 스코프 없음 목록 |
| `NpcEditor` | NPC 추가·교체·삭제 |
| `EntityEditor` | 엔티티 교체·삭제(보강이 쓴다) |
| `WorldCatalog` | 월드 목록 |

- `WorldContainer`가 각 클래스를 노출한다. 보강 적용은 필요한 클래스를 주입받는다.

### 2.1 `ConnectionKey`
```python
class ConnectionKey(LocusModel):    # 연결 하나 = 두 지역 + 종류 (방향 없음)
    world_id: str
    a_region_id: str
    b_region_id: str
    kind: ConnectionKind
```
- 저장은 늘 두 방향(a→b, b→a)이고 종류·가중치·근거가 같다(A3-3). 같은 두 지역 사이에 종류가 다른 연결은 따로 있을 수 있다(엣지 정체성 = 끝점 + 종류).

### 2.2 `RegionDeletePlan` / `RegionDeleteReport` (Q1=A)
```python
class RegionDeletePlan(LocusModel):   # 확인 대화가 보이는 것 (쓰기 없음)
    region_id: str
    region_name: str
    new_parent_id: str | None          # 자식이 옮겨 갈 곳 (지운 지역의 부모)
    children: list[NameRef]            # 옮겨질 자식 지역
    connections: list[ConnectionKey]   # 함께 지워질 연결
    npcs: list[NameRef]                # 함께 지워질 NPC
    knowledge_to_unscope: list[NameRef]   # 이 지역에만 붙어 있어 "스코프 없음"이 될 지식
    knowledge_scope_removed: list[NameRef]  # 다른 지역에도 붙어 있어 이 스코프만 빠질 지식
    entities_unlocated: list[NameRef]  # located_in이 비워질 엔티티
    blocked_by_sessions: list[str]     # Q2=A: 플레이어가 서 있는 열린 세션 id (있으면 지울 수 없다)

class RegionDeleteReport(RegionDeletePlan):  # 지운 뒤 돌려주는 것 (같은 모양)
    deleted_ids: list[str]             # 지운 노드 id (지역 + NPC)

class NameRef(LocusModel):
    id: str
    name: str
```

### 2.3 에디터 읽기 모델 (US-2.3·2.4)
```python
class EditorRegionView(LocusModel):    # 에디터가 지역 하나를 열 때 (합의 보기 아님)
    region: Region
    children: list[NameRef]
    connections: list[ConnectionView]   # 이 지역에서 나가는 연결
    knowledge: list[ScopedKnowledge]    # 이 지역에 DIRECT로 붙은 지식(원문)
    npcs: list[NPC]

class ConnectionView(LocusModel):
    key: ConnectionKey
    other_region_name: str
    weight: float
    rationale: str | None
    prior: PriorRefView | None          # Q4=A: 근거 prior (끊겼으면 broken)

class ScopedKnowledge(LocusModel):
    knowledge: Knowledge
    scope_region_ids: list[str]         # 이 지식이 붙은 모든 지역
```
- API 응답은 `api/schemas.py`에서 **지식** 진술에만 `*_ko`를 붙인다(U5 `enrich` 재사용, A3-9). NPC 글은 번역하지 않는다. 번역 종류에 `npc`가 없고, NPC 글은 의도적으로 원문이다(U5 A-1, 검토 01 R-02).

### 2.4 월드 목록 (US-6.4)
- `WorldSummary(id, name, description, region_count, updated_at)`를 `WorldCatalog.list_worlds()`가 돌려준다. 지금 라우터에 있는 계산을 옮긴다.
- 열린 세션 수는 라우터가 play에서 붙인다(지금처럼 `WorldInfo.open_sessions`).

## 3. NPC 초안 (W8, US-2.5)
```python
class NpcDraft(LocusModel):            # 저장되지 않은 제안
    name: str
    role: str
    description: str
    traits: list[str] = []

class NpcDraftResult(LocusModel):
    region_id: str
    drafts: list[NpcDraft]             # 0~3명
    llm_calls: int                     # 0 또는 1
    failed: bool                       # LLM 실패 → drafts=[]
```
- `NpcDraftService.suggest(world_id, region_id, *, n=3) -> NpcDraftResult`(component-methods W8의 이름, 반환형은 실패 표시를 담으려고 넓힘)
- 받아들이기는 `NpcDraft` 하나를 `NPC(home_region_id=region_id)`로 바꿔 `NpcEditor.upsert_npc`로 저장한다.

## 4. 보강 Q&A (W5, Q3=A, A3-6)

### 4.1 이슈 종류 (`IssueType`)
| 값 | 뜻 | 새로? |
|---|---|---|
| `gap` | 직접 지식이 없는 지역 | 그대로 |
| `low_confidence` | 신뢰도 낮은 지식·엔티티 | 그대로 |
| `wiki_conflict` | 지역 지형(`attributes.terrain_kind`)과 맞지 않는 지식 | 그대로, 읽는 키 고침(B5) |
| `orphan` | 어디에도 붙지 않은 엔티티 | 그대로 |
| `dangling` | **id 속성이 없는 노드를 가리킨다**: `Region.parent_id`, `Entity.located_in`, `ConnectionEdge.wiki_prior_ref`, `Knowledge.derived_from_prior_ids`·`about_entity_ids`. NPC의 `home_region_id`는 넣지 않는다. 로더가 지역 없는 NPC를 이미 버리기 때문이다(검토 01 R-06). 지금 `detect_gaps` 안의 "끝점 없는 관계" 분기는 지운다(로더가 걸러서 닿지 않는다) | 뜻 바뀜(Q3=A) |
| `unscoped` | 전역이 아닌데 어느 지역에도 붙지 않은 지식 | **새로**(Q3=A) |

### 4.2 이슈 키, 질문 대상과 선택지
```python
class Issue(_Aug):                     # 필드 추가
    ...
    field: str | None = None           # dangling: 끊긴 속성 이름
    target_kind: str                   # knowledge | entity | region | connection
    @property
    def key(self) -> str:              # 탐지마다 같은 값 (검토 01 R-03)
        return f"{self.type}:{self.target_kind}:{'|'.join(self.target_ids)}:{self.field or ''}"

class QuestionTarget(_Aug):
    kind: Literal["knowledge", "entity", "region", "npc", "connection"]
    id: str                            # connection은 "a|b|kind"
    name: str                          # 제목·이름 (UI에 보인다, B1)
    region_id: str | None = None
    region_name: str | None = None
    field: str | None = None           # dangling: 끊긴 속성 이름

class AugmentationQuestion(_Aug):      # 필드 추가
    ...
    issue_key: str                     # 이 질문의 이슈 키
    target: QuestionTarget | None      # gap(지역 대상)도 region으로 채운다
    actions: list[AnswerAction]        # 이슈 종류마다 고정(BR-U3-24). LLM은 text만 다듬는다(B4)

class AugmentationAnswer(_Aug):        # 필드 추가
    ...                                # question_id, action, statement, title, confidence, region_id 그대로
    ref_id: str | None = None          # dangling/edit의 새 참조(지역·엔티티·prior id). 서버가 종류를 검사한다

class AugmentationRun(_Aug):           # 필드 추가
    ...
    issues: list[Issue]                # 이번 탐지의 이슈 (지금은 버린다)
    ignored_keys: list[str] = []       # 무시한 이슈 키 (다시 묻지 않는다, BR-U3-28)
    answers: int = 0                   # 이 run에서 받은 답 수 (지금의 round)
```
- `AnswerAction` enum은 그대로다: confirm / edit / remove / add / ignore.
- `target_id`는 질문 대상에서 서버가 채운다. UI는 `question_id`·`action`·편집 값(`statement`·`title`·`confidence`·`region_id`·`ref_id`)만 보낸다.
- `detect_all`의 중복 제거 키는 이슈 키다(유형 + 대상 + 속성). 한 노드의 끊긴 속성 둘은 이슈 둘이다.

### 4.3 변경 기록 (B6)
```python
class ChangeSet(_Aug):                 # 필드 추가
    id, description, added_ids          # 그대로
    nodes_before: list[NodeSnapshot]    # 바뀌거나 지워진 노드의 이전 상태(속성 전부)
    edges_added: list[EdgeSnapshot]     # 이 답이 만든 엣지
    edges_removed: list[EdgeSnapshot]   # 이 답이 지운 엣지(지운 노드에 붙어 있던 것 포함)
    reverted: bool = False              # 두 번 되돌리지 않는다

class EdgeSnapshot(_Aug):
    type: str
    source_id: str
    target_id: str
    properties: dict
```
- `removed`·`updated`(지금 필드)는 `nodes_before`로 합친다.
- 되돌리기는 `replace_nodes`로 노드를, `upsert_edges`·`delete_edges`로 엣지를, 검색 문서를 다시 색인한다.
- 되돌리기는 **나중 것부터**(LIFO)다. 한 run에서 되돌릴 수 있는 것은 아직 되돌리지 않은 변경 중 가장 나중 것 하나다(검토 01 R-08).

### 4.4 답의 결과
```python
class AnswerResult(_Aug):
    change: ChangeSet
    run: AugmentationRun               # 다음 질문까지 (UI는 run을 유지한다, B2)
    changed: list[QuestionTarget]      # 무엇이 바뀌었는지 (US-2.6 둘째)
```

## 5. wiki 참조 (Q4=A, US-2.8)
```python
class PriorRefView(LocusModel):
    prior_id: str
    condition: str | None              # 끊겼으면 None
    effect: str | None
    broken: bool                       # 이 월드에 그 prior가 없다 → "저장되지 않은 근거"

class PriorUsage(LocusModel):          # wiki 탭의 한 줄
    prior: WikiPrior
    connections: list[ConnectionKey]
    knowledge: list[NameRef]
```
- `WikiAdmin.list_priors(world_id) -> list[WikiPrior]`(지금은 Node를 돌려준다)
- `WikiAdmin.prior_refs(world_id) -> list[PriorUsage]`(component-methods W4의 이름; 필터 인자는 두지 않는다)
- `WikiAdmin.broken_refs(world_id) -> list[BrokenRef]`, `BrokenRef(ref_id, connections, knowledge)`

## 6. 오류
| 오류 | 언제 | HTTP |
|---|---|---|
| `LookupError` | 없는 지역·지식·NPC·연결·prior | 404 |
| `ValueError` | 경로와 본문의 id·world_id가 다르다(A3-13), 부모 순환, 자기 연결, 연결의 지역이 없다 | 400 |
| `RegionInUseError` (새, world 경계) | 열린 세션의 플레이어가 서 있는 지역 삭제(Q2=A) | 409, 세션 id 목록 |
| `ChangeAlreadyRevertedError` (새) | 되돌린 변경을 다시 되돌림 | 409 |
| `LlmUnavailableError` | NPC 초안·보강 질문 다듬기에 LLM이 없다 | 503(초안), 질문은 템플릿으로 |

## 7. U7 이월 (Q6=A, 플랜 A3-14·15)
- **GM 설정**: GM 왜곡도 설정은 같은 UoW에서 그 지역에 대한 ACTIVE 사건들의 기여(`SessionEvent.contributions[region]`)를 0으로 한다. 지운 양을 `set_distortion` 줄의 `event_contributions_cleared`에 남긴다. U7 BR-U7-5를 넓힌다.
- **지난 줄**: 지역 id가 없는 U7 이전의 지역 줄은 `summary`로 보인다(A3-14).
- **`TOPOLOGY_DEFAULT_BASE`**: 없앤다(A3-15).

## 8. 설계 이탈 (완결 목록)
0. **component-methods W4~W8과 다른 계약** (검토 01 R-07)
   - W7 `WorldEditor` 한 클래스를 §2.0의 일곱 클래스로 나눈다.
   - W7 `delete_region(..., cascade: CascadePolicy) -> DeleteReport`는 `plan_region_delete` + `delete_region(..., protected=) -> RegionDeleteReport`가 된다(정책은 Q1=A 하나라 인자를 두지 않는다).
   - W7 `upsert_connection(edge) -> ConnectionEdge`는 두 방향 목록을 돌려준다. `delete_connection(world_id, a, b)`는 종류를 받는다(`ConnectionKey`). `change_connection_kind`가 새로 생긴다.
   - W7 `upsert_knowledge(k, *, scope_region_ids)`는 `create_knowledge(k, region_id)`와 `upsert_knowledge(k)`(스코프 유지)로 나뉜다.
   - W7 `list_worlds() -> list[WorldInfo]`는 `WorldCatalog.list_worlds() -> list[WorldSummary]`가 된다. 열린 세션 수는 라우터의 `WorldInfo`가 붙인다.
   - W8 `suggest(...) -> list[NpcDraft]`는 `NpcDraftResult`를 돌려준다.
   - W4 `prior_refs(world_id, *, edge, knowledge_id) -> list[PriorRef]`는 필터 없는 `prior_refs(world_id) -> list[PriorUsage]`와 `broken_refs`가 된다.
   - W5 `AugmentationQuestion(target_ids, region_id, options)`는 `QuestionTarget`·`actions`·`issue_key`가 된다. `answer`는 `AnswerResult`를 돌려준다.
   - F2 `UploadPanel`·`BuildReportPanel`은 `BuildPanel`(폼 + 리포트)이 된다.
1. **`WorldEditor.delete_node`(일반)**: 라우터에서 내린다. 종류별 삭제(`delete_region`·`delete_knowledge`·`delete_npc`·`delete_prior`)로 바꾸고, 일반 경로는 보강 REMOVE가 라벨로 나눠 부르는 내부 함수로만 남긴다.
2. **`DELETE /worlds/{w}/nodes/{n}`**: 없앤다. 웹은 종류별 경로를 쓴다.
3. **보강 `answer` 응답**: `ChangeSet`에서 `AnswerResult`로 바뀐다.
4. **빌드**: LLM 폴백 prior를 저장한다(Q4=A). U2의 "새 prior 목록에 없는 참조는 버린다"는 `증류 prior ∪ 이번 빌드가 만든 prior`에 없는 참조(지워질 옛 월드의 prior)만 버린다. 폴백 prior는 같은 질의에서 한 번만 만들고, 빌드당 상한이 있다(BLM §5.1).
5. **U7 BR-U7-5**: 사건 기여까지 지운다(Q6=A).
6. **`TOPOLOGY_DEFAULT_BASE`**: 없앤다(U7에서 더한 env).
7. **에디터의 NPC 글 번역 없음**: unit-of-work U3의 번역 표시는 캐노니컬 지식만이다. NPC 설명은 원문이다(검토 01 R-02).

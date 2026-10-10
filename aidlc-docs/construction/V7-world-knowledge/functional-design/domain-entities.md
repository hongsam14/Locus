# V7 월드·지식 정확성 — Domain Entities

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: V7 Functional Design. 이 문서는 V7이 더하거나 바꾸는 값과 포트를 적는다. 흐름은 `business-logic-model.md`, 규칙과 시험은 `business-rules.md`에 있다.

결정(계획 `construction/plans/V7-world-knowledge-functional-design-plan.md`): Q1 = A. 합의의 각 목록은 확실한 것부터 정렬한다.

---

## 1. 합의 (`locus/knowledge/consensus.py`)

### 1.1 `best_origins` [새, 순수]

```python
def best_origins(
    pw: dict[str, float],                                  # region_id -> 이 지역에서 그 지역까지의 최대곱 경로 가중
    region_direct: dict[str, list[tuple[str, float]]],     # region_id -> [(knowledge_id, scope confidence)] (직접 스코프)
    exclude: str,                                          # 자기 지역(이미 1단계가 맡음)
) -> dict[str, tuple[str, float]]:                         # knowledge_id -> (출처 region_id, 그 출처의 경로 가중)
```

- 지식 하나가 여러 출처 지역에서 직접 스코프로 닿으면, `pw[출처]`가 가장 큰 출처를 고른다.
- 가중이 같으면 지역 id가 사전 순으로 앞서는 출처를 고른다.
- `pw`에 없는 지역(닿지 않는 지역)과 `exclude`는 출처가 될 수 없다.
- 이 함수는 입력 dict·list의 순서와 무관하게 같은 결과를 낸다(PBT-V7-1).

### 1.2 `ConsensusView` [유지, 정렬과 셈의 뜻만 정함]

| 칸 | 뜻 | 정렬(Q1 = A) |
|---|---|---|
| `direct` | 이 지역의 직접 스코프 지식 | `confidence` 내림차순, 같으면 `knowledge_id` 오름차순 |
| `inherited` | 조상 지역의 직접 스코프 지식(아직 정해지지 않은 것) | 같다 |
| `global_knowledge` | 전역 지식(아직 정해지지 않은 것) | 같다 |
| `propagated` | 가장 강한 출처의 가중 ≥ `propagate_min` | 같다(유효 확신도 = 지식 확신도 × 출처 가중) |
| `hearsay` | `hearsay_min` ≤ 가장 강한 출처의 가중 < `propagate_min` | 같다 |
| `unknown_count` | 가장 강한 출처도 `hearsay_min` 아래인 지식의 **수**(지식마다 한 번) | — |

- 묶음 사이의 차례는 그대로다: 직접 → 이어받음 → 전역 → 전파 → 전언. 한 지식은 앞 묶음에 들면 뒤 묶음에 나오지 않는다(지금 규칙).
- 정렬은 `compute_consensus`가 결과를 돌려주기 전에 한다. 그래서 이 결과를 쓰는 곳(플레이 장면의 "아는 것", GM 지식 접힘, 세션 질의, 에디터 미리보기)이 모두 같은 순서를 본다.

## 2. 캐시와 저장 (`locus/knowledge/cache.py`, `locus/shared/storage/persistence.py`)

- `persist_graph` [바뀜: 순서만]
  - 쓰는 차례: 노드(WorldMeta 제외) → 엣지 → 임베딩·색인 → WorldMeta
  - 노드·엣지 쓰기가 실패하면 거기서 돌아간다. WorldMeta는 쓰지 않는다.
  - WorldMeta 쓰기가 실패하면 `stage="persist-meta"`, `severity="error"` 경고다.
- `WorldCache.get` [바뀜]
  - 버전을 읽을 수 있는 캐시에서 이 월드의 버전 표식이 `None`(WorldMeta 없음)이면, 그 스냅샷을 돌려주되 캐시하지 않는다.
  - 로더에 `version()`이 없거나 `check_version=False`면 지금처럼 캐시한다. `_current_version`은 둘을 다른 값으로 돌려준다(`UNVERSIONED` 표식).
  - hit 경로에서 버전 읽기가 예외를 내면, 항목을 버리고 miss처럼 새로 불러온다. 이때도 캐시하지 않는다.

## 3. 백업 (`locus/world/build.py`, `locus/world/worldfile/import_.py`)

```python
class BackupFailedError(RuntimeError): ...       # [새] 백업을 쓰지 못함 (원인 메시지)

def _backup(self, world_id: str) -> Path | None: # [바뀜]
    # 미설정(exporter 또는 backup_dir 없음) -> None (통과)
    # 성공 -> 백업 파일 경로
    # 실패 -> BackupFailedError (warnings에 더하지 않고 던진다)
```

- 빌더와 불러오기는 `BackupFailedError`를 잡아 **지우기 전에** 멈춘다.
  - 리포트에 `BuildWarning(stage="backup", severity="error", message="backup failed; the world was not replaced: …")`를 싣는다.
  - `replaced=False`, `backup_path=None`이고 `ok=false`(error 경고)다.

## 4. 이어 붙이기 (`locus/world/carry_over.py` [새, 순수])

```python
@dataclass(frozen=True)
class CarryOver:
    npcs: list[NPC]            # home_region_id를 새 지역 id로 바꾼 옛 NPC (id 그대로)
    seeds: list[EventSeed]     # region_id를 새 지역 id로 바꾼 옛 씨앗 (id 그대로)
    warnings: list[BuildWarning]  # stage="carry-over", severity="warning", item_id=그 NPC·씨앗 id

def carry_over(old: WorldSnapshot, new_regions: list[Region], world_id: str) -> CarryOver
def region_key(name: str, level: str) -> tuple[str, str]   # (정규화한 이름, 단계)
```

- **정규화한 이름**: NFKC, `casefold()`, 앞뒤 공백 제거, 안쪽 공백을 하나로 모은다.
- **맞추기**: 옛 집 지역 `r`의 열쇠 `region_key(r.name, r.level)`로 새 지역을 찾는다.
  1. 그 열쇠의 새 지역이 하나면 그 지역이다.
  2. 여럿이면 각 후보의 부모 열쇠를 옛 `r` 부모의 열쇠와 비교한다. 부모가 없으면 열쇠는 `None`이다. 하나만 같으면 그 지역이다.
  3. 그래도 하나가 아니거나, 처음부터 없으면 붙이지 않는다.
- **경고 문장**(영어, 리포트 칸)
  - `"NPC {name} was not carried over: no region named {region} ({level}) in the new world"`
  - 여럿일 때는 `"… : {n} regions named {region} ({level})"`
  - 씨앗도 같은 꼴이다.
  - 옛 집 지역이 옛 스냅샷에 없으면(이미 깨진 참조) `"… : its region {id} is not in the old world"`다.
- `world_id`는 새 월드의 것으로 맞춘다(같은 월드를 다시 빌드하므로 보통 같다).

## 5. 리포트 칸

| 모델 | 칸 | 뜻 |
|---|---|---|
| `BuildReport` [바뀜] | `carried_npcs: int = 0`, `carried_seeds: int = 0` | 이어 붙인 수. 못 붙인 것은 `warnings`(stage `carry-over`) |
| `ImportReport` [유지] | — | 중복 id는 `warnings`(stage `duplicate-ids`, severity error)와 `ok=false`로 보고한다 |

## 6. World File 검사 (`locus/world/worldfile/remap.py`)

```python
def duplicate_ids(file: WorldFile) -> list[str]   # [새] 정렬한 목록, 비면 중복 없음
```

- 대상 절: `regions`, `entities`, `relations`, `knowledge`, `priors`, `npcs`, `event_seeds`
- 한 id가 절 안에서 두 번이거나, 두 절에 걸쳐 나오면 중복이다.
- 연결·스코프·사전 링크는 id가 없으므로 대상이 아니다.

## 7. 그래프 포트 (`locus/shared/storage/base.py`, `neo4j_repo.py`)

```python
def get_node(self, world_id: str, node_id: str, *, label: str | None = None) -> Node | None
def delete_node(self, world_id: str, node_id: str, *, label: str | None = None) -> None
```

- `label`이 있으면 그 라벨의 노드만 찾고 지운다.
- 없으면 지금처럼 그 id의 아무 노드다. 둘 이상이면 어느 것인지 정해지지 않는다. 중복을 막아 생기지 않게 한다.
- 테스트 대역 두 곳(`tests/shared/storage/fakes.py`, `tests/world/services/test_services.py`)도 같은 시그니처를 따른다.

## 8. 보강 질문의 입력 칸 (`locus/world/augmentation/questions.py`)

`NEEDS: dict[(IssueType, TargetKind), dict[AnswerAction, list[Input]]]`

| 이슈 | 대상 | 행동 → 입력 칸 |
|---|---|---|
| GAP | region | 더하기 → 문장, 제목 |
| LOW_CONFIDENCE | knowledge | 고치기 → 문장, 제목, 확신 |
| LOW_CONFIDENCE | entity | 고치기 → **설명(statement 칸), 확신** — 제목 없음 |
| WIKI_CONFLICT | knowledge | 고치기 → 문장, 제목, 확신 (탐지는 지식에만 낸다, `augmentation/engine.py`) |
| ORPHAN | entity | 고치기 → 지역 |
| DANGLING | region · entity · connection · knowledge | 고치기 → 참조 |
| UNSCOPED | knowledge | 고치기 → 지역 |

- 표에 없는 (이슈, 대상) 쌍은 입력 칸이 없다(확인·지우기·두기만).
- 화면은 질문의 `needs`를 받아 그린다(지금과 같음). 에디터 카드의 배치는 V8 몫이다.

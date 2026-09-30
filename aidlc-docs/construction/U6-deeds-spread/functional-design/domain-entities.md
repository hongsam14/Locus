# U6 행적·전파 — Domain Entities

근거
- 플랜 `construction/plans/U6-deeds-spread-functional-design-plan.md`의 답이다. Q1은 섞은 방식이다. 발언은 들은 NPC 한 명이 판단하고, 도착과 선언은 목격한 NPC마다 판단해 각자 씨앗을 만든다. Q2는 A(행적 전파가 먼저), Q3은 A(한 호출로 표시 언어 서술과 영어 기록)다.
- 가정 A6-1~13을 따른다.
- 앱 설계는 `component-methods.md` "play — 변경"이다. 이 문서와 다른 곳은 §7에 모았다.

모든 모델은 `locus/play/models.py`에 있고, 경계 규칙상 play 안에만 둔다. 저장 텍스트는 영어다(C-1). 예외는 선언 서술의 표시 언어 판본이고, 그것은 `TurnRun` 결과와 타임라인에만 남는다.

## 1. 행적과 판단

### 1.1 `DeedKind` / `Deed`
```python
class DeedKind(str, Enum):
    ARRIVAL = "arrival"                 # 세션 시작 위치 + 이동 도착 (결정적 영어 문장)
    STATEMENT = "statement"             # 대화를 마칠 때, 그 대화의 새 플레이어 발언 요약 (영어 한 줄)
    DECLARED_ACTION = "declared_action" # 선언 서술의 영어 기록 (Q3=A)

class Deed(LocusModel):
    id: str = Field(default_factory=new_id)
    session_id: str
    player_id: str
    region_id: str                      # 행적이 일어난 지역 = 씨앗이 태어날 지역
    turn: int = Field(ge=0)             # 기록 시점의 세션 턴
    kind: DeedKind
    text: str = Field(min_length=1)     # 영어(LLM 없을 때의 선언만 예외, BR-U6-24)
    declaration: str | None = None      # DECLARED_ACTION: 플레이어가 입력한 원문(언어 무관, GM 확인용)
    messages_through: datetime | None = None  # STATEMENT: 요약에 넣은 마지막 플레이어 메시지 시각
    witnessed_npc_ids: list[str] = Field(default_factory=list)  # 도착·선언 = 그 지역 NPC 전원, 발언 = 대화 상대 한 명
    voided: bool = False
    voided_turn: int | None = None
    created_at: datetime | None = None  # 앱이 찍는다(`next_timestamp()`); 체류 구간의 순서 기준
```
- **체류(stay)**: 한 지역에 들어와 머무는 동안을 말한다. 플레이어의 가장 최근 `ARRIVAL` 행적부터 지금까지이고, 판단 대상의 창이 된다(A6-3, A-6). 세션 시작 위치도 `ARRIVAL` 행적을 남기므로 체류는 늘 정의된다.
- 행적은 세션 레이어에만 있고 캐노니컬 월드를 바꾸지 않는다(FR-C8).

### 1.2 `DeedAppraisal`
```python
class DeedAppraisal(LocusModel):
    id: str = Field(default_factory=new_id)
    session_id: str
    deed_id: str
    npc_id: str                         # 판단한 NPC (그 행적의 목격자여야 한다, BR-U6-8)
    noteworthy: bool
    salience: float = Field(ge=0.0, le=1.0)
    slant: str = ""                     # 한두 단어 시각 (예: "admiring", "suspicious"), 영어
    retelling: str = ""                 # 그 NPC가 남에게 옮길 문장, 영어. noteworthy=False면 ""
    turn: int = Field(ge=0)
    seeded_rumor_id: str | None = None  # 씨앗이 된 소문 (한 판단에 최대 하나, BR-U6-12)
    created_at: datetime | None = None
```
- `(deed_id, npc_id)`는 유일하다. 한 NPC는 한 행적을 한 번만 판단한다.
- Q1 섞은 방식은 저장 모양 하나로 표현된다. 발언은 목격자가 한 명이라 판단이 하나다. 도착과 선언은 대화한 목격자 수만큼 판단이 생긴다. 씨앗은 판단 단위로 태어난다.

### 1.3 `DeedView` (GM 읽기 모델)
```python
class DeedView(LocusModel):
    deed: Deed
    appraisals: list[DeedAppraisal]
    rumors: list[SessionRumor]           # 이 행적 기원 소문 전부(비활성 포함)
    reached_region_ids: list[str]        # rumors의 지역 집합, 정렬
```

## 2. 행동·서술·전파 값

### 2.1 `DeclareAction`
```python
class DeclareAction(LocusModel):
    type: Literal["declare"] = "declare"
    text: str = Field(min_length=1)      # 길이 상한(`declare_max_chars`)과 공백 검사는 서비스가 한다(400)

PlayerAction = Annotated[Union[MoveAction, WaitAction, EndTalkAction, DeclareAction], Field(discriminator="type")]
```
비용은 1턴이다(`action_cost`의 기본 갈래).

### 2.2 `Narration` (Q3=A)
```python
class Narration(LocusModel):
    text: str                            # 플레이어에게 보일 서술, 표시 언어
    record: str                          # 행적으로 남길 영어 한 문장
    lang: str
    llm_calls: int = Field(default=1, ge=0)   # LLM 없거나 실패하면 0 (BR-U6-24)
```

### 2.3 `SpreadTarget` (순수 계획의 출력)
```python
class SpreadTarget(LocusModel):
    region_id: str
    from_region_id: str
    weight: float = Field(ge=0.0, le=1.0)     # 원점에서의 도달 가중치 w(Y)
    degree: float = Field(ge=0.0, le=1.0)     # max(부모 왜곡도, 1 − w(Y))
    support: float = Field(ge=0.0, le=1.0)    # 부모 지지도 × 이 칸의 연결 가중치
```

### 2.4 `SessionRumor` 기원 필드 (추가만)
```python
origin_kind: Literal["canonical", "deed"] = "canonical"
origin_deed_id: str | None = None
origin_appraisal_id: str | None = None      # 어느 NPC 판본인지 (Q1 섞은 방식, §7 이탈 1)
spread_from_region_id: str | None = None    # 씨앗은 None, 전파는 부모 지역
```
- 씨앗은 `distorted_from_kind="deed"`, `distorted_from_id=deed.id`이다. 전파는 `distorted_from_kind="rumor"`, `distorted_from_id=부모 소문 id`이다.
- `is_session_origin(r) = r.origin_kind == "deed"`

### 2.5 결과·실행 기록 확장
- `ActionResult.declaration: Narration | None`: 선언 행동의 서술이다. 기존 `narration: list[str]`은 턴 요약 템플릿이라 이름이 겹치지 않게 따로 둔다.
- `TurnRun.lang: str | None`: 서술을 만들 표시 언어다. 선언 요청의 `?lang=`을 받아 배경 실행에 넘긴다.
- `TurnResult`에 `seeded_rumor_ids`·`spread_rumor_ids`를 더한다(`list[str]`). `RegionTurnChange.rumors_added`에도 함께 들어가므로 지역 알림은 그대로 뜬다.

## 3. 타임라인 (추가만; 페이로드에 `region_name`, FR-D3)
| 종류 | 언제 | 페이로드 |
|---|---|---|
| `ACTION_DECLARED` | 선언 서술 뒤 | `deed_id`, `region_id`, `region_name`, `narration`(표시 언어), `lang`, `record` |
| `DEED_RECORDED` | 발언 행적 기록 | `deed_id`, `kind`, `npc_id`, `npc_name`, `region_id`, `region_name` |
| `DEED_APPRAISED` | 판단 하나마다 | `deed_id`, `npc_id`, `npc_name`, `noteworthy`, `salience`, `region_id`, `region_name` |
| `DEED_SEEDED` | 씨앗 소문 탄생 | `deed_id`, `appraisal_id`, `npc_name`, `rumor_id`, `region_id`, `region_name` |
| `RUMOR_SPREAD` | 전파 한 칸 | `deed_id`, `rumor_id`, `from_region_id`, `from_region_name`, `region_id`, `region_name`, `weight`, `degree` |
| `DEED_VOIDED` | GM 취소 | `deed_id`, `rumor_ids`, `region_ids` |

- 도착 행적은 따로 줄을 남기지 않는다. `SESSION_STARTED`·`PLAYER_MOVED` 페이로드에 `deed_id`만 더한다. 이동마다 줄이 두 번 생기지 않게 하려는 것이다.

## 4. 포트·저장

### 4.1 `DeedStore` (`PlayUnitOfWork.deeds`, `PlayRepository`에 포함)
```python
class DeedStore(Protocol):
    def record_deed(self, deed: Deed) -> Deed: ...                 # created_at = next_timestamp()
    def get_deed(self, session_id: str, deed_id: str) -> Deed | None: ...
    def list_deeds(self, session_id: str, *, region_id: str | None = None,
                   include_voided: bool = True) -> list[Deed]: ... # (created_at, id) 순
    def update_deed(self, deed: Deed) -> Deed: ...                 # voided 표시; KeyError: 없음
    def save_appraisals(self, appraisals: list[DeedAppraisal]) -> list[DeedAppraisal]: ...
        # (deed_id, npc_id) 중복은 AppraisalExistsError(ValueError); 한 트랜잭션
    def list_appraisals(self, session_id: str, *, deed_ids: list[str] | None = None,
                        npc_id: str | None = None) -> list[DeedAppraisal]: ...
    def mark_seeded(self, session_id: str, appraisal_id: str, rumor_id: str) -> None: ...
```

### 4.2 `RumorStore` 추가
```python
def list_rumors_by_origin(self, session_id: str, *, deed_id: str | None = None,
                          include_inactive: bool = False) -> list[SessionRumor]: ...
    # origin_kind == "deed"만; deed_id로 좁힌다
```
취소는 새 메서드 없이 한다. `list_rumors_by_origin(deed_id=…)`로 소문을 읽고, `active=False`로 바꾼 뒤 `upsert_rumors`로 쓴다. 모두 한 UoW 안이다.

### 4.3 테이블 (PostgreSQL, 추가만; 인메모리 트윈 같은 계약)
- `deeds`
  - 열: `id` PK, `session_id` idx, `player_id`, `region_id`, `turn`, `kind`, `text`, `declaration` null, `messages_through` null, `witnessed_npc_ids` JSON, `voided` bool, `voided_turn` null, `created_at` not null(앱이 찍는다)
- `deed_appraisals`
  - 열: `id` PK, `session_id` idx, `deed_id` idx, `npc_id`, `noteworthy`, `salience`, `slant`, `retelling`, `turn`, `seeded_rumor_id` null, `created_at` not null
  - 제약: **`UNIQUE (deed_id, npc_id)`** 이름 `uq_deed_appraisals_deed_npc`
- `session_rumors` 열 추가
  - `origin_kind` not null default `'canonical'`, `origin_deed_id` null idx, `origin_appraisal_id` null, `spread_from_region_id` null
  - `ensure_play_schema`가 없으면 `ALTER TABLE … ADD COLUMN`을 실행한다. 선례와 같은 방식이고 기존 행은 `canonical`이 된다(A6-12).

## 5. 조정값 (`PlayTuning`, `Settings` env)
| 값 | 기본 | env | 쓰임 |
|---|---|---|---|
| `spread_min_weight` | 0.15 | `SPREAD_MIN_WEIGHT` | 도달 가중치가 이 값 미만이면 전파 대상이 아니다 |
| `deed_seed_min_salience` | 0.5 | `DEED_SEED_MIN_SALIENCE` | `noteworthy`여도 이 값 미만이면 씨앗이 되지 않는다 |
| `max_spread_per_region_turn` | 1 | `MAX_SPREAD_PER_REGION_TURN` | 한 지역이 한 턴에 받는 전파 소문 수 |
| `declare_max_chars` | 300 | `DECLARE_MAX_CHARS` | 선언 길이 상한(400) |
| `npc_max_deeds` | 5 | `NPC_MAX_DEEDS` | NPC 대화 컨텍스트에 넣는 자기 판단 행적 수 |
| `appraisal_max_deeds` | 8 | `APPRAISAL_MAX_DEEDS` | 판단 호출 한 번에 넣는 행적 수(최신 순, 넘으면 오래된 것이 대기로 남는다) |

모든 값은 `ge=0`이다. `declare_max_chars`만 `ge=1`이다.

## 6. 오류
| 상황 | 타입 | HTTP |
|---|---|---|
| 선언이 비었거나 너무 길다 | `InvalidActionError` | 400 |
| 행적이 없다 / 다른 세션 | `LookupError("deed not found: …")` | 404 |
| 턴 진행 중 취소 | `TurnInProgressError` | 409 |
| 닫힌 세션에 선언·취소 | `SessionClosedError` | 409 |
| 판단 중복(경합) | `AppraisalExistsError(ValueError)` | 내부 처리. 한쪽이 건너뛴다(BR-U6-10) |

## 7. 설계 이탈 (승인 때 함께 받는 것)
| # | 상위 산출물 | 이 설계 | 까닭 |
|---|---|---|---|
| 1 | P1 `SessionRumor`에 기원 필드 셋 | `origin_appraisal_id`를 더해 넷 | Q1 섞은 방식이다. 도착·선언은 NPC 판본마다 따로 퍼지므로 "(행적, 지역) 중복 없음"이 "(판단, 지역) 중복 없음"이 된다 |
| 2 | services §5.3 "`retelling` 원문의 소문 체인" | 씨앗은 소문 **하나**, 문장 = `retelling`, **LLM 0회** | NPC의 말이 이미 그 지역의 왜곡이다. 체인을 돌리면 턴 예산만 쓰고 NPC의 목소리를 지운다 |
| 3 | P6 `PlayService.act(Declare)`가 서술 뒤 `advance`, `act(EndTalk)`가 판단 뒤 `advance` | 서술과 판단은 **배경 실행 안**, 첫 턴 전 준비 단계에서 한다. 요청은 202로 곧바로 답한다 | 요청이 LLM을 최대 93초 기다리지 않게 한다. U4 Q4=A의 202 모델과 한 실행 = 한 가드를 지킨다 |
| 4 | P1 `Narration(text, llm_calls)` | `Narration(text, record, lang, llm_calls)` | Q3=A |
| 5 | 타임라인 다섯 종류 | `DEED_SEEDED`를 더해 여섯 | 씨앗(원점 탄생)과 전파(한 칸 이동)는 GM에게 다른 사건이다 |
| 6 | P2 `DeedStore.record/get/list_by_session/list_pending_by_region/save_appraisals/void`, `RumorStore.list_session_origin/deactivate_by_deed` | §4의 이름. 대기 행적은 서비스가 체류 구간으로 거른다. 취소는 읽고·바꾸고·쓰기다 | 체류 구간은 플레이어 위치와 도착 행적에 달린 규칙이라 저장소 질의보다 서비스에 둔다 |
| 7 | S2 조정값 넷 | `npc_max_deeds`·`appraisal_max_deeds`를 더해 여섯 | 프롬프트 두 곳의 크기를 묶는다(NFR-5) |
| 8 | P1 `Deed` 필드 | `declaration`·`messages_through`·`voided_turn`·`created_at`을 더했다 | GM 확인(선언 원문), 발언 요약 커서(경합에도 메시지를 놓치지 않음, BR-U6-6), 취소 기록 |
| 9 | FR-C8 "지역 도착" | 세션 시작 위치도 `ARRIVAL` 행적을 남긴다 | 체류 구간이 늘 정의되고, 시작 지역에서 한 선언도 판단 대상이 된다 |
| 10 | P19 `plan_spread(snapshot, rumor, reached, tuning)` | `plan_spread(snapshot, rumor, *, origin_region_id, reached, tuning)` | 도달 가중치를 원점부터의 최대 곱 경로로 계산하려면 원점이 필요하다(열을 더하지 않는다) |
| 11 | (없음) | `TurnRun.lang` | 배경 실행이 서술 언어를 알아야 한다 |

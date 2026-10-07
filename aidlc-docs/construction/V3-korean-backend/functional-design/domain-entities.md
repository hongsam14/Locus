# V3 한국어 표시 백엔드 — Domain Entities

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V3 Functional Design. 키 없이 연 데모가 처음부터 한국어로 보이게 하는 데 쓰는 자료의 모양을 정한다.

결정(계획 `construction/plans/V3-korean-backend-functional-design-plan.md`):

| 질문 | 답 | 내용 |
|---|---|---|
| Q1 | A | 고유명사는 음역에 지형 낱말만 옮긴다 |
| Q2 | A | 번역 파일에 영어 원문을 적고 해시는 읽을 때 계산한다 |
| Q3 | A | 검사는 CI에서 엄격, 실행에서 너그럽다 |
| Q4 | A | 매니페스트 이름과 `world.id`가 다르면 검사가 문제로 보고한다 |
| Q5 | A | 지역·NPC·씨앗·월드 번역은 월드 이름표 하나로 보낸다 |

---

## 1. 번역 종류와 필드 (정본)

번역 캐시의 키는 지금과 같다: `(source_kind, source_id, source_field, target_lang)`(`locus/localization/storage/schema.py:25-27`). `world_id`·`session_id`는 키가 아니라 표시다.

| 종류 `kind` | id | 필드 | 범위 표시 | 화면에 가는 길 | 상태 |
|---|---|---|---|---|---|
| `world` | 월드 id | `name`, `description` | 시딩한 행은 `world_id`, 월드 목록의 warm 행은 `None`. 그래서 월드 id(`ids`)로 지운다(BR-V3-13) | 월드 목록 `name_ko`·`description_ko`, 이름표 `world` | **새** |
| `region` | 지역 id | `name`, `description` | `world_id` | 이름표 `regions` | **새** |
| `npc` | NPC id | `name`, `role`, `description` | `world_id` | 이름표 `npcs` | **새** |
| `event_seed` | 씨앗 id | `title`, `description` | `world_id` | 이름표 `event_seeds` | **새** |
| `knowledge` | 지식 id | `statement`, `title` | `world_id` | 지금처럼 응답의 `statement_ko`·`title_ko` | 있음(설계 리뷰 R-07: 목록에 함께 적음) |
| `rumor`·`event`·`deed`·`deed_appraisal` | 세션 내용 id | 지금과 같음 | `session_id` | 지금과 같음 | 있음, 바꾸지 않음. 단 씨앗에서 시작한 사건의 `event` 행을 씨앗 번역에서 옮겨 쓴다(BR-V3-17) |

번역하지 않는 것:
- 엔티티 이름·설명, NPC `traits`, 지식 `topic`이다. 에디터에만 보이고, 에디터는 영어 원문을 고치는 자리다.
- 시간선 `summary`는 그대로 제외한다(BR-X1-25). 화면은 `payload`의 id로 이름표를 찾는다.

**빈 원문**: 원문이 비었거나 공백뿐인 필드는 번역 대상이 아니다. 시딩·검사·이름표 모두 건너뛴다.

## 2. `TranslationEntry` — `locus/shared/models/i18n.py` [새]

world(번역 파일을 읽음)와 localization(캐시에 넣음)이 함께 쓰므로 shared에 둔다(`component-dependency.md`). 두 경계는 서로 import하지 않는다.

```python
TranslationKind = Literal["world", "region", "npc", "event_seed", "knowledge"]

TRANSLATABLE_FIELDS: dict[TranslationKind, tuple[str, ...]] = {
    "world": ("name", "description"),
    "region": ("name", "description"),
    "npc": ("name", "role", "description"),
    "event_seed": ("title", "description"),
    "knowledge": ("statement", "title"),
}

def source_hash(text: str) -> str            # sha256(text.strip()), 지금의 localization 함수를 옮김

class TranslationEntry(LocusModel):          # 데모 번역 파일 한 줄
    kind: TranslationKind
    id: str = Field(min_length=1)
    field: str                               # TRANSLATABLE_FIELDS[kind] 안 (모델 검증)
    source: str = Field(min_length=1)        # 영어 원문 (Q2=A)
    text: str = Field(min_length=1)          # 번역문, strip 뒤 비지 않음

    @property
    def key(self) -> tuple[str, str, str]: ...        # (kind, id, field)
    @property
    def source_hash(self) -> str: ...                 # source_hash(self.source)

class TranslationFile(LocusModel):           # 데모 번역 파일 전체
    format: Literal["locus.translations"] = "locus.translations"
    version: Literal[1] = 1
    lang: str = Field(pattern=r"^[a-z]{2}$")
    world_id: str                            # 파일이 옮긴 World File의 world.id
    entries: list[TranslationEntry]

    @classmethod
    def parse(cls, data: object) -> TranslationFile   # 형식·버전이 다르면 ValueError
    def to_json(self) -> dict                          # parse(to_json(x)) == x (PBT-02)
```

- `lang`은 항목마다 두지 않고 파일에 한 번 둔다. 설계 초안(`component-methods.md` § 2)의 `TranslationEntry.lang`·`source_hash` 칸은 이렇게 바뀐다. 해시는 원문에서 계산한다(Q2=A).
- `source_hash`를 shared로 옮겨도 값은 그대로다. `locus.localization.service.source_hash`는 같은 함수를 다시 내보낸다. 그래서 이미 캐시에 있는 행이 그대로 맞는다.

## 3. 데모 번역 파일 — `locus/world/demo/worlds/<name>.<lang>.json` [새]

```json
{
  "format": "locus.translations",
  "version": 1,
  "lang": "ko",
  "world_id": "emberleaf",
  "entries": [
    {"kind": "world", "id": "emberleaf", "field": "name", "source": "Emberleaf Isle", "text": "엠버리프 섬"},
    {"kind": "region", "id": "region-saltwake", "field": "name", "source": "Saltwake Harbor", "text": "솔트웨이크 항구"},
    {"kind": "npc", "id": "npc-brisa", "field": "role", "source": "archer captain", "text": "궁수대장"}
  ]
}
```

- 항목 순서는 World File 순서다: `world` → `regions` → `npcs` → `event_seeds` → `knowledge`. 절 안은 파일 순서이고 필드는 표 § 1의 순서다. 이 순서는 사람이 읽기 위한 것이고, 뜻은 순서와 무관하다.
- Emberleaf ko 파일은 항목이 123개다.

  | 종류 | 계산 | 항목 수 |
  |---|---|---|
  | world | 1 × 2 | 2 |
  | regions | 12 × 2 | 24 |
  | npcs | 15 × 3 | 45 |
  | seeds | 3 × 2 | 6 |
  | knowledge | 23 × 2 | 46 |

  빈 원문이 있으면 그만큼 준다.
- 문체(Q1=A):
  - 고유명사는 음역하고 지형·직함 낱말만 옮긴다. 예: "솔트웨이크 항구", "아이언크래그", "브리사 대장".
  - 설명·지식·씨앗 문장은 뜻으로 옮기고 해라체로 쓴다. 이야기 줄의 문체가 해라체이기 때문이다(V2 Q2=A).
  - NPC 역할은 값 이름이라 마침표가 없다.

## 4. 매니페스트 항목의 새 칸 — `DemoInfo` (`locus/world/demo/__init__.py`)

```python
class DemoCardText(BaseModel):
    title: str = Field(max_length=60)
    description: str | None = Field(default=None, max_length=300)
    credits: str | None = Field(default=None, max_length=200)

class DemoInfo(BaseModel):
    ...                                                    # 지금 칸 그대로
    i18n: dict[str, DemoCardText] = {}                     # lang → 카드 문구 (Q4=A, 설계)
    translations: dict[str, str] = {}                      # lang → 매니페스트 폴더 기준 상대 경로
```

- 두 칸의 키는 `^[a-z]{2}$`이고 `en`이 아니다(원문 언어). 모델 검증으로 막는다.
- `i18n`은 매니페스트 항목의 일부다. 형식이 틀리면 지금 규칙대로 그 항목 전체가 빠진다(BR-U8-2). 영어 `title`이 틀린 것과 같은 취급이다.
- `translations`의 파일 문제는 항목을 빼지 않는다(Q3=A, BR-V3-10).

Emberleaf의 매니페스트 추가분:

```json
"i18n": {"ko": {"title": "엠버리프 섬", "description": "…", "credits": "…"}},
"translations": {"ko": "emberleaf.ko.json"}
```

## 5. `SeedReport` — localization

```python
class SeedReport(LocusModel):
    seeded: int = 0        # 캐시에 넣은 행
    stale: int = 0         # 원문이 지금 텍스트와 다른 항목(버림)
    unknown: int = 0       # 지금 월드에 그 (kind, id, field)가 없는 항목(버림)
```

## 6. API 응답 (가산, NFR-5)

### 6.1 이름표 `WorldNamesOut` [새] — `GET /api/world/worlds/{world_id}/names?lang=`

```python
class WorldNamesOut(BaseModel):
    world_id: str
    lang: str                                    # 실제로 쓴 표시 언어
    world: dict[str, str] = {}                   # {"name": …, "description": …} 중 번역된 것
    regions: dict[str, dict[str, str]] = {}      # region id → {field: 번역}
    npcs: dict[str, dict[str, str]] = {}
    event_seeds: dict[str, dict[str, str]] = {}
```

- 값은 번역문뿐이다. 영어 원문은 싣지 않는다. 화면은 id로 찾고, 없으면 자기가 가진 영어를 쓴다(BR-V3-21).
- `lang`이 원문 언어(`en`)이거나 번역이 꺼져 있으면 네 맵이 모두 비어 있다(200).
- 모양은 `{id: {field: text}}`다. 번역이 없는 필드는 키 자체가 없다(`null`이 아님). 번역이 하나도 없는 id도 맵에 없다.

### 6.2 기존 응답에 더하는 칸

| 응답 | DTO | 더하는 칸 | 채우는 곳 |
|---|---|---|---|
| `GET /api/world/demos?lang=` | `DemoInfoOut` | `title_ko`, `description_ko`, `credits_ko` | 매니페스트 `i18n[lang]`(번역 캐시와 무관) |
| `GET /api/world/worlds?lang=` | `WorldInfo` | `name_ko`, `description_ko` | 번역 캐시 `kind="world"` |
| `POST /api/world/worlds/{w}/demo/{name}` | `DemoLoadOut(ImportReport)` [새 이름, 같은 칸 + 둘] | `translations_seeded: int = 0`, `translations_stale: int = 0` | 시딩 보고 |
| `GET /api/play/sessions/{s}/region` | `RegionView` | `level_path_ids: list[str] = []` | 지역 경로의 id(지금 `level_path`는 이름만 있다) |

- `*_ko`라는 이름은 "기본 대상 언어" 칸이라는 뜻이다. 가정 A-2에 따라 이름은 그대로 둔다.
- 데모 목록과 월드 목록이 `?lang=`을 받는다. 이 값은 `display_lang`이 검사하고, `en`이면 칸이 `None`이다.

### 6.3 기록 `payload`에 더하는 id (가산)

| 기록 | 지금 | 더함 |
|---|---|---|
| `deed_seeded`(`locus/play/turn/advancer.py:885`) | `npc_name`만 | `npc_id` |

다른 기록 줄은 이름 옆에 이미 id가 있다(`region_id`, `from_region_id`/`to_region_id`, `npc_id`, `region_ids`, `seed_id`). 그래서 이름표로 찾을 수 있다.

## 7. 웹 타입 (V3는 타입과 API 함수만; 화면은 V4·V6·V8)

```ts
// web/src/types.ts
export interface WorldNames { world_id: string; lang: string; world: Record<string, string>;
  regions: Record<string, Record<string, string>>; npcs: Record<string, Record<string, string>>;
  event_seeds: Record<string, Record<string, string>> }
// DemoInfo += title_ko?, description_ko?, credits_ko?; WorldInfo += name_ko?, description_ko?
// RegionView += level_path_ids?: string[]
// web/src/api: worldNames(worldId): Promise<WorldNames>   (?lang= 는 지금 규칙대로 붙음)
```

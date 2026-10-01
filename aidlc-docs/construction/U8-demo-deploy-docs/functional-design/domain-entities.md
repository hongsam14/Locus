# U8 데모·배포·문서 — Domain Entities

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 기능 설계 중 데이터 정의입니다. 다음을 고정합니다.
- 데모 매니페스트 항목(데모는 데이터)
- 사건 씨앗 `EventSeed`
- 세션 안의 씨앗 상태
- LLM 유무 보고
- 새 데모 월드의 내용 명세
- 저장소 메타

근거
- 답: FD-U8 Q1=C(새 월드로 바꾼다), Q1-1=A(강·산맥의 변경 지방, 메이플스토리 참고), Q1-2=A(구조·분위기만, 이름은 새로), Q1-3=B(빅토리아 아일랜드 바탕), Q2=A(월드에 저장, GM [시작]), Q3=A([바로 플레이]+[에디터에서 보기]), Q4=A(서버가 알리고 화면이 미리 안내), Q5=A(CI, audit 0건), Q6=A(MIT)
- 설계 원칙 "데모는 데이터다"(플랜, 사람의 지적)
- 가정: 플랜 A8-1~12

## 1. 데모 매니페스트 항목 `DemoInfo` (`locus/world/demo`)
코드는 데모를 이 항목으로만 압니다(BR-U8-1). 매니페스트는 `locus/world/demo/worlds/manifest.json`(패키지 데이터)입니다.

| 필드 | 타입 | 뜻 |
|---|---|---|
| `name` | str (slug, `^[a-z0-9-]{1,40}$`) | 데모 이름. 불러올 때 기본 world id다 |
| `title` | str (≤ 60) | 카드 제목 |
| `description` | str (≤ 300) | 카드 설명 |
| `file` | str | World File 경로(매니페스트 폴더 기준) |
| `start_region_id` | str | [바로 플레이]가 세션을 시작하는 지역. 그 World File의 지역이고, 지나갈 수 있는 연결이 하나 이상 있어야 한다 |
| `credits` | str \| None (≤ 200) | 출처·영감 한 줄. 카드와 README에 보인다 |
| `sources` | `DemoSources` \| None | LLM 빌드 경로용 소스. 없으면 소스 빌드를 거절한다 |

`DemoSources`
| 필드 | 타입 | 뜻 |
|---|---|---|
| `memos` | list[str] | 메모 글 파일(UTF-8) 경로 |
| `maps` | list[str] | 구조 지도 JSON 경로(`WorldInputs.structured_maps` 형식) |
| `map_images` | list[str] | 지도 그림(PNG·JPEG·WebP) 경로. 빌드 때 base64로 읽는다 |

- 경로는 매니페스트 폴더 밖을 가리킬 수 없다(`..`·절대 경로 거절).
- 검사(조립 때 한 번): `DemoWorlds`를 만들 때 매니페스트를 읽어 항목마다 검사하고 결과를 둡니다. `list()`·`info()`는 그 결과를 돌려주고, 요청마다 World File을 다시 읽지 않습니다. 아래 중 하나라도 어긋나면 그 항목은 빠지고 경고 로그가 한 번 남습니다. 나머지 항목은 그대로 보입니다. 패키지 매니페스트에 잘못된 항목이 0개인지는 테스트가 지킵니다(BR-U8-2). 〔검토 01 R-09〕
  - 파일이 있고 World File로 읽힌다.
  - `start_region_id`가 그 파일의 지역이고, 지나갈 수 있는 연결이 있다.
  - `sources`의 경로가 있다.
- API 응답 `DemoInfo`(`GET /api/world/demos`)는 `name`, `title`, `description`, `credits`, `start_region_id`, `has_sources`를 줍니다. 파일 경로는 주지 않습니다.

## 2. 사건 씨앗 `EventSeed` (캐노니컬, `shared/models`)
월드에 속한 "일어날 법한 사건"입니다. GM이 세션에서 [시작]하면 사건이 됩니다(Q2=A).

| 필드 | 타입 | 뜻 |
|---|---|---|
| `id` | str | 씨앗 id(`seed-…`) |
| `world_id` | str | 월드 |
| `region_id` | str | 사건이 일어나는 지역(캐노니컬 지역 id) |
| `title` | str (1~80) | 짧은 이름. GM 목록과 타임라인 줄에 쓴다 |
| `description` | str (≤ 500) | 시작된 사건의 설명이 된다 |
| `category` | `EventCategory` | war · plague · politics · disaster · festival · discovery |
| `magnitude` | float [0, 1] | 시작된 사건의 크기 |
| `lifecycle` | `EventLifecycle` \| None | 없으면 시작할 때 분류 기본값(`CATEGORY_DEFAULT_LIFECYCLE`) |
| `provenance` | `Provenance` | 데모는 `source=input, generated_by=demo-author` |

- **enum 자리 옮김**: `EventCategory`, `EventLifecycle`, `CATEGORY_DEFAULT_LIFECYCLE`를 `play/models.py`에서 `shared/models/enums.py`로 옮깁니다. `play/models.py`는 같은 이름으로 다시 내보내서 호출처는 바뀌지 않습니다. 까닭은 World File(world 경계)이 씨앗을 검사해야 하는데, world는 play를 import할 수 없기 때문입니다(경계 규칙).
  - 〔검토 01 R-07〕 `shared/models/enums.py`는 "shared 어휘는 어느 경계의 개념도 모른다"(FR-A2)를 적고 있습니다. 사건 분류·수명은 이제 월드 데이터(씨앗)의 어휘이기도 하므로 FR-A2의 **의도된 예외**로 기록합니다. 그 파일 docstring에 한 줄로 남깁니다.
- **World File**: 선택 절 `event_seeds: list[EventSeed]`(기본 `[]`)를 둡니다.
  - `format_version`은 1 그대로입니다. 옛 읽기는 모르는 키를 무시하고, 새 읽기는 옛 파일에서 `[]`를 얻습니다.
  - `SECTIONS`에 더하고, 내보내기는 id 순으로 씁니다.
  - 재매핑(A2)은 씨앗 id를 다른 절과 같은 규칙으로 바꾸고, `region_id`는 지역 재매핑을 따라갑니다.
  - 참조 검사: `region_id`가 파일에 없는 씨앗은 빼고 error 경고를 남깁니다(BR-U2-5와 같음).
- **저장**: 그래프 노드 라벨 `EventSeed`에 모델 속성을 그대로 둡니다. 엣지는 없고, 지역은 `region_id` 속성으로 가리킵니다. 검색 문서와 번역은 없습니다.
- **바뀌는 곳**(〔검토 01 R-07〕)
  - 저장소: `neo4j_repo.NODE_LABELS`에 `EventSeed`(id 유일 제약, world_id 색인). 이미 떠 있는 Neo4j는 `locus init-schema --world`를 다시 돌려야 제약이 생긴다(operations.md에 적는다). 인메모리 가짜는 라벨 목록이 없어 그대로다.
  - 매핑·쓰기: `graph_mapping`에 `seed_to_node`·`node_to_seed`, `persist_graph(…, seeds=)`.
  - 읽기: 로더의 `nodes("EventSeed", …)` → `WorldSnapshot.event_seeds`.
  - World File: `schema.SECTIONS`·`WorldFile.event_seeds`, `remap`의 `file_ids`·`set_world_id`·재매핑·`validate_references`, `export.sort_sections`, 불러오기의 쓰기.
- **읽기**: `WorldSnapshot.event_seeds: list[EventSeed]`. 로더가 라벨을 읽습니다.
- **삭제**
  - 월드 삭제·교체는 world_id로 모든 노드를 지우므로 씨앗도 지워집니다(지금 그대로).
  - 에디터의 지역 삭제는 그 지역의 씨앗을 지웁니다(BR-U8-14). `RegionDeletePlan`·`RegionDeleteReport`에 `seed_ids`·`seeds_deleted`를 더합니다.
- **편집**: U8에서는 에디터가 씨앗을 고치지 않습니다(범위 밖). 고치려면 World File을 고쳐 불러옵니다.

## 3. 세션 안의 씨앗 상태 `SeedView` (읽기 모델, 저장하지 않음)
| 필드 | 뜻 |
|---|---|
| `seed` | `EventSeed` |
| `region_name` | 지역 이름(사라진 지역이면 id, U7 C4 규칙) |
| `running_event_id` | 이 세션에서 이 씨앗으로 시작해 아직 해소되지 않은 사건의 id. 없으면 None |

- 씨앗으로 시작한 사건은 `SessionEvent.provenance = {source: input, generated_by: "seed", refs: [seed_id]}`입니다. 세션 표에 열을 더하지 않습니다. 그래서 저장 스키마는 바뀌지 않습니다.
- `running_event_id`는 그 세션의 사건 중 `provenance.generated_by == "seed"`이고 `seed.id ∈ provenance.refs`이며 RESOLVED가 아닌 것의 id입니다.

## 4. LLM 유무 `Capabilities` (`GET /api/capabilities`)
| 필드 | 뜻 |
|---|---|
| `llm` | 대화·서술·소문 생성·사건 제안·빌드·NPC 초안·번역에 쓰는 LLM 공급자가 있다 |
| `vlm` | 지도 그림 읽기 공급자가 있다 |
| `embedding` | 임베딩 공급자가 있다(빌드·보강의 wiki 검색) |

- 값은 기동 때 조립한 공급자에서 읽습니다. 요청마다 바뀌지 않습니다.
- `/health`의 `status`는 바꾸지 않습니다. 키가 없어도 경계가 모두 떠 있으면 `ok`입니다.

## 5. 새 데모 월드 내용 명세 (Q1=C, Q1-1=A, Q1-2=A, Q1-3=B)
빅토리아 아일랜드의 구조와 분위기(숲 위 마법사 마을, 버섯 초원의 궁수 마을, 바위산의 전사 마을, 뒷골목 도시, 신참이 내리는 항구, 깊은 동굴 위 마을, 봉인된 마법사 전설)를 빌립니다. 이름과 글은 모두 새로 짓습니다(BR-U8-10). 원작에 없는 강 Glimmerrun을 그려 넣어 "소문이 강을 따라 빨리, 막힌 길을 돌아 느리게"가 보이게 합니다. 이름과 장소는 게이트에서 바꿀 수 있습니다.

| 항목 | 값 |
|---|---|
| 매니페스트 `name` / world id | `emberleaf` |
| `title` | Emberleaf Isle |
| `description` | An island of tree-top mages, meadow archers, cliff warriors and harbor rogues, split by the Stonebrow cliffs and joined by the Glimmerrun river. |
| `credits` | An original world inspired by the structure and mood of MapleStory's Victoria Island. Not affiliated with Nexon. |
| `start_region_id` | `region-saltwake` |
| 글 언어 | 영어(A8-2, US-9.1 "저장 텍스트는 영어"). 키가 있으면 한국어 표시는 번역 캐시가 맡는다 |
| `sources` | `emberleaf/memo.md`(설정 글), `emberleaf/map.json`(구조 지도). 지도 그림은 없다 |

### 5.1 지역 (12, 계층 3단)
| id | 이름 | 단계 | 부모 | 성격 |
|---|---|---|---|---|
| region-emberleaf | Emberleaf Isle | continent | — | 섬 전체 |
| region-greenreach | Greenreach | province | emberleaf | 서쪽 숲과 초원. Glimmerrun이 흐른다 |
| region-stonebrow | Stonebrow | province | emberleaf | 동쪽 바위 고원 |
| region-saltmarch | Saltmarch | province | emberleaf | 남쪽 해안과 저지대 |
| region-sylvarch | Sylvarch | town | greenreach | 거목 꼭대기의 마법사 마을. Glimmerrun의 샘 |
| region-ambermeadow | Ambermeadow | town | greenreach | 버섯 밭이 펼쳐진 궁수 마을 |
| region-ironcrag | Ironcrag | town | stonebrow | 바위 위 전사 마을 |
| region-ashen-dig | Ashen Dig | town | stonebrow | 옛 문명을 파는 발굴지 |
| region-saltwake | Saltwake Harbor | town | saltmarch | 신참이 배에서 내리는 항구(시작 지역) |
| region-gutterlight | Gutterlight | town | saltmarch | 운하와 뒷골목의 도적 도시 |
| region-hollowdeep | Hollowdeep | town | saltmarch | 깊은 동굴 위의 조용한 마을 |
| region-sunstrand | Sunstrand | town | saltmarch | 항구 옆 해변 |

### 5.2 연결 (10쌍, 쌍마다 두 방향)
무게 → 이동 턴은 `clamp(ceil(1/w), 1, 5)`, 합의는 `w ≥ 0.5` 그대로·`0.15 ≤ w < 0.5` 전해 들음(KnowledgeTuning 기본값)입니다.

| # | 두 지역 | 종류 | 무게 | 턴 | 뜻 |
|---|---|---|---|---|---|
| 1 | Sylvarch – Ambermeadow | river | 1.0 | 1 | Glimmerrun 상류. 소식이 강을 타고 하루에 닿는다 |
| 2 | Ambermeadow – Saltwake Harbor | river | 1.0 | 1 | Glimmerrun 하류 |
| 3 | Saltwake Harbor – Gutterlight | route | 0.6 | 2 | 항구 길 |
| 4 | Saltwake Harbor – Sunstrand | adjacent | 0.8 | 2 | 해변 |
| 5 | Gutterlight – Hollowdeep | route | 0.5 | 2 | 운하 너머 숲길 |
| 6 | Sylvarch – Hollowdeep | route | 0.4 | 3 | 깊은 숲 오솔길(전해 들음 수준) |
| 7 | Gutterlight – Ironcrag | route | 0.34 | 3 | Dustroad. 바위산으로 가는 유일하게 열린 먼 길 |
| 8 | Ironcrag – Ashen Dig | adjacent | 0.8 | 2 | 고원 안 |
| 9 | Ambermeadow – Ironcrag | blocked | 0.2 | — | 무너진 절벽길. 가까워 보이지만 막혔다 |
| 10 | Hollowdeep – Ashen Dig | blocked | 0.2 | — | 봉인된 지하 통로 |

- 시작 지역에서 지나갈 수 있는 연결로 8개 마을에 모두 닿습니다. 막힌 두 쌍은 각각 돌아가는 길이 있습니다(9 → 2·3·7, 10 → 5·3·7·8).
- 의도한 결과(BR-U8-11). 〔검토 01 R-04〕 세 계산이 서로 다른 그래프를 씁니다.
  - **합의**(지식, `compute_consensus`)와 **사건 번짐**(`propagate_delta`)은 막힌 연결을 포함한 **모든 연결**에서 최대 곱 경로 무게를 씁니다. 합의는 `≥ 0.5` 그대로, `0.15~0.5` 전해 들음입니다. 사건은 `≥ 0.15`인 지역에 `크기 × 0.3 × 무게`만큼 번집니다.
  - **행적 확산**(`plan_spread`)은 **지나갈 수 있는 연결만** 쓰고 턴마다 한 칸 갑니다.
  - 마을 지식(DIRECT)만 이웃으로 퍼집니다. 지방(Greenreach 등)에 붙은 지식은 그 아래 마을이 물려받을 뿐 연결을 타고 퍼지지 않습니다.

  모든 연결 기준 최대 곱 무게(설계 값, 테스트가 단언한다)

  | 출발 \ 도착 | Sylvarch | Ambermeadow | Saltwake | Gutterlight | Sunstrand | Hollowdeep | Ironcrag | Ashen Dig |
  |---|---|---|---|---|---|---|---|---|
  | Ambermeadow | 1.0 | — | 1.0 | 0.6 | 0.8 | 0.4 | 0.204 | 0.163 |
  | Saltwake | 1.0 | 1.0 | — | 0.6 | 0.8 | 0.4 | 0.204 | 0.163 |
  | Gutterlight | 0.6 | 0.6 | 0.6 | — | 0.48 | 0.5 | 0.34 | 0.272 |
  | Ashen Dig | 0.163 | 0.163 | 0.163 | 0.272 | 0.131 | 0.2 | 0.8 | — |
  | Ironcrag | 0.204 | 0.204 | 0.204 | 0.34 | 0.163 | 0.17 | — | 0.8 |

  - 그래서 강 마을 셋(Sylvarch, Ambermeadow, Saltwake)은 서로의 마을 지식을 그대로 압니다. Ironcrag는 Saltwake·Gutterlight·Hollowdeep·Sunstrand의 마을 지식을 전해 들음으로만 압니다. 〔Step 1.2 정정〕 정확히는 표의 Ironcrag 줄에서 0.15 이상 0.5 미만인 마을 모두(Sylvarch·Ambermeadow·Saltwake 0.204, Gutterlight 0.34, Sunstrand 0.163, Hollowdeep 0.17)이고, Ashen Dig(0.8)는 그대로 압니다. 테스트는 표 값에서 계산한다(FD 검토 02 R-13).
  - 지나갈 수 있는 연결만 쓰면 Ambermeadow 출발 무게는 위 첫 줄과 같습니다(막힌 연결이 최대 경로에 쓰이지 않음). 행적 소문은 Ambermeadow에서 1턴에 Saltwake·Sylvarch, 2턴에 Gutterlight·Sunstrand·Hollowdeep, 3턴에야 Ironcrag(0.204)에 닿을 수 있습니다. 3턴째 도달은 support에 달려 있으므로(business-logic-model §7) 단언은 "3턴 전에는 없다"입니다.
- 1·2·9번 연결의 `wiki_prior_ref`는 아래 prior를 가리킵니다.

### 5.3 NPC (15, 마을마다 1~3, 지방·섬 0)
| 마을 | NPC (역할) |
|---|---|
| Sylvarch | Archmage Elowen(마법사 장로), Pip(말 많은 견습생) |
| Ambermeadow | Captain Brisa(궁수 대장), Tobbin(버섯 농부) |
| Ironcrag | Chief Durgan(전사 족장), Ketta(대장장이) |
| Ashen Dig | Foreman Rusk(발굴 감독) |
| Saltwake Harbor | Harbormaster Olin(항만장), Pell(나룻배 선장), Nessa(여관 주인) |
| Gutterlight | Vex(등불 길드 우두머리), Marlo(장물아비) |
| Hollowdeep | Warden Ysolde(깊은 문의 파수꾼), Old Fenn(은자) |
| Sunstrand | Coral(해변 안내인) |

### 5.4 지식 (뼈대)
- 전역 1~2: 옛 창건자 다섯이 "재의 마법사(the Ashen Sorcerer)"를 섬 아래에 봉인했다. 배는 Saltwake로만 들어온다.
- 지방마다 1~2(그 아래 마을이 물려받음): Greenreach의 강과 거목, Stonebrow의 절벽과 자부심, Saltmarch의 무역과 밀수.
- 마을마다 DIRECT 2개 이상. 그 마을만 아는 일이고, 소문거리가 될 만한 것이 셋 이상 있습니다(예: Ambermeadow의 버섯에 번지는 얼룩, Ashen Dig에서 나온 봉인 문양, Gutterlight 길드의 내분).
- 엔티티 8 안팎: 지형(Glimmerrun River, Stonebrow Cliffs), 인물(장로·족장·우두머리), 물건(봉인 문양 조각).
- wiki prior 2: `prior-river-news`(강은 장사와 소식을 빨리 나른다), `prior-collapsed-road`(무너진 산길은 마을을 고립시킨다).

### 5.5 사건 씨앗 (3)
| id | 지역 | 분류 | 크기 | 수명 | 제목 |
|---|---|---|---|---|---|
| seed-mushroom-blight | Ambermeadow | plague | 0.5 | (기본) persistent | Blight in the mushroom fields |
| seed-sealed-relic | Ashen Dig | discovery | 0.6 | (기본) one_shot | A sealed relic unearthed |
| seed-lantern-feud | Gutterlight | politics | 0.4 | (기본) persistent | The Lantern Guild splits |

- 씨앗 셋은 서로 다른 지방에 있습니다. 〔검토 01 R-04〕 위 무게표 그대로 번지는 모양이 다릅니다.
  - 마름병(Ambermeadow): 강을 따라 Sylvarch·Saltwake에 그대로(1.0) 번지고, 절벽 너머 Ironcrag(0.204)·Ashen Dig(0.163)에는 약하게 닿습니다.
  - 유물(Ashen Dig): 고원 안 Ironcrag(0.8)에서 강하고, 평지로는 약하게(0.16~0.27) 번지며, Sunstrand(0.131)에는 닿지 않습니다.
  - 내분(Gutterlight): 길을 따라 항구·강 마을에 중간 세기(0.6)로 번집니다.

### 5.6 옛 Aldermoor
- 패키지 데모에서 빠집니다. World File과 소스(`memo.txt`, `map.json`, `map.png`, `generate_map.py`)는 `tests/fixtures/aldermoor/`로 옮겨 테스트 입력으로 씁니다(A8-12).
- `examples/` 폴더는 지웁니다. README가 데모 패키지 폴더를 안내합니다.

## 6. 저장소 메타 (Q6=A, A8-5)
| 항목 | 값 |
|---|---|
| `LICENSE` | MIT 그대로 |
| `pyproject.toml` `license` | `{ text = "MIT" }`. 〔검토 01 R-01〕 문자열 `"MIT"`(PEP 639)는 setuptools 77 이상에서만 유효한데 build-system 하한은 61이다. 하한을 올리지 않고 표 형식을 쓴다 |
| `pyproject.toml` `description` | "A solo TRPG: build a world from lore notes, then live in it as rumors and events spread along the terrain and each region's NPCs know different things." (§0 문장의 영어판) |
| `pyproject.toml` `urls` | Repository = 원격 저장소 주소 |
| `requirements.txt` | `pyproject.toml`의 `dependencies`와 같은 이름·버전 조건 |
| README 첫 줄 | §0 문장(한국어) |
| `CLAUDE.md` Project Overview | §0 문장으로 바꾼다 |

# U8 데모·배포·문서 — Business Logic Model

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 기능 설계 중 흐름입니다. 다음을 정합니다.
- 데모를 데이터로 다루는 방법
- 원클릭으로 플레이에 들어가는 흐름
- 사건 씨앗을 시작하는 흐름
- 키 없이 둘러보기
- 문서·메타 정합과 CI
- 라이브 시나리오

데이터는 `domain-entities.md`, 규칙 번호는 `business-rules.md`(BR-U8-n)를 봅니다.

## 1. 데모는 데이터다 (설계 원칙, A8-11)
### 1.1 백엔드 `DemoWorlds`
| 연산 | 동작 |
|---|---|
| `list()` | 조립 때 한 번 읽고 검사한 결과(domain-entities §1)에서 통과한 항목을 돌려줍니다. 요청마다 다시 읽지 않습니다 〔검토 01 R-09〕 |
| `info(name)` | `list()`에서 찾습니다. 없으면 `LookupError` → 404 |
| `load(name, world_id, replace)` | 항목의 World File을 `WorldFileImporter`로 불러옵니다. LLM 0회(BR-U2-28) |
| `build_from_sources(name, world_id, replace, include_map)` | 항목에 `sources`가 없으면 `LookupError("no sources for demo world")` → 404. 있으면 메모 글·구조 지도를 읽고, `include_map`이면 지도 그림을 base64로 읽어 `WorldInputs(name=title, description=description)`를 만든 뒤 `WorldBuilder.build`에 넘깁니다 |

- 지금의 Python 상수(`_DEMO_MEMO`, `_DEMO_MAP`)와 `load_demo_world()`, 패키지 밖 `examples/` 경로, `name != "aldermoor"` 검사를 지웁니다.
- 〔검토 01 R-10〕 이름이 남은 도움말·docstring도 고칩니다: `locus/__main__.py`의 `--demo-sources` 도움말("bundled Aldermoor sources")과 `--name` 도움말("e.g. aldermoor"), `locus/world/npc_drafts.py:112`의 예시("Aldermoor > Riverton" → 일반 예시).
- 소스 파일은 패키지 데이터(`locus/world/demo/worlds/<name>/…`)라 Docker 이미지에도 들어갑니다. 〔검토 01 R-01〕 `package-data`는 `world/demo/worlds/*.json`과 `world/demo/worlds/*/*`로 한 단계씩 적습니다(`**`는 setuptools 62.3 이상이 필요한데 하한은 61이다). 비편집 설치(이미지)에 소스 폴더가 들어갔는지는 Infra-light의 이미지 확인 항목이 봅니다.

### 1.2 CLI
| 명령 | 동작 |
|---|---|
| `locus world demo --list` | 그대로(매니페스트 목록) |
| `locus world demo --name <n> --world <id>` | 그대로 |
| `locus world build --world <id> --demo <n>` | **바뀜**. `--demo-sources`(Aldermoor 전용)를 `--demo <n>`으로 바꿉니다. 그 데모의 `sources`로 빌드합니다 |
| `locus build-world --world <id> --demo` | 옛 별칭은 한 주기 동안 남습니다. 매니페스트에서 `sources`가 있는 첫 항목을 씁니다 |

### 1.3 웹
- `HomePage`의 `DEMO` 상수, `loadDemo`의 기본 이름, 쓰지 않는 `buildWorldDemo`(`/demo/aldermoor/build`)를 지웁니다.
- `AppNav`의 `"aldermoor"` 기본값을 지웁니다. 월드가 정해지지 않은 화면에서 에디터 링크는 `/`로 갑니다.
- 데모는 `api.listDemos()`로만 찾습니다(§2).

### 1.4 옛 Aldermoor
- World File과 소스는 `tests/fixtures/aldermoor/`로 옮깁니다. Aldermoor를 일반 입력으로 쓰던 테스트(World File 왕복, 지역 삭제, API, CLI)는 그 파일을 씁니다.
- 데모 자체를 확인하는 테스트(`test_demo`, 홈 화면)는 새 매니페스트와 `emberleaf`로 바꿉니다(`# U8 intended change`).

## 2. 원클릭 (Q3=A)
### 2.1 카드
- `/`는 `listDemos()`가 돌려준 항목마다 카드를 그립니다. 월드가 있든 없든 그립니다(BR-U8-19).
- 카드에는 제목, 설명, `credits`, [바로 플레이], [에디터에서 보기]가 있습니다.
- 그 데모의 world id는 항목 `name`입니다. 카드는 `listWorlds()`로 그 id의 월드가 이미 있는지 압니다.

### 2.2 [바로 플레이]
```
월드 있음?
├─ 아니오 → 불러오기(replace=true, confirm=false)
└─ 예    → 고르기: [지금 월드로 플레이] [새로 불러와 플레이] [취소]
             └─ [새로 불러와] → "교체합니다" 확인 → 불러오기(confirm=false)
불러오기가 409(열린 세션 N개) → "열린 세션 N개를 닫습니다" 확인 → 불러오기(confirm=true)
→ 세션 시작(start_region_id, 플레이어 이름 = 화면 언어의 기본 이름) → /play/:sessionId
```
- 플레이어 이름의 기본값은 i18n `demo.playerName`(ko "여행자", en "Traveler")입니다. 이름은 이 흐름에서 묻지 않습니다(한 번 누르기).
- 어느 단계에서 실패하면 그 카드에 오류를 보이고 멈춥니다. 이미 된 단계는 되돌리지 않습니다. 불러온 월드는 아래 목록에 나타납니다(BR-U8-22).
- 〔검토 01 R-03〕 실패로 보는 것
  - HTTP 오류(4xx·5xx).
  - 불러오기 응답 `ImportReport.ok == false`. 저장 중 예외(`stage="commit"`)와 참조 검사로 빠진 항목이 이렇게 옵니다. 카드에 error 경고 앞 3개와, 있으면 백업 경로를 보이고 세션을 시작하지 않습니다.
  - 409의 두 모양. `open_sessions`가 있으면 닫기 확인으로 갑니다. `busy_sessions`가 있으면(턴이 도는 세션) 확인 없이 "턴이 도는 세션이 있어 지금은 바꿀 수 없습니다. 잠시 뒤 다시 누르세요"를 보입니다.
- 〔검토 01 R-03〕 [지금 월드로 플레이]에서 세션 시작이 시작 지역 없음(404·400)으로 실패하면, 카드는 "이 월드에는 데모의 시작 지역이 없습니다(편집됨)"와 [새로 불러와 플레이]를 보입니다.
- LLM이 필요 없습니다. 불러오기와 세션 시작 모두 LLM 0회입니다.

### 2.3 [에디터에서 보기]
- 월드가 있으면 다시 불러오지 않고 `/editor/:id`로 갑니다(BR-U8-21).
- 없으면 불러온 뒤 갑니다.
- 다시 불러오기는 [바로 플레이]의 [새로 불러와]나 에디터의 World File 막대가 맡습니다.

## 3. 사건 씨앗 (Q2=A)
### 3.1 저장 경로
| 경로 | 씨앗 |
|---|---|
| World File 불러오기·데모 불러오기 | `event_seeds` 절을 검사·재매핑한 뒤 `EventSeed` 노드로 씁니다 |
| World File 내보내기 | 스냅샷의 씨앗을 `event_seeds`로 씁니다 |
| 자료로 빌드(LLM) | 씨앗을 만들지 않습니다. `replace`면 월드를 지우므로 옛 씨앗도 사라집니다 |
| 월드 교체·삭제 | world_id로 함께 지워집니다 |
| 에디터 지역 삭제 | U3 삭제 순서의 ③(스코프) 뒤, ④(NPC) 앞에 "그 지역의 씨앗 삭제"를 둡니다. 그래프 삭제 하나이고, 재시도 계획은 남은 씨앗을 다시 찾습니다(BR-U8-14) |

### 3.2 GM 읽기 `GET /api/gm/sessions/{sid}/seeds`
1. 세션을 읽습니다(없으면 404). 닫힌 세션도 읽을 수 있습니다.
2. 세션 월드의 스냅샷에서 `event_seeds`를 읽습니다.
3. 세션 사건 목록에서 씨앗마다 `running_event_id`를 계산합니다(domain-entities §3).
4. `SeedView` 목록을 제목 순으로 돌려줍니다.

### 3.3 GM 시작 `POST /api/gm/sessions/{sid}/seeds/{seed_id}/start` → 201 `EventOut`
〔검토 01 R-06〕 씨앗 읽기와 시작은 새 서비스 `SeedService`(`locus/play/event/seeds.py`, 단일 책임)가 맡습니다. `play/wiring.py`가 `EventService`와 스냅샷 원천을 주입해 `PlayContainer.seeds`로 둡니다. 응답 모델은 기존 사건 라우트와 같은 `EventOut`이고, 새로 만든 것이므로 201입니다.

GM 쓰기 리스 아래에서 다음을 차례로 확인합니다(BR-U8-15·16).
1. 세션이 열려 있다. 닫혔으면 409 `session is closed`.
2. 턴이 돌고 있지 않다. 돌고 있으면 409 `turn in progress`(리스 규칙 그대로).
3. 씨앗이 세션 월드에 있다. 없으면 404.
4. 씨앗 지역이 월드에 있다. 없으면 404(지역 삭제가 씨앗을 지우므로 보통 일어나지 않는 방어).
5. 이 씨앗으로 시작해 해소되지 않은 사건이 없다. 있으면 `SeedAlreadyRunningError`(`locus/play/errors.py`의 새 클래스, `api/errors.py`에서 409로 매핑) `seed already running`.
6. `EventService.create_event`로 ACTIVE 사건을 만듭니다. 〔검토 01 R-06〕 지금 서명은 provenance를 `SIMULATION/gm:event`로 고정하고 타임라인 payload를 받지 않으므로, 키워드 인자 둘을 더합니다: `provenance: Provenance | None = None`(없으면 지금 값), `timeline_extra: Mapping[str, str] | None = None`(payload에 합침). 기존 호출처는 바뀌지 않습니다.
   - `description`은 씨앗 설명입니다.
   - `lifecycle`은 씨앗 값이고, 없으면 분류 기본값입니다.
   - `provenance`는 `{source: input, generated_by: "seed", refs: [seed_id]}`입니다.
   - 타임라인 `event_created` 줄의 payload에 `seed_id`·`seed_title`을 더합니다. 화면 문구는 "씨앗 사건 시작: {seed_title}"입니다.
- 그 뒤 사건은 수동으로 만든 사건과 똑같이 움직입니다. 턴마다 지역 왜곡도가 바뀌고, 지형을 따라 번지고, 해소되면 복원됩니다. LLM은 0회입니다.
- 해소된 뒤에는 같은 씨앗을 다시 시작할 수 있습니다.

## 4. 키 없이 둘러보기 (Q4=A, US-1.4, NFR-4)
### 4.1 서버
- `GET /api/capabilities` → `{llm, vlm, embedding}`. 기동 때 조립한 공급자에서 읽습니다. 화면은 `llm`만 씁니다. `vlm`·`embedding`은 알림용입니다(지도 그림 읽기와 wiki 검색이 꺼졌는지 운영자가 볼 수 있게).
- 〔검토 01 R-02〕 LLM이 필요한 경로와 그 근거(지금 코드 기준). 공급자가 없으면 모두 503이고 500이 아니어야 합니다(BR-U8-24).

  | 경로 | 의존 | 지금 |
  |---|---|---|
  | `POST /api/world/worlds/{w}/build`, `…/build/upload` | `WorldContainer.builder` | `_need` → 503 |
  | `POST …/demo/{n}/build` | `builder` | `_need` → 503 |
  | `POST …/regions/{r}/npc-drafts` | `npc_drafts` | None 검사 → 503 |
  | `POST /api/gm/sessions/{s}/regions/{r}/rumors`, `…/rumors/regen` | 소문 서비스의 LLM | `LlmUnavailableError` → 503 |
  | `POST /api/gm/sessions/{s}/events/suggest` | 사건 서비스의 LLM | `LlmUnavailableError` → 503 |
  | `POST /api/play/sessions/{s}/npcs/{n}/start`, `…/say` | 대화 서비스의 LLM | `LlmUnavailableError` → 503 |

  - LLM이 필요 없는 경로는 키 없이 503도 500도 아니어야 합니다. `priors`(wiki 관리, 임베딩만), 보강 Q&A, 데모·World File, 에디터, 세션·이동·턴, 씨앗이 여기에 듭니다. `POST …/priors`는 LLM 경로가 아닙니다(검토 01 R-02, 목록에서 뺐다).
  - 테스트(TP-U8-8)는 공급자 없이 조립한 앱에서 위 표의 경로가 503이고, 키 없이 쓰는 대표 경로(데모 불러오기, 세션 시작, 이동 턴, 씨앗 시작, 보강 시작)가 2xx임을 봅니다.
  - 코드를 고칠 때 이 표 밖의 LLM 사용처(공급자가 None인데 `RuntimeError`가 새는 곳)가 나오면 같은 503 규칙으로 막고 표에 더합니다.
- 턴은 LLM 없이 돕니다. 선언 서술과 턴 안의 LLM 단계는 `llm_failed`로 알립니다(U4~U6 그대로).
- 보강 Q&A는 LLM 없이 템플릿으로 돕니다(U3 그대로).
- 번역 읽기는 캐시만 읽습니다. 키가 없으면 원문을 보입니다(X1 그대로).

### 4.2 화면
- 앱이 뜰 때 `capabilities`를 한 번 읽어 모듈 안에 둡니다. 읽기에 실패하면 "모름"으로 두고, 안내와 끄기를 하지 않습니다. 서버의 503이 마지막 방어입니다(BR-U8-26).
- `llm=false`이면 아래와 같이 합니다.
  - `/`, 에디터, GM 화면 머리에 한 줄 안내를 둡니다. 무엇이 꺼졌는지와 `.env`의 `OPENAI_API_KEY`를 넣고 다시 띄우면 켜진다는 것을 적습니다.
  - LLM 버튼을 끄고 까닭("LLM 키가 필요합니다")을 붙입니다. 대상은 빌드 패널 [만들기], NPC [초안], GM [사건 제안], 소문 [생성]·[전체 생성]·[재생성]·[전체 재생성]입니다. 대화는 지금처럼 세션 보기의 `llm_available`을 씁니다.
  - LLM이 필요 없는 것은 그대로 켜 둡니다. 데모 불러오기, 지도, 에디터 편집, World File, 보강 Q&A, 이동, 턴, 씨앗 시작, GM 수동 사건·왜곡도·지지도가 여기에 듭니다.
- 503을 받은 화면의 문구는 "LLM 키가 필요합니다"입니다(BR-U8-27).

## 5. 문서·메타 정합 (H1~H4)
| 대상 | 할 일 |
|---|---|
| README | 전면 다시 씁니다(A8-1). 순서: §0 문장 → 6단계 흐름(자료 넣기 → 월드 자동 구성 → 에디터에서 다듬기 → 세션·이동·대화 → 선언·사건 → 소문이 지형을 따라 퍼지고 지역마다 다르게 듣기) → 스크린샷 자리 → 시작 명령(`.env` 두 값, `docker compose --profile service up -d`, `:3000`, [바로 플레이]) → 키 없이 둘러보기 → 진행 중 기능 표 → 개발(테스트·게이트) → 디렉터리 → 라이선스(MIT)와 데모 크레딧. CI 배지를 둡니다 |
| `pyproject.toml` | `license = "MIT"`, 설명(§0 영어판), `urls` |
| `requirements.txt` | `dependencies`와 같게 맞춥니다. 테스트가 둘을 비교합니다(BR-U8-30) |
| `CLAUDE.md` | Project Overview를 §0으로 바꿉니다. Status에 U8을 넣고, 명령은 새 데모 이름을 씁니다 |
| `operations.md` | "Web UI (U10)" 절, "editor's Load demo world button", `/health` `degraded` 설명, `--legacy-peer-deps`를 고칩니다. 옛 명령의 `aldermoor` → `emberleaf` 대응 한 줄을 둡니다 |
| `env.example` | 머리말 중복을 지웁니다 |
| i18n | 쓰지 않는 `toolbar.loadDemo`·`editor.noWorld`를 지웁니다 |
| 진행 중 기능(H3) | 교차 월드 prior 검색, 컨셉 아트 수집, LangGraph 래퍼, wiki 순환 개선. README 표(기능·상태·한 줄)와 모듈 docstring `STATUS:`를 둡니다. 화면에 닿는 것은 빌드 패널의 컨셉 아트 칸이고, "진행 중" 표시를 답니다 |
| 지난 code-summary | 고치지 않습니다. 그때 돌린 명령의 기록이기 때문입니다 |

## 6. CI (Q5=A)
GitHub Actions 워크플로 하나가 push와 PR에서 돕니다. 배치(러너, 캐시, 버전)는 Infra-light에서 정합니다.

| 작업 | 확인 |
|---|---|
| backend | `ruff check locus api tests`, `black --check locus api tests`, `pytest`(seed 기록) |
| frontend | `npm ci`, `tsc --noEmit`, `vitest run` |
| audit | `npm audit --omit=dev --audit-level=moderate`(Q5=A대로 막는다). 〔검토 01 R-11〕 따로 된 작업이라 코드와 무관한 자문 DB 변경으로 실패해도 다른 작업의 결과는 그대로 보인다 |

- **hypothesis seed**(PBT-08): 실행마다 seed를 하나 정해 로그에 찍고 `--hypothesis-seed`로 넘깁니다. 실패하면 지금 프로필(`print_blob=True`)이 재현 blob을 찍습니다.
- **mypy**: 넣지 않습니다(기준선 11건). README의 개발 절에 손으로 돌리는 게이트로 적습니다.
- **npm audit**: react-router를 고친 판으로 올려 0건으로 만듭니다(BR-U8-35). 〔검토 01 R-11〕 외부 자문이 새로 나오면 그 작업만 빨갛게 됩니다. 사람이 보고 고치거나 그때 정합니다(Q5=A의 감수한 위험).
- **전제**: `npm ci`가 lock 그대로 성공해야 합니다(peer 충돌 없음). 지금 lock에서는 충돌이 보이지 않고, Infra-light가 깨끗한 `npm ci`를 확인합니다. 〔검토 01 R-11〕
- 워크플로는 push해야 돕니다. push와 원격 실행 확인은 사람이 합니다.

## 7. 라이브 시나리오 `scripts/live_scenario.py` (A8-8)
운영자가 띄운 스택에 대고 돕니다. CI에는 넣지 않습니다. 새 의존을 쓰지 않습니다(표준 라이브러리 HTTP).

〔검토 01 R-05〕 대화는 플레이어가 있는 지역의 NPC하고만 됩니다. 그래서 순서를 플레이어 위치에 맞추고, 먼 지역은 GM 읽기로 봅니다. 턴 번호 T는 각 단계가 끝난 뒤의 세션 턴입니다.

| 단계 | 스토리 | 플레이어 위치 | 확인 | LLM |
|---|---|---|---|---|
| 1 기동 | US-1.1 | — | `/health` 200 `ok`, `/api/capabilities` | — |
| 2 데모 | US-1.3 | — | `GET /demos`에 `emberleaf`, 불러오기 `ok`·`llm_calls=0`, 지역 12 | — |
| 3 세션 | US-3.1 | Saltwake (T0) | 플레이어 세션 시작 | — |
| 4 이동 | US-3.3 | Ambermeadow (T1) | 강 연결 1턴 | — |
| 5 대화 | US-4.1 | Ambermeadow | Ambermeadow NPC와 한 줄 | 필요 |
| 6 선언 | US-4.5, US-6.5 | Ambermeadow (T2) | 행동 선언 → 서술, 행적 기록. 그 턴 끝에 판단으로 행적 소문이 씨앗된다(기준 시점 T2) | 필요 |
| 6a 대화 마침 〔U8 리뷰 01 정정 #3〕 | US-6.5 | Ambermeadow (T3) | 행적 판단은 대화를 마칠 때(`end_talk`)만 한다(BR-U6-7). 그 지역 NPC에게 한 줄 하고 `end_talk` → 판단 → 전할 만하면 행적 소문이 씨앗된다(기준 시점 T3). 전할 만한 판단이 있는데 소문이 없으면 FAIL, 전할 만한 판단이 없으면 9·11은 SKIP | 필요 |
| 7 씨앗 | US-1.3 | Ambermeadow | GM이 `seed-mushroom-blight` 시작 → ACTIVE (턴 소모 없음) | — |
| 8 이동 | US-3.3, US-3.4 | Saltwake (T3) | 강 연결 1턴. 이 턴에 마름병 번짐과 행적 확산 1칸이 일어난다 | — |
| 9 행적 1칸 | US-6.5 | Saltwake | GM 소문 목록(`listRumors`): Saltwake·Sylvarch에 그 행적 소문이 있다. Ironcrag·Gutterlight에는 없다 | 선언에 필요 |
| 9a 기다리기 〔Step 1.2 정정〕 | US-3.4 | Saltwake (T4) | `WaitAction` 1턴(T3→T4). 대화는 턴을 쓰지 않으므로 10·11의 T4는 이 단계가 만든다(FD 검토 02 R-05) | — |
| 10 다르게 듣기 | US-6.1 | Saltwake (T4) | Saltwake NPC에게 마름병을 묻는다(대화). Ironcrag의 마름병 관련 소문·왜곡도는 GM 읽기로 본다. 두 지역의 왜곡도와 소문 수가 다르다(Saltwake 무게 1.0, Ironcrag 0.204) | 대화에 필요 |
| 11 행적 3칸 전 | US-6.5 | Saltwake (T4) | T4(기준 T2 + 2턴)까지 Ironcrag에 그 행적 소문이 없다 | 선언에 필요 |
| 12 세계 상태 | US-5.5 | — | `GET …/state`의 지역별 사건·소문 수 | — |

- 〔U8 리뷰 01 정정 #3〕 6단계는 서술만 한다. 판단·씨앗은 6a(T3)에서 일어나므로 뒤 턴 번호가 하나씩 밀린다: 8 이동 T4, 9 행적 1칸(T4), 9a 기다리기 T5, 10·11은 T5(기준 T3 + 2). 9·11은 그 세션의 모든 행적 소문을 센다(도착 행적도 함께 판단되어 목초지의 한 턴 한 칸을 먼저 쓸 수 있다). 10단계는 10a(왜곡도, LLM 없음)와 10b(대화)로 나뉜다.
- support 계산(〔검토 01 R-05〕, 기본 조정값): 행적 소문의 처음 support는 `0.2 × (1 + salience)`이고 씨앗이 되려면 salience ≥ 0.5이므로 0.30~0.40입니다. 한 칸 갈 때 `× (0.5 + 0.5·w)`, 다시 퍼질 바닥은 `prune_floor + support_decay = 0.10`입니다.
  - Saltwake(w 1.0): 0.30 이상 → 9단계의 "있다"는 바닥보다 충분히 위입니다.
  - Ironcrag까지(1.0 → 0.6 → 0.34, 턴마다 −0.05 감쇠): salience 0.5이면 0.10 근처라 닿지 않을 수 있습니다. 그래서 스크립트는 Ironcrag 도달을 단언하지 않고 "T4까지 없다"만 단언합니다(한 턴 한 칸이라 위상으로 보장됨).

- 각 단계는 PASS, FAIL, SKIP 중 하나를 찍습니다. 키가 없으면 LLM 단계는 SKIP이고 까닭을 적습니다. FAIL이 하나라도 있으면 종료 코드는 1입니다.
- 옛 `build-and-test/integration-test-instructions.md`는 Build&Test 단계에서 이 스크립트를 쓰는 안내로 바꿉니다.

## 8. 범위 밖과 알려진 공백
- 에디터의 씨앗 편집 화면(World File로 고칩니다).
- 씨앗 목록의 번역(원문으로 보입니다. 시작된 사건의 설명은 세션 내용 번역을 따릅니다).
- CLI 교체가 번역을 지우지 않는 공백(U5, A8-10). 화면 경로는 API를 거쳐 지웁니다.
- mypy 기준선 11건 정리.
- 〔검토 01 R-09〕 소스 빌드(LLM)는 패키지 World File과 같은 월드를 보장하지 않습니다. 연결 무게는 빌드 표(base weight)에서 오고, 지식·NPC 글은 LLM이 씁니다. 소스는 "자료로 월드를 만든다"를 보이기 위한 것이고, 데모 플레이는 World File을 씁니다.

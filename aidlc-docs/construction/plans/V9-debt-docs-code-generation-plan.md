# V9 부채·문서 마무리 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V9(실행 9/9, 마지막 유닛), Code Generation Part 1.
- 이 유닛이 하는 일: 게이트를 세우고(dev audit 0, mypy 0과 CI 단계), 시험을 시간에 기대지 않게 하고, 문서를 코드와 맞추고, 남은 일을 다음 주기 목록에 근거와 함께 적는다.
- FD·NFR은 SKIP이다(unit-of-work). 이 계획이 Part 2의 유일한 기준이다.

**입력**
- 유닛 `inception/application-design/follow-up/unit-of-work.md` V9(범위, 완료 조건 넷)
- 요구 `inception/requirements/follow-up-requirements.md` FR-T2~T7, FR-C14, FR-D10, 요구 리뷰 R-03(U8 이월 묶음)
- RE `inception/reverse-engineering/` `code-quality-assessment.md` § G(문서 어긋남)와 RE-W/P/F/T low·정리 항목
- 앞 유닛이 넘긴 것: V1~V8 code-summary § 8과 코드 리뷰 기록, U8 `code/reviews/code-review-01.md`·`code-summary.md` § 8
- **사람의 결정**(2026-10-11, V9 범위 질문): **A. 정해진 범위 + 작은 것**. V9가 어차피 여는 파일에서 끝나는 작은 넘김은 V9에서 고치고, 큰 넘김은 `next-cycle.md`에 근거와 함께 적는다(§ 1.1).

**기준선**(Step 1에서 다시 잰다, 2026-10-11 현재)
- pytest 1228 passed, ruff·black clean(`locus api tests`), mypy 11건(6파일)
- vitest 813 passed, tsc clean, `npm audit --omit=dev` 0, 전체 `npm audit` 5건(moderate 3, high 2: `browserslist`, `source-map-js` 등, 모두 `npm audit fix` 범위)
- pytest의 sqlite `ResourceWarning` 53줄(`-W default::ResourceWarning`)
- 고정 대기: `test_u4_uow_rollback_does_not_erase_other_threads_writes` 5.00 s, `test_with_retry_*` 3.00 s × 2

---

## 1. 실행 메모

### 1.1 사람이 정한 범위 (A)

V9에서 고친다(정해진 범위에 더해, 같은 파일에서 끝나는 작은 넘김):
- **W-1 에디터·지도 문장 말투**(V8 code-summary § 6·§ 8): `map.hint.*`, `editor.*.none`, `editor.unscoped.none`, `delete.region.*`, `delete.prior`, `delete.knowledge`, `delete.npc`, `delete.connection` 등 에디터가 보이는 ko 문장 가운데 합니다체를 해요체로 고친다. en은 뜻이 같은지만 본다.
- **W-2 옛 사전 키**(V2·V4 넘김): `play.`·`gm.`·`editor.`·`map.`·`session.`·`home.` 앞머리 키 가운데 코드가 쓰지 않는 것을 지운다. 동적 키(`` t(`map.hint.${tool}`) `` 꼴)는 쓰는 것으로 센다. 시험만 쓰는 키(`session.none`)는 그 시험을 사전 밖 값으로 바꾸고 지운다.
- **W-3 CI의 `scripts` 린트**(U8 §2 C11): CI ruff·black의 대상에 `scripts`를 더한다(`ci.yml`을 어차피 고친다).
- **W-4 시험 대역 결함 둘**(U8 §3 #20, #21): `tests/shared/storage/fakes.py:64-75`의 `upsert_edges`가 Neo4j처럼 병합하게, `tests/api/test_keyless_api.py:48`의 `/health` 시험이 실제로 실패할 수 있게 고친다(FR-T6와 같은 묶음).

V9에서 고치지 않고 `next-cycle.md`에 적는다(큰 넘김):
- 화면별 사전 나누기(첫 화면 JS +2.55 kB, V8 이탈), 1024px 경계에서 부품이 다시 그려짐(V8 § 6), 교체 전 끌기 저장 기다리기(V8 § 9), SQL 엔진 `connect_timeout`·`pool_pre_ping`(V3 #11), 작은 지도 초점·글자 크기(V4), CSS 84.7 kB gzip(V2), V3 알려진 한계, V5 § 6 알려진 한계, 서버 쪽 타임라인 페이지(V6), GM 타임라인 줄의 말투(V6)
- RE의 남은 low·정리 항목, RE medium 중 남은 것(W08, W13 일부, W17), U8 §3·§2·설계 메모의 남은 것, 이번 주기 범위 밖(§9) 목록 — § 2 Step 9의 표대로

**고칠 것이 아님으로 판정**: "데모 번역에 엔티티·사전 하나의 한국어가 없음"(V8 § 9)은 캡처용 가짜 서버가 번역을 직접 덮어쓰다 생긴 것이다. 제품의 번역 종류는 `world`, `region`, `knowledge`, `npc`, `event_seed`이고 에디터는 원문을 보인다. code-summary에 이 판정을 적는다.

### 1.2 코드를 읽고 정한 것

- **mypy 11건**(모두 타입을 바로잡아 고친다. `# type: ignore`는 쓰지 않는다)

| 위치 | 원인 | 고침 |
|---|---|---|
| `world/ontology/reconciler.py:126` | `self._llm`이 `LLMProvider \| None` | 없으면 `None`을 돌려주는 가드 |
| `world/topology/hierarchy.py:68` | `cur`가 `Region`으로 선언된 뒤 `by_id.get`을 받음 | `cur: Region \| None` |
| `world/wiki/linker.py:51` | `tuple(sorted(...))`은 `tuple[str, ...]` | `a, b = sorted(...)`로 두 칸 튜플 |
| `shared/storage/neo4j_repo.py:46-47` | `_driver = None`으로 시작 | `Driver \| None` 주석(`TYPE_CHECKING` 가져오기), `connect`는 지역 변수로 확인 |
| `shared/storage/opensearch_repo.py:98-99` | 같은 꼴 | `OpenSearch \| None` |
| `shared/llm/openai_provider.py:28,72,111` | `api_key`에 `str` | `SecretStr(api_key)` |
| `shared/llm/openai_provider.py:92` | `content: list[object]` | `list[str \| dict[str, Any]]` 주석 |

- **dev audit 5건**: 모두 `npm audit fix`(주 버전을 넘지 않음) 범위다. 바뀐 `vite`·`vitest`가 있으면 tsc·vitest·`vite build`로 확인한다.
- **FR-T6 기제**
  - `tests/play/test_repository_contract.py:258-292`: 주 스레드의 `repo.get_player`가 A가 쥔 잠금에 막힌다. 그래서 A의 `a_release.wait(timeout=5)`가 끝나야만 지나간다(5 s). `or True`가 그 사실을 가린다. 고침: B가 잠금 앞에 왔다는 사건(`b_started`)과 끝났다는 사건(`b_done`)을 두고, 주 스레드는 잠금을 잡지 않은 채 "`b_done`이 짧은 시간 안에 오지 않음"을 단언한 뒤 A를 풀어 준다. 그 뒤의 두 단언은 그대로다.
  - `tests/play/test_player_mode.py:611-616`: `... or True`. 실제 값(`region_name`, `narration`)을 확인해 그대로 단언한다.
  - `tests/shared/llm/test_retry_and_factory.py:14,28`: tenacity가 실제로 1 s, 2 s를 잔다. `locus/shared/llm/retry.py`가 기다리는 함수를 모듈 수준(`_sleep`)으로 두고 tenacity에 넘긴다. 시험은 그것을 바꿔 끼워 기다린 값 `[1, 2]`를 단언한다(자지 않음).
  - sqlite `ResourceWarning`: 시험이 만든 엔진을 닫지 않아 GC 때 아무 시험에서나 나온다. `tests/play/conftest.py`의 `sql` 픽스처는 끝에 `engine.dispose()`, 시험 안의 `create_engine("sqlite://")`(예: `test_repository_contract.py:363`, `test_u3_review_carry.py:55`)는 닫는 픽스처를 쓴다. 확인: `-W default::ResourceWarning`으로 0줄.
- **FR-T7**(`scripts/live_scenario.py`)
  - 10a(`:285-293`)는 두 지역의 왜곡도가 "같지 않음"만 본다. 고침: `GET /api/gm/sessions/{sid}/events?status=active`의 `contributions`로 사건 퍼짐만 떼어, 가까운 지역(솔트웨이크 항구)의 기여가 먼 지역(아이언크래그)보다 큼을 단언한다. 상태(`/state`)의 왜곡도는 가까운 쪽 > 먼 쪽, 가까운 쪽 > 0.3을 함께 본다(U8 domain-entities § 5.2의 기대값: 약 0.60과 0.36).
  - 응답 꼴이 이상하면 traceback이 아니라 FAIL로 적는다: `_parse`가 JSON이 아니면 그 단계를 FAIL로, `run()`이 `AttributeError`·`http.client.HTTPException`도 잡는다.
  - `--poll 0`이면 영원히 기다린다: 하한을 둔다.
  - 시험: `tests/test_live_scenario.py`의 가짜 서버에 `/events` 경로를 더하고, 방향 단언(통과·실패), JSON 아닌 응답의 FAIL, poll 하한을 시험한다.
- **FR-D10**: `web/index.html`은 `lang="en"`, 제목 "Locus — Spatial Knowledge", 설명·favicon 없음, `web/public/` 없음.
- **FR-T5**: `env.example`에 `SESSION_DB_HOST`(기본 `localhost`, `settings.py:60`), `TRANSLATION_WARM_WORKERS`(기본 2, `settings.py:141`)가 없다.

### 1.3 이 계획이 정한 것

- **CI**: backend 잡에 `mypy locus api` 단계를 더하고 오류가 하나라도 있으면 실패한다. ruff·black 대상은 `locus api tests scripts`다(W-3).
- **게이트 스크립트** `v9gate.sh`(세션 scratchpad): ruff·black(`locus api tests scripts`), mypy 0, pytest, `-W default::ResourceWarning`으로 경고 0줄, tsc, vitest, `npm audit`(전체) 0, `npm audit --omit=dev` 0, `vite build`.
- **문서의 언어 표시**: `index.html`은 `lang="ko"`(기본 화면 언어)다. 화면 언어를 바꾸면 `document.documentElement.lang`도 바뀐다(i18n의 `setLang`). 제목은 "Locus", 설명은 목적 문장(README 첫 줄)이다. favicon은 `web/public/favicon.svg` 하나(앱의 accent 색 토큰 값으로 그린 단순 글리프)다.
- **CLAUDE.md**: Status를 Follow-up 주기 기준으로 다시 쓴다(V1~V9 완료, Build and Test 남음, 실제 수치). Gates는 실제 CI와 맞춘다. Code 목록과 Conventions는 § G 표대로 고친다.
- **`web/README.md`**: 지금 구조(`layout/`, `map/`, `hooks/`, `errors/`, `format/`, `ui/`, `features/{home,play,gm,editor}`, `i18n/`)로 다시 쓴다.
- **`next-cycle.md`**: 머리를 Follow-up 주기 뒤로 바꾸고, 이번 주기에 끝난 줄은 지운다. 남은 것을 출처(유닛·리뷰 번호)와 지금 위치(file:line)로 적는다.

### 1.4 실행 메모 (코드 계획 리뷰 01, 승인 2026-10-12 때 Accepted risk)

- 〔R-01〕 시험 대역 `tests/shared/storage/fakes.py`의 `replace_edges`는 지금 `upsert_edges`가 전체를 바꾸는 데 기댄다. Step 4.5에서 `replace_edges`를 따로 구현한다(Neo4j `SET r = $props`와 같은 전체 교체). `upsert_edges`는 Neo4j `SET r +=`처럼 병합한다. `tests/shared/storage/test_port_contract.py`에 병합 계약 시험을 더하고(두 구현 모두에서 돈다), `tests/world/editor/helpers.py:66`의 계량 대역도 확인한다.
- 〔R-02〕 FR-T4의 항목마다 닫힘 표를 code-summary § 3에 둔다. README의 NPC 문장, operations의 409·중단된 실행 문장, `cache.py` 독스트링, `api/errors.py` 목록은 앞 유닛(V2·V5·V7)에서 이미 고쳐졌다. 표에는 "이미 고침(유닛)"으로 적는다. operations.md의 "World editor" 절(400~406행)은 V8 에디터대로 고친다(Step 8.4). operations의 LLM 없음 문장(키가 있으면 임베딩 호출)도 8.4에서 고친다. 요구에 없는 "V1·V3 운영 메모"는 하지 않는다.
- 〔R-03〕 `setLang`은 이미 `document.documentElement.lang`을 바꾼다(`i18n/index.ts`의 처음 읽기와 `notify()`). Step 5.3은 `index.html`의 정적 `lang`을 `ko`로 바꾸고, 지금 동작(언어를 바꾸면 `lang`이 바뀜)을 지키는 시험 하나만 둔다.
- 〔R-04〕 10a의 이름→id 대응은 `/state`의 `regions[].region_id`(같은 항목의 `region_name`)로 얻는다. `--poll`의 하한은 1초다. 1초보다 작은 값은 1초로 올리고 그렇다고 한 줄 알린다.
- 〔R-05〕 Step 4.1: B가 잠금 앞에 섰다는 사건(`b_started`)을 기다린 뒤, A를 풀기 **전에** `b_done.wait(0.2)`가 거짓임을 단언한다. 그다음 A를 풀고, 모든 `join`에 시한(5초)을 둔다. 시한이 지나면 실패로 끝난다. Step 4.2: `or True` 줄의 실제 값을 먼저 돌려 읽고, 그 값으로 단언을 확정한다. Step 4.5: `/health`는 조립된 경계 하나를 비우면 `degraded`가 나오는지를 단언한다(지금은 `do_assemble`가 거짓이라 늘 `ok`).
- 〔R-06〕 전체 `npm audit` 0은 이번 한 번의 확인이다. CI `audit` 잡은 지금처럼 `--omit=dev`다(개발 의존성의 새 공지가 CI를 막지 않게). Step 2.2에 `npm ci`로 잠금 파일이 그대로 설치되는지 확인을 더한다.

---

## 2. 단계

각 단계는 게이트 GREEN 뒤 커밋 하나다. 커밋 메시지는 단계에 적힌 대로다.

### Step 1 — 진행 기록과 기준선
- [x] 1.1 진행 기록을 커밋한다: audit, state, 이 계획과 그 리뷰(`docs(aidlc): V9 code plan`).
- [x] 1.2 기준선을 다시 잰다(§ 머리의 수치). `v9gate.sh`를 만든다(§ 1.3).

### Step 2 — dev audit 0 (FR-T2)
- [x] 2.1 `web/`에서 `npm audit fix`. 주 버전이 바뀌는 수정은 하지 않는다. 바뀐 패키지와 버전을 기록한다.
- [x] 2.2 확인: `npm audit` 0, `npm audit --omit=dev` 0, tsc, vitest 813, `vite build`(첫 화면 gzip이 늘지 않음).
- [x] 2.3 커밋: `chore(web): dev dependencies without known advisories (V9, FR-T2)`

### Step 3 — mypy 0과 CI 단계 (FR-T3, W-3)
- [x] 3.1 § 1.2 표의 일곱 곳을 고친다. 동작은 바뀌지 않는다(가드는 지금도 그 길에서 `None`을 돌려주는 것과 같은 결과).
- [x] 3.2 `.github/workflows/ci.yml` backend 잡: `mypy locus api` 단계, ruff·black에 `scripts`. `scripts`의 린트 오류가 있으면 함께 고친다.
- [x] 3.3 확인: mypy 0, ruff·black clean, pytest 1228.
- [x] 3.4 커밋: `fix(types): mypy is clean and CI checks it; scripts are linted too (V9, FR-T3)`

### Step 4 — 시험 위생 (FR-T6, W-4)
- [x] 4.1 `test_repository_contract.py` U4 롤백 시험: 사건 둘로 B의 막힘을 실제로 단언, `or True` 없앰, 고정 대기 없음(§ 1.2).
- [x] 4.2 `test_player_mode.py:611-616`의 `or True`: 실제 값을 단언한다.
- [x] 4.3 `locus/shared/llm/retry.py`: 기다리는 함수를 바꿔 끼울 수 있게 한다. `test_retry_and_factory.py`는 자지 않고 기다린 값을 단언한다.
- [x] 4.4 sqlite 엔진 닫기(§ 1.2). 그 밖에 시험이 여는 연결이 있으면 같은 규칙으로 닫는다.
- [x] 4.5 W-4: `fakes.py`의 `upsert_edges` 병합, `test_keyless_api.py`의 `/health` 단언. 바꾼 대역 위의 시험이 그대로 통과하는지 본다.
- [x] 4.6 확인: pytest 1228 이상, `ResourceWarning` 0줄, `--durations=10`에 1 s 넘는 고정 대기 없음(PBT·가드 머신처럼 실제로 계산하는 시험은 제외하고 이름을 적는다).
- [x] 4.7 커밋: `test: no test waits on a timeout to pass, retries do not sleep, every sqlite engine is closed (V9, FR-T6)`

### Step 5 — env.example과 문서 머리 (FR-T5, FR-D10)
- [x] 5.1 `env.example`: `SESSION_DB_HOST`, `TRANSLATION_WARM_WORKERS`를 기본값·뜻과 함께 더한다.
- [x] 5.2 `web/index.html`: `lang="ko"`, 제목, 설명 메타, favicon 링크. `web/public/favicon.svg`.
- [x] 5.3 `web/src/i18n/index.ts` `setLang`: `document.documentElement.lang`을 화면 언어로 바꾼다(처음 읽을 때도). 시험 하나(`i18n` 또는 `layout.test`).
- [x] 5.4 확인: tsc, vitest, `vite build`(favicon이 빌드에 들어감).
- [x] 5.5 커밋: `fix(web): the page says what Locus is, in the language on screen, with an icon; env.example lists every setting (V9, FR-D10, FR-T5)`

### Step 6 — 라이브 시나리오 (FR-T7)
- [x] 6.1 `scripts/live_scenario.py`: 10a 방향 단언(§ 1.2), 이상한 응답은 FAIL, poll 하한.
- [x] 6.2 `tests/test_live_scenario.py`: `/events` 경로, 방향 단언의 통과와 실패, JSON 아닌 응답의 FAIL, poll 하한.
- [x] 6.3 확인: pytest, ruff·black(`scripts`).
- [x] 6.4 커밋: `test(live): the scenario checks that a nearer region is distorted more, and a bad answer is a FAIL, not a traceback (V9, FR-T7)`

### Step 7 — 사전 말투와 옛 키 (W-1, W-2)
- [x] 7.1 W-1: 에디터·지도가 보이는 ko 문장의 합니다체를 해요체로. 바꾼 키 목록을 code-summary에 적는다.
- [x] 7.2 W-2: 앞머리 `play.`·`gm.`·`editor.`·`map.`·`session.`·`home.` 키마다 쓰임을 확인하고(정적·동적), 쓰지 않는 키를 ko·en에서 함께 지운다. 지운 목록을 적는다.
- [x] 7.3 시험: `i18n.style.test.ts`에 "에디터·지도 앞머리(`editor.`, `map.hint.`, `delete.`)의 문장은 해요체" 규칙을 더한다(값 이름처럼 마침표 없는 줄은 제외). 사전 일치·자리표시 시험은 그대로 통과.
- [x] 7.4 확인: tsc, vitest(fr-d8 포함).
- [x] 7.5 커밋: `fix(web): the editor's and the map's lines speak 해요체; dictionary keys no screen uses are gone (V9)`

### Step 8 — 문서 (FR-T4)
- [x] 8.1 `CLAUDE.md`: Status(Follow-up 주기, V1~V9, 실제 수치), Gates(실제 CI), Conventions(교차 월드 사전 검색은 지금 0건을 돌려줌 — 사실대로, `world_id`는 색인일 뿐 분할이 아님), Code 목록(§ G 표의 빠진 파일과 V2~V8 웹 구조), "127.0.0.1" 주장 바로잡음.
- [x] 8.2 `README.md`: 사건 퍼짐 문장(행적 소문만 한 칸씩, 사건은 같은 턴에 길을 따라 퍼짐), [바로 플레이]의 LLM 없음 설명(키가 있으면 임베딩 호출).
- [x] 8.3 `web/README.md` 다시 씀(§ 1.3).
- [x] 8.4 `aidlc-docs/operations/operations.md`: 제목의 "(placeholder)", Observability의 app·web healthcheck, "Doodly"·SessionBar 언급, V1(CI 러너)·V3(번역 파일) 운영 메모.
- [x] 8.5 docstring·주석: `neo4j_repo.py:3,76-77`, `knowledge/loader.py:3-5`, `play/event/dynamics.py:4`, `play/event/suggester.py:4`, `api/routers/play.py:7-8`, `play/storage/postgres_repo.py:7-8`, `Dockerfile:9`.
- [x] 8.6 확인: 문서가 말하는 수치·경로가 실제와 같은지 하나씩 본다(경로는 `ls`, 수치는 게이트 출력). ruff·black·mypy·pytest(docstring 고침).
- [x] 8.7 커밋: `docs: CLAUDE.md, README, web/README and operations match the code after the Follow-up cycle (V9, FR-T4)`

### Step 9 — 다음 주기 목록 (FR-C14)
- [x] 9.1 `aidlc-docs/operations/next-cycle.md`를 다시 쓴다. 이번 주기에 끝난 줄은 지운다(머리, 화면 다듬기, U8 #5(a)·#9~#15, CI 액션, dev audit "4건").
- [x] 9.2 남은 것을 출처와 지금 위치로 적는다.
  - RE low·정리: W05, W06, W07(일부), W09, W10, W11, W12, W14, W15, W16, W19, W20, W21, W22, W23, W24, P08~P15, F13, F15, T04~T07, T09, T10, T11(일부), T13
  - RE medium 남은 것: W08, W13(일부), W17
  - U8 §3: #1(일부), #6, #7, #8, #12, #13, #14, #18, #19 / U8 §2: C2~C10(C3·C9 일부) / U8 설계 메모 2, 3, 5(확인), 7, 8, 9, 10
  - V1~V8 넘김(§ 1.1의 큰 넘김)
  - 이번 주기 범위 밖(요구 §9): 잠금 파일, Docker non-root·digest 고정, `api` 패키징, 의존성 선언, 0.0.0.0 바인드, Playwright·axe·지도 키보드, UX-26, 어두운 테마 밖, 에디터·GM의 폰 배치
- [x] 9.3 커밋: `docs(aidlc): next-cycle list after the Follow-up cycle, each item with its source and place (V9, FR-C14)`

### Step 10 — 마무리
- [ ] 10.1 `v9gate.sh` 전체 GREEN. 수치: pytest, vitest, mypy 0, audit 0/0, `ResourceWarning` 0, 가장 느린 시험 10개, JS gzip.
- [ ] 10.2 `construction/V9-debt-docs/code/code-summary.md`
  - § 1 기준선과 결과, § 2 파일, § 3 요구 → 확인 표, § 4 바뀐 기존 시험, § 5 이탈, § 6 알려진 한계, § 7 돌연변이(시험 위생 고침: `or True`를 되돌리면, 잠금 사건을 빼면 등), § 8 넘기는 것(Build and Test)
- [ ] 10.3 audit, state 갱신 → 커밋 `docs(aidlc): V9 code summary`

---

## 3. 요구 대응

| 요구 | 단계 | 완료 조건(unit-of-work) · 확인 |
|---|---|---|
| FR-T2 dev audit 0 | 2 | `npm audit` 0 · `--omit=dev` 0 |
| FR-T3 mypy 0, CI | 3 | mypy 0, `ci.yml`에 mypy 단계 |
| FR-T4 문서 | 8 | CLAUDE.md Status·Gates가 실제와 같음 |
| FR-T5 env.example | 5 | 두 설정이 있음 |
| FR-T6 시험 위생 | 4 | `ResourceWarning` 0, 고정 대기 11 s 사라짐, `or True` 0 |
| FR-T7 라이브 시나리오 | 6 | 방향 단언, FAIL로 기록(오프라인 시험) |
| FR-C14 넘김 기록 | 9 | `next-cycle.md`에 넘긴 항목이 모두 있음(§ 1.1, § 2 Step 9) |
| FR-D10 문서 머리 | 5 | 제목·설명·언어·favicon |
| 사람의 결정 A (W-1~W-4) | 3, 4, 7 | 말투 규칙 시험, 지운 키 목록, CI `scripts`, 대역 시험 |

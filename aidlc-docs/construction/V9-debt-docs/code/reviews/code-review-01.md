# V9 부채·문서 마무리 — Code Review 01

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**이 리뷰가 하는 것**: 승인된 V9 코드가 승인된 계획과 요구를 지키는지 결함 위주로 확인한다.
- 설계 기준: FR-T2~T7, FR-D10, FR-C14, 계획 § 1.1~1.4(W-1~W-4, R-01~R-06), code-summary § 3·§ 5·§ 6.
- 범위: `git diff 10f2333..bc4ac75`(커밋 9개와 요약).
- 새 시험이 주장대로 잡는지도 본다.
- 코드는 고치지 않았다(리뷰 전용).

**방법**: V5~V8 리뷰와 같다.
- 네 각도를 병렬로 돌렸다.
  1. 백엔드·시험 위생(mypy 고침의 동치, 재시도 대기, 엔진 dispose, 잠금 순서 시험, 대역 병합, `/health`, CI): 무작위 동치 비교 20만 번, 잠금 시험 300회 반복과 부하 반복, 돌연변이 22
  2. 라이브 시나리오(10a가 실제 스택에서 성립하는지, JSON 아님 검사가 정상 응답을 FAIL로 만들지 않는지, 예외 처리, poll 하한): 서버 코드 추적, in-process 실행(키 없음·가짜 LLM), 돌연변이 26
  3. 웹(지운 키 11개, 쓰임 시험, 말투 규칙, 고친 24줄, `index.html`·favicon, 잠금 파일): 정규식 탐침, `vite build`, `npm ci --dry-run`, 돌연변이 24
  4. 문서(CLAUDE.md·README·web/README·operations·docstring의 주장, next-cycle 60줄 넘게, code-summary § 3.1)
- 각도마다 작업 사본(git worktree)을 따로 썼다. 사본이 `main`에서 만들어져 넷 모두 `bc4ac75`를 직접 꺼내 봤다. 재현물은 세션 scratchpad의 `v9review/{backend,live,web,docs}/`에만 두었다. 저장소는 바뀌지 않았다.
- 이 세션이 medium 셋을 다시 확인했다.
  - #1: 규칙의 정규식을 node로 돌렸다. `"만드는 중입니다…"`, `"…지웁니다(되돌릴 수 없음)"`, `"누르십시오"`는 통과하고, `"키가 없으니까 쉬어요"`는 걸린다.
  - #2: 에디터 라우터에 씨앗을 만드는 경로가 없다(`api/routers/world_editor.py`는 씨앗 번역 지우기만 한다). `carry_over.py:3-4` docstring도 "에디터에서 더한다"고 한다.
  - #3: 옛 next-cycle의 "정확성 #9~#15"는 U8 리뷰 § 1의 번호였다. 새 약어는 § 3 번호로 정했다.
- 판정
  - **C**: 재현했거나 코드로 기제가 확정됨.
  - **P**: 기제는 실재하지만 직접 돌리지 못한 조건에 달림.
- 두 각도가 같은 것을 찾은 경우는 하나로 합쳤다(#7 = 백엔드 8·문서 17).
- 심각도는 설계자·플레이어·운영자가 겪는 결과로 매겼다. 시험의 빈틈은 그 빈틈이 놓치게 할 결함의 무게로 매겼다. 문서의 틀린 사실은 그 문서를 믿고 한 일이 틀어지는 정도로 매겼다.

## 1. 지적 — medium

| # | 판정 | 위치 | 무엇이 틀리나 | 실패 장면 | 고칠 방향 |
|---|---|---|---|---|---|
| 1 | C | `web/src/__tests__/i18n.style.test.ts:82` | 말투 규칙의 `HAPNIDA`는 정해 둔 문자 뒤의 합니다체만 잡는다. `니다…`, `니다(`, `니다"`, `니다;`, `-ㅂ니다만`, 마침표 없는 `-십시오`는 통과한다 | `"만드는 중입니다…"`나 `"씨앗 {n}개를 지웁니다(되돌릴 수 없음)"`를 에디터 줄에 넣어도 초록이다. 이 사전에서 `…`는 흔하다. W-1이 약속한 "에디터·지도 문장은 해요체로 남는다"를 지키지 못한다 | NFD로 풀어 받침 ㅂ+`니다`·`니까`를 뒤 문자와 상관없이 잡고, `십시오`를 따로 막는다(#13의 거짓 양성도 함께 사라진다) |
| 2 | C | `README.md:7`; `locus/world/carry_over.py:3-4`; code-summary § 3.1 "README — NPC" 줄 | "NPC와 사건 씨앗은 에디터에서 더하고 …"라고 하지만, 에디터가 더할 수 있는 것은 NPC뿐이다. 씨앗은 World File의 `event_seeds`로만 들어온다 | README를 보고 에디터에서 씨앗을 찾는 사람은 찾지 못한다. code-summary는 이 줄을 "이미 고침"으로 보증했다 | "NPC는 에디터에서 더하고, 사건 씨앗은 World File로 넣는다. 둘 다 소스로 다시 빌드해도 남는다." docstring과 code-summary 줄도 고친다 |
| 3 | C | `aidlc-docs/operations/next-cycle.md:8`, `:14`, `:55-57` | 약어는 "U8 #n = 리뷰 § 3의 행 순서"인데, § 0의 "U8 #5(a)·#9~#15"는 § 1의 번호다. 약어대로 읽으면 § 3의 #12~#14가 닫힌 셈인데 § 3.2는 셋을 열림으로 적는다. 닫은 유닛도 빠졌다(§ 1 #11 매니페스트 검사는 V3, #14 PlayerStrip·#15 일괄 503은 V6) | 다음 주기에 이 목록으로 일을 고르는 사람이 같은 번호를 두 뜻으로 읽는다 | § 0을 "U8 § 1 #5(a)·#9~#15 — V3·V5·V6·V7"로 고치고, 약어에서 § 1 번호와 § 3 번호를 나눠 적는다 |

## 2. 지적 — low (코드·스크립트)

| # | 판정 | 위치 | 무엇이 틀리나 | 고칠 방향 |
|---|---|---|---|---|
| 4 | C | `scripts/live_scenario.py:400-406`, `:127-131`, `:414` | `--timeout`은 검증이 없다. `nan`이면 `waited >= nan`이 늘 거짓이라 이번에 고친 "끝나지 않는 대기"가 다시 생긴다. `--poll inf`는 `time.sleep(inf)`의 OverflowError가 traceback으로 나간다. `--timeout 0`·음수는 읽지도 않고 run 단계가 모두 FAIL이다 | argparse 형에서 유한하고 0보다 큰 값만 받는다 |
| 5 | C | `scripts/live_scenario.py:129` | FAIL 문구가 실제로 기다린 시간이 아니라 설정값을 `.0f`로 찍는다(`--timeout 0.5`로 1 s를 기다리고 "after 0s") | 기다린 시간을 찍는다 |
| 6 | P | `locus/shared/llm/openai_provider.py:28`, `:72`, `:111`; `pyproject.toml:22` | V9가 `api_key`를 pydantic v2 `SecretStr`로 넘긴다. langchain-openai 0.1.x(pydantic v1 필드)는 이를 받지 않는데 의존성 하한(`>=0.0.5`)은 그 판을 허용한다. 지금 판(1.4.3)에서는 키가 맞게 닿는다 | 하한을 `langchain-openai>=0.2`로 올린다 |
| 7 | C | `tests/api/test_demo_seeding_api.py:24`(V7부터) | `Settings()`의 기본 `data_dir=./data` 때문에 시험을 돌릴 때마다 저장소의 `./data/backups`에 World File 백업 4개를 쓴다. 메인 저장소에 이미 369개가 쌓였다(git 무시 파일) | 그 시험의 `data_dir`를 `tmp_path`로 둔다 |

## 3. 지적 — low (시험)

| # | 판정 | 위치 | 무엇이 틀리나 | 고칠 방향 |
|---|---|---|---|---|
| 8 | P | `scripts/live_scenario.py:305` | 10a의 왜곡도 단언이 사건이 닿은 정도와 묶여 있지 않다. LLM이 있으면 항구의 피드백 몫(0.10)만으로 0.3을 넘으므로, 사건 delta가 왜곡도에 쓰이지 않는 퇴행이 생겨도 PASS할 수 있다 | `/state`의 `feedback_share`를 빼고 `near.distortion − share ≥ 0.3 + near_c − ε`를 단언한다 |
| 9 | C | `tests/test_live_scenario.py:223-225` | 가짜 서버가 `?status=`를 버린다. `status=active`를 빼도 모든 시험이 통과한다 | 가짜에 해소된 사건을 하나 더 두고 `status`로 거른다 |
| 10 | C | `tests/test_live_scenario.py:53-79`, `:358-382` | 0.3 문턱이 위쪽에서 고정되지 않는다(0.55로 바꿔도 통과). 키 없는 실제 API 시험은 10a의 숫자를 보지 않는다 | 항구 0.31·Ironcrag 0.30인 PASS 사례를 더하고, 키 없는 실행의 10a 숫자를 단언한다 |
| 11 | C | `tests/test_live_scenario.py:397-408` | JSON 아님 시험이 HTML을 `/export`에 넣는다. 옛 스크립트도 그 경로는 이미 FAIL(TypeError)이었다. traceback이 나던 경로는 `/health`다 | `/health`에 넣는다 |
| 12 | C | `tests/test_live_scenario.py:411-424` | HTTPException 계열은 BadStatusLine 하나만 시험한다(잡는 대상을 그것으로 좁혀도 통과) | `IncompleteRead`를 더한다 |
| 13 | C | `web/src/__tests__/i18n.style.test.ts:82` | 거짓 양성: 해요체 줄 안의 연결어미 `-(으)니까`나 `…다니다`도 합니다체로 본다(지금 걸리는 줄은 없다) | #1과 같은 받침 ㅂ 기준 |
| 14 | C | `web/src/__tests__/i18n.style.test.ts:89` | 해요체 확인은 줄이 `.`으로 끝날 때 마지막 문장에만 돈다. 에디터 줄은 대부분 마침표가 없어 `"이곳에 사는 NPC가 없다"`(해라체)가 통과한다 | 범위 안의 줄이 `다`·`까`로 끝나면 막고, 마침표로 나눈 문장마다 해요체를 본다 |
| 15 | C | `web/src/__tests__/i18n.style.test.ts:107-114`; `web/src/i18n/ko.ts:383`, `en.ts:367` | 쓰임 시험이 `` `word.${…}` ``·`` `enum.${…}` `` 같은 묶음을 첫 마디로 떼어 그 아래 키를 모두 쓰인 것으로 센다. 그래서 V2부터 읽는 곳이 없는 `word.rumor.promoted`가 남아 있고, code-summary의 "화면이 쓰지 않는 사전 키가 없다"는 사실이 아니다 | `word.rumor.promoted`를 지운다. `word.`·`enum.`은 `BANDS`·`ENUM_VALUES`에서 키 집합을 만들어 대조한다 |
| 16 | C | `web/src/__tests__/i18n.style.test.ts:111-113` | 주석 안의 `"key"`도 쓰임으로 센다 | 주석을 걷어 낸 뒤 맞춘다 |
| 17 | C | `web/src/__tests__/i18n.style.test.ts:81-82`, `:107-123` | 자기 점검이 규칙을 느슨하게 고치는 것(묶음을 첫 마디로, `"prefix." +` 인식 빼기, `니까` 빼기, 앞머리 목록에서 `map.hint.` 빼기)을 막지 못한다 | 자기 점검을 몇 개 더한다 |
| 18 | C | `web/src/__tests__/document-head.test.ts:22-36`; `web/src/i18n/index.ts:36` | favicon은 있는지만 본다(깨진 XML도 초록). theme-color를 보지 않는다. 모듈을 읽을 때 `lang`을 맞추는 줄을 지키는 시험이 없다(빼면 저장된 en에서 `/api/langs`가 답할 때까지 `lang`이 ko다) | SVG를 파싱해 루트가 `svg`인지, theme-color가 있는지, 저장된 en으로 모듈을 다시 읽으면 `lang`이 en인지 단언한다 |
| 19 | P | `web/src/__tests__/components.test.tsx:285` | 바꿔 넣은 `"— 없음 —"`은 지금 `editor.region.noParent`의 문장이다. 단언이 주석의 의도(GM에 죽은 세션 항목 없음)와 다른 것을 본다. 원래 막던 회귀는 키가 사라져 다시 생길 수 없다 | 단언을 지운다 |
| 20 | P | `web/index.html:11`; `web/public/favicon.svg:2-4` | `#17120e`·`#e2a54b`는 `index.css`의 `--color-bg`·`--color-accent` 값을 베낀 것이다. design grep은 `src`만 본다 | 두 색이 토큰 값과 같은지 단언한다 |
| 21 | P | `tests/conftest.py:20-47` | 시험 중 연결된 엔진이면 무엇이든 dispose한다. module·session 범위 엔진 픽스처가 생기면 둘째 시험이 깨진다(재현: `no such table`). 지금은 그런 픽스처가 없다 | 시험 안에서 처음 연결된 엔진만 dispose한다 |
| 22 | C | `pyproject.toml:74-76`, `ci.yml` | "ResourceWarning 0"을 지키는 게이트가 없다. dispose를 빼도 1244건이 통과하고 53줄이 돌아온다 | pytest `filterwarnings`에 `error::pytest.PytestUnraisableExceptionWarning`을 둔다 |
| 23 | C | `tests/world/topology/test_topology.py:69-74`; `locus/world/topology/hierarchy.py:54-68` | 순환 시험이 `_break_cycles`에 닿지 않는다(`resolve_region`이 먼저 부모를 버린다). V9가 고친 루프를 지나는 시험이 없다 | `_break_cycles`를 직접 시험한다(순환 하나, 꼬리 하나) |
| 24 | C | `tests/shared/test_config.py:85-119` | 기록용 가짜가 `api_key`를 단언하지 않는다. V9가 바꾼 인자가 바로 이것이다(가려진 키로 바꿔도 통과) | `api_key.get_secret_value() == "k"`를 단언한다 |
| 25 | C | `tests/shared/storage/fakes.py:83`, `:98`, `:196` | 저장된 간선이 호출자·읽은 쪽과 `properties` dict를 공유한다(Neo4j는 아니다). 지금 이 때문에 잘못 통과하는 시험은 없다 | 넣고 읽을 때 dict를 복사한다 |
| 26 | P | `pyproject.toml:43` | "mypy 오류 0" 게이트인데 mypy·langchain 판이 고정돼 있지 않다. 새 판이 나오면 코드 바뀜 없이 CI가 빨개질 수 있다 | 판 고정은 잠금 파일·의존성 선언(요구 § 9, RE-T04)과 한 묶음이다 |

## 4. 지적 — low (문서)

| # | 판정 | 위치 | 문서가 말하는 것 | 실제 |
|---|---|---|---|---|
| 27 | C | `operations.md:404` | 1024px 아래에서 "the map in a dialog" | 지도는 패널 위에 그대로 있다(`EditorPage.tsx:194-195`). 대화상자는 새 지역·새 연결뿐이다 |
| 28 | C | `operations.md:334-339` | U7의 "GM mode" 버튼, `GmHub`, `ManualTurnPanel` | V6가 지웠다. 〔Follow-up V6〕 메모가 없다 |
| 29 | C | `operations.md:172-175` | 타임라인이 앱 시계를 쓰는 "유일한 테이블" | 메시지·행적·평가도 쓴다(`postgres_repo.py:550,589,656`) |
| 30 | C | `operations.md:229-232` | CLI는 번역을 지우지 않는다 | `world demo`는 지운다(V3). 같은 문서 § U8의 메모와 어긋난다 |
| 31 | C | `operations.md:467` | `/health`는 `ok` 아니면 `degraded` | 경계가 하나도 없으면 503 `unavailable`이다(`api/main.py:188-199`) |
| 32 | C | `web/README.md:31-32` | 데모가 있으면 [continue]·[new session] | 열린 세션이 있을 때만이다. 불러왔지만 세션이 없으면 [play now]가 그대로다(`DemoCard.tsx:14-18`) |
| 33 | C | `next-cycle.md:115`(RE-W16) | CLI `world import`·`build`가 API와 다르다 | `:234`는 `world demo`이고, `world build`는 임베딩을 갖춘다(`__main__.py:169`). "import·demo"다 |
| 34 | C | `next-cycle.md:31`, § 4 말투 줄, `:37`·`:128` | U8 메모 3의 위치 `:51-53` | 첫 탐지는 `start_run :45-49`다. § 4 말투 줄에 `ko.ts:282`가 빠졌다. RE-P14가 § 2와 § 5에 두 번 나온다 |
| 35 | P | `next-cycle.md` | RE 정리 항목을 넘겼다 | `code-quality-assessment` § F(죽은 코드·중복, RE id 없음)가 목록에 없다(예: `topology/builder.py:109` `set_wiki`) |
| 36 | P | `README.md:41-42` | 키가 없을 때 꺼지는 것 | 선언 서술은 고정 문장, 대화를 마쳐도 판단 없음, 행적 소문도 퍼지지 않음이 빠졌다(`operations.md:318-319`) |
| 37 | C | `operations.md:26-27` | `related-priors`가 다른 월드의 prior를 준다 | 늘 0건이다. CLAUDE.md는 고쳤고 이 문서는 그대로다 |
| 38 | C | `operations.md:44`, `:60`, `:75`, `:472` | 경로 `advance-turn` | 실제는 `POST /api/gm/sessions/{sid}/advance`다(U4 때 바뀜) |
| 39 | C | `operations.md:207` | NPC 호출이 재시도 뒤에도 실패하면 500 | 503 `llm_failed`다(`api/errors.py:71`) |
| 40 | C | 계획 `:139`(Step 8.4) | [x]인데 "V1·V3 운영 메모"가 남아 있다 | R-02로 하지 않기로 했다. 줄에 그렇게 적는다 |

## 5. 돌연변이 요약

| 각도 | 돌연변이 | 잡힘 | 살아남음 |
|---|---|---|---|
| 백엔드 | 22 | 12 | 10 — 시험 공백(#22 dispose, #23 순환 둘, #24 키), 동치 넷(linker 정렬, reconciler 가드, retry 결합 시점, 대역 실패 주입), 연결 확인 둘(`verify_connectivity`·`info()`, 대역으로는 닿지 않음) |
| 라이브 | 26 | 19 | 7 — 시험 공백(#9, #10, #12), 동치 셋, 기존 코드 하나 |
| 웹 | 24 | 9 | 15 — 말투 규칙(#1, #14 다섯), 쓰임 시험(#15, #16, #17 여섯), 머리(#18 셋), theme-color |

구현 때의 36개와 겹치지 않는다.

## 6. 확인하고 문제없음

- **수치**: pytest 1244건 수집·통과, vitest 40파일 821건, mypy 0(167파일), npm audit 전체 0, ruff·black(`locus api tests scripts`) clean. 가장 느린 시험 1.33 s, 시간을 기다려 지나가는 시험 없음, `-X dev`에서도 ResourceWarning 0.
- **mypy 고침은 동작을 바꾸지 않는다.** hierarchy 루프를 옛 코드와 무작위 20만 번 비교해 부모·경고가 한 번도 다르지 않았다. linker 정렬, reconciler 가드, neo4j·opensearch `connect`는 동치다. `SecretStr` 키는 지금 판의 클라이언트에 원래 키로 닿는다.
- **재시도**: 실제로 1 s·2 s를 잔다. `retry-after-ms`도 따른다.
- **잠금 순서 시험**: 300회 반복과 부하 반복에서 실패 0, 잠금을 뺀 코드는 한 번도 통과하지 못한다. 모든 대기에 시한이 있어 멈추지 않는다.
- **대역**: 식별 키·방향·병합(`+=`)·전체 교체(`=`)가 Neo4j와 맞는다. 병합 대역으로 전체가 GREEN이다.
- **10a는 실제 스택에서 성립한다.** 마름병 씨앗은 지속형이라 10a 때도 ACTIVE다. 두 턴 적용으로 항구 기여 0.30, Ironcrag 0.0612다. 키 없음: 항구 0.60, Ironcrag 0.3612. 가짜 LLM: 항구 0.70(피드백 0.10), Ironcrag 0.3612. 15/15 PASS. 소문 피드백·support 진화·GM 설정은 10a를 뒤집지 못한다.
- **`_ok`의 JSON 검사는 정상 응답을 FAIL로 만들지 않는다.** 시나리오가 부르는 경로는 모두 JSON을 돌려준다. 204 경로는 부르지 않는다.
- **예외 처리**: 현실적인 연결·HTTP 오류는 모두 FAIL로 받는다(남는 것은 #4의 OverflowError).
- **지운 키 11개**는 web·api·locus·scripts 어디에서도 쓰이지 않는다. 묶음으로도 만들어지지 않는다. 대체 키가 화면에 있다.
- **고친 ko 24줄**은 자리표시가 그대로이고, 해요체로 자연스럽고, en과 뜻이 맞는다. 에디터·지도 화면에 남은 합니다체는 없다.
- **`index.html`과 favicon**: 설명이 README 첫 줄과 같다. SVG는 올바르다. `vite build`와 nginx가 내준다.
- **잠금 파일**: 바뀐 17개가 모두 dev이고, `npm ci --dry-run`이 된다.
- **CLAUDE.md**의 Gates·포트·V1~V9·What runs·Frontend·Code·Conventions가 모두 맞다.
- **docstring** 바꾼 곳이 모두 코드와 맞는다.
- **next-cycle**: 60줄 넘게 대조해 위치와 "열림"이 맞았다. Step 9.2 목록에서 빠진 항목이 없다.

## 7. 처리 (2026-10-12)

사람의 답: **A — 거의 모두 고침(권장)**. 39건을 고쳤고, #26만 next-cycle § 8(잠금 파일·의존성 선언, 요구 § 9)에 붙였다.

| 지적 | 처리 | 커밋 |
|---|---|---|
| #1, #13, #14 | 말투 규칙을 NFD로: 받침 ㅂ+니다/니까, 십시오, 문장 끝 시오를 줄 어디서든 잡는다. 마침표로 끝나는 문장마다 해요체(괄호 덧말은 그 문장에 속한다), 줄 끝의 맨 다/까는 막는다. 자기 점검 다섯 | `011f7e7` |
| #2 | README: NPC는 에디터에서, 사건 씨앗은 World File의 `event_seeds`로. `carry_over.py` docstring, code-summary § 3.1, README 문장 시험(`test_packaging.py`)도 같이 | 문서 커밋 |
| #3 | next-cycle 약어를 § 1 번호와 § 3 번호로 나누고, § 0에 닫은 유닛을 번호마다 적었다(V3 #11, V5 #5(a)·#9·#12, V6 #14·#15, V7 #10·#13) | 문서 커밋 |
| #4, #5 | `--timeout`은 0보다 큰 유한한 수, `--poll`은 유한한 수(argparse 종료 코드 2). FAIL은 기다린 시간을 적는다 | `10bdc20` |
| #6 | `langchain-openai>=0.2`(pyproject, requirements.txt) | `c53e527` |
| #7 | 세션 픽스처가 `LOCUS_DATA_DIR`을 임시 폴더로. 전체 실행 뒤에도 `data/backups`는 369개 그대로다. 옛 파일은 사람이 지울 것으로 두었다 | `c53e527` |
| #8 | 10a: 항구 왜곡도 − 피드백 몫 ≥ 0.3 + 사건 기여. 피드백이 대신 올린 경우 둘(0.40, 0.65)을 FAIL로 시험 | `10bdc20` |
| #9~#12 | 가짜가 해소된 사건을 앞에 두고 `status`로 거른다. 0.31 PASS와 키 없는 실행의 숫자(0.60/0.30, 0.36/0.06). HTML을 `/health`에. `IncompleteRead` | `10bdc20` |
| #15~#17 | `word.rumor.promoted` 지움. `word.`·`enum.`은 `BANDS`·`ENUM_VALUES`의 키만. 주석은 쓰임이 아니다. 자기 점검을 더함 | `011f7e7` |
| #18, #20 | favicon을 SVG로 파싱, theme-color와 아이콘 색이 토큰과 같은지, 저장된 en이 첫 로드부터 `lang`인지 | `011f7e7` |
| #19 | 단언 지움 | `011f7e7` |
| #21 | 시험 안에서 처음 연결된 엔진만 닫는다(세션 전체 리스너 + WeakSet). module 범위 엔진 시험 | `c53e527` |
| #22 | `filterwarnings`: `error::ResourceWarning`, `error::pytest.PytestUnraisableExceptionWarning` | `c53e527` |
| #23 | `_break_cycles` 직접 시험(순환, 꼬리, 사슬). 꼬리의 부모를 끊던 것을 고쳤다(순환을 만나면 r이 그 순환에 있을 때만 끊는다) | `c53e527` |
| #24 | LLM·VLM·임베딩의 `api_key.get_secret_value() == "k"` | `c53e527` |
| #25 | 대역이 노드·간선을 깊게 복사해 넣고 읽는다. 시험 하나 | `c53e527` |
| #26 | next-cycle § 8 잠금 파일 줄에 붙임 | 문서 커밋 |
| #27~#34, #36~#39 | 문서를 코드대로 고침(operations 〔Follow-up〕 메모 넷, `/health` 503, 503 `llm_failed`, `advance-turn` 메모, web/README 데모 카드 상태, README 키 없음의 "달라집니다", next-cycle 위치 셋과 RE-P14 하나로) | 문서 커밋 |
| #35 | next-cycle § 5에 RE § F 줄(표본 둘 확인) | 문서 커밋 |
| #40 | 계획 Step 8.4 줄에 R-02로 하지 않았다고 적음 | 문서 커밋 |

고친 뒤: pytest 1262, vitest 825, mypy 0, npm audit 0/0, ResourceWarning 0(이제 오류), 첫 화면 JS 119.39 kB. 고침의 돌연변이 34개가 모두 잡혔다(code-summary § 9).

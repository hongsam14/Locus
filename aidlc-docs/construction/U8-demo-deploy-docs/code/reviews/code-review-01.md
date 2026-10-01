# U8 데모·배포·문서 — Code Review 01

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG. U8은 처음 온 사람이 준비 명령과 기동 명령으로 띄우고 클릭 한 번으로 데모 월드에서 플레이하게 하는 마지막 유닛이다.
- 데모는 데이터다: 매니페스트와 World File(Emberleaf Isle), `/`의 원클릭 카드, GM이 [시작]하는 사건 씨앗(US-1.3)
- 키 없이 둘러보기: `GET /api/capabilities`, 화면 안내와 LLM 버튼 끄기, 503(US-1.4)
- compose·CI·README·라이선스(US-1.1·1.2·7.3·7.5·7.6), 라이브 시나리오(BR-U8-36)
- U3 리뷰 이월(#10·#12~#15, S01~S32, C1~C17)

**이 리뷰가 하는 것**: 승인된 U8 코드(`git diff 589dc2b..7490b4b`, 커밋 20개)가 위 경험과 승인된 규칙(BR-U8-*)을 지키는지, 이월한 U3 지적을 실제로 닫았는지 버그 위주로 확인한다. 코드는 고치지 않았다(리뷰 전용).
- 크기: 백엔드 63파일 +1474/−373(`locus/`·`api/`·`scripts/`, 데모 데이터 제외), 웹 35파일 +1047/−325(`web/src`, 테스트 제외), 배치·메타 12파일 +201/−56, 데모 데이터 5파일 +1860/−665, 테스트 36파일 +3823/−94.
- HEAD 3a6b5b6은 문서만 바꿨으므로 코드는 7490b4b와 같다.

**대상**: `locus/shared/{models,storage}/*`(EventSeed, `replace_edges`·`edges_touching`), `locus/knowledge/loader.py`, `locus/world/{worldfile,demo,editor,augmentation,wiki}/*`·`npc_drafts.py`·`ingestion/service.py`, `locus/play/{event/{seeds,service},distortion_service,storage/*,gm/narrator,turn/advancer,rumor/*,session_service}.py`, `locus/__main__.py`, `api/{main,deps,errors,schemas,uploads}.py`·`routers/{world,world_editor,gm}.py`, `web/src/**`(`features/{home,gm,editor,play}/*`, `routes/*`, `capabilities.ts`, `api/*`, `i18n.ts`, `ui/*`), `scripts/{live_scenario.py,setup-volumes.sh}`, `docker-compose.yml`, `web/{Dockerfile,nginx.conf}`, `.github/workflows/ci.yml`, `env.example`, `pyproject.toml`, `requirements.txt`, `README.md`, 데모 데이터, 테스트. 바뀐 파일과 같은 함수 안의 손대지 않은 줄도 함께 봤다.
설계 기준: `functional-design/*`(BR-U8-1~36, TP-U8-1~8, EX-1~14), `infrastructure-design/*`, `plans/U8-demo-deploy-docs-code-generation-plan.md`(이월 결정 표 포함), `code/code-summary.md`(§6 이탈·알려진 한계), 이월 원본 `U3-world-editor/code/reviews/code-review-01.md`.
**방법**: `/code-review` max(재현율 우선).
- 탐색 각도 16개를 병렬로 돌렸다.
  - 줄 단위 일곱: shared·데모·CLI / 에디터·보강·wiki / play / API / 웹 에디터 / 웹 홈·GM·플레이 / 배치·CI·스크립트
  - 제거된 동작, 호출처 추적, 언어 함정, 래퍼·어댑터
  - 재사용, 단순화, 효율, 고도(altitude), CLAUDE.md 규약
  - 이 세션도 직접 후보를 찾았다(#1, 라이브 시나리오의 예외 처리).
- 후보를 중복 제거한 뒤 검증자 13명이 후보마다 CONFIRMED / PLAUSIBLE / REFUTED를 따로 판정했다. 정확성 후보는 검증자 하나가 2~7건을, 정리 후보 16건은 검증자 하나가 맡았다. 검증자는 가능한 한 운영 조립(`assemble_*`)과 실제 라우트로 다시 재현했고, 필요하면 589dc2b 트리를 따로 풀어 옛 동작과 비교했다. 승인된 설계가 고른 동작은 결함에서 빼고 설계 메모로 옮겼다(§4·§5).
- 마지막에 새 검토자 1명이 목록에 없는 틈만 찾았다(sweep). sweep이 찾은 4건은 검증자 1명이 따로 판정했다(§1 #2, §3, §5).
- 실제 Neo4j·PostgreSQL은 쓰지 않았다. Neo4j 쪽은 어댑터의 Cypher를 그대로 따르는 에뮬레이터로, PostgreSQL 쪽은 SQLite 파일 위의 운영 SQL 어댑터(`PostgresPlayRepository`)로 재현하고 나머지는 추론으로 적었다(해당 지적에 표시).
- 재현 스크립트·vitest는 모두 세션 scratchpad에만 두었다. 저장소에는 이 기록 파일만 더했다.
  - `pytest`는 hypothesis 저장소를 scratchpad로 돌리고 `--no-cov -p no:cacheprovider`로 돌려 `.hypothesis/`·`.coverage`를 건드리지 않았다.
  - 한 탐색 각도의 재현이 작업 디렉터리를 저장소로 둔 채 월드를 교체해, git이 무시하는 `data/backups/`에 백업 파일 4개가 생겼다. 그 자리에서 지웠고, `data/`의 기존 bind mount 폴더(neo4j·opensearch·postgres)는 그대로다. 그 뒤 모든 재현은 작업 디렉터리와 `LOCUS_DATA_DIR`를 scratchpad에 두었다.
  - vitest 사본은 `web/node_modules`를 심볼릭 링크로 써서 git이 무시하는 `web/node_modules/.vite*` 캐시가 바뀌었다.
  - 리뷰를 마친 뒤 `git status`에는 이 기록 파일만 보인다.

## 1. 지적 (상한 15, 심각도 순)
판정: C = CONFIRMED(입력·결과로 재현), P = PLAUSIBLE(기제는 실재, 발생 조건이 타이밍·설정에 달림). 괄호 안은 그 지적을 독립적으로 찾은 탐색 각도 수다. 15건 모두 C다. #9의 PostgreSQL 쪽과 #10의 Neo4j 쪽은 위에 적은 방식으로 재현했고, #2의 둘째 계기(nginx 130초)만 실제 빌드 시간에 달려 P다.

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `web/src/features/home/DemoCards.tsx:17`, `DemoCard.tsx:35·63·81-88`, `routes/HomePage.tsx:57` | 데모 카드는 `/demos`가 오면 바로 그려지고, 월드가 있는지는 HomePage의 `worlds`로 안다(`new Set((worlds ?? []).map(…))`). `/worlds`가 아직 오지 않았거나 실패하면 모든 카드가 "없음"이다. `/demos`는 조립 때 읽은 매니페스트라 그래프·DB를 읽지 않고, `/worlds`는 월드마다 그래프와 PostgreSQL을 읽어서 보통 카드가 먼저 켜진다. 이때 [바로 플레이]와 [에디터에서 보기]는 `loadDemo(name, name, {replace:true, confirm:false})`를 보낸다. 열린 세션이 없으면 서버는 묻지 않고 편집된 월드를 교체한다(백업만 남고, 성공하면 백업 경로도 보이지 않는다). 열린 세션이 있으면 "열린 세션 N개를 닫을까요?"만 묻고 교체 질문은 건너뛴다. BR-U8-5(교체 확인), BR-U8-20(지금 월드로/새로 불러와), BR-U8-21([에디터에서 보기]는 다시 불러오지 않음)과 어긋난다. `/`에 들어올 때마다 열리는 창이고, `/worlds`가 실패하면 닫히지 않는다. 옛 홈은 `worlds?.length === 0`일 때만 데모 버튼을 보였다 | C (7각도 + 이 세션) | **medium** | `worlds`가 `null`인 동안(실패 포함) 카드 버튼을 끈다. 또는 "없음" 갈래를 `replace=false`로 보내고, 서버의 409 "world already exists"를 "지금 월드로/새로 불러와" 선택으로 바꾼다. 목록 대기·실패 vitest를 더한다 |
| 2 | `web/src/routes/EditorPage.tsx:36·124·198`, `routes/HomePage.tsx:24·47·109`, `features/editor/BuildPanel.tsx:43·67·105`, `locus/world/build.py:177-179` | U3 #14 수정이 BuildPanel을 열 때마다 새 key로 다시 마운트한다. 그런데 빌드(분 단위 LLM 작업)가 도는 동안에도 [닫기]가 켜져 있어서, 닫았다 다시 열면 `busy=false`인 빈 패널이 나온다("working" 줄 없음). 입력을 다시 넣으면 같은 월드의 두 번째 빌드가 함께 돈다. 서버에는 월드별 빌드 잠금이 없고, 있는지 검사(`build.py:177-179`)가 긴 준비 단계 앞이라 둘 다 통과한다. `/`의 새 id면 두 빌드가 모두 커밋해 지역이 두 벌이 된다. 첫 빌드의 리포트·백업 경로·오류는 내려간 인스턴스에 써져 보이지 않는다. 589dc2b에서는 같은 인스턴스가 남아 다시 열면 "working"과 꺼진 제출이 보였다. sweep이 찾은 둘째 계기(P)도 있다. compose의 nginx는 `/api`를 130초에 끊는다(Infra §3.2가 대화 한 줄에 맞춰 다시 승인한 값). Emberleaf 소스 빌드만 해도 LLM 호출 34~59번과 임베딩 21번을 차례로 해 gpt-4o 지연으로 약 84~150초다. 130초를 넘기면 패널은 nginx 504 HTML을 원문으로 보이고 [만들기]를 다시 켠다. 서버 빌드는 계속 돌아 나중에 월드를 조용히 교체하고, 다시 누르면 패널을 닫지 않아도 같은 겹침이 생긴다. 작은 빌드의 130초는 U8 이전에도 같았고, U8은 49m으로 큰 업로드를 통과시키고 README로 :3000을 주된 시작 방법으로 만들었다 | C (1각도) + 둘째 계기 P (sweep) | **medium** | 빌드가 도는 동안은 key를 바꾸지 않거나 `busy`·리포트를 부모로 올린다(#14가 요구한 것은 파일·리포트 비우기다). 서버가 같은 world_id 빌드를 한 번에 하나만 받게 한다(U2 BLM:163은 "막지 않는다(문서에 적는다)"인데 운영 문서에 그 줄이 없다). 빌드는 202 + 진행 조회로 바꾸거나 `/build` 경로의 nginx 시간을 늘린다. 빌드 중 닫고 열기 vitest를 더한다 |
| 3 | `scripts/live_scenario.py:212-224·284-288`, `tests/test_live_scenario.py:162-167`, `locus/play/turn/advancer.py:408·422` | 행적은 대화를 마칠 때(EndTalk)만 판단되고(BR-U6-7, `appraise`의 호출처는 advancer:422 하나), 판단이 있어야 소문 씨앗이 된다. 스크립트는 선언만 하고 `end_talk`를 보내지 않으므로, 키가 있어도 선언한 행적은 판단되지 않고 `seeded`는 늘 False다. 그래서 9(행적 1칸)·11(3칸 전)은 늘 SKIP이고 종료 코드는 0이다("12 passed, 0 failed, 2 skipped"). Build & Test가 돌릴 유일한 라이브 행적 전파 확인(US-6.5, BR-U8-11)이 아무것도 보지 않는다. 테스트의 흉내 서버는 선언 때 바로 씨앗을 만들어 이것을 감춘다. BLM §7 6단계("그 턴 끝에 판단으로 행적 소문이 씨앗된다")의 전제가 BR-U6-4·BR-U6-7과 어긋난다. 또 15.1이 고른 "씨앗이 없으면 SKIP" 규칙은 판단이 전할 만하다고 했는데 소문이 없는 경우(전파가 깨진 경우)도 SKIP으로 만든다 | C (2각도) | **medium** | 선언 뒤 그 지역 NPC와 say + end_talk를 하고(씨앗은 T3, 뒤 턴 번호가 하나씩 밀림), `/deeds`의 appraisals로 "판단 없음·전할 만하지 않음 → SKIP, 전할 만한데 소문 없음 → FAIL"로 가른다. 도착 행적도 판단되어 지역당 전파 한 칸을 차지할 수 있으므로(12번 중 4번 9단계 FAIL) 그 행적을 빼거나 단언을 맞춘다. 흉내 서버는 EndTalk에서만 씨앗을 만든다. BLM §7을 정정한다 |
| 4 | `locus/world/editor/writes.py:80-89`, `knowledge.py:27·34-36·53-55`, `npcs.py:47-48`, `entities.py:39-40` | C11(같은 문서는 다시 색인하지 않음)과 S29(신뢰도가 바뀌면 DIRECT 스코프 엣지 값도 고침)가 "무엇이 바뀌었나"를 그래프 노드에서 읽는다. 그런데 노드를 먼저 쓰므로, 그 뒤(색인 또는 스코프 쓰기)에서 끊긴 요청을 그대로 다시 보내면 노드가 이미 새 값이라 둘 다 건너뛰고 200을 준다. (i) 노드 0.3·SCOPED_TO 0.9로 남아 지역 보기(direct)·NPC 사실 고르기·brief가 낡은 값을 쓴다. S29가 고치려던 바로 그 증상이다. 화면에서도 생긴다: 보강 "맞음"(0.3 → 0.9)에서 OpenSearch가 한 번 실패하면 500이고, 질문이 남아 다시 누르면 200인데 노드 0.9·엣지 0.3이며 low_confidence 질문은 더 나오지 않는다. (ii) 지식·NPC·엔티티 검색 문서가 옛 글·옛 `home_region_id`로 남는다. U8 전에는 재시도가 다시 색인했다(지금은 WikiPrior만 검색하므로 잠복). 모듈 계약("a retry finishes the job", BR-U3-8)과 어긋난다 | C (7각도) | low–medium | 비교 기준을 저장된 쪽으로 바꾼다. S29는 `scopes`의 DIRECT 엣지 값이 노드와 다르면 고친다(그러면 §5 설계 메모 4의 기존 어긋남도 저장 한 번에 풀린다). C11은 저장된 검색 문서(또는 글 해시)와 비교하거나, 임베딩만 건너뛰고 문서는 쓴다. 끊고 다시 보내는 테스트(TP-U3-2a 방식)에 스코프 값과 검색 문서를 단언한다 |
| 5 | `web/src/routes/PlayPage.tsx:26·210-221`, `locus/play/turn/guard.py:44-47` | S02 수정은 `turn_running`인데 진행 중인 run이 없으면(GM 쓰기가 세션을 쥠) 1초마다 최대 5번 다시 읽고 멈춘다. (a) U3 S02의 상황(GM이 생성·제안 중에 플레이로 돌아옴)은 대개 5초보다 길다. Emberleaf 마을 하나의 생성은 LLM 호출 12~36번을 잇달아 하고, 전체 생성은 219번을 5개씩 한다. 그래서 GM 쓰기가 끝난 뒤에도 이동·기다리기가 새로고침 전까지 꺼져 있다. 이월한 지적이 그 상황에서는 닫히지 않았다(상한은 플랜 S02 행이 골랐다). (b) 다시 읽기 하나가 실패하면 `view`가 그대로라 효과가 다시 걸리지 않고 재시도가 그 자리에서 끝난다. 파일 머리의 "모든 경로가 다시 읽어 `turn_running`이 버튼을 잠그지 않게 한다"(U4-2 #15)와 어긋난다 | C (3각도) | low–medium | 서버가 `turn_running`을 TurnRun이 있을 때만 참으로 하고(U4 domain-entities의 정의) GM 보유는 따로 알린다. 아니면 상한 없이 간격을 늘리며 읽는다. (b)는 실패한 읽기도 다음 읽기를 예약하게 한다. (a)의 방향은 §7에서 정한다 |
| 6 | `locus/world/augmentation/apply.py:194-216·265-289`, `engine.py:81-84` | S03 수정은 되돌리기가 그래프를 다 되돌린 뒤(검색·WorldMeta 쓰기)에 끊긴 경우만 이어 준다(`is_undone`이 전부 아니면 전무). 되돌리기의 그래프 쓰기 사이에서 끊기면(Neo4j는 쓰기마다 auto-commit) 그래프가 반쯤 되돌아간 채 남고, 재시도는 자기 반쪽 쓰기를 run 밖 편집으로 보고 409 "… was edited after this change"를 계속 낸다. 그 변경이 끝내 되돌려지지 않으므로 앞 변경도 순서 409로 막혀 그 run의 되돌리기가 통째로 멈춘다. 데이터도 잃는다. 연결의 dangling prior 답을 되돌리다 `upsert_edges`에서 끊기면 연결 쌍이 사라지고(2 → 0), gap/add 되돌리기가 `delete_node`에서 끊기면 더한 지식이 스코프 없이 남는다. S29 때문에 "맞음"·신뢰도 고침도 이제 SCOPED_TO를 기록하므로, 그 되돌리기가 끊기면 지식이 스코프 없음이 된다(U8에서 새로 생김, 앞의 둘은 U3부터). S03 테스트는 그래프 뒤만 끊는다 | C (4각도) | low–medium | 되돌리기를 항목별 멱등 쓰기로 바꾼다. 같은 identity는 `replace_edges`로 제자리 교체하고, `revert_started`가 서 있으면 각 항목이 before·after 어느 쪽이어도 받아들여 같은 쓰기를 다시 한다. 그러면 `is_undone`·`finish_revert`가 필요 없다. 되돌리기의 모든 쓰기 자리에서 끊는 테스트를 더하고 code-summary 9b의 "409가 나지 않는다"를 고친다 |
| 7 | `locus/world/augmentation/engine.py:94-106·124-133` | S09는 실패한 wiki 조회를 캐시하지 않게 했는데, 같은 탐지 안에서도 기억하지 않는다. 검색(임베딩 또는 OpenSearch)이 실패하면 같은 (지형, 지역) 키를 가진 (지식, 지형) 쌍마다 실패한 조회를 다시 하고, JUDGE_MAX는 prior를 찾은 쌍만 세므로 묶지 못한다. 탐지는 시작·답·무시·되돌리기·unignore마다 run 잠금 안에서 돈다. 조회 하나는 `with_retry` 3회(최소 3초)다. Emberleaf에서 요청마다 21번(63초)이고, U8 전에는 run당 11번 뒤 0번이었다. 429 Retry-After면 요청마다 336초, 시도마다 시간 초과면 약 32분이라 nginx 130초를 넘겨 504가 되고, 그동안 잠금을 쥔다. OpenSearch만 죽으면 탐지마다 성공한 임베딩 21번이 청구된다 | C (4각도) | low–medium | 이번 탐지 안에서 실패한 키를 기억하거나(11번), 탐지에서 첫 실패 뒤 wiki 단계를 멈춘다(1번). 짧은 TTL로 실패를 캐시하는 것도 방법이다. "탐지마다 다시"는 플랜 S09가 골랐으므로 그 비용을 NFR 문구에 적을지는 §5 설계 메모 2에서 정한다 |
| 8 | `locus/world/augmentation/questions.py:86-89`, `apply.py:84·173`, `api/routers/world.py:448-451` | C2는 연결 대상을 `a\|b\|kind` 문자열 대신 ConnectionKey로 싣자는 것이었다. U8은 키를 그 문자열에서 다시 쪼개 만들고 `ConnectionKind(kind)`로 엄격하게 바꾼다. 그래서 지역 id에 `\|`가 있고(Region.id에 제약이 없어 `POST /regions`·World File로 된다) 그 지역의 연결이 없는 prior를 가리키면(WikiPanel에서 인용된 prior를 지우면 생긴다) `start_run`이 ValueError로 실패해 `POST /augmentation/runs`가 500이다. 그 월드에서는 보강을 시작할 수 없다. U8 전에는 질문 하나의 이름만 이상했다. run 도중이면 gap/add 답이 400을 주면서도 사실은 쓰고 기록하며, 질문은 0개가 된다(S15). 답 경로는 여전히 문자열을 쪼개서 U3 C2 증상(400 "too many values to unpack")도 그대로다. `QuestionTarget.connection`은 웹도 서버도 읽지 않는다 | C (5각도) | low–medium | 탐지기가 이미 가진 `ConnectionKey.of(c)`(detectors.py:137)를 Issue에 싣고 questions·apply 세 곳이 그것을 읽는다. 적어도 파싱 실패를 그 이슈 하나에 가둔다. 지역 id에 `\|`를 금지할지도 정한다 |
| 9 | `locus/play/event/service.py:140-159`, `play/storage/postgres_repo.py:265-273` | #10 수정(9d)은 GM 설정 ∥ 해소와 같은 사건의 해소 ∥ 해소를 PG에서 줄 세웠지만, 다른 두 사건의 해소 ∥ 해소는 남았다. 해소는 자기 사건 행만 `FOR UPDATE`로 잠그고, 지역 왜곡도는 잠그지 않고 읽어 절대값으로 다시 쓴다. GM 쓰기는 리스를 나눠 쥐므로(U7 #2), 같은 지역에 기여한 두 사건을 10ms 안쪽으로 해소하면 한 쪽의 복원이 사라진다(기준 0.3, 기여 뒤 0.57 → 0.42/0.45로 남음). 두 사건이 모두 RESOLVED라 되돌릴 길이 없고, 타임라인은 둘 다 복원했다고 적는다. 데드락은 아니다(JSONB 키 순서가 같아 쓰기 순서가 같다). U8 이전부터 있던 경로이고, U3 #10은 겹치는 GM 쓰기를 고치라고 했다. 화면 하나로는 어렵고 GM 탭 둘이나 API로 생긴다 | C (2각도) | low–medium | 짧은 결정적 GM 쓰기(사건 생성·해소·승인, 씨앗 시작, 왜곡도·지지도 설정)를 세션 단위 잠금으로 줄 세운다(U3 #10의 (b)). 그러면 #12와 §3의 피드백 몫 기록도 함께 닫힌다. 아니면 해소가 바뀌는 지역 행을 잠그고 상대값으로 쓴다 |
| 10 | `locus/world/worldfile/remap.py:18-30`, `locus/world/editor/regions.py:111-112`, `locus/shared/storage/neo4j_repo.py:201-202·284` | 씨앗은 World File을 손으로 고쳐서만 편집한다(BLM §8). 씨앗 id가 다른 노드(예: 지역) id와 같아도 불러오기는 ok·경고 0이다. `file_ids`가 집합이라 중복을 조용히 합치고, 검사는 참조만 본다. Neo4j는 라벨마다 유일 제약이라 같은 id의 Region과 EventSeed가 둘 다 생기고, 라벨 없는 `get_node`(LIMIT 1)·`delete_node`가 둘을 가르지 못한다. 그 씨앗의 지역을 지우면 ③b의 `delete_node(world, seed_id)`가 id가 같은 다른 지역을 연결째 지우고, 그 지역 NPC의 집이 끊긴다(경고 없음; 열린 세션 보호는 지우려는 지역만 보므로 그 지역에 선 플레이어도 막지 못한다 — 추론). 인메모리 가짜는 (world, id)로 잡아서 불러올 때 지역이 덮여 사라진다. NPC id가 지역 id와 같을 때도 U8 이전부터 같다. U8은 손으로 고치는 새 길을 더했다 | C (1각도) | low–medium | World File 검사가 절 사이 중복 id를 error로 거른다. 삭제·읽기 쿼리에 라벨을 붙인다(`MATCH (n:EventSeed {id, world_id})`). 가짜를 (world, label, id)로 잡는 것(U3 S26의 원안)도 다시 본다 |
| 11 | `locus/world/demo/__init__.py:169-191`, `world/worldfile/import_.py:56-57`, `tests/world/test_demo.py:101-126` | 매니페스트 검사는 `start_region_id`를 파일의 원래 id로 본다. 그런데 데모는 world id = `name`으로 불러오고(BR-U8-3), 파일의 `world.id`가 다르면 불러오기가 모든 id를 uuid5로 바꾼다(BR-U2-6). 그래서 `name`과 파일 `world.id`가 다른 항목은 검사와 `check_packaged()`를 통과하지만 [바로 플레이]가 매번 400 "start region not in world"이고, [새로 불러와]도 같다. operations.md "Adding a demo"는 둘이 같아야 한다고 적지 않는다. 저장소의 테스트 항목 `name="isle"`(emberleaf 파일)이 바로 이 경우인데 유효하다고 단언하고 불러 보지는 않는다. 시작 지역의 연결이 자기 자신이거나 파일에 없는 지역이어도 통과한다(이동 0, 또는 불러오기가 매번 ok=false). 배포된 emberleaf는 맞으므로 잠복이다 | C (2각도) | low–medium | `_check`가 `file.world.id == name`을 요구하거나, 검사 때 `name`으로 remap한 뒤 시작 지역을 본다. 연결의 다른 끝이 파일에 있고 자기 자신이 아닌지도 본다. test_demo의 isle 항목을 바로잡고 실제로 불러와 세션을 시작한다 |
| 12 | `locus/play/event/seeds.py:54-57`, `api/routers/gm.py:281-285`, `web/src/features/gm/SeedPanel.tsx:52-53` | 씨앗 시작은 "진행 중인가" 검사와 생성 사이에 잠금이 없고, GM 쓰기는 리스를 나눠 쥔다(U7 #2). 두 시작이 수 ms 안에 겹치면(GM 탭 둘, API) 둘 다 201이고 ACTIVE 사건이 둘이 된다. 턴마다 왜곡도 증가가 두 배이고(0.3 → 0.6, 한 번이면 0.45), 목록은 첫 사건만 보여서 그것을 해소해도 "진행 중"이다. TP-U8-5·BR-U8-16과 어긋나고, 테스트는 차례로만 돈다. 웹 [시작]은 요청 중에도 켜져 있다. 사람의 더블클릭(100~250ms)은 대개 201 뒤 409가 되는데, 그 409 원문(`seed already running …`)이 성공한 뒤에도 허브 오류 줄에 남는다 | C (4각도) | low | #9와 같이 짧은 GM 쓰기를 세션 잠금으로 줄 세운다. 아니면 씨앗 시작에 (세션, 씨앗) 잠금을 둔다(BR-U8-18 때문에 저장 제약은 쓰지 않는다). 웹은 요청 중에 [시작]을 끈다 |
| 13 | `locus/world/augmentation/questions.py:40-47`, `apply.py:122-135`, `web/src/features/editor/AugmentQuestion.tsx:55-58` | C2·S06이 질문에 `needs`를 실었는데, 표가 이슈 종류만 보고 대상 종류는 보지 않는다. low_confidence 고치기는 늘 진술·제목·신뢰도를 받는다고 하므로 엔티티 카드에도 제목 칸이 생긴다. 그런데 엔티티 갈래는 제목을 읽지 않는다(U3 BLM:161 "엔티티면 설명·신뢰도"). 제목만 바꿔 보내면 200이고 이름은 그대로이며, 빈 변경이 기록되고 답 수를 쓰며 같은 질문이 다시 나온다. 엔티티를 고칠 다른 화면이 없어 이 칸이 이름 바꾸기로 보인다. U8에서 새로 생겼다 | C (2각도) | low | `needs`를 (이슈, 대상 종류)로 가른다(엔티티 고치기는 진술·신뢰도). 바뀐 것이 없는 답은 기록하지 않는다 |
| 14 | `web/src/features/gm/PlayerStrip.tsx:30-53`, `routes/GmPage.tsx:63·137·142` | S14 수정(띠에 `key={session.id}`, 세션이 바뀌면 표식의 플레이어를 비움) 뒤에도, s1 띠의 `getPlayer(s1)`가 진행 중일 때 s2로 바꾸면 그 답이 늦게 와 `onPlayer(P1)`를 부른다. 띠 효과에 정리 함수가 없어서다. 그래서 s2 지도에 s1 플레이어 표식이 그려진다. s2 읽기가 500이면 S14의 그 상황이고, s2가 성공해도 표식과 띠가 다른 플레이어를 가리킨다. code-summary 11c의 "s2 읽기가 실패해도 s1의 플레이어·표식이 남지 않는다"와 다르다. 표시만 틀린다 | C (1각도) | low | 띠 효과에 `alive` 플래그(정리 함수)를 두거나, `onPlayer`가 세션 id를 함께 알려 GmPage가 지금 세션인지 본다 |
| 15 | `web/src/features/gm/useBulkRumors.ts:35-38·46-50`, `features/gm/RumorPanel.tsx:27-34` | GM 허브의 LLM 없음 처리가 FC §2.5·BR-U8-27대로가 아니다. (a) [전체 생성]·[전체 재생성]은 모든 오류를 실패 수로만 센다. capabilities를 모르거나 낡았을 때(읽기 실패, 서버가 키 없이 다시 뜸) 503 "rumor generation needs an LLM provider"가 "0/2 완료 · 2건 실패"로만 보이고 "LLM 키가 필요합니다"는 어디에도 없다. 단일 [생성]은 그 문구를 보인다. U8 이전에도 같았지만, FC §2.5가 이 두 버튼을 503 문구 대상으로 적었고 code-summary 10.4는 GmHub가 한다고 적었다. (b) RumorPanel의 [생성]·[재생성]은 꺼질 때 title만 있고 옆 글(`llm-required`)이 없다(FC §2.5 "같음", code-summary 10.4 "모두 title과 옆 글"). gm.test는 옆 글이 하나뿐이라고 고정한다 | C (3각도) | low | 일괄 실행이 `needsLlm`이면 그 문구를 알림·오류 줄에 싣는다. LLM이 필요한 버튼과 옆 글을 `ui` 컴포넌트 하나로 묶는다(§2 C6) |


### 지적별 재현 상황
1. **데모 카드의 조용한 교체**: 실제 HomePage(api 모듈만 mock)에서 `/worlds`를 붙잡아 두고 [바로 플레이]를 누르면 `loadDemo("emberleaf","emberleaf",{"replace":true,"confirm":false})`가 바로 나간다. `demo-ask`·확인 창은 0번이고 `/play/s1`로 간다. [에디터에서 보기]도 불러온 뒤 `/editor/emberleaf`로 간다. `/worlds`가 500이면 오류 줄은 보이지만 두 버튼 모두 불러온다. 대조로 목록이 먼저 오면 `demo-ask`가 뜨고 불러오기는 0번이다. 서버(키 없는 운영 조립)에서 emberleaf를 불러오고 에디터로 지역을 하나 더해 13개로 만든 뒤 같은 요청을 보내면 200 `replaced=true`이고 12개로 돌아간다. 더한 지역은 백업 파일에만 남는다. 열린 세션이 하나면 409 `{open_sessions: 1}`이라 화면은 "열린 세션 1개를 닫고 새로 불러올까요?"만 묻는다. 월드 4개에서 `/demos`는 그래프·DB 읽기 0번, `/worlds`는 `list_world_ids` 1번, `find_nodes` 8번, 월드마다 PG 세션 읽기 1번이다.
2. **빌드 중 다시 연 패널**: 실제 EditorPage(api mock, 업로드를 붙잡아 둠)에서 메모 → [만들기] → 교체 확인 → [닫기] → 파일 띠의 [자료로 만들기]를 했다. 다시 연 패널에 "working" 줄이 없고 메모가 비어 있다. 메모를 다시 치면 제출이 켜지고, 확인 뒤 `uploadBuild`가 두 번 나간다(`["w","true","false"]` ×2). 첫 빌드가 끝나도 백업 경로는 보이지 않는다. 589dc2b 트리에서 같은 시험은 "working"과 메모가 남고 제출이 꺼져서 업로드가 한 번이며 백업 경로가 보인다. `/`의 새 id도 HEAD 2번, 589dc2b 1번이다. 실제 `build/upload` 라우트(인메모리 가짜 위의 운영 WorldBuilder, 수집 단계의 barrier로 두 요청을 준비 구간에 붙잡음)에서 둘 다 200 `replaced=false`이고 Region 노드가 4개(R0, R0, R1, R1)다. 세 번째 순차 빌드는 409다. 둘째 계기: 업로드가 `HttpError(504, nginx HTML)`로 끝나면 오류 줄이 `Error: 504 Gateway Time-out: <html>…`이고 working 줄이 사라지며 [만들기]가 다시 켜지고 `onBuilt`는 불리지 않는다. 다시 누르고 확인하면 두 번째 업로드가 `replace=true, confirm=false`로(`/`에서는 `replace=false`로) 나간다. 실제 uvicorn에 운영 `assemble_world`(호출마다 60ms 자는 가짜 LLM)를 띄우고 첫 업로드의 클라이언트를 1초에 끊으면(nginx 130초 대신), 빌드는 작업 스레드에서 계속 돌아 2.94초에 끝나고 1.07초에 들어온 재시도가 둘째 빌드를 시작해 지역 이름 12개에 Region 노드가 24개가 된다. 운영 WorldBuilder를 Emberleaf 소스(메모 1, 지도 1, 지역 12)에 돌리면 증류 prior 수에 따라 LLM 호출 34·47·59번과 임베딩 21번을 모두 한 스레드에서 차례로 한다(병렬 실행 없음). 실제 빌드가 130초를 넘는지는 라이브 지연에 달려 있다. 확인: 키를 넣고 :3000으로 Emberleaf 소스 빌드 하나의 시간을 잰다.
3. **라이브 시나리오의 9·11단계**: 실제 API를 프로세스 안에서 운영 방식으로 조립하고(아무것도 고치지 않음), 모든 행적을 전할 만하다고(salience 0.9) 판단하는 가짜 LLM을 붙여 스크립트를 그대로 돌렸다. 결과는 "12 passed, 0 failed, 2 skipped", 종료 0이다. 6단계는 "not seeded (the witnesses shrugged)"이고, LLM 호출은 complete 2, NarrationDraft 1, RumorDraft 4, AppraisalDraft 0이다. 선언한 행적의 판단과 소문은 0개다. 선언 뒤 그 NPC와 say + end_talk만 더하면 AppraisalDraft 1, T3에 씨앗, 14 passed다. 이때 도착 행적의 소문이 지역당 한 칸(`max_spread_per_region_turn=1`)을 차지할 수 있어, 12번 돌리면 4번은 9단계가 FAIL이었다. 판단은 전할 만한데 소문이 없는 흉내 서버(파이프라인이 깨진 경우)에서도 9·11은 SKIP, 종료 0이다.
4. **재시도가 끝내지 못하는 편집**: 키 없는 운영 조립에 Emberleaf를 불러오고 `PUT knowledge`(k-arrivals, 신뢰도 0.9 → 0.3, 진술도 고침)를 보냈다. 대조는 200이고 지역 보기 direct가 0.3이다. OpenSearch가 한 번 실패하면 첫 PUT 500, 같은 PUT 200(색인 호출 0번)이고 노드 0.3, SCOPED_TO 0.9다. `GET …/regions/region-saltwake`의 direct는 0.9, 이웃 Ambermeadow의 propagated는 0.3이고, `/briefs`는 이 지식을 맨 앞에 둔다(대조에서는 맨 뒤). 스코프 쓰기에서 끊어도 같다. 보강 "맞음"(0.3)에서 OpenSearch가 한 번 실패하면 500이고 질문이 남는다. 다시 누르면 200이고 노드 0.9, 엣지 0.3, 보기 0.3이다. NPC PUT·엔티티 고침도 색인에서 한 번 끊고 다시 보내면 200(색인 0번)이고 문서가 옛 글·옛 집이다. U8 전 트리는 재시도마다 다시 색인했다. 덧붙여 `create_knowledge`는 노드 → 색인 → 스코프 순서라 색인이 실패하면 스코프 없는 지식이 남는다. id를 실은 재시도는 영구 400(S32)이고, id를 싣지 않는 웹에서는 같은 지식이 둘이 된다(이 순서는 U8 이전부터다).
5. **S02 상한**: 실제 PlayPage(기본 props, 서버가 세션을 8초 쥠)에서 `getRegion`이 50·71·1095·2102·3106·4110·5114ms에 읽고 멈춘다. 11.07초에 기다리기·이동 버튼이 여전히 꺼져 있다. 시간을 줄인 판(30간격 동안 쥠)도 7번 뒤 멈추고 풀린 뒤에도 꺼져 있다. 첫 쥠 다시 읽기가 502이고 1ms 뒤 쥠이 풀리면, 40간격 뒤에도 읽기는 3번이고 버튼은 꺼져 있으며 오류 줄은 "502 Bad Gateway"다. Emberleaf 세션에서 지역별 생성의 LLM 호출 수는 마을 12~36번(출처마다 3번씩 이어서), 지방 3번, 전체 생성 219번(5개씩)이다. 저장소의 play.test는 "다섯 번 더 읽고 멈춘다"를 고정한다.
6. **되돌리기 중간 끊김**: TP-U3-2a 방식(n번째 쓰기 앞에서 한 번 실패)으로 되돌리기의 쓰기를 하나씩 끊고 같은 되돌리기를 두 번 더 보냈다. gap/add를 `delete_node`에서 끊으면 재시도마다 409 "SCOPED_TO k->hollow was edited after this change"이고 "Wells run dry"가 스코프 없이 남는다. 지식 "맞음"이나 신뢰도 고침의 되돌리기를 `replace_nodes`·`upsert_edges`에서 끊으면 409가 계속되고 fish가 스코프 없음이 된다. wiki_prior_ref 고침·지움의 되돌리기를 `upsert_edges`에서 끊으면 riverton–hollow CONNECTED_TO가 2 → 0이다. HTTP로는 답 A(gap/add)와 B("맞음") 뒤 B 되돌리기를 끊으면 500, 재시도 셋 모두 409이고, A 되돌리기는 409 "revert the later changes first"다. 589dc2b 트리에서 "맞음"은 엣지를 기록하지 않아 같은 자리에서 끊어도 재시도가 됐다. 지식 지우기·엔티티 맞음·unscoped 고침은 모든 자리에서 이어진다.
7. **S09 반복 조회**: Emberleaf(지형 쌍 21개, 키 11개)를 인메모리 Stack에 두고, 운영의 `CommonsenseWiki(search, None, embedding)`에 실제 `with_retry` 안에서 실패하는 임베딩을 붙였다. HEAD는 start·ignore·unignore·add·revert마다 조회 21번(시도 63번, 대기 63초)이고, 589dc2b의 `_lookup`은 11번 뒤 0번이다. 실제 시간으로 HTTP를 돌리면 `POST runs` 63.1초, ignore 답 63.0초가 걸렸고, 1초 뒤 보낸 unignore는 run 잠금을 62.0초 기다렸다. 조회 하나의 대기는 빠른 실패 3초, 429(Retry-After, 대기 상한 8초) 16초, 시도마다 30초 시간 초과 93초다. 실패는 `_lookup`까지 올라온다(임베딩 공급자는 재시도 뒤 다시 던지고 `hybrid_search`에는 try가 없다).
8. **C2 회귀**: World File로 지역 "north|gate"·"south"와 p-road를 인용하는 route를 같은 world id로 불러오면(remap 없음) `POST runs` 200이다. `DELETE /priors/p-road`(204) 뒤 `POST runs`는 500(questions.py:89 ValueError "'south' is not a valid ConnectionKind")이다. API만으로도 같다(`POST /regions {"id":"north|gate"}` 201, 없는 prior로 `PUT /connections` 200). 589dc2b의 `target_of`를 끼우면 200이고 질문 이름이 "north – gate (south)"다. run 도중이면 gap/add 답이 400인데 사실은 쓰이고 기록되며, `GET run`은 open에 질문 0개다. 되돌리기도 400이면서 실제로는 되돌려진다. 지역 id가 "bbb|route"이면 run은 시작되지만 키가 틀리고(aaa–bbb route), 고치기·지우기는 400 "too many values to unpack (expected 3, got 4)"이다.
9. **해소 ∥ 해소**: 지역 r1↔r2(0.8)에 지속 사건 E1(war 0.5)·E2(plague 0.5)를 라우트로 만들고, 실제 턴 한 번(0.3/0.3 → 0.57/0.57) 뒤 운영 SQL 어댑터(SQLite 파일 위 `PostgresPlayRepository`)에서 두 해소를 함께 풀었다. 차례로면 3/3 모두 기준으로 돌아오고, 함께면 모두 200인데 100번 중 75번 0.42/0.45로 남는다. 저장소 호출당 1ms, 스냅샷 3ms 지연을 주면 0~5ms 간격은 20/20, 10ms는 4/20, 20ms 이상은 0/20이다. 인메모리 저장소(RLock이 UoW 전체를 덮음)는 0/100이다. PostgreSQL은 READ COMMITTED에서 두 `FOR UPDATE`가 다른 행이라 서로 막지 않고, 지역 SELECT에는 잠금이 없어 같은 일이 생긴다(추론). 확인: 실제 PG에서 두 해소를 5ms 안쪽으로 보내고 지역이 기준 위에 남는지 본다.
10. **씨앗 id 충돌**: Emberleaf의 seed-lantern-feud(Gutterlight)의 id를 region-hollowdeep으로 바꿔 불러오면 ok, 경고 0이다(id 65개 중 하나가 합쳐짐). 인메모리 가짜에서는 불러올 때 지역이 덮여 11개가 되고 `own_label`이 400이다. 쿼리를 그대로 따르는 에뮬레이터((world, label, id)로 저장하고 `get_node`·`delete_node`는 라벨을 보지 않음)에서는 12개로 잘 불러와지지만, Gutterlight를 지우면 지역이 10개가 되고 Hollowdeep과 그 연결이 사라지며 NPC npc-fenn·npc-ysolde가 dangling이 된다. NPC id가 지역 id와 같을 때도 HEAD·589dc2b 모두 같은 식으로 지역이 지워진다. 실제 Neo4j 확인: 그 파일을 불러와 `MATCH (n {id:'region-hollowdeep', world_id:'emberleaf'}) RETURN labels(n)`이 2행인지, Gutterlight 삭제 뒤 0행인지 본다.
11. **매니페스트 이름과 world.id**: emberleaf.world.json(world.id "emberleaf")을 isle.world.json으로 복사하고 `name="isle"`, `start_region_id="region-saltwake"` 항목을 더해 키 없는 앱에 붙였다. `problems == []`, `check_packaged() == []`다. `POST /worlds/isle/demo/isle`은 200 `ok=True remapped=True`이고, 이어 그 지역으로 세션을 시작하면 400 "start region not in world: region-saltwake"다. 다시 불러와도 같다. 시작 지역의 유일한 지나갈 연결이 자기 자신이면 problems []·불러오기 ok인데 이동 선택지가 0개이고, 다른 끝이 파일에 없으면 불러오기가 매번 ok=false다.
12. **씨앗 경합**: 실제 라우트(`_idle` 리스, 실제 서비스)와 SQLite 위 운영 SQL 어댑터에서 두 POST를 함께 풀면 지연 없이 100번 중 77번, 저장소 1ms·스냅샷 3ms 지연이면 100번 모두 둘 다 201이다. 그러면 타임라인에 "started seed 'Blight in the fields' in R1"이 둘이고, 한 턴에 r1이 0.3 → 0.6(한 번이면 0.45)이며, 목록이 보이는 사건을 해소해도 "진행 중"이다. 두 번째 POST를 늦추면 0~5ms는 19~20/20, 10ms 이상은 0/20이고, 50~250ms는 모두 (201, 409)다. vitest에서 시작을 붙잡고 120ms 간격으로 두 번 누르면 `startSeed`가 두 번 불린다. 409가 첫 시작의 다시 읽기 뒤에 오면 패널은 "진행 중"인데 허브에 `Error: 409 Conflict: {"detail":"seed already running: seed-a (event ev-1)"}`가 남는다.
13. **엔티티 제목 칸**: 실제 조립 월드에서 엔티티 "Old Bell"(신뢰도 0.2)의 low_confidence 질문은 needs가 `{'edit': ['statement','title','confidence']}`다. 제목만 "Great Bell"로 고치기를 보내면 200이고 이름은 그대로다. 빈 변경(`nodes_after` 0)이 기록되고 답 수가 1이 되며 같은 질문이 다시 나온다. 셋을 다 보내면 설명·신뢰도만 바뀐다. 웹 카드는 엔티티에도 제목 칸을 그리고 본문에 `title`을 싣는다. U8 전의 엔티티 카드에는 진술 칸뿐이었다.
14. **늦게 온 플레이어 읽기**: 실제 GmPage(라우터)에서 s1 띠의 `getPlayer(s1)`를 붙잡아 둔 채 s2로 바꾸고 `getPlayer(s2)`를 500으로 두었다. 늦은 답이 오기 전에는 marker-a가 없고, 온 뒤에는 `/gm/s2`에 marker-a가 있으며 띠는 비어 있다. s2가 성공하는 변형(Bo, 지역 b)에서는 marker-a가 그려지고 marker-b가 사라지며 띠는 "Bo · Hollow"다. s1 읽기가 바꾸기 전에 끝난 대조에서는 남는 표식이 없다.
15. **GM 허브의 LLM 문구**: capabilities 읽기를 실패로 두고(BR-U8-26: 아무것도 끄지 않음) 생성·재생성이 503 "rumor generation needs an LLM provider (set OPENAI_API_KEY)"를 주게 하면 알림이 "전체 생성 0/2 완료 · 2건 실패", "전체 재생성 0/2 완료 · 2건 실패"이고 "LLM 키가 필요합니다"는 화면 어디에도 없다. 같은 503에 단일 [생성]은 `gm-hub-error`에 그 문구를 보인다. llm=false에서 RumorPanel의 두 버튼은 꺼지고 title만 있으며, 허브의 `llm-required` 옆 글은 ManualTurnPanel 한 곳뿐이다. 589dc2b의 GmHub 일괄도 오류를 같은 식으로 삼켰다.

## 2. 상한 아래 — 정리(cleanup) 지적
모두 검증 CONFIRMED다. 심각도는 모두 low다. C3·C6은 겹친 코드가 이미 다르게 동작한다. 정확성 지적이 우선이라 상한 밖에 두었다.

| # | 위치 | 지적 | 권장 조치 |
|---|---|---|---|
| C1 | `web/src/features/editor/RegionInspector.tsx:58-79·86-88·126-127` | 인스펙터 쓰기마다 `await fn(); await load(); onChanged()`로 한 번 읽고, 페이지의 `rev`가 `reloadKey` 효과로 또 읽는다(지역 보기 GET 2번 + export 1번). U3 C12가 UnscopedPanel에서만 고쳐졌고 이것이 남은 하나다 | `write`·`confirmDelete`에서 `load()`를 빼고 `reloadKey`에 맡긴다 |
| C2 | `locus/world/worldfile/export.py:44·67-70`, `locus/knowledge/loader.py:127-128·137`, `locus/shared/models/io.py:105-110` | `export_world`가 스냅샷을 두 번 읽는다(따뜻한 캐시에서 WorldMeta 2번, 589dc2b는 1번). 그 사이 쓰기가 끼면 지식 목록과 스코프 없음 목록이 다른 스냅샷에서 온다. C5가 "규칙 하나"를 만들면서 속성이 직접 계산하게 됐는데, 로더는 여전히 `kg.unscoped_knowledge_ids`를 계산한다(운영에서 읽는 곳 없음, 테스트 하나는 일부러 다른 값을 넣는다) | 스냅샷 하나로 둘 다 만든다. 로더의 계산을 지운다 |
| C3 | `locus/world/wiki/admin.py:40-62·69-82·92-95` | C9의 `refs()`가 `usages`·`broken`을 불러 `_citations`를 두 번 만들고, 옛 `prior_refs`·`broken_refs`는 테스트에서만 쓰인다. C3는 WikiAdmin이 EditorWrites를 쓰게 하자는 것이었는데 `upsert_prior`는 여전히 `written()`·`index()`·스냅샷 읽기를 따로 구현한다. 그래서 이미 다르게 동작한다: 같은 prior를 다시 저장해도 임베딩을 다시 부르고, 병합 쓰기와 None 버리기 때문에 `description=None`으로 보내도 옛 설명이 남는다. S21·S26이 빠진 결과는 §3에 적었다 | `refs()`가 `_citations`를 한 번 만들고 옛 두 메서드를 지운다. `upsert_prior`는 `self._writes.writing(...)`·`index(previous=)`를 쓰고 `_snapshot`은 `self._writes.snapshot`을 쓴다 |
| C4 | `api/deps.py:37-42·49-52`, `api/routers/world_editor.py:46-49·289-290·298-301`, `api/routers/world.py:231-233·425`, `locus/world/augmentation/{questions.py:48-54, apply.py:30-36·357-358}`, `web/src/{i18n.ts:294·642, types.ts:371}` | `need_service`의 docstring은 "모든 라우터가 쓰는 하나의 규칙(U3 C7)"인데 world.py만 쓴다. U3 C7이 짚은 `_editors`·`_wiki`와 둘의 인라인 검사, `deps._require`가 같은 None → 503을 다른 문장으로 다시 쓴다. 같은 `wiki_admin is None`이 "wiki admin unavailable"과 "wiki admin (LLM provider) unavailable" 두 문장이 되고, 뒤의 것은 사실과 다르다(wiki_admin은 늘 조립됨). C4가 지운 `"npc"` 대상은 i18n `augment.target.npc`, 웹 타입, `_doc`의 NPC 갈래로 남았다(닿지 않음). C2가 더한 `REF_KIND`는 `_REF_KIND`와 같은 필드 다섯을 키로 하는 둘째 표다 | 넷 모두 `need_service`를 쓴다. npc 잔재를 지운다. 두 표를 하나에서 만든다 |
| C5 | `locus/world/npc_drafts.py:74-75`, `locus/world/augmentation/apply.py:165-167` | 플랜 C6의 "require_region 중복 정리"가 빠졌다(code-summary 9a의 C6 줄에도 없음). 손으로 쓴 지역 확인 둘이 `editor/writes.py:129-133`의 `require_region`과 같은 일을 한다 | 기존 함수를 부른다 |
| C6 | `web/src/features/gm/{RumorPanel.tsx:28·32, ManualTurnPanel.tsx:43·63·67·70, GmHub.tsx:119}`, `features/editor/{BuildPanel.tsx:67·104·107, NpcDraftCards.tsx:36·45·48}`, `features/play/DialoguePanel.tsx:121` | "LLM 키가 필요합니다" 처리가 복사되어 있다: `title={x ? t("llm.required") : undefined}` 7번, 옆 글 span 3번, `needsLlm(e) ? t("llm.required") : String(e)` 4번. 이미 갈라졌다(RumorPanel에는 옆 글이 없음, #15) | `ui`에 LLM이 필요한 버튼 컴포넌트와 오류 문구 도우미를 둔다 |
| C7 | `locus/world/demo/__init__.py:183-188`, `locus/play/player/movement.py:25-27` | 매니페스트의 "지나갈 수 있는 연결" 검사가 이동 규칙 `is_passable`을 그대로 다시 썼다. world는 play를 import할 수 없으니 규칙이 shared에 있어야 한다. 이동 규칙이 바뀌면 BR-U8-2 검사가 [바로 플레이]로 떠날 수 없는 시작 지역을 받아들인다 | 규칙을 shared(예: `ConnectionEdge`)로 옮겨 둘이 부른다 |
| C8 | `locus/shared/storage/neo4j_repo.py:102-121·123-145·223-247·249-280` | `replace_edges`는 `upsert_edges`와 `SET r =`/`SET r +=`만 다르고, `edges_touching`은 `get_edges`와 종류 검사·행 매핑이 같다. MERGE identity 처리가 두 벌이라 오프라인 테스트가 둘의 어긋남을 잡지 못한다(§3의 가짜 충실도와 같이 봄) | 공통 쿼리 빌더 하나에서 SET 연산자와 WHERE만 바꾼다 |
| C9 | `locus/play/event/seeds.py:50-53·70-76`, `event/service.py:89-91` | 씨앗 시작 한 번이 스냅샷 3번·세션 2번을 읽는다(U3 C16이 `create_event`에서 없앤 꼴이 돌아옴). SeedService의 `require_region`은 두 읽기 사이에 월드가 바뀔 때만 실패할 수 있고, 그때는 `create_event`도 같이 거절한다. `_running`은 해소된 사건까지 모두 읽는다 | 첫 스냅샷으로 씨앗·지역을 보고 열림·지역 검사는 `create_event`에 맡긴다. `_running`은 `list_events(sid, "active")`를 쓴다 |
| C10 | `locus/world/wiki/distiller.py:1`, `ingestion/concept_art_ingestor.py:1`, `wiki/cross_world.py:1`, `augmentation/graph.py:1` | `STATUS:` docstring 첫 줄이 251·238·187·165자다(CLAUDE.md "ruff + black (line 100)"; E501을 무시하고 black은 docstring을 접지 않아 게이트는 통과). 테스트는 접두사만 본다 | 첫 줄을 접는다 |
| C11 | `.github/workflows/ci.yml:31·33` | CI의 ruff·black은 `locus api tests`만 돌아 새 `scripts/live_scenario.py`(350줄)를 지키지 않는다. code-summary §1·16.1의 "clean (scripts 포함)"은 로컬 실행으로는 맞다 | CI에 `scripts`를 더한다 |

검증하지 않은 정리 메모(목록만): `readSeq` 최신 읽기 장치가 다섯 컴포넌트에 손으로 복사됨, HomePage·EditorPage의 `buildKey`는 `{building && <BuildPanel/>}`로 대신할 수 있음(#2를 고칠 때 함께), `seeds_deleted`를 웹이 읽지 않음, `GmNarrator.narrate`가 테스트에서만 쓰임, `MapCanvas.sameConnection`과 `MapOverlay.isSelectedConnection`이 같은 판정, 지역 이름 찾기가 네 곳, `AugmentQuestion`의 신뢰도 파싱이 ConnectionList와 같음, `InProgressBadge`가 `ui/Badge`를 쓰지 않음, CLI `_load_inputs`·`_demo_name`이 `DemoWorlds()`를 다시 만들어 World File을 다시 읽음, `resolve_event`가 `_require_event`를 다시 씀.

테스트 적정성 메모(검증 없이 목록만):
- S03 테스트는 그래프 쓰기 뒤만 끊는다(#6). 편집 끊기 테스트는 검색 문서·스코프 값을 보지 않고, `Stack.state()`는 문서 키만 비교한다(#4).
- `test_live_scenario`의 흉내 서버는 선언 때 씨앗을 만든다(#3). 실제 API 실행은 키 없이만 돈다.
- `test_demo`의 isle 항목은 유효하다고만 단언하고 불러 보지 않는다(#11).
- 그래프 가짜의 `replace_edges`가 `upsert_edges`이고 가짜의 upsert가 통째 교체라, `set_prior_ref`를 병합 쓰기로 되돌려도 933개가 모두 통과한다(§3).
- 씨앗 시작·GM 쓰기의 경합은 인메모리 저장소가 UoW를 통째로 잠가 오프라인 테스트로 볼 수 없다(#9·#12). PostgreSQL 행 잠금도 그렇다(code-summary §6).
- TP-U8-8의 `/health` "ok" 단언은 컨테이너를 주입한 앱이면 경계 상태와 상관없이 ok라서 키 없는 `/health`를 지키지 못한다(§3).
- play.test가 S02의 "다섯 번 뒤 멈춤"을(#5), gm.test가 `llm-required` 하나뿐임을(#15) 고정한다.
- 웹 테스트에 "목록이 오기 전의 데모 카드"(#1), "빌드 중 닫고 다시 열기"(#2), "실패한 쥠 다시 읽기"(#5)가 없다.

## 3. 상한으로 뺀 정확성 지적
검증을 통과했지만 상한(15) 밖으로 밀린 정확성 지적이다. 따로 적지 않으면 심각도는 low다.

| 위치 | 지적 | 판정 | 권장 조치 |
|---|---|---|---|
| `web/src/features/gm/{GmHub.tsx:91-97, useBulkRumors.ts:63}`, `WorldStateOverlay.tsx:44-49` | S13은 제안 상한을 [전체 생성]의 `/state` 읽기에서만 고친다. 마운트 읽기가 실패하면 [제안]만 쓰는 GM은 1~5를 보고 400 "n must be between 1 and 3: 5"를 계속 받는다(플랜 S13 행의 수동 방식). 지도 겹쳐 보기를 켜서 `/state`를 읽어도 상한은 고쳐지지 않는다(플랜 행과 다름) | C | `/state`를 읽는 곳 하나가 상한을 고치거나, 상한을 `/api/capabilities`에 싣고 400에서 다시 읽는다 |
| `web/src/features/gm/SeedPanel.tsx:29·39` | `listSeeds` 실패(500·503·404)를 빈 목록으로 받아 "이 월드에는 사건 씨앗이 없습니다"를 보인다. 오류는 보이지 않고, 타임라인이 바뀔 때까지 다시 읽지 않는다 | C (2각도) | 실패는 허브 오류 줄로 보낸다 |
| `web/src/features/home/DemoCard.tsx:65-69·88` | 불러오기가 몇 초 걸리는 동안 다른 월드의 [수정]으로 떠나도, 끝나면 내려간 카드가 세션을 만들고 `/play/…`로 끌고 간다(react-router 7의 `useNavigate`는 언마운트 뒤에도 이동한다). 원하지 않은 세션이 남는다 | C | 마운트 표시를 두고 내려갔으면 이어 가지 않는다 |
| `web/src/features/home/DemoCard.tsx:36-42` | 불러오기가 `ok=false`인데 이미 교체된 경우(삭제 뒤 커밋 오류, 또는 끊긴 씨앗이 있는 매니페스트 파일 — `_check`는 참조 검사를 하지 않음)에도 `onLoaded()`를 건너뛰어, 목록이 지워진 월드와 옛 세션 수를 계속 보인다 | C | `ok=false`여도 `replaced`면 목록을 다시 읽는다 |
| `web/src/routes/AppNav.tsx:18·27` | 월드가 없으면 에디터 링크가 `/`라서 `/`에서 "에디터"가 지금 페이지로 표시된다(`aria-current="page"`, 굵게·밑줄). 눌러도 그대로다 | C | 월드가 없으면 에디터 링크를 숨기거나, 활성 표시가 없는 일반 `Link`로 그린다 |
| `locus/world/augmentation/service.py:122-130`, `api/routers/world.py:470-480·494-500` | 쓰기 뒤 다시 탐지가 실패하면 S15가 질문을 비우고 예외를 다시 던져, 라우트가 S10의 `purge_translations`에 닿지 않는다. 지우기 답(지식이 이미 지워짐)과 gap/add 되돌리기 모두 번역 행이 남고, 재시도는 404·409라 끝내 지우지 않는다. 저장 공간만 남는다(읽기는 source hash로 거름) | C | 지운 id를 쓰기 쪽에서 돌려받아 finally에서 지운다 |
| `locus/world/wiki/admin.py:44-62` | `upsert_prior`가 EditorWrites를 거치지 않아 S21·S26이 빠졌다. `POST /worlds/{오타}/priors`는 200이고 그 오타가 `/` 목록에 월드로 뜬다(지역 쓰기는 404). 지식 id로 prior를 보내면 받아서, 가짜에서는 그 지식이 prior로 바뀌어 지역 보기에서 사라지고 Neo4j에서는 같은 id 노드가 둘이 된다. U8 이전부터이고 웹은 이 경로를 부르지 않는다(C3 이월이 덜 끝남) | C | C3와 같이 EditorWrites로 옮긴다 |
| `locus/world/editor/npcs.py:39-41` | #13a 순서(새 LIVES_IN → 노드)가 새 NPC에도 적용되어, Neo4j의 `MATCH (a {id…}) MATCH (b…) MERGE`가 노드가 없어 아무것도 쓰지 않는다(오류도 없음). 새 NPC(초안 받아들이기 포함)는 다음 저장 전까지 LIVES_IN이 없다(BR-U3-18). 로더·삭제 계획은 `home_region_id`를 보므로 화면 영향은 없고 가짜는 끝점 없이 엣지를 써서 테스트가 못 본다. 지역 편집은 같은 경우를 "노드 먼저"로 다룬다(regions.py:52) | C (3각도) | 새 NPC면 노드를 먼저 쓴다 |
| `scripts/live_scenario.py:119-124·165·319·341` | `except (OSError, KeyError, TypeError, ValueError)`가 AttributeError·`http.client.BadStatusLine`을 잡지 못한다. README가 열라는 :3000(nginx의 SPA 대체가 `/health`에 index.html 200)을 `--base`로 주면 첫 단계에서 traceback으로 끝나고 단계 줄·요약이 없다(종료 코드는 1). `--poll 0`이면 `--timeout`이 듣지 않아 멈춘 run을 끝없이 읽는다. code-summary 15.1의 "응답 모양 오류는 FAIL이고 멈추지 않는다"와 다르다 | C (2각도 + 이 세션) | Exception을 FAIL로 받고, `--poll`에 하한을 두거나 벽시계로 시간을 잰다 |
| `scripts/live_scenario.py:256-264` | 10a는 왜곡도만 다르면 PASS다. BLM §7 10단계는 "왜곡도와 소문 수가 다르다"인데, 키 없는 실행에서 두 지역 소문이 모두 0이어도(차이는 씨앗 사건의 번짐에서만 옴) PASS다. #3과 합치면 어느 단계도 소문이 하나라도 있는지 보지 않는다 | C | 키가 있으면 소문 수 차이를 단언한다 |
| `locus/play/distortion_service.py:55-62·74·89` | U3 #10 수정이 사건 읽기는 UoW 안으로 옮겼지만 피드백 몫 읽기는 밖에 남겼다. 같은 지역 설정 둘이 겹치면(SQL 어댑터에서 100번 중 83~90번) 두 줄 모두 `feedback_share_cleared: 0.2`를 적는다(실제로는 한 번 비움). 감사 payload만 틀리고 읽는 곳은 없다. U7 BR-U7-5부터 같은 줄이다 | C | UoW 안에서 잠그고 읽거나 `UPDATE … RETURNING`으로 쓴다(#9의 세션 잠금이면 함께 닫힘) |
| `api/main.py:34-44·152-157` | S27은 bytes만 고쳤다. 실패한 필드가 외톨이 서로게이트 문자열을 되돌려 보내면(예: `{"degree": "\udfff"}`) Starlette의 UTF-8 인코딩에서 500이다. 아주 깊은 리스트는 `_finite`의 RecursionError로 500이다(로컬 3.14에서 깊이 1,000 이상, python:3.11 이미지에서는 약 450~950 단계이고 더 깊으면 JSON 파싱이 400). 기본 FastAPI도 같아 회귀는 아니다 | C | 서로게이트를 `errors="replace"`로 바꾸고 깊이를 제한한다 |
| `api/routers/world.py:403-414` | 소스 빌드 라우트가 이름만 본 뒤 열린 세션 관문을 지난다. 소스가 없는 데모 + 열린 세션이면 409 "세션 N개를 닫으려면 confirm=true"를 주고, 확인하면 그제야 404 "no sources"다(BR-U8-4, 옆 load 라우트는 review #6 원칙대로 관문 앞에서 본다). 아무것도 닫히지 않고, 웹은 이 라우트를 부르지 않는다. 순서는 U8 이전과 같다 | C | 관문 앞에서 `has_sources`를 본다 |
| `locus/world/ingestion/service.py:27-49`, `locus/__main__.py:47` | S19 상한이 `WorldInputs`에 있어서 CLI `world build --inputs`도 받는다. 메모 21개나 60,001자 메모는 이제 잡히지 않은 pydantic traceback으로 끝난다(U8 이전에는 빌드됨). 같은 뿌리로, 메모 소스가 21개인 매니페스트 데모는 BR-U8-2 검사를 통과하지만 `POST …/demo/{n}/build`가 500이다 | C (2각도) | CLI가 ValidationError를 고정 문장으로 바꾼다. 데모 검사가 소스 수를 본다 |
| `web/src/routes/EditorPage.tsx:92-99`, `features/editor/RegionInspector.tsx:86-88` | 끌기는 페이지 export의 지역에 위치만 얹어 PUT한다. 인스펙터에서 이름을 고쳐 저장한 직후(인스펙터 PUT → 인스펙터 GET → 전체 export가 오기 전) 같은 지역을 끌면 옛 이름이 다시 저장된다. U8 이전과 같고, C1로 끌기 뒤 다시 읽기가 없어져 지도는 서버와 다른 이름을 보인다 | C | 위치만 바꾸는 쓰기(또는 낙관적 동시성)로 바꾼다(U3 #1의 근본 권장) |
| `web/src/routes/EditorPage.tsx:71-73·108-113` | 지역 추가 도구로 만든 지역이 선택되지 않는다. `setSelected(made.id)` 뒤 옛 export로 도는 효과가 선택을 지운다. U3부터 같다 | C | 다시 읽기가 끝난 뒤 고르거나 효과가 진행 중 읽기를 기다린다 |
| `web/src/features/editor/{AugmentPanel.tsx:75, BuildPanel.tsx:67, WorldFileBar.tsx:72, RegionInspector.tsx:131-134}` | 409 처리가 아직 셋으로 남았다(모두 U8 이전과 같은 출력). 보강 패널은 모든 409를 "되돌릴 수 없습니다: Error: 409 Conflict: {…}"로 보인다(`detailOf`를 쓰지 않음). BuildPanel·WorldFileBar는 턴 중 `busy_sessions` 409를 JSON 원문으로 보인다(DemoCard만 `demo.busy`). 지역 삭제 409가 "turn in progress"(문자열 detail)이면 원문이다(U3 S05가 "또는 다른 세션의 턴"이라 적은 경우) | C | `detailOf`·`openSessionsOf().busy`를 세 곳에 쓴다 |
| `web/src/features/editor/AugmentQuestion.tsx:56`, `i18n.ts`(`augment.titleLabel`), `AugmentPanel.tsx:110`, `locus/world/augmentation/apply.py:146` (sweep) | S06의 제목 칸 라벨은 "제목(비우면 진술에서)"인데, low_confidence·wiki_conflict 고치기에서 제목을 비우면 진술에서 만들지 않고 옛 제목이 남는다(`if answer.title`일 때만 바꿈). 인스펙터의 지식 고침은 빈 제목이면 `fallback_title`을 쓴다. 같은 "빈 제목"이 에디터 안에서 두 뜻이다 | C | 고치기의 빈 제목도 새 진술의 `fallback_title`로 채우거나 라벨을 바꾼다 |
| `web/nginx.conf:10`, `docker-compose.yml:166-168`, `README.md:44` | `proxy_pass http://app:8000`은 nginx가 뜰 때 한 번만 이름을 푼다. README대로 키를 넣고 `up -d`하면 app만 다시 만들어지고 web은 그대로다. 새 app이 다른 IP를 받으면 healthcheck는 정상인 채 `/api`가 모두 502다. Docker 로컬 bridge는 가장 낮은 빈 주소를 주므로 보통은 같은 IP를 다시 받는다 | P | `resolver 127.0.0.11` + 변수 upstream, 또는 `depends_on.app.restart: true`. 확인: 다시 띄우기 전후 `docker inspect`로 app IP를 보고 `curl :3000/api/capabilities` |
| `tests/shared/storage/fakes.py:58-68`, `tests/shared/storage/test_port_contract.py:247-261` | 가짜의 `upsert_edges`는 속성을 통째 바꾸고(Neo4j는 `SET r +=` 병합) `replace_edges`는 그것을 부를 뿐이라, 오프라인 테스트가 교체와 병합을 가르지 못한다. `set_prior_ref`를 `upsert_edges`로 되돌리는 변이가 933개를 모두 통과한다(가짜를 병합으로 바꾸면 test_13b가 잡는다). U3 #13b가 `replace_edges`를 만든 까닭이 바로 그 차이다 | C | 가짜의 upsert를 Neo4j처럼 병합으로 바꾼다 |
| `tests/api/test_keyless_api.py:48`, `api/main.py:161-171` (sweep) | TP-U8-8의 "키 없이 `/health`는 ok" 단언은 컨테이너를 주입한 앱이면 `do_assemble`이 거짓이라 경계 상태와 상관없이 ok여서, 그 앱이 knowledge·localization을 내린 채로도 통과한다. 운영 경로는 지금 맞다 | C | 운영 조립(`create_app()` + 키 없는 설정)으로 `/health`를 단언한다 |
| `locus/world/demo/__init__.py:194-199` | 경로 검사는 POSIX 규칙인데 합치기는 호스트 경로라, Windows에서는 `..\..\x.json`·`C:\x.json`이 매니페스트 폴더를 벗어난다. 입력은 패키지 데이터이고 배포는 Linux다 | P | `Path(rel)`로 검사하고 `resolve()` 뒤 `is_relative_to`를 본다 |

## 4. 기각
| 위치 | 지적 | 기각 이유 |
|---|---|---|
| `web/src/features/editor/MapCanvas.tsx:214·226-232` | #15 연결 폼에서 다른 종류로 바꾸면 저장된 가중치가 그대로 새 연결에 쓰이고, 되돌아오면 슬라이더 값이 저장값으로 바뀐다 | 화면에 보이는 가중치가 저장되는 값이라 숨은 상태가 없다. 종류별 기본값을 정한 문서가 없고(FC §2.2 "가중치 0~1"), code-summary 11a는 "다른 종류를 고르면 새 연결"만 정했다. UX 메모 정도다 |
| `web/src/features/editor/{AugmentPanel.tsx:41·104, AugmentQuestion.tsx:68-70}` | S28 입력이 issue_key로 남아, 다른 답이 지운 엔티티 id가 숨은 채 전송된다 | 서버(`apply.py:160-163`)가 지워진 id를 빈 선택과 똑같이 400으로 거절하고 아무것도 쓰지 않는다. 그 엔티티가 되돌리기로 돌아오면 다시 보인다 |
| `locus/shared/storage/neo4j_repo.py:256-260` | `edges_touching(types=[])`가 Neo4j는 전부, 가짜는 없음 | 빈 목록을 넘기는 호출처가 없다(apply.py 둘은 생략, npcs.py는 `["LIVES_IN"]`). `get_edges`도 U8 이전부터 같다 |
| `web/src/features/gm/GmHub.tsx:177` | 씨앗 목록이 턴마다, 시작마다 두 번 다시 읽힌다 | 턴마다 읽기는 필요하다(one_shot 씨앗 사건이 턴에 자동 해소됨). 시작마다 두 번은 jsdom이 `window.event`를 남겨 두는 탓이고, 브라우저에서는 React가 두 갱신을 묶어 한 번이다. `_running`이 해소된 사건까지 읽는 것만 정리 C9에 남겼다 |
| `locus/play/event/service.py:106-111` | `create_event(timeline_extra=)`가 `seed_title` 키를 보고 요약을 바꾼다 | BLM §3.3 6, 플랜 7.1, code-summary 7이 고른 서명이다. `**extra`가 뒤에 합쳐져 앞으로의 호출이 `event_id` 같은 키를 덮을 수 있다는 점만 메모한다 |
| `locus/play/event/service.py:140-159` | 해소 ∥ 해소가 PostgreSQL에서 데드락으로 500이 된다 | contributions는 JSONB라 키가 정해진 순서로 나와 두 해소가 같은 순서로 쓴다. 남는 것은 #9의 잃어버린 복원이다 |
| `api/uploads.py:39-41` | S20의 +1 MiB가 JSON `POST /file`에도 붙어 21 MiB까지 받는다 | 플랜 S20 행("World File 길의 요청 한도 = 20 MiB + 1 MiB")과 "U8 intended change"로 표시한 테스트 둘이 고른 동작이다. 두 불러오기 경로의 한도가 갈린 점은 설계 메모 7, 문서는 §5 |
| `web/src/routes/PlayPage.tsx:26` (#5 (a)) | S02의 5번 상한 | 플랜 S02 행이 골랐다. 다만 이월한 지적의 상황을 닫지 못해 #5에 함께 적고 §7에서 정한다 |
| `locus/world/augmentation/service.py:127-130` | S15가 질문을 비워 run이 질문 0개로 남는다 | 플랜 S15 행과 code-summary 9b가 고른 동작이다. [빈틈 찾기]가 늘 켜져 있어 막다른 길은 아니다(설계 메모 3). 번역이 남는 부분은 §3 |
| `locus/world/editor/knowledge.py:35`, `locus/knowledge/consensus.py:100·136` | S29가 신뢰도가 바뀔 때만 엣지를 고쳐, 이미 어긋난 값(U3 시기 편집, 스코프 신뢰도가 빠진 World File)은 저장해도 풀리지 않는다 | 플랜 S29가 쓰기 쪽 동기화를 골랐다(설계 메모 4). #4를 "엣지와 비교"로 고치면 함께 풀린다 |
| `web/src/features/editor/AugmentQuestion.tsx`, `questions.py:40-47` | 신뢰도 칸에 쓴 값이 "맞음"에서는 보내지지 않는다 | code-summary 11b("답은 그 행동이 받는 입력만 보낸다")와 U3 BLM:160(맞음 = `max(현재, 0.9)`), editor.test:776이 고른 동작이다(설계 메모 5) |
| `web/src/features/editor/AugmentPanel.tsx:37·41`, `routes/EditorPage.tsx:168·191` | 지도를 누르면 보강 패널이 내려가 쳐 둔 답과 바뀐 것 이름이 사라진다 | U3 #2 수정이 run id만 페이지에 두기로 했고 S28은 다시 탐지만 다뤘다. U8 이전과 같다(설계 메모 6) |
| `scripts/live_scenario.py:287-288` | 씨앗이 없으면 9·11을 SKIP으로 본다 | code-summary 15.1이 골랐다. 그 규칙이 깨진 전파를 숨기는 점은 #3의 권장에 넣었다 |
| `pyproject.toml:2·13` | `license = { text = "MIT" }`가 최신 setuptools에서 deprecated다 | BR-U8-29가 setuptools 하한 61 때문에 골랐다. 기한(2027-02-18)이 있으므로 설계 메모 11 |
| `pyproject.toml`(`extend-exclude = "tests/fixtures"`) | 옮긴 `generate_map.py`가 린트를 통과하지 못해 픽스처 폴더를 게이트에서 뺐다 | code-summary 5.6이 적은 이탈이다. 고쳐 넣는 데 줄 셋이면 되지만 결함은 아니다 |

## 5. 문서 정확도 메모
규약 각도에서 **인용할 수 있는 CLAUDE.md 규칙 위반은 없었다**.
- 경계 import는 `test_boundaries`가 통과하고, 함수 안 import(`wiki/admin.py` → `editor.writes`, CLI → `world.editor`, demo의 TYPE_CHECKING)도 경계 안이다. 사건 열거형을 shared로 옮긴 뒤에도 shared는 내부를 import하지 않는다.
- 새 외부 I/O는 모두 포트 뒤다(`replace_edges`·`edges_touching`은 GraphRepository, `update_event_contributions`·`for_update`는 EventStore). urllib는 `scripts/live_scenario.py`에만 있다.
- 새 쿼리는 모두 `world_id`로 나뉜다(Neo4j 두 끝점, 씨앗 노드, 가짜 필터).
- SeedService는 `PlayContainer.seeds`로 `assemble_play`에서, DemoWorlds·WikiAdmin은 `assemble_world`에서 조립된다. 새 직렬화(EventSeed, World File `event_seeds`)는 hypothesis 왕복(TP-U2-1·TP-U8-1·2)이 돈다.

사실과 다른 문장은 다음과 같다.
- `CLAUDE.md:13`
  - "compose ports on 127.0.0.1"은 인프라 포트만 맞다. app(:8000)·web(:3000)은 모든 주소에 열린다(README는 맞게 적음).
  - "**986 offline tests GREEN** (857 pytest backend + 129 vitest frontend)"는 U8 이전 기준선이다. 같은 단락이 "922 pytest + 197 vitest after Step 13"이라 적어 서로 어긋나고, 지금은 933 + 197이다.
  - "U8 … code generation in progress"는 3a6b5b6("U8 code approved")과 다르다. "U3 review items carried and closed"는 S16(알려진 한계), U3 #8과 설계 메모 1·2(남은 결정), 이월 수정이 다 닫지 못한 이 리뷰의 #4~#9·#14와 §3의 S13·S05를 생각하면 지나치다.
- code-summary
  - 9b "그래서 409 'edited after'가 나지 않는다"는 그래프 쓰기 뒤에서 끊긴 경우만 맞다(#6).
  - 9d "지운 몫은 실제로 지운 것만 기록한다"는 사건 기여에만 맞고, 피드백 몫은 겹치면 두 번 적힌다(§3).
  - 10.4 "모두 title과 옆 글 llm.required"와 "공급자가 없다는 503은 llm.required로 보인다(GmHub…)"는 RumorPanel과 일괄 실행에서 맞지 않는다(#15).
  - 11c S14 "s2 읽기가 실패해도 s1의 플레이어·표식이 남지 않는다"는 늦게 온 s1 읽기에서 맞지 않는다(#14).
  - §9 운영자 확인의 "키가 있으면 LLM 단계까지"는 9·11단계가 돌 수 없어 맞지 않는다(#3).
- FD business-logic-model
  - §7 6단계 "그 턴 끝에 판단으로 행적 소문이 씨앗된다"는 BR-U6-4·BR-U6-7(판단은 EndTalk에서, 대화하지 않은 NPC는 판단하지 않음)과 어긋난다(#3). 10단계의 "소문 수가 다르다"는 스크립트가 보지 않는다(§3).
  - §4.1 표와 operations.md:97(〔U8 정정〕)이 NPC 대화 `start`를 키 없으면 503인 경로로 적었다. 코드는 BR-U5-29("`say`만 503이고 `start`·`history`·모든 읽기는 동작한다")대로 `start`가 LLM 없이 200이고(`play.py:198`) 503은 `say`뿐이다. 같은 operations.md의 :148도 `start`를 "no LLM"으로 적어 :97과 어긋난다. 웹은 `start`가 성공한다는 데 기댄다(대화 기록 열기, dialogue.test). sweep이 찾고 검증 C다.
- operations.md
  - U8 "Event seeds" 절의 필드 목록(`id`, `region_id`, `title`, `description`, `category`, `magnitude`, 선택 `lifecycle`)에 필수인 `world_id`·`provenance`가 빠졌다. 적힌 대로 쓴 씨앗 하나가 World File 전체를 422로 만든다(`event_seeds.3.world_id Field required`). `id`는 오히려 선택이다.
  - "Adding a demo"는 파일의 `world.id`가 항목 `name`과 같아야 한다는 것을 적지 않는다(#11).
  - :392 "World File routes: 20 MiB"와 U3 nfr-light.md:150은 S20 뒤 JSON 경로가 21 MiB인 것과 다르다.
  - U2 BLM:163이 "같은 world_id 동시 빌드는 막지 않는다(… 문서에 적는다)"라 했는데 운영 문서에 그 줄이 없다(#2).
- README
  - "검사" 블록에서 `cd web && npx tsc … && npx vitest run` 다음 줄이 다시 `cd web && npm audit`이라, 차례로 붙여 넣으면 둘째 `cd`가 실패해 audit가 돌지 않는다. CLAUDE.md Build/Run 블록에도 블록 중간의 `cd web` 꼴이 있다(U8 이전부터).
  - 디렉터리 목록의 `scripts/  setup-volumes.sh`에 `live_scenario.py`가 없다.
- 코드 안 문장: `api/deps.py` `need_service`의 "모든 라우터가 쓰는 하나의 규칙"(§2 C4), `world.py:425`의 "wiki admin (LLM provider)"(wiki_admin은 늘 조립됨), `tests/fixtures/aldermoor/generate_map.py`의 `examples/demo_world/…` 경로.

설계 메모(결함으로 올리지 않음):
1. **S02와 `turn_running`의 뜻**(#5): 가드는 GM 보유도 `turn_running`으로 알린다. 화면이 몇 번 다시 읽을지 정하는 대신, 서버가 TurnRun만 `turn_running`으로 알리고 GM 보유는 따로 둘지 정한다. U4 domain-entities의 정의는 앞의 것이다.
2. **S09 재시도 비용**(#7): "탐지마다 다시"는 플랜이 골랐다. 탐지 안 반복을 없애도 빠른 실패에서 요청마다 33초, Retry-After에서 176초다. 연속 실패에 물러서기(backoff)를 둘지, NFR-5에 이 비용을 적을지 정한다.
3. **S15의 빈 run**: 다시 탐지가 실패하면 질문을 비운다. 다음 GET이나 답에서 게으르게 다시 탐지하고, 같은 답을 막는 것은 "답한 질문 id"로 하는 쪽이 막다른 길을 없앤다.
4. **신뢰도의 두 원천**(S29): 직접·물려받은 범위는 SCOPED_TO 값을, 전파·전해 들음은 노드 값을 읽는다. 쓰기 쪽 동기화를 유지하면 #4를 "엣지와 비교"로 고쳐 기존 어긋남도 풀고, 아니면 합의가 노드를 읽게 한다.
5. **"맞음"의 신뢰도 칸**: 신뢰도 칸 하나를 [맞음]과 [고치기]가 함께 보지만 [맞음]은 그 값을 쓰지 않는다. 칸을 고치기 전용으로 표시할지 정한다.
6. **보강 입력 보존**: 지도 클릭으로 패널이 내려가면 쳐 둔 답과 "바뀐 것" 이름이 사라진다(U3 #2가 자연스러운 흐름이라 한 그 클릭). `input`·`changed`를 run id 옆으로 올리거나 패널을 숨겨 둔다.
7. **두 World File 불러오기 경로의 한도**: JSON 21 MiB, multipart 20 MiB로 갈렸다. 정규식을 나눠 `/file/upload`에만 여유를 둘지 정한다.
8. **편집 쓰기마다 월드 전체 읽기**(S21): `require_world`가 스냅샷을 읽고 쓰기는 캐시를 비우므로, 읽기 없이 이어지는 쓰기(선택 없는 끌기, API 스크립트)는 쓸 때마다 월드를 다시 읽는다(지역 PUT 다섯 번에 포트 호출 57번, 589dc2b는 20번). WorldMeta를 먼저 보고 없을 때만 스냅샷을 보면 U2 이전 월드도 그대로 된다.
9. **라벨 없는 `edges_touching`**(C10): 플랜이 U3 C10의 WHERE를 그대로 골랐다. 라벨이 없어 Neo4j가 색인을 쓰지 못하고, 이제 NPC 저장마다 돈다. 라벨·관계 종류를 넘겨 받게 할지 정한다.
10. **S27 응답 크기**: 해석할 수 없는 본문을 그대로 되돌려 보내 1 MiB가 3 MiB, 40 MiB가 120 MiB가 된다(NUL 본문의 6배는 U8 이전부터). 큰 입력은 길이만 보일지 정한다.
11. **pyproject 라이선스 표**: setuptools 84가 "2027-Feb-18 이후 지원하지 않는다"고 경고한다(약 4.5개월). 빌드 요구에 상한이 없어 이미지·CI가 최신 setuptools를 받는다. SPDX 문자열 + `setuptools>=77`로 바꾸거나 상한을 둔다.
12. **GM 짧은 쓰기의 직렬화**: #9·#12·§3 피드백 몫은 뿌리가 같다(U7 #2가 GM 쓰기끼리 리스를 나누게 함). LLM 쓰기는 지금처럼 나누고, 결정적인 짧은 쓰기만 세션 잠금으로 줄 세울지 정한다.
13. **빌드 시간과 nginx**(#2, sweep): Infra §3.2는 130초를 대화 한 줄에 맞췄다. compose가 주된 실행 방법이 된 지금, 빌드를 202 + 진행 조회로 바꿀지 `/build` 경로만 시간을 늘릴지 정한다.

## 6. 확인한 것
| 검사 | 값 |
|---|---|
| 전체 `pytest -q --no-cov -p no:cacheprovider`(hypothesis 저장소는 scratchpad) | 933 passed (55초) |
| 깨끗한 clone(UTC, coverage 켬, seed 둘) | 933 passed |
| `npx vitest run` | 197 passed (9 files) |
| `npx tsc --noEmit` / `npm run build` | clean / 됨 |
| `ruff check` / `black --check --line-length 100` (`locus api tests scripts`) | clean (274 files unchanged) |
| `mypy locus api` | 11 errors (6 files), 기준선과 같다. U8이 더한 줄에는 0이다(`neo4j_repo.py:41-42`는 손대지 않은 `connect()`) |
| 경계 import·포트 | `test_boundaries` 4 passed. 외부 클라이언트 import는 어댑터와 조립 루트에만 있다 |
| Python 3.11 | ruff(py311) clean, 모든 .py가 Python 3.10에서도 compile된다, 3.12+ API를 쓰지 않는다(로컬 venv는 3.14) |
| 패키지·이미지 | Docker 문맥에서 만든 wheel에 데모 파일 넷(`manifest.json`, `emberleaf.world.json`, `emberleaf/map.json`, `emberleaf/memo.md`)이 다 있고, 풀어 놓은 wheel에서 `check_packaged()`가 []다. requirements.txt = dependencies. CI YAML이 파싱되고 이미지 작업의 `python -I -c` 들여쓰기·종료 코드가 맞다. `npm audit --omit=dev`(lock만) 0. `docker compose config`(정적, 띄우지 않음)가 유효하고 인프라 포트가 `127.0.0.1`로 풀린다. web 이미지의 lock에 Alpine(musl)·arm64 바이너리가 있다 |
| 데모 데이터 | Emberleaf가 BR-U8-6~11과 domain-entities §5에 맞다: 지역 12·3단, 마을 NPC 2/2/2/1/3/2/2/1(지방·섬 0), 10쌍 모두 두 방향, 시작 지역에서 여덟 마을 도달, 막힌 쌍 둘의 우회로, 마을 DIRECT 2개 이상, 전역 2, 서로 다른 마을·분류의 씨앗 3. §5.2 최대 곱 무게표가 셋째 자리까지 같다. 중복 id·끊긴 참조가 없고, 첫 보강 run은 대륙 지역의 GAP 하나만 묻는다. 유물 사건은 Sunstrand(0.131)에 닿지 않는다 |
| EventSeed 저장·World File | Neo4j 속성은 값만이다(열거형은 문자열, provenance는 `prov_*`로 펼침, lifecycle None은 빠졌다가 None으로 읽힘). `replace_edges`의 `$props`에 identity 속성이 늘 있다. World File 절의 재매핑·`set_world_id`·참조 검사·정렬·불러오기, 로더의 dangling 씨앗 제외, 지역 삭제 ③b(재시도 계획이 남은 씨앗을 다시 찾음, 모든 쓰기 자리 끊기 PBT)가 맞다. `unscoped_knowledge_ids`는 옛 세 계산과 값이 같다 |
| 키 없음 | 운영 방식으로 조립한 키 없는 앱에서 경로 약 85개를 불렀다. 5xx는 기대한 503뿐이다. 데모·World File·에디터·priors·related-priors·보강 시작·knowledge·play·GM·씨앗(201 → 409 진행 중 → 409 닫힘)이 된다. 빈 `OPENAI_API_KEY=`는 llm=None이다. `needsLlm`은 서버의 503 문장과 맞고, 실패한 대화 호출 문장에는 맞지 않는다 |
| 씨앗 | 확인 순서(리스·턴 → 열림 → 씨앗 → 지역 → 진행 중)가 BLM §3.3과 같다. lifecycle None은 분류 기본값, 설명이 비면 제목, 타임라인 payload에 `seed_id`·`seed_title`, 닫힌 세션 읽기, 해소 뒤 다시 시작, 지역이 없는 씨앗의 404가 맞다. PostgreSQL에서 provenance가 JSON 통째로 저장되어 `refs`가 남는다. 씨앗 시작 → 지역 삭제 → 턴 → 해소 → 내보내기 → 다른 world id로 불러오기에서 5xx가 없다 |
| U3 이월 | #10(PG에서 설정 ∥ 해소, 같은 사건 해소 ∥ 해소는 `FOR UPDATE`로 줄 섬, 조건부 contributions 쓰기가 두 어댑터에서 같음), #12 패널(404 → GET run, 서버 문장), #13(NPC 옮기기 순서·옛 집을 엣지에서, `set_prior_ref`의 `replace_edges`), #14·#15 기본 흐름, S01, S04, S05(`session_ids`), S07, S08, S10(정상 경로), S17, S18, S19·S20·S27(정한 범위), S21, S23(다른 표식 위에서 놓아도 저장, 다음 클릭은 고르기), S24, S25, S26, S30, S31, S32, C3(`delete_held`), C4, C5(값), C7(`open_sessions`의 `SessionStatus` 비교), C8, C9(스냅샷 한 번), C12, C13, C14, C15, C16(create·resolve 이름), C17이 맞다(빠진 곳은 위 지적) |
| 웹 API 계약 | 이 diff가 건드린 모든 경로의 메서드·쿼리·본문·응답 필드가 라우트·`schemas.py`와 맞다(capabilities, demos, 데모 불러오기, 씨앗 둘, 삭제 계획·보고의 씨앗, export의 `unscoped_knowledge_ids`, AugQuestion `type`·`needs`·`ref_kind`·`connection`, AugAnswer `title`·`confidence`, `WorldInfo`, `ConnectionSave`). 409 본문 셋이 `openSessionsOf`와 맞는다 |
| 래퍼·어댑터 | `replace_edges`·`edges_touching`은 Neo4j와 가짜에서 identity·방향·world 범위·반환이 같다(`types=[]`만 다르고 부르는 곳 없음). EventStore의 새 인자가 메모리·`_PgStores`·PG 래퍼에 모두 있고 `for_update`는 UoW 안에서만 쓰인다. MeteredGraph는 `replace_edges`를 쓰기 하나로 센다. 손으로 쓴 가짜 둘은 새 메서드에 닿지 않는다. WikiAdmin이 만든 EditorWrites는 에디터와 같은 graph·search·cache를 쓴다. 서술기 분리(`prompts`·`call`·`finish`)를 쓰는 곳이 맞다 |
| 추출·이동 | `useBulkRumors`(순서·가드·`mapLimit`·클로저·`after`의 `refreshRef`)와 `AugmentQuestion`(testid·입력)이 옛 코드와 같다. `useReplaceConfirm`의 세 호출처가 부수 효과 있는 `sessionsAsked`를 맞게 쓰고 `answer()`는 늘 최신 렌더를 읽는다. `_need` → `need_service`는 같은 문장이다. `load_demo_world`·`buildWorldDemo`·`LlmBanner`·`Editors.get_node`/`prior_ids`·DEMO 상수를 부르는 곳이 없다. 사건 열거형은 같은 클래스로 다시 내보낸다. 지운 i18n 키 22개는 동적 키로도 닿지 않고, ko·en 키 집합이 같으며, 모든 리터럴 키와 자리표시자가 채워진다 |
| react-router 7.18 | 쓰는 API 중 동작이 바뀐 것이 없다(모든 경로가 절대, `NavLink` 매칭이 같음). 이동이 `startTransition` 안에서 돈다. 언마운트 뒤 `navigate`가 이동하는 점은 §3 |
| 저장소 상태 | 리뷰를 마친 뒤 `git status`에는 이 기록 파일만 있다. 부수 효과는 "방법"에 적었다 |

## 7. 남은 결정 (사람이 고른다)
원하시는 것: 세계관 자료로 만든 월드에서 소문과 사건이 지형을 따라 퍼지는 솔로 TRPG를, 처음 온 사람이 명령 두 줄과 클릭 한 번으로 데모로 겪게 하는 것.
지금 하는 것: 승인된 U8 코드의 리뷰를 마쳤습니다(코드는 고치지 않음). 이 질문은 찾은 결함을 Build & Test 전에 U8 후속으로 고칠지, 다음 주기로 넘길지를 정합니다.

U8 코드는 승인됐다(3a6b5b6). 아래 지적을 지금 고치면 **승인된 코드를 바꾸게 된다**. 다음 단계는 Build & Test이고, 거기서 code-summary 15.3의 라이브 시나리오를 실제 스택에 돌린다.
- 지금 아는 것: 정확성 지적 15건이 모두 재현으로 확인됐다.
  - medium 셋: #1은 `/`에 들어올 때마다 잠깐 열리는 창(목록이 실패하면 계속)에서 데모 카드가 묻지 않고 편집된 월드를 교체한다. #2는 빌드 중 패널을 닫았다 열거나 nginx 504 뒤 다시 누르면 같은 월드를 두 번 빌드해 지역이 두 벌이 된다. #3은 Build & Test가 돌릴 라이브 시나리오가 행적 전파(US-6.5)를 한 번도 확인하지 못하고 종료 0이다.
  - #4·#6·#7·#8은 이번에 들어간 U3 이월 수정(S29·C11, S03, S09, C2)이 원래 지적을 다 닫지 못했거나 새 결함을 만든 것이다. #5(b)는 한 줄짜리다.
  - 나머지(#9~#15)는 low–medium 이하이고, 겹치는 GM 쓰기(#9·#12)는 GM 탭 둘이나 API에서만 생긴다.
- 왜 지금 정하나: Build & Test가 #3이 있는 채로 돌면 9·11단계가 SKIP이라 행적 전파의 판정 증거가 비어 있다. U8은 이 주기의 마지막 유닛이라 넘기면 다음 주기로 간다.
- 이 답에 기대는 것: U8 후속 커밋을 할지, Build & Test의 라이브 시나리오 판정, operations.md의 알려진 한계 목록.

선택지와 결과:
- **A. (권장) 섞는다. medium 셋(#1~#3)과 이번 이월 수정이 남긴 결함(#4·#6·#7·#8)과 한 줄짜리 #5(b)를 지금 U8 후속 커밋으로 고치고, 나머지는 다음 주기 목록에 올린다.**
  - 까닭: #1·#2는 고칠 때까지 사용자의 월드를 조용히 바꾸고 #3은 바로 다음 단계의 증거를 비게 하며, #4·#6~#8은 이번에 손댄 코드라 같은 맥락에서 닫는 편이 싸다.
  - 결과: 고칠 것은 다음과 같다.
    - 데모 카드: 목록을 모르는 동안 버튼을 끄거나 "없음" 갈래를 `replace=false`로
    - BuildPanel: 빌드 중에는 key를 바꾸지 않고 `busy`·리포트를 유지, 서버의 같은 world_id 빌드 하나로 제한
    - 라이브 시나리오: say + end_talk, appraisals로 SKIP/FAIL 가르기, 10a에 소문 수, 흉내 서버는 EndTalk에서만 씨앗, BLM §7 정정
    - S29·C11: 비교 기준을 저장된 스코프 값·검색 문서로
    - S03: 되돌리기 쓰기를 항목별 멱등으로
    - S09: 탐지 안에서 실패한 키 기억
    - C2: 탐지기의 ConnectionKey를 Issue에 싣기
    - S02 (b): 실패한 다시 읽기도 다음 읽기를 예약
  - 테스트: vitest 3~4개(목록 대기·실패의 데모 카드, 빌드 중 닫고 열기, 실패한 쥠 다시 읽기)와 pytest 5~6개(재시도 뒤 스코프 값·검색 문서, 되돌리기 중간 끊기, 탐지 안 실패 조회 수, `|` 지역 id, 같은 월드 빌드 둘, 라이브 시나리오의 EndTalk 경로)를 더한다. 게이트(pytest·vitest·ruff·black·tsc)를 다시 돈다.
  - 비용·위험: 승인된 U8 코드를 다시 연다(audit에 후속 수정으로 남긴다). Build & Test가 그만큼 늦어진다.
  - 되돌리기: 커밋 단위라 쉽다.
- **B. 전부 다음 주기로 넘기고 Build & Test로 간다.**
  - 결과: U8 코드는 그대로 두고 정확성 15건·§3 22건·정리 11건·설계 메모 13건을 다음 주기 목록에 올린다. Build & Test 문서에 #3을 알려진 한계로 적고 9·11단계 SKIP을 "확인 안 됨"으로 읽는다.
  - 비용·위험: 그동안 #1·#2가 데모 사용자의 월드를 바꿀 수 있다(백업은 남음). Build & Test가 US-6.5를 라이브로 확인하지 못한 채 승인된다. 이월 수정 넷(#4·#6~#8)이 code-summary에 "고침"으로 적힌 채 남는다.
  - 되돌리기: 쉽다(목록 문서만 바뀐다).
- **C. 감수 위험으로 기록하고 진행한다.**
  - 결과: operations.md "Accepted risks"에 적고 고치지 않는다.
  - 비용·위험: #1은 BR-U8-5·20·21을, #3은 BR-U8-36과 code-summary §9의 기대를 어긴 채 남고 회귀 테스트도 없다. 다음 주기에 같은 지적을 다시 찾게 된다.
  - 되돌리기: 나중에 고칠 수 있지만, 그사이 교체된 월드는 백업에서 손으로 되살려야 한다.
- X. Other (please specify)

어느 쪽을 고르든 설계 결정 넷은 따로 남는다. `turn_running`이 GM 보유를 포함할지(설계 메모 1, #5 (a)), GM의 짧은 결정적 쓰기를 세션 단위로 줄 세울지(설계 메모 12, #9·#12), 빌드를 nginx 130초 밖으로 뺄지(설계 메모 13), pyproject 라이선스 표의 기한(설계 메모 11, 2027-02-18)이다. 셋째·넷째는 배포 문서와 이미지에 바로 닿으므로 Build & Test 전에 정하는 편이 낫다.

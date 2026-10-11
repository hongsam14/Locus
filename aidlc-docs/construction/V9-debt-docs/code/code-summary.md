# V9 부채·문서 마무리 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V9 코드 생성을 마쳤다(Step 1~10). 이번 주기의 마지막 유닛으로 부채를 갚고 문서를 코드에 맞췄다.
- mypy 오류 0이고 CI가 이를 지킨다. npm audit은 전체 0이다.
- 시간 초과에 기대던 시험, 실제로 자던 재시도 시험, 닫지 않던 sqlite 엔진, 공허한 단언 둘을 고쳤다. ResourceWarning은 53줄에서 0줄이 됐다.
- 라이브 시나리오 10a는 가까운 지역이 더 크게 듣는지 단언하고, 이상한 응답을 FAIL로 기록한다.
- 페이지가 Locus를 화면의 언어로 말하고 아이콘을 갖는다. `env.example`이 모든 설정을 적는다.
- 에디터·지도 문장이 해요체이고, 화면이 쓰지 않는 사전 키가 없다. 〔코드 리뷰 01 #15: `word.rumor.promoted` 하나가 남아 있었다. § 9에서 지웠다.〕
- CLAUDE.md, README, web/README, operations.md, 낡은 docstring이 코드와 맞는다. 다음 주기 목록은 항목마다 출처와 위치를 갖는다.

이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V9-debt-docs-code-generation-plan.md`(10단계, 승인 2026-10-11; 범위 답 A, 실행 메모 § 1.4 R-01~R-06 포함).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `10f2333`) | 결과 (Step 10, `e8e2fe0`) |
|---|---|---|
| pytest | 1228 | **1244** (+16) |
| `ResourceWarning` 줄 (`-W default::ResourceWarning`) | 53 | **0** |
| 전체 pytest 시간 | 51 s | 41 s |
| mypy `locus api` | 11 | **0** (CI 단계) |
| ruff · black | `locus api tests` clean | `locus api tests scripts` clean (CI 대상) |
| vitest | 813 | **821** (+8) |
| tsc | clean | clean |
| npm audit 전체 | 5 (moderate 3, high 2) | **0** |
| npm audit `--omit=dev` | 0 | 0 |
| 첫 화면 JS gzip (`index`) | 119.74 kB | **119.41 kB** (−0.33, 지운 키와 짧아진 ko 문장) |
| 에디터 · GM 묶음 gzip | 14.68 · 11.98 kB | 같음 |

가장 느린 시험 10개(0.55~0.99 s)는 hypothesis 상태 기계와 성질 시험, SQL 겹침 시험이다. 시간을 기다려 지나가는 시험은 없다(기준선의 가장 느린 시험은 5.00 s 잠금 대기, 3 s 재시도 둘이었다).

게이트 스크립트는 세션 scratchpad의 `v9gate.sh`다(ruff·black·mypy 수·pytest와 `ResourceWarning` 수·tsc·vitest·audit 둘·vite build).

커밋(9개 + 이 요약):

| 단계 | 커밋 | 내용 |
|---|---|---|
| 2 | `d386805` | dev 의존성 공지 0(vitest 4.1.11 등, 잠금 파일만) |
| 3 | `d34c0a8` | mypy 0(동작 바꿈 없는 타입 고침 6파일), CI mypy 단계, CI 린트에 `scripts` |
| 4 | `49ca342` | 시험 위생: 잠금 순서 사건, `or True`의 실제 값, 재시도 대기 기록, 엔진 dispose, 대역 병합, `/health` 실패 가능 |
| 5 | `239f82d` | `index.html`(ko, 제목, 설명, theme-color, favicon), `env.example` 두 설정 |
| 6 | `5db8ae9` | 라이브 시나리오 10a 방향, 이상한 응답 FAIL, poll 하한 |
| 7 | `7eb0b61` | 에디터·지도 ko 24줄 해요체, 쓰지 않는 키 11개 지움, 규칙 시험 둘 |
| 8 | `86e225b` | CLAUDE.md·README·web/README·operations.md·docstring 7곳 |
| 9 중 | `fa0927d` | GM 수동 턴 docstring(Step 9의 조사에서 찾음) |
| 9 | `e8e2fe0` | 다음 주기 목록 다시 씀 |

## 2. 바꾼 파일과 만든 파일

- **의존성**: `web/package-lock.json`(17개 patch·minor; `lockfileVersion` 3 그대로).
- **타입**(Step 3): `locus/world/ontology/reconciler.py`, `locus/world/topology/hierarchy.py`, `locus/world/wiki/linker.py`, `locus/shared/storage/neo4j_repo.py`, `locus/shared/storage/opensearch_repo.py`, `locus/shared/llm/openai_provider.py`. `type: ignore`를 더하지 않았다.
- **CI**: `.github/workflows/ci.yml`(ruff·black 대상에 `scripts`, mypy 단계).
- **시험 위생**(Step 4): `locus/shared/llm/retry.py`(모듈 `_sleep`), `tests/conftest.py`(엔진 dispose 자동 fixture), `tests/play/test_repository_contract.py`, `tests/play/test_player_mode.py`, `tests/shared/llm/test_retry_and_factory.py`, `tests/shared/storage/fakes.py`, `tests/shared/storage/test_port_contract.py`, `tests/world/editor/helpers.py`, `tests/api/test_keyless_api.py`, `tests/api/test_knowledge_api.py`.
- **페이지 머리·설정**(Step 5): `web/index.html`, 새 `web/public/favicon.svg`, 새 `web/src/__tests__/document-head.test.ts`, `web/src/test/node-fs.d.ts`, `env.example`.
- **라이브 시나리오**(Step 6): `scripts/live_scenario.py`, `tests/test_live_scenario.py`.
- **사전**(Step 7): `web/src/i18n/{ko,en}.ts`, `web/src/__tests__/i18n.style.test.ts`, `web/src/test/paths.ts`(`sourceFiles`를 옮겨 옴), `web/src/__tests__/{design.grep,dialogue,capabilities,components}.test.*`.
- **문서**(Step 8·9): `CLAUDE.md`, `README.md`, `web/README.md`, `aidlc-docs/operations/operations.md`, `aidlc-docs/operations/next-cycle.md`, `Dockerfile`(주석), docstring: `neo4j_repo.py`, `knowledge/loader.py`, `play/event/dynamics.py`, `play/event/suggester.py`, `api/routers/play.py`, `api/routers/gm.py`, `play/storage/postgres_repo.py`.

## 3. 요구 → 확인

| 요구 | 한 일 | 확인 |
|---|---|---|
| FR-T2 dev 의존성 공지 | `npm audit fix`(npm 11.20.0, § 5 이탈 1) | 전체 audit 0, `npx npm@10.9.2 ci`가 잠금 파일 그대로 설치, vitest·tsc·build 같음 |
| FR-T3 mypy 게이트 | 11건을 코드로 고침, CI 단계 | `mypy locus api` 0, ci.yml 단계 |
| FR-T4 문서 어긋남 | § 3.1 닫힘 표 | 문서의 경로를 하나씩 `ls`로, 수치는 게이트 출력으로 대조 |
| FR-T5 `env.example` | `SESSION_DB_HOST`(URL 조립 설명), `TRANSLATION_WARM_WORKERS` | `Settings`의 별칭을 하나씩 `env.example`과 대조했다(이번 한 번; 시험은 없다 — § 6) |
| FR-T6 시험 위생 | 잠금 순서 사건(5.00 s → 0.20 s), `or True` → 실제 값 둘, 재시도 대기 기록(`[1, 2]`), 엔진 dispose, 대역 병합(R-01), `/health` | `ResourceWarning` 0, 돌연변이 § 7 |
| FR-T7 라이브 시나리오 | 10a: 씨앗 지역 사건의 `contributions`가 항구 > Ironcrag, 왜곡도 항구 > Ironcrag이고 > 0.3; JSON 아님·`AttributeError`·`HTTPException`은 FAIL; `--poll` ≥ 1 s | 가짜 서버 시험 13개 더함, 실제 API의 키 없는 실행이 10a PASS, 돌연변이 L1~L10 |
| FR-D10 문서의 언어 표시 | `lang="ko"`, 제목 "Locus", 설명 = README 목적 문장, favicon | `document-head.test.ts` 4개(언어 바꾸면 `lang`이 따라감 — R-03, 이미 있던 동작) |
| FR-C14 다음 주기 목록 | `next-cycle.md` 다시 씀 | 항목마다 출처와 `fa0927d`의 file:line; 위치 8곳을 직접 읽어 대조 |
| W-1 에디터·지도 해요체 | ko 24줄 | `i18n.style.test.ts` 규칙(합니다체 끝 없음, 마침표로 끝나면 해요체), 돌연변이 K1~K3 |
| W-2 옛 사전 키 | 11개 지움 | "모든 키가 쓰인다" 시험(글자 그대로 또는 키 묶음), 돌연변이 K4 |
| W-3 CI `scripts` 린트 | ruff·black 대상 | ci.yml |
| W-4 대역 결함 둘 | `upsert_edges` 병합·`replace_edges` 전체 교체, `/health` degraded 시험 | 계약 시험 2개, 돌연변이 H4~H6 |

unit-of-work의 완료 조건 넷(mypy 0과 CI, audit 0, 시험 위생, CLAUDE.md Status·Gates)은 위 표의 FR-T3, FR-T2, FR-T6, FR-T4 줄로 닫힌다.

### 3.1 FR-T4 닫힘 표 (code-quality-assessment § G와 FR-T4의 줄마다)

| 문서 · 문장 | 처리 |
|---|---|
| CLAUDE.md Status — 수치 두 벌, "in progress", "ports on 127.0.0.1" | 고침(`86e225b`): Follow-up 주기, pytest 1244 + vitest 821, 인프라만 127.0.0.1 |
| CLAUDE.md Gates — mypy가 CI처럼 읽힘 | 고침: 이제 CI에 있고, Gates는 CI 잡대로 적었다 |
| CLAUDE.md Conventions — 교차 월드 prior 검색 | 사실대로 적음: 필터가 `domains`, 색인은 `meta.domains`라 늘 0건. 기능 고치기는 next-cycle § 7 |
| CLAUDE.md Conventions — "`world_id` partitions every graph" | 고침: 색인된 속성이고, id는 라벨마다 전역 유일 |
| CLAUDE.md Code 목록 — 빠진 play 파일, DeedPanel 자리 | 고침: rumor 넷, `event/seeds`, `turn/changes`, `deeds/caps`, `storage/clock`, `write_section`, `knowledge/cache`, `world/carry_over`; Frontend 줄은 V2~V8 구조와 `GmTabs`로 |
| README — "NPC가 만들어집니다" | ~~이미 고침(앞 유닛)~~ 〔코드 리뷰 01 #2: 앞 유닛의 문장도 틀렸다. 에디터는 씨앗을 만들지 않는다. § 9에서 "NPC는 에디터에서, 사건 씨앗은 World File의 `event_seeds`로"로 고쳤다〕 |
| README:11 — 행적과 사건이 한 칸씩 | 고침: 행적 소문은 한 턴에 한 칸, 사건은 같은 턴에 가장 강한 길로 |
| README · operations — [바로 플레이]는 LLM 없음 | 고침: LLM은 없고, 키가 있으면 API 길은 임베딩을 부른다(CLI `world demo`는 부르지 않는다) |
| operations — 씨앗 두 번째 시작 409 | 이미 맞음: V5가 겹친 시작을 세션 쓰기 구간으로 줄 세웠다 |
| operations — interrupted run | 이미 고침(V5): 위치와 턴 청구도 되돌리고, 확인 절차를 적었다 |
| operations — Observability healthcheck 셋, 제목 "(placeholder)" | 고침: app·web healthcheck와 `/health` ok·degraded, 제목·머리말 |
| operations — SessionBar·SessionPanel·Doodly·옛 에디터 | 고침: 〔Follow-up Vn〕 메모로 바뀐 곳을 적음(V4 홈, V6 GM, V8 에디터, V2 디자인), CI mypy, 라이브 시나리오, A8-10 |
| next-cycle.md:40 — dev audit 4건 | 다시 씀(`e8e2fe0`) |
| web/README — LLM 꺼짐 안내, 세션 띠 | 다시 씀: 경로별 화면, 소스 구조, 키 없을 때 |
| web/index.html:6 — 옛 제목 | 고침(`239f82d`) |
| X2 BR-X2 — 손글씨, 가로 스크롤, 하드코드 색 | 이미 닫힘(V2 디자인 시스템과 design grep 시험) |
| docstring — `neo4j_repo.py:1-4`, `:71-72` | 고침: traversal 없음, `WorldMeta`, 라벨마다 유일한 id |
| docstring — `cache.py:4` "no TTL" | 이미 고침(V7): 버전 표시 확인을 적는다 |
| docstring — `loader.py:3-4` 노드 종류 | 고침: `EventSeed`를 더함 |
| docstring — `event/dynamics.py`·`suggester.py` "GameMasterService" | 고침: 턴 advancer와 EventService |
| docstring — `api/routers/play.py:7-8` "U5에 온다" | 고침: 대화 경로가 여기 있다 |
| docstring — `postgres_repo.py:7-8` "DB가 created_at" | 고침: 타임라인·메시지·행적·평가는 앱 시계(인라인 주석도) |
| docstring — `api/errors.py` 매핑 목록 | 이미 고침(V2): 목록을 두지 않고 규칙만 적는다 |
| `Dockerfile:9` "api = …" | 고침: pip은 `locus*`만 설치하고 `api`는 WORKDIR의 소스다 |
| (조사 중 찾음) `api/routers/gm.py` 수동 턴 "LLM 없이" | 고침(`fa0927d`): LLM이 있으면 다른 턴처럼 소문을 쓴다 |
| 이번 주기의 변경 반영 | CLAUDE.md Status의 V1~V9 줄, operations의 〔Follow-up〕 메모. V1·V3 운영 메모는 더하지 않았다(R-02) |

### 3.2 데모 번역 판정 (§ 1.1)

"데모 번역에 엔티티·사전 하나의 한국어가 없음"(V8 § 9)은 고칠 것이 아니다. 캡처용 가짜 서버가 번역을 직접 덮어쓰다 생긴 일이다. 제품의 번역 종류는 `world`, `region`, `knowledge`, `npc`, `event_seed`이고, 에디터는 엔티티와 사전을 원문으로 보인다.

## 4. 바뀐 기존 시험

- `tests/play/test_repository_contract.py` — U4 되돌림 시험: B가 잠금 앞에 섰다는 사건(`b_started`)을 기다린 뒤, A를 풀기 전에 `b_done.wait(0.2)`가 거짓임을 단언한다. 모든 `join`에 5초 시한이 있다(R-05).
- `tests/play/test_player_mode.py` — `… or True`를 지우고 실제 값 둘을 단언한다. 먼저 돌려 읽은 값은 `rumors_added` 2개와 `"C: 2 new rumors, event applied"`이다. 옛 리터럴 "1 new rumor"는 틀린 값이었다.
- `tests/shared/llm/test_retry_and_factory.py` — 실제로 자지 않고, 기다린 시간 `[1.0, 2.0]`을 기록해 단언한다.
- `tests/api/test_keyless_api.py` — `/health`가 world·play가 켜졌다고 단언한다. 새 시험은 조립된 서버에 경계가 하나 빠지면 `degraded`임을 본다.
- `tests/world/editor/helpers.py` — 계량 대역의 `replace_edges`가 대역의 전체 교체를 부른다.
- `tests/test_live_scenario.py` — `test_main_parses_its_options`가 0.5 대신 2.5를 쓴다(0.5는 이제 1로 올라간다).
- `web/src/__tests__/dialogue.test.tsx` — `t()` 되돌아가기 시험이 지운 `play.npcs`·`play.facts` 대신 `nav.play`·`lang.label`을 쓴다.
- `web/src/__tests__/capabilities.test.ts` — C14 "새 키" 목록에서 `llm.offNotice`·`seed.none`을 뺐다.
- `web/src/__tests__/components.test.tsx` — GM 화면에 옛 "— 없음 —" 항목이 없는지를 사전 밖 글자로 본다.
- `web/src/__tests__/design.grep.test.ts` — 소스 목록을 `src/test/paths.ts`의 `sourceFiles`에서 받는다(동작 같음).

지운 시험은 없다.

## 5. 이탈

1. **npm 11로 `audit fix`**(Step 2). 시스템 npm 9.2.0과 CI의 npm 10.9.2는 `audit fix`에서 arborist가 죽는다(`#loadPeerSet`의 `edgesOut` null — vitest의 peer jsdom → 선택 peer canvas). npm 11.20.0(`npx`, 2026-09-22 공개)으로 고치고, CI와 같은 `npx npm@10.9.2 ci`가 그 잠금 파일을 그대로 설치하는 것을 확인했다. 앞으로 잠금 파일을 고칠 때도 같은 일이 날 수 있다.
2. **W-2가 앞머리 여섯 밖의 키 다섯도 지움**(Step 7). `region.title`·`region.empty`, `llm.offNotice`, `seed.title`·`seed.none`, `notice.llmNeeded`는 계획이 적은 앞머리(`play.`·`gm.`·`editor.`·`map.`·`session.`·`home.`) 밖이지만 같은 종류(어느 화면도 읽지 않음)라 함께 지웠다. 쓰임 시험은 사전 전체에 건다.
3. **말투 규칙 시험의 앞머리**(Step 7). 계획 7.3은 `editor.`·`map.hint.`·`delete.`였다. 에디터가 보이는 `augment.`·`wiki.`·`build.`도 해요체로 고쳤으므로 규칙에 넣었다.
4. **10a의 지역 id**(Step 6). R-04대로 `/state` 행의 `region_id`를 쓴다(처음엔 내보내기의 id를 썼다가 계획대로 바꿨다).
5. **docstring 한 곳 더**(Step 9 중). `api/routers/gm.py`의 수동 턴 docstring은 § G 목록에 없었지만 같은 종류라 고쳤다(`fa0927d`).

## 6. 알려진 한계

- 플레이·대화·데모 카드의 ko 16줄은 아직 합니다체다. W-1은 에디터·지도만 다룬다(next-cycle § 4).
- 쓰임 시험은 글자 그대로의 키와 `` `prefix.${…}` ``·`"prefix." +` 꼴의 키 묶음만 안다. 다른 방식으로 키를 만들면 시험이 그 키를 안 쓰는 것으로 본다. 그때는 시험이 실패해 알려 준다.
- `/health`의 degraded 시험은 `assemble_all`을 바꿔 끼운다. 실제 조립(`assemble_all`) 자체를 지나는 시험은 여전히 없다(RE-T11, next-cycle § 5).
- 새 설정을 더하고 `env.example`을 잊어도 잡는 시험이 없다. 이번에는 손으로 대조했다.
- 남은 경고 하나는 Starlette의 httpx 지원 종료 공지다(제3자).
- 라이브 시나리오는 이번 단계에서 실제 스택에 대고 돌리지 않았다. 가짜 서버와 실제 API의 키 없는 조립으로만 확인했다. 키가 있는 실행은 Build and Test 몫이다.

## 7. 돌연변이 확인

모두 잡혔다(36/36). 고친 코드를 하나씩 되돌려 시험이 실패하는지 본다.

| 묶음 | 돌연변이 | 결과 |
|---|---|---|
| Step 4 | H1 저장소 잠금을 뺌(되돌림 시험이 순서를 잡는지) · H2 재시도 대기 값을 바꿈 · H3 대기를 바꿔 끼울 수 없게 · H4 `upsert_edges`가 다시 전체 교체 · H5 `replace_edges`가 병합 · H6 `/health`가 늘 ok | 6/6 |
| Step 4 (`or True`) | M1 요약이 소문 수를 하나 적게 셈 · M2 "event applied"를 뺌 — 옛 `… or True` 단언이면 둘 다 살아남는다 | 2/2 |
| Step 6 | L1 영향 방향 `>` → `!=` · L2 영향 검사 없앰 · L3 0.3 하한 없앰 · L4 왜곡도 방향 `>` → `!=` · L5 JSON 검사 없앰 · L6 `AttributeError` 안 잡음 · L7 `HTTPException` 안 잡음 · L8 poll `<` → `<=` · L9 poll 하한 없앰 · L10 씨앗 지역이 아닌 사건도 받음 | 10/10 (L10은 다른 지역 사건 시험을 더한 뒤) |
| Step 7 | K1 "연결이 없습니다"로 되돌림 · K2 줄 가운데의 "지웁니다:" · K3 해라체 문장 · K4 아무도 안 쓰는 키 하나 더함 | 4/4 |

## 8. 다음에 넘김

- **Build and Test**(이번 주기): compose를 띄우는 것은 사람에게 먼저 묻는다(호스트 3000은 다른 서비스가 쓰므로 `WEB_PORT=13000`). 키가 있는 라이브 시나리오 15단계(새 10a 포함), V5 nfr-light § 3의 PG 스모크 P1~P6, nginx 머리, Neo4j 라벨 삭제, 백업 실패, GM·에디터 한 바퀴(next-cycle § 1).
- 다음 주기: `aidlc-docs/operations/next-cycle.md`(설계 결정 12, 정확성 결함, 화면 넘김 17, RE low·정리, U8 § 2, 진행 중 기능 넷, 범위 밖).

## 9. 코드 리뷰 01 뒤 (2026-10-12)

기록: `reviews/code-review-01.md`(지적 40: high 0, medium 3, low 37). 사람의 답은 **A — 거의 모두 고침**이다. 39건을 고쳤고, #26(mypy·langchain 판 고정)은 next-cycle § 8의 잠금 파일 줄에 붙였다.

| 커밋 | 고친 지적 |
|---|---|
| `10bdc20` | 라이브 시나리오 #4, #5, #8~#12 |
| `011f7e7` | 웹 시험·사전 #1, #13~#20 |
| `c53e527` | 백엔드·시험 #6, #7, #21~#25 |
| (이 요약과 같은 커밋) | 문서 #2, #3, #27~#40, README 문장 시험 |

| 항목 | 리뷰 전 (`bc4ac75`) | 고친 뒤 |
|---|---|---|
| pytest | 1244 | **1262** |
| vitest | 821 | **825** |
| mypy · ruff · black | 0 · clean · clean | 같음 |
| ResourceWarning | 0 (지키는 것 없음) | 0, 그리고 하나라도 나면 실패(`filterwarnings`) |
| npm audit 전체 · `--omit=dev` | 0 · 0 | 같음 |
| 첫 화면 JS gzip | 119.41 kB | 119.39 kB |
| 저장소 `data/backups`의 시험 백업 | 실행마다 4개씩 늘어 369개 | 늘지 않는다(옛 파일은 그대로 두었다 — 사람이 지울 것) |

고친 것 가운데 동작이 바뀐 것:
- `scripts/live_scenario.py`
  - 10a는 항구 왜곡도에서 피드백 몫을 뺀 값이 0.3 + 사건 기여 이상인지 본다.
  - `--timeout`은 0보다 큰 유한한 수만, `--poll`은 유한한 수만 받는다.
  - FAIL 문구는 실제로 기다린 시간을 적는다.
- `locus/world/topology/hierarchy.py` — 순환으로 들어가기만 하는 지역의 부모 고리는 끊지 않는다. 공개 경로로는 닿지 않는 가지다.
- `pyproject.toml`·`requirements.txt` — `langchain-openai>=0.2`.
- `pyproject.toml` — pytest가 ResourceWarning과 그로 생긴 unraisable 경고를 오류로 본다.
- `tests/conftest.py`
  - 시험이 처음 연결한 엔진만 닫는다.
  - 데이터 폴더를 임시 폴더로 돌린다.
- `web/src/i18n/{ko,en}.ts` — `word.rumor.promoted`를 지웠다.

새 시험은 #8~#12, #13~#20, #21~#25의 실패 장면을 하나씩 재현한다. 돌연변이는 웹 X1~X14, 백엔드 F1~F10과 옛 순환 규칙, 라이브 R1~R9로 34개이고 모두 잡혔다.
- F5(`if False:`)는 꼬리 시험을 끝없이 돌게 해서 실패가 아니라 멈춤으로 나타났다.
- 옛 규칙 그대로의 돌연변이는 실패로 잡혔다.

알려진 한계(새로 적음):
- 쓰임 시험에서 `error.`·`timeline.`·`log.`·`tab.`은 앞머리로 센다. 서버나 화면이 넘기는 값으로 키를 만들기 때문이다. 그래서 그 아래 새 키가 쓰이지 않아도 시험이 잡지 못한다.
- 넓은 범위 픽스처의 엔진은 설정될 때 연결해야 한다. 첫 시험 안에서 처음 연결하면 그 시험 끝에 닫힌다.

# U6 행적·전파 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.

**이 유닛이 한 것**: 플레이어가 한 일이 세계에 흔적을 남긴다.
- 도착, NPC에게 한 말, 선언한 행동이 행적이 된다. 선언 행동은 LLM GM이 서술한다.
- 대화를 마치면 그 NPC가 행적을 남에게 전할지 판단한다.
- 전할 만한 행적은 소문으로 태어나고, 턴마다 지나갈 수 있는 길을 따라 한 칸씩 더 왜곡되며 퍼진다.
- GM은 행적과 그 판단, 소문이 닿은 지역을 보고 취소할 수 있다.
- **US-6.5("내 행적을 먼 지역에서 다르게 듣는다")가 동작한다.** 통합 테스트 EX-6이 확인한다. 소문이 A에 태어나고, 다음 턴에 B, 그다음 턴에 C로 가며, 막힌 길로는 가지 않는다.

근거
- 플랜: `construction/plans/U6-deeds-spread-code-generation-plan.md`(승인 2026-10-01, 11단계)
- FD: `functional-design/*`(승인 2026-10-01)
- NFR: `nfr/nfr-light.md`(승인 2026-10-01)

## 1. 기준선과 결과
| 검사 | 기준선 (Step 1.1) | 결과 (Step 10.1) |
|---|---|---|
| `pytest -q --no-cov` | 557 passed | **630 passed** (+73, 회귀 0) |
| `npx vitest run` | 64 passed | **74 passed** (+10) |
| `mypy locus api` | 11 errors | **11 errors** (새 모듈 오류 0) |
| `ruff check` / `black --check` (locus api tests) | clean | clean |
| `tests/test_boundaries.py` | 4 passed | 4 passed |
| `tsc --noEmit` / `vite build` | clean | clean |
| `docker build` | OK | OK (`locus-u6-check`). 이미지의 OpenAPI에 `/deeds`·`/deeds/{d}/void`가 있고, `act`가 `lang`을 받는다 |

- 의도적으로 바꾼 기존 테스트는 하나다. `test_models.py::test_u5_npc_talked_is_appended_after_the_u4_kinds`는 "npc_talked가 맨 끝"을 "U4 < U5 < U6 순으로 덧붙인다"로 바꿨다. U6 타임라인 종류가 뒤에 붙었기 때문이다(NFR-1).
- 변이 확인을 했다. 하나씩 일부러 없애면 해당 테스트가 실패한다. 대상은 준비 실패의 회로 차단, 캐노니컬 원천에서 행적 소문 제외, 새 행적 소문의 감쇠 면제다.

## 2. 바뀐 파일 (55개, +4.5k / −0.1k)
**백엔드 — 새 파일**
- `locus/play/deeds/service.py`: `DeedService`. 행적과 판단을 쓰는 유일한 곳이다. 체류, 대기, 씨앗 준비, 기억, 최근 행적, GM 보기, 이름, 취소를 맡는다.
- `locus/play/deeds/caps.py`: 출력 길이 상한
- `locus/play/gm/narrator.py`: `GmNarrator`, 대체 서술
- `locus/play/rumor/spread.py`: 순수 `plan_spread`, `passable_both_ways`
- `locus/play/turn/quota.py`: `RegionQuota`

**백엔드 — 바뀐 파일**
- `models.py`
  - 행적 모델: `Deed`·`DeedAppraisal`·`DeedView`·`VoidResult`
  - 행동·서술·전파 값: `DeclareAction`(PlayerAction 유니온), `Narration`, `SpreadTarget`
  - 준비 단계 값: `DeedMemory`, `SceneBrief`, `NarrationDraft`·`AppraisalDraft`·`AppraisalOutcome`
  - 기존 모델: 소문 기원 필드 넷, `TurnRun.lang`, `ActionResult.declaration`, `TurnResult.seeded/spread_rumor_ids`, `RegionView.declare_max_chars`, 타임라인 6종, `NpcContext.deeds`
- `errors.py`: `AppraisalExistsError`
- `ports.py`: `DeedStore`, `RumorStore.list_rumors_by_origin`, `PlayUnitOfWork.deeds`
- `storage/schema.py`: 새 테이블 둘, 기존 테이블 열 7개, inspector 열 추가(두 방언)와 색인
- `storage/memory_repo.py`: 행적 저장소, `uow_depth`(구조 단언용)
- `storage/postgres_repo.py`: 행적 SQL, 소문 기원 매핑, `turn_runs` 세 열 매핑(**U4 보상 결함 수정**), `_aware`(SQLite 시각)
- `turn/advancer.py`: 선언 검증, 이동 도착 행적, `_prepare`·`_narrate`·`_scene`, 씨앗·전파·할당·면제, 실패 보상의 행적 삭제
- `rumor/service.py`: `seed`, `spread`, `append_for_turn(reserved=)`, 캐노니컬 원천만, 재생성의 행적 보존
- `rumor/dynamics.py`: `decay_support(exempt_ids=)`
- `npc/dialogue.py`: `appraise`, 기억 주입, `context_ids`에 행적
- `npc/prompts.py`: 판단 프롬프트, 행적 절, `MATERIAL` 프레이밍
- `npc/scope.py`: `pick_facts`, `deeds` 인자
- `player/movement.py`: `npcs_here`·`find_npc`(U5 C4)
- `player/service.py`: `act(lang=)`, `declare_max_chars`
- `session_service.py`: 시작 도착 행적
- `event/service.py`: 최근 행적 컨텍스트
- `wiring.py`: 조립 순서, `PlayContainer.deeds`
- `__init__.py`: 공개 이름
- `shared/config/{tuning,settings}.py`: 조정값 6개

**API**
- `api/routers/play.py`: `act`가 `lang`을 받는다.
- `api/routers/gm.py`: `GET deeds`, `POST deeds/{d}/void`(`_idle` 리스)
- `api/schemas.py`: `DeedOut`·`DeedAppraisalOut`·`DeedViewOut`

**프론트엔드**
- 새 파일: `features/play/NarrationCard.tsx`, `features/gm/DeedPanel.tsx`, `__tests__/deeds.test.tsx`
- 바뀐 파일
  - `ActionBar`(선언 입력), `PlayPage`(`act` → `Promise<boolean>`, 서술 카드)
  - `RegionScene`·`SessionPanel`(행적 배지, `reloadKey`), `PlayLog`(`GM_ONLY_KINDS`), `GmPage`(DeedPanel)
  - `types.ts`, `api/{play,gm}.ts`, `i18n.ts`(ko·en 키 + 타임라인 6종)

**테스트·문서**
- 새 테스트 파일: `tests/play/{test_deeds,test_spread,test_narrator,test_deed_turns}.py`, `tests/api/test_deeds_api.py`
- 넓힌 테스트 파일: `test_repository_contract.py`(두 어댑터 매개변수), `test_postgres_repo.py`(EX-15), `test_dialogue.py`, `test_models.py`, `test_config.py`, `strategies.py`
- 문서: `operations.md`(행적·전파 절), `env.example`(6), `CLAUDE.md`

## 3. 검증 번호와 테스트
| 번호 | 테스트 |
|---|---|
| TP-U6-1 | `test_spread.py::test_tp_u6_1_*`: 통행 가능한 이웃, 미도달, 가중치 ≥ 기준이고 ≤ `best[Y]`, 왜곡도 단조, 캐노니컬은 빈 결과 |
| TP-U6-2 | `test_spread.py::test_tp_u6_2_*`: 순수 다턴 시뮬레이션에서 판본·지역 중복 없음, 지역·턴 상한, 단조 |
| TP-U6-3 | `test_deeds.py::test_tp_u6_3_*`: 독립 필터와 같은 씨앗 준비 |
| TP-U6-4 | `test_deed_turns.py::test_ex10_tp_u6_4_*`: 취소 뒤 3턴 동안 계보가 되살아나지 않음 |
| TP-U6-5 | `test_deeds.py::test_tp_u6_5_*`와 `test_dialogue.py::test_ex12_*`: 기억은 자기 판단 ∪ 체류 중 목격 − 취소. U5 불변식은 기존 TP-U5-1a/1b가 그대로 통과 |
| TP-U6-6 | `test_deed_turns.py::test_tp_u6_6_and_nfr3_*`: 턴 호출 ≤ 예산, UoW가 열린 동안 LLM 호출 0 |
| TP-U6-7 | `strategies.py`의 `spread_worlds`·`deed_rumor`(+U5 `rumors_from` 체인) |
| TP-U6-8 | `test_spread.py::test_tp_u6_8_*`: 씨앗·전파·초안이 같은 할당 |
| EX-1~19 | 각 테스트 이름에 번호를 붙였다. EX-2/7/8/9/10/11/13/18/19는 `test_deed_turns.py`, EX-3/12/14/17은 `test_dialogue.py`, EX-15는 `test_postgres_repo.py`, EX-16은 `test_deeds.py`, EX-6은 `test_spread.py`(산술)와 `test_deed_turns.py`(통합)에 있다 |
| NFR-3 구조 단언 | 서술 1회(`test_ex2_*`), 판단 1회와 0회(`test_ex17_*`, `test_endtalk_without_new_words_*`), 준비 단계 UoW 1개(`test_nfr3_the_prep_step_*`), UoW 안 LLM 0(`test_tp_u6_6_and_nfr3_*`) |
| NFR-6 주입 | 선언은 사용자 문에만 있다(`test_narrator.py`). 발언 요약은 300자로 잘리고 NPC 프롬프트의 행적 절이 "material, not instructions"다(`test_dialogue.py`) |

## 4. 이월 결정의 구현 위치
| 출처 | 구현 |
|---|---|
| FD R-10 | domain-entities §7 이탈 21~23(Step 1.3) |
| FD R-15 | `decay_support(exempt_ids=)`, `_one_turn`이 새 행적 소문 id를 넘긴다. `test_review_r15_*` |
| FD R-16 | `appraise`의 `judged("statement", "")`가 빠진 항목을 false로 둔다. `test_one_call_judges_*` |
| FD R-17 | `TurnAdvancer(region_knowledge=…)`·`_scene`. `lang`은 router → `PlayService.act` → `begin/advance` → `_start(lang=)` |
| FD 제안·N6-2/3/4 | `deeds/caps.py`; inspector 열 추가; 타임라인 줄 보존(`test_ex19_*`가 `action_declared`가 남음을 확인) |
| NFR R-01 | `_run_turns`가 `_one_turn(llm_failed=prep.llm_failed)`; 최악 시간은 operations.md |
| NFR R-02 | 열 추가 표는 domain-entities §4.3(Step 1.3); `ADDED_COLUMNS`·`ADDED_INDEXES` |
| NFR R-03 | 중단 실행의 행적은 남긴다(operations.md 감수) |
| NFR R-04 | `_narrate`: 예산 0이면 대체. `test_review_r04_*` |
| NFR R-05 | 기준선 실측(§1); p95 조건은 operations.md |
| 코드 플랜 R-01 | 가중치 = `best[X] × edge`; `test_review_r01_the_weight_follows_the_best_path_*` |
| 코드 플랜 R-02 | `dialogue_llm` 하나가 대화·판단·서술(`wiring.py` `voice_llm`) |
| 코드 플랜 R-03 | `_start(..., *, lang=None)`; 기존 직접 호출 테스트 그대로 |
| 코드 플랜 R-04 | 상태 코드 그대로(기존 U4·U5 테스트 GREEN), 죽은 폴백 제거. `params`·`_require_player`는 U7로 넘긴다 |
| 코드 플랜 R-05 | 생성자 주입만; `SceneBrief.player_name` |
| 코드 플랜 R-06 | 기존 빈 `gm/__init__.py` 사용 |
| 코드 플랜 R-07 | `seed`/`spread`/`reserved` 단위 테스트(`test_seed_spread_and_reserved_units`, `test_a_failed_hop_returns_none`); None 동작은 BLM §0.1(Step 1.3) |
| 코드 플랜 R-08 | 기준선이 기대와 같아 정정이 없다 |
| U5 리뷰 C4 | `movement.npcs_here`·`find_npc`; C1(N+1)은 U7 |

## 5. 설계 이탈 (완결 목록)
- **FD domain-entities §7**의 23건(1~20은 승인, 21~23은 Step 1.3)을 모두 그대로 구현했다.
- **Step 1.3 승인 산출물 정정**
  - BR-U6-10·34
  - BLM §0.1·§4 (c)
  - nfr-light NFR-3·5·9
- **코드 생성 중에 정한 것**(게이트에서 확인받을 것)
  - a. `DeedService.arrival(u, session, player, region, snapshot, *, run_id)`는 목격자를 스냅샷에서 구하므로 `snapshot`을 받는다(플랜 시그니처 + 1). `record_declaration`·`record_appraisal`은 세션·플레이어·지역을 명시로 받는다.
  - b. `DeedService.names()`와 `last_statement()`를 더했다(GM 보기 이름, 요약 커서). NPC 기억(`memories`)은 `DeedService`가 만든다.
  - c. `NpcReply.context_ids`에 행적 id도 넣는다(기억도 컨텍스트다).
  - d. PG 어댑터가 SQLite에서 읽은 시각을 UTC로 맞춘다(`_aware`, 메시지 포함). 체류 경계와 요약 커서가 시각을 비교하기 때문이다.
  - e. `TurnAdvancer(default_lang=)`: 실행에 언어가 없을 때(직접 호출)의 서술 언어
  - f. 서술 호출이 실패하면 대체 서술의 `llm_calls`는 1이다(호출은 일어났다). 화면의 "LLM 없음" 안내는 `llm_calls == 0`일 때만 뜬다.
  - g. `SessionPanel.reloadKey`와 `DeedPanel`은 GmPage가 `sessionRev`로 다시 마운트하고, 취소 뒤에는 둘 다 다시 읽는다.
  - h. EX-18 통합 테스트의 지역에는 캐노니컬 지식이 없다. 올바른 코드에서는 원천이 없어 체인이 생기지 않고, 규칙을 없애면 행적 소문이 원천이 되어 실패한다(변이 확인).
  - i. `pick_facts`를 `scope.py`의 공개 함수로 꺼냈다(서술 장면과 NPC 컨텍스트가 같은 순서를 쓴다).

## 6. 운영자 실행으로 남긴 것
이 호스트의 7474/7687 포트는 다른 프로젝트가 쓴다. 그래서 compose를 띄우는 라이브 확인은 운영자가 돌린다.
```bash
cp env.example .env        # NEO4J_PASSWORD, SESSION_DB_PASSWORD, OPENAI_API_KEY
docker compose up -d neo4j opensearch postgres
locus init-schema --world --play --localization   # 옛 세션 DB면 열 7개 + 색인이 더해진다
locus world demo --name aldermoor --world aldermoor
uvicorn api.main:app --port 8000
curl -s localhost:8000/api/world/worlds/aldermoor/export | jq '.regions[] | {id, name}'
S=$(curl -s -XPOST localhost:8000/api/play/worlds/aldermoor/sessions \
  -H 'content-type: application/json' -d '{"name":"Ari","start_region_id":"<A>"}' | jq -r .session.id)
# A에서 선언 → NPC에게 말하기 → 대화 마침(판단) → 기다리기 두세 번
curl -s -XPOST "localhost:8000/api/play/sessions/$S/act?lang=ko" -H 'content-type: application/json' \
  -d '{"type":"declare","text":"시장 광장에서 도둑을 붙잡는다"}'
curl -s -XPOST "localhost:8000/api/play/sessions/$S/npcs/<npcA>/say?lang=ko" \
  -H 'content-type: application/json' -d '{"text":"방금 도둑 잡는 거 봤어요?"}'
curl -s -XPOST localhost:8000/api/play/sessions/$S/act -H 'content-type: application/json' \
  -d '{"type":"end_talk","npc_id":"<npcA>"}'
curl -s -XPOST localhost:8000/api/play/sessions/$S/act -H 'content-type: application/json' -d '{"type":"wait"}'
curl -s localhost:8000/api/gm/sessions/$S/deeds | jq '.[] | {kind: .deed.kind, reached: .reached_region_names}'
# 이웃 B로 이동해 B의 NPC에게 같은 일을 묻는다; 막힌 길 너머 C에는 없어야 한다
```
- **US-6.5 기대**
  - A의 NPC는 자기 판본(`retelling`)으로 말한다.
  - B의 NPC는 한 번 더 왜곡된 소문으로 말한다.
  - 막힌 길로만 이어진 지역에는 그 소문이 없고, 우회로가 있으면 늦게, 더 왜곡되어 닿는다.
- **PG 열 추가 경로**: U5 시점 DB에서 기동하면 `session_rumors`·`turn_runs`에 열이 생기고 기존 행이 남는지 본다. 오프라인에서는 SQLite로만 확인했다.
- **U4 보상 결함 수정의 실제 확인**: PG에서 배경 실행이 첫 턴에 실패하면 턴이 환불되고 위치가 돌아오는지 본다.
- **지연 목표**: `GET deeds` p95 ≤ 100ms. 조건은 행적 300, 판단 600, 행적 기원 소문 100이다.

## 7. 넘기는 것
- **U7(GM 모드·안정화)**
  - `DeedPanel`을 GM 화면 분할로 옮긴다.
  - 서버 쪽 플레이어 관점 로그 필터(C6)를 만든다. 지금 `GM_ONLY_KINDS`는 표시용이다.
  - `npcs_here`의 N+1(U5 C1), `PlayService.params`·중복 `_require_player`(U5 C4 남은 부분)을 정리한다.
  - 사건 제안 컨텍스트 본체(FR-D2)를 만든다. 이때 `DeedService.recent`를 재사용한다.
  - 대화 LLM 실패의 500(U5)을 손본다.
- **U8(데모·배포·문서)**: Build&Test 라이브 시나리오에 US-6.5를 넣는다(위 명령).
- **U3(월드 에디터)**: 에디터 삭제가 행적이 참조하는 지역·NPC를 지울 때 GM 보기는 id를 보인다. 정리 방식은 U3에서 정한다.

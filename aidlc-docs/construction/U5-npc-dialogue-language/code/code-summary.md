# U5 NPC 대화·언어 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**이 유닛이 한 것**: 플레이어가 지역 NPC에게 말을 걸면, NPC는 자기 지역이 아는 것과 그 지역에 도는 소문만으로 답한다. 먼 곳의 일은 그 지역 소문대로 틀리게 말한다(US-4.1~4.3, **US-6.1 완성**). 화면 라벨은 ko·en 두 사전으로 옮겼다. 번역이 붙는 읽기는 요청마다 표시 언어를 받는다. 소문 재생성과 월드 교체 때에는 낡은 번역을 지운다(US-9.1~9.4).

근거: 플랜 `construction/plans/U5-npc-dialogue-language-code-generation-plan.md`(승인 2026-09-30T12:41:51Z, 8단계). FD `functional-design/*`(승인 12:11:36Z). NFR `nfr/nfr-light.md`(승인 12:19:54Z).

## 1. 기준선과 결과
| 검사 | 기준선 (Step 1.1) | 결과 (Step 8.1) |
|---|---|---|
| `pytest -q --no-cov` | 475 passed | **545 passed** (+70, 회귀 0) |
| `npx vitest run` | 39 passed | **56 passed** (+17) |
| `mypy locus api` | 11 errors | **11 errors** (늘지 않음. 새 모듈은 오류 0) |
| `ruff check locus api tests` / `black --check locus api tests` | clean | clean |
| `tests/test_boundaries.py` | 4 passed | 4 passed (play는 localization을 import하지 않는다) |
| `tsc --noEmit` / `vite build` | clean | clean |
| `docker build` | OK | OK (`locus-u5-check`). 이미지 안 OpenAPI에서 대화 라우트 4개가 보이고, `lang`을 받는 라우트는 정확히 6개다(읽기 5 + `say`, 타임라인 제외) |

- 저장소 전체에 `ruff check .`을 돌리면 2건이 나오고, `black --check .`는 1건을 잡는다. 셋 다 `examples/demo_world/generate_map.py`에 있다. 이 파일은 U5보다 앞선 인프라 커밋(`ce8fd98`) 때부터 있었고 U5는 건드리지 않았다. U4까지의 게이트도 코드 경로만 검사했다.
- pytest 경고 1건은 FastAPI 테스트 클라이언트의 `httpx` 폐기 예고이고, 기준선에도 있었다.

## 2. 바뀐 파일 (77개, +3.9k / −0.25k)
**백엔드: 새 파일**
- `locus/play/npc/scope.py`: 순수 함수로 NPC가 아는 범위를 정한다. `KNOWN_SCOPES`, `pick_rumors`, `shadowed_sources`, `build_context`가 있다.
- `locus/play/npc/prompts.py`: 시스템·사용자 프롬프트와 빈 응답 때의 고정 문구, 소문 어조 태그를 만든다.
- `locus/play/npc/dialogue.py`: `NpcDialogueService`에 `npcs_here`·`start`·`say`·`history`가 있다. `say`는 LLM을 한 번 부르고 트랜잭션을 하나 연다. 첫 대화가 겹치면 UoW 밖에서 복구한다.

**백엔드: 바뀐 파일**
- `locus/play/models.py`, `errors.py`, `ports.py`, `storage/{schema,memory_repo,postgres_repo}.py`: 대화 모델, `ConversationStore` 포트, 테이블 `conversations`·`messages`와 두 어댑터를 넣었다.
- `locus/play/region_knowledge.py`: `RegionSources`와 `region_sources`를 더했다. 지역마다 합의를 한 번만 계산하고, `knowledge_for_region`과 `PlayService.current_region`이 그 결과를 함께 쓴다.
- `locus/play/player/service.py`, `rumor/service.py`(`RegenerateResult`), `turn/advancer.py`(`NPC_TALKED`), `wiring.py`(`dialogue`, `dialogue_llm` 주입점), `__init__.py`를 고쳤다.
- `locus/shared/config/{tuning,settings}.py`: env 5개를 받고, 기동할 때 기본 언어가 지원 집합에 있는지 검사한다.
- `locus/shared/llm/{openai_provider,retry}.py`: `max_retries=0`으로 두어 호출당 상한을 93초로 맞췄다.
- `locus/localization/{ports,service}.py`, `storage/{memory_repo,postgres_repo}.py`: 필터로 고르는 `purge`를 더했다. PG는 500개씩 나눠 지운다.
- `api/deps.py`(`display_lang`), `api/schemas.py`(`SOURCE_LANG`, `lang` 인자, 대화 DTO, `purge_translations`)를 고쳤다.
- `api/routers/{play,gm,knowledge,world}.py`: 새 라우트 4개를 더했고, 읽기 5개가 `lang`을 받는다. 재생성과 월드 교체 뒤에는 번역을 정리한다.

**프론트엔드**
- 새 파일은 `features/play/{LangToggle,NpcList,DialoguePanel}.tsx`와 `__tests__/dialogue.test.tsx`다.
- `i18n.ts`는 ko·en 두 사전과 언어 상태를 가진다. 키 집합이 같다는 조건은 타입(`Record<Key, string>`)과 테스트가 함께 강제한다.
- `api/{http,play,gm,knowledge}.ts`와 `types.ts`를 고쳤다.
- `RegionScene`·`PlayPage`·`AppNav`에 대화 화면을 연결했다.
- 라벨을 사전으로 옮긴 곳은 `Toolbar`·`RegionPanel`·`SessionBar`·`SessionPanel`·`AugmentPanel`·`EditorPage`·`GmPage`·`ui/{Modal,Toast}`다.

**테스트와 문서**
- 새 테스트 파일은 `tests/play/{test_npc_scope,test_dialogue}.py`, `tests/api/test_dialogue_api.py`, `tests/localization/test_purge.py`, `tests/shared/test_config.py`다.
- 넓힌 테스트 파일은 `strategies.py`, `test_models.py`, `test_repository_contract.py`, `test_postgres_repo.py`, `test_world_api.py`다. 호출처가 바뀐 곳은 `test_play_services.py`, `test_player_mode.py`, `helpers.py`, `play_fixtures.py`다.
- 문서는 `env.example`, `aidlc-docs/operations/operations.md`, `CLAUDE.md`를 고쳤다.

## 3. 검증 번호와 테스트
| 번호 | 테스트 |
|---|---|
| TP-U5-1 | 둘로 나눴다. **1a** `test_npc_scope.py::test_tp_u5_1a_…`는 순수 `build_context`의 출력이 알려진 범위에서 가려진 원본을 뺀 것 안에 드는지 본다. **1b** `test_dialogue.py::test_tp_u5_1b_…`는 `region_sources`와 `build_context`를 합친 결과를 `ConsensusEngine`과 저장소로 따로 만든 기준과 비교한다(플랜 검토 R-03) |
| TP-U5-2·3·4 | `test_npc_scope.py`가 한도와 우선순위, 결정성, 다른 지역 문장이 프롬프트에 없는지를 본다 |
| TP-U5-5 | `test_dialogue_api.py`와 `test_dialogue.py::test_nfr_r02_…`가 `say` 한 번에 LLM이 정확히 1회 불리는지 본다 |
| TP-U5-6 | `test_purge.py`가 필터별 삭제, 필터 없음, 정확히 맞는 행만 지우는 PBT를 본다 |
| TP-U5-7 | 생성기를 `tests/play/strategies.py`의 `regional_worlds`·`rumors_from`으로 재사용했다 |
| TP-U5-8 | `test_dialogue_api.py::test_tp_u5_8_…`가 `lang`을 받는 모든 라우트에서 `?lang=fr`이 400이고 번역 행이 생기지 않는지 본다 |
| NFR R-02 | 정상 경로의 `say`가 `complete` 1회, `uow()` 1회, 스냅샷 조회 2회 이하인지 본다. 경합 복구 경로는 `uow()` 2회를 허용한다 |
| NFR R-03 | `test_nfr_r03_the_race_loser_keeps_its_answer` |
| NFR-6 | `test_nfr6_an_injection_line_is_just_a_player_line`(Step 8에서 보충) |
| NFR-9 | `test_nfr9_a_removed_npc_keeps_its_history_but_cannot_talk`(Step 8에서 보충) |
| 화면 | `dialogue.test.tsx`가 열기, 전송, 실패 되돌림, LLM 없음, 대화 끝내기, 키 집합, 토글 뒤 `?lang=en`과 재조회를 본다. 재조회 효과와 되돌림을 각각 일부러 없애 보면 해당 테스트가 실패한다 |

## 4. 이월 결정의 구현 위치
| 출처 | 구현 |
|---|---|
| FD R-04 (1) | `settings.py::_default_lang_is_supported` 검증자. `tests/shared/test_config.py` |
| FD R-04 (2) | `gm.py`의 타임라인 라우트는 `lang`을 받지 않는다. 프론트 `getTimeline`·`getLog`도 붙이지 않는다. `test_the_timeline_takes_no_lang` |
| FD R-12 | `scope.py::build_context`가 소문을 먼저 고르고, 고른 소문의 원본만 가린다. 한도 밖으로 잘린 소문의 원본은 facts에 남는다(`test_npc_scope.py`) |
| FD R-13 | `world.py::_after_replace`가 세션 종료의 조기 반환과 따로 `report.replaced`일 때 정리한다. 여섯 라우트가 다섯 호출 지점을 공유한다(R-13 문구). 열린 세션이 없는 교체 테스트가 있다 |
| NFR R-01 | `openai_provider.py`의 두 `ChatOpenAI(max_retries=0)`. `retry.py` docstring과 operations.md의 93초 |
| NFR R-02 / R-05 | 구조 단언 테스트가 있다. 지연 목표는 운영자 실행이다(아래 §6) |
| NFR R-03 | `dialogue.py::say`가 `ConversationExistsError`를 UoW 밖에서 잡는다. 그 뒤 재조회하고, append만 하는 두 번째 UoW를 연다 |
| NFR R-04 | operations.md의 "Accepted risks"에 주입이 그 대화 안에서 이어질 수 있다는 점과 빈도 제한이 없다는 점을 적었다 |
| NFR R-06 | `PlayService.__init__`에 필수 위치 인자 `region_knowledge`를 두었다. 생성처 둘을 같은 단계에서 고쳤다 |
| 코드 플랜 R-13~R-16 | R-13 여섯 라우트 / 다섯 호출 지점. R-14 `SUPPORTED_LANGS`는 쉼표 문자열 필드이고 property에서 나눈다. R-15는 아래 §6. R-16 `assemble_play`의 지역 변수 `region_knowledge` |

## 5. 설계 이탈 (완결 목록)
**FD domain-entities §7의 10건**(승인 때 받았다. 모두 그대로 구현했다)
1. 전언을 NPC 컨텍스트에서 뺐다.
2. `RegenerateResult`를 쓴다.
3. `start`·`history`는 LLM이 필요 없고, `say`만 503이다.
4. 필터로 고르는 `purge`를 쓴다.
5. 합의 해석을 `region_sources` 하나로 모았다.
6. `ConversationStore`의 메서드 이름을 바꿨다.
7. `messages`에 `lang`을 더했다.
8. `build_context`에 hearsay가 없다.
9. `NpcDialogueService`의 시그니처를 바꿨다.
10. `i18n.ts` 한 파일을 넓혔다.

**이 플랜이 확정한 값**
- 컨텍스트 한도는 facts 12, rumors 8, 메시지 10, 메시지당 500자다.
- `SUPPORTED_LANGS`의 기본값은 `ko,en`이다.
- 호출당 상한은 93초다.
- 소문 어조가 `uncertain rumor`로 바뀌는 왜곡도 기준은 0.5다.

**Step 1.3 승인 산출물 정정**(각 곳에 "〔Step 1.3 정정〕" 표시)
- BLM §1, BR-U5-11, TP-U5-1의 순서를 고쳤다.
- BLM §2.2는 `ScopeLimits.from_tuning`과 93초로 고쳤다.
- BLM §7의 타임라인 행에서 `lang`을 뺐다.
- NFR-3의 구조 단언과 NFR-5·8의 93초를 고쳤다.

**코드 생성 중에 정한 것**(게이트에서 확인받을 것)
- a. **ko 타임라인 문구**: `timeline.npc_talked`의 ko는 "대화: {npc_name} · {region_name}"이다. 설계 문구 "{npc_name}와 대화"는 받침으로 끝나는 이름(예: Tom)에서 조사가 틀린다. en은 설계대로 "spoke with …"다.
- b. **라벨 범위**: 영어 라벨만이 아니라 하드코딩된 한국어 라벨도 사전으로 옮겼다. 그래야 en 토글이 화면 전체에 먹는다. 편집기 교체 확인, GM 재시도, 네비게이션이 그런 곳이다. 열거형 코드는 코드로 남겼다. scope type, 사건 status·category·lifecycle, 세션 status, level이 여기에 든다. 전언과 소문 배지는 `badge.*` 키로 번역한다.
- c. **`NpcList` props**: FD §2.4는 `disabled` prop을 적었지만 같은 절이 "버튼은 눌린다"고도 적는다. 그래서 prop을 두지 않았다. 입력 잠금은 `DialoguePanel`이 한다.
- d. **대화 표시**: NPC 카드의 대화 표시와 메시지 수는 `GET .../npcs`에서 가져온다. 이 조회가 실패해도 지역 화면은 깨지지 않는다(best effort). `dialogueHistory` API 함수는 있지만 화면은 `start`가 돌려주는 이력을 쓴다.
- e. **빈 지역 안내**: `RegionPanel`은 항목이 없을 때 `region.empty` 안내를 보인다.
- f. **LLM 호출 실패**: 재시도 뒤에도 LLM 호출이 예외로 끝나면 **500**이다. BR-U5-30은 "오류를 올린다"고만 하고 상태를 정하지 않는다. 저장은 되지 않고, 화면은 발화를 되돌린 뒤 오류를 보인다. operations.md에 적었다. 502나 503으로 바꿀지는 U7 안정화에서 고를 수 있다.

## 6. 운영자 실행으로 남긴 것
이 호스트의 7474/7687 포트는 다른 프로젝트의 `sigraph-neo4j-1`이 쓰고 있다. 그래서 compose를 띄우는 라이브 확인은 운영자가 돌린다.
```bash
cp env.example .env        # NEO4J_PASSWORD, SESSION_DB_PASSWORD, OPENAI_API_KEY
docker compose up -d neo4j opensearch postgres
locus init-schema --world --play --localization
locus world demo --name aldermoor --world aldermoor
uvicorn api.main:app --port 8000
# 지역 id 확인
curl -s localhost:8000/api/world/worlds/aldermoor/export | jq '.regions[] | {id, name}'
# A에서 시작하는 플레이 세션
S=$(curl -s -XPOST localhost:8000/api/play/worlds/aldermoor/sessions \
  -H 'content-type: application/json' -d '{"name":"Ari","start_region_id":"<A>"}' | jq -r .session.id)
# GM: A에 사건을 만들고 턴을 돌려 B까지 소문이 번지게 한다
curl -s -XPOST localhost:8000/api/gm/sessions/$S/events -H 'content-type: application/json' \
  -d '{"region_id":"<A>","category":"disaster","description":"The mill burned down","magnitude":0.8}'
curl -s -XPOST localhost:8000/api/gm/sessions/$S/advance
# US-6.1: A의 NPC에게 묻고, B로 이동한 뒤 B의 NPC에게 같은 것을 묻는다
curl -s localhost:8000/api/play/sessions/$S/npcs | jq '.[].npc | {id, name}'
curl -s -XPOST "localhost:8000/api/play/sessions/$S/npcs/<npcA>/say?lang=ko" \
  -H 'content-type: application/json' -d '{"text":"방앗간에 무슨 일이 있었나요?"}'
curl -s -XPOST localhost:8000/api/play/sessions/$S/act -H 'content-type: application/json' \
  -d '{"type":"move","to_region_id":"<B>"}'   # 202 → turn-runs 폴링
curl -s -XPOST "localhost:8000/api/play/sessions/$S/npcs/<npcB>/say?lang=ko" \
  -H 'content-type: application/json' -d '{"text":"방앗간에 무슨 일이 있었나요?"}'
```
- **US-6.1 기대**: A의 NPC는 캐노니컬 사실대로 답한다. B의 NPC는 B에 도는 왜곡된 소문대로 말하거나 모른다고 한다. 두 답의 `context_ids`가 다르다.
- **PostgreSQL 경합 경로(코드 플랜 R-15)**: 같은 NPC의 첫 `say` 두 개를 동시에 보낸다. 그러면 `uq_conversations_session_npc` 위반이 트랜잭션을 중단시키고, 두 번째 UoW가 답을 붙인다. 오프라인에서는 SQLite와 인메모리로만 확인했다. 두 요청이 모두 200이고 대화가 하나이며 메시지가 네 개면 통과다.
- **지연 목표(NFR-3, R-05)**: `start`·`history`·`npcs`의 p95가 100ms 이하인지 로컬 compose에서 잰다. 오프라인 게이트는 구조 단언이다.

## 7. 넘기는 것
- **U6(행적·전파)**: `build_context`에 "자기 판단 행적"을 더할 자리가 있다. `EndTalk`의 `NPC_TALKED` 자리에 대화 요약을 행적으로 남기는 일이 U6의 몫이다. `Conversation`·`Message`에는 `turn`과 `lang`이 있다.
- **U7(GM 모드·안정화)**: GM 화면이 `RegionSources`를 쓸 수 있다. LLM 실패 상태 코드(§5 f), `say` 빈도 제한, 주입 방어 강화가 남아 있다.
- **U3(월드 에디터)**: 에디터 삭제가 지운 id로 번역을 정리하는 자리는 문서화만 했다(BLM §6). 새 화면의 라벨은 `i18n.ts` 두 사전에 키를 함께 더한다.
- **U8(데모·배포·문서)**: CLI 교체는 번역을 정리하지 않는다(알려진 공백, operations.md). 필요하면 전용 CLI 명령을 만든다.

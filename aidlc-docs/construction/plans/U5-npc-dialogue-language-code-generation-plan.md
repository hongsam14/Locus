# U5 NPC 대화·언어 — Code Generation Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U5 — 플레이어가 지역 NPC에게 묻고 NPC는 자기 지역에서 알 수 있는 것만 답하게 만든다. 먼 곳 일은 그 지역 소문대로 틀리게 말한다. 화면은 한국어, 저장 텍스트는 영어이며 NPC는 표시 언어로 직접 말한다. US-6.1이 이 유닛에서 완성된다.

> 근거: `construction/U5-npc-dialogue-language/functional-design/*`(승인 2026-09-30T12:11Z; 검토 02의 R-04·R-12·R-13은 Accepted risk), `construction/U5-npc-dialogue-language/nfr/nfr-light.md`(승인 2026-09-30T12:19Z; 검토 01의 R-01~R-06은 Accepted risk). 두 게이트의 이월 결정은 아래 표가 단일 기준이다. 이 플랜이 코드 생성의 단일 기준이다.

---

## 유닛 컨텍스트

- **스토리**: US-4.1(지역 NPC와 대화), US-4.2(자기 지역에서 알 수 있는 것만 안다), US-4.3(소문은 왜곡된 대로), US-6.1(**완성**: 같은 사건을 다른 지역에서 다르게 듣는다), US-9.1~9.4(화면은 한국어·저장은 영어, NPC는 표시 언어로, 번역은 어느 경계에서도, UI 라벨 통일), US-1.4(키 없이 둘러보기: 대화 부분).
- **의존**: U2(스냅샷·캐시), U4(플레이어·턴·가드·UoW·`EndTalk`·`RegionView`·`LlmUnavailableError`·`next_timestamp`). 뒤 유닛이 기대하는 것: `NpcScope.build_context`(U6가 "자기 판단 행적"을 더한다), `NpcDialogueService`(U6 `appraise`), `Conversation`/`Message`(U6 행적 요약), `RegionSources`(U7 GM 화면), `display_lang`·`en` 사전(U3·U7 새 화면).
- **DB 엔티티(PostgreSQL, 추가만)**: `conversations`(`UNIQUE (session_id, npc_id)`), `messages`. `init-schema --play`/기동 시 `ensure_play_schema`가 만든다.
- **바뀌는 외부 계약**: (1) 새 라우트 4개(`npcs`, `npcs/{n}/start`, `npcs/{n}/say`, `npcs/{n}/history`). (2) 읽기 라우트 5개에 선택 `?lang=` 추가(기존 호출은 기본값으로 동작, 응답 형태 불변). (3) `GET /api/gm/sessions/{s}/timeline`은 `lang`을 받지 **않는다**(번역 필드가 없다 — 이월 FD R-04(2)). (4) `RumorService.regenerate_region` 반환형 `list[SessionRumor]` → `RegenerateResult`(응답 형태는 불변: 라우터가 `result.rumors`를 돌려준다). (5) `PlayService.__init__`에 `region_knowledge` 필수 위치 인자 추가.
- **바꾸지 않는 것**: 합의 계산 값, 소문·사건·턴 규칙, `QueryResult` 형태(FR-F5), GM 라우트 응답 형태, U4 플레이 화면의 동작(내부 계산만 공유로 바뀐다), 임베딩·검색 텍스트는 영어 유지(C-1).

## 이월 결정 (두 게이트에서 확정 — 이 플랜에서 닫는다)
| 출처 | 결정 | 단계 |
|---|---|---|
| FD R-04 (1) | 기동 시 `translation_target_lang ∈ supported_langs`를 검증한다. 어긋나면 `Settings` 검증 오류로 기동을 막는다 | 2.2 |
| FD R-04 (2) | `GET /api/gm/sessions/{s}/timeline`에서 `lang`을 빼고 승인된 설계 §7 표의 그 행도 지운다 | 1.3, 6.2 |
| FD R-12 | `build_context`는 **소문을 먼저 고른 뒤** 선택된 소문에서만 `shadowed`를 계산한다. 승인된 BLM §1·BR-U5-11·TP-U5-1의 문구도 그 순서로 고친다 | 1.3, 3.1, 3.4 |
| FD R-13 | 번역 정리는 세션 종료의 조기 반환과 **독립**이다. `_close_if_replaced` → `_after_replace(report, open_ids, play, loc, world_id)`; 정리 조건은 `report.replaced`만 | 6.3 |
| NFR R-01 | 두 provider에 `max_retries=0`을 지정한다. 그러면 `with_retry` 층의 상한은 **93초**(30×3 + 대기 1+2)다. 승인된 설계·NFR 노트·operations.md의 "≈97초"를 93초로 맞춘다 | 1.3, 2.3, 7.4 |
| NFR R-02 | 구조 단언: `LLM.complete` 정확히 1회, **정상 경로에서** `repo.uow()` 진입 정확히 1회(경합 복구 시 2회), `SnapshotSource.get` 2회 이하, 그래프·검색 저장소 직접 호출 0회 | 5.4 |
| NFR R-03 | 같은 NPC의 첫 `say`가 겹치면 `ConversationExistsError`를 **UoW 밖에서** 잡아 재조회한 뒤 append만 하는 두 번째 UoW를 연다 | 4.1, 4.6 |
| NFR R-04 | 프롬프트 주입 서술에 "오염은 그 대화의 이후 턴으로 이어질 수 있음"과 "요청 빈도 제한 없음(감수)"을 적는다 | 7.4 |
| NFR R-05 | 지연 목표는 운영자 실행으로 남기고 오프라인 게이트는 구조 단언이다 | 5.4, 7.4 |
| NFR R-06 | `PlayService.__init__(repo, snapshots, region_knowledge, params=…, *, guard, turns, tuning)` — `region_knowledge`는 필수 위치 인자. 생성처는 `locus/play/wiring.py:96`과 `tests/play/test_player_mode.py:641`(`_services`, 636행부터) 둘뿐이고 **같은 단계에서** 함께 고친다 | 4.4 |

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. 복사본·`_v2` 없음.
- 각 단계는 **그 단계의 테스트가 GREEN인 상태로** 끝낸다. 시그니처를 바꾸는 하위 단계는 그 호출처 전부를 같은 하위 단계에서 고친다(4.4, 4.5). 어쩔 수 없이 두 하위 단계에 걸치는 곳은 "이 구간은 붉다"를 명시한다(4.2).
- 규칙 번호(BR-U5-n)·검증 번호(TP-U5-n, EX-n)를 테스트 이름이나 docstring에 적는다.
- 새 외부 의존 없음.
- 각 단계 완료 즉시 체크박스를 [x]로 바꾼다.

---

## Steps

### Step 1 — 베이스라인·뼈대·승인 산출물 정정
- [x] 1.1 `./.venv/bin/python -m pytest -q --no-cov`(기대 475) / `cd web && npx vitest run`(39) / `mypy locus api`(11) 실측을 `construction/U5-npc-dialogue-language/code/code-summary.md` 초안에 기준선으로 기록.
- [x] 1.2 새 파일(전부 신규, 빈 docstring): `locus/play/npc/{scope,dialogue,prompts}.py`, `tests/play/test_npc_scope.py`, `tests/play/test_dialogue.py`, `tests/shared/test_config.py`(**신규** — 지금 설정 전용 테스트가 없다), `tests/api/test_dialogue_api.py`, `tests/localization/test_purge.py`, `web/src/features/play/{NpcList,DialoguePanel,LangToggle}.tsx`, `web/src/__tests__/dialogue.test.tsx`.
- [x] 1.3 **승인 산출물 정정**(게이트가 받은 disposition을 문서에 반영; audit에 한 줄 남긴다): (a) FD `business-logic-model.md` §1 `build_context` 의사코드와 `business-rules.md` BR-U5-11·TP-U5-1을 "소문 선택 → `shadowed` 계산" 순서로, (b) FD §7 표에서 `GET .../timeline`의 `lang` 행 삭제, (c) FD §2.2와 `nfr/nfr-light.md`의 "≈97초"를 "93초(`max_retries=0` 전제)"로, (d) `nfr-light.md` NFR-3 구조 단언을 이월 NFR R-02 문구로, (e) FD §2.2의 `tuning.scope_limits()`를 `ScopeLimits.from_tuning(tuning)`으로(그 메서드를 `PlayTuning`에 두면 shared가 play의 `ScopeLimits`를 import해 경계 규칙이 깨진다). 정정 뒤 두 산출물의 나머지는 손대지 않는다.

### Step 2 — 모델·조정값·설정 (domain-entities §1~2)
- [x] 2.1 `locus/play/models.py`: `Conversation`, `Message`(role `Literal["player","npc"]`, text 1~`npc_max_message_chars`, lang, turn), `NpcContext`, `ScopeLimits`, `NpcReply`, `RegenerateResult`(+`rumors` property), `TimelineKind += NPC_TALKED`. `locus/play/errors.py`: `ConversationExistsError(ValueError)`(이월 NFR R-03 — 무관한 `ValueError`를 삼키지 않기 위한 전용 타입).
- [x] 2.2 `locus/shared/config/tuning.py::PlayTuning += npc_max_facts=12, npc_max_rumors=8, npc_max_recent_messages=10 (ge=0), npc_max_message_chars=500 (ge=1)` + `scope_limits() -> ScopeLimits`는 두지 않는다(`PlayTuning`은 경계를 모르는 값 전용이므로 `ScopeLimits`는 `npc/scope.py`가 `PlayTuning`에서 만든다). `settings.py`: env 4개 alias + `supported_langs: tuple[str, ...]`(env `SUPPORTED_LANGS`, 쉼표 구분, 비면 `("ko","en")`) + `play_tuning()` 전달 + **모델 검증자**로 `translation_target_lang ∈ supported_langs`(이월 FD R-04(1)).
- [x] 2.3 `locus/shared/llm/openai_provider.py`: 두 `ChatOpenAI(...)`(LLM·VLM)에 `max_retries=0`. **주의: 이 변경은 U5 대화뿐 아니라 모든 LLM·VLM 호출의 재시도 성질을 바꾼다** — SDK 재시도가 사라지고 재시도는 `with_retry` 한 층으로 통일된다(3회, 대기 1+2초). `retry.py` docstring에 "호출당 상한 93초(30×3 + 1 + 2). SDK timeout은 연결·읽기 단계별이라 엄격한 상한은 아니다"를 적는다.
- [x] 2.4 테스트: `tests/play/test_models.py`에 새 모델 왕복(`Message.role` 판별, 길이·범위), `RegenerateResult.rumors`; `tests/shared/test_config.py`(신규)에 env 5개 로딩, 기본 언어 정합 검증 실패, **두 provider의 `max_retries == 0`**(생성자 인자를 가로채는 가짜로 확인).

### Step 3 — 아는 범위 (순수) (business-logic-model §1)
- [x] 3.1 `locus/play/npc/scope.py`: `ScopeLimits.from_tuning(tuning)`, `build_context(*, npc, facts, rumors, recent, limits) -> NpcContext`. **순서**: 소문 정렬·절단 → 선택된 소문에서 `shadowed` 계산 → facts에서 제외 → facts 정렬·절단 → `recent` 뒤 `limits.recent_messages`개(0이면 빈 목록). `allowed_ids`는 선택 뒤 남은 facts와 선택된 소문의 id.
- [x] 3.2 `locus/play/npc/prompts.py`: `system_prompt(npc, lang)`, `user_prompt(ctx, question, lang)`, `fallback_text(lang)`, `LANG_NAMES`. 소문 태그는 `known`(승격) / `uncertain rumor`(왜곡도 ≥ 0.5) / `rumor`.
- [x] 3.3 `tests/play/strategies.py` 확장: `regional_worlds()`(두 지역, 지역 전용 문장 표지, 전언을 만드는 약한 연결), `rumors_from(knowledge_ids)`.
- [x] 3.4 테스트 `tests/play/test_npc_scope.py`: TP-U5-1(독립 기준 — `ConsensusEngine`으로 직접 계산 + 저장소 소문에서 기준식을 만들고 **같은 선택 순서**를 쓴다), TP-U5-2(한도·순서, 한도 0), TP-U5-3(결정성), TP-U5-4(프롬프트 문자열에 다른 지역 문장·소문 원본·전언 없음), EX-5, EX-7, 그리고 소문이 한도를 넘는 경우 잘려 나간 소문의 원본이 facts에 **남는다**(이월 FD R-12).

### Step 4 — 저장·서비스
- [x] 4.1 `locus/play/ports.py`: `ConversationStore`(`create_conversation`(중복이면 `ConversationExistsError`)/`get_conversation`/`append_message`/`list_conversations`), `PlayUnitOfWork += conversations`, `PlayRepository += ConversationStore`. `locus/play/storage/schema.py`: `conversations`·`messages` 테이블.
- [x] 4.2 어댑터 둘(포트 추가와 어댑터 구현 **사이 구간은 붉다** — `PlayRepository` 프로토콜 검사 테스트가 4.2 끝에 다시 GREEN): `_PgStores`에 네 메서드(메시지 시각 `next_timestamp()`, 조회 `ORDER BY created_at, id`, 대화는 세션 범위) + `PostgresPlayRepository`에 네 위임 메서드 + `_PgUnitOfWork.conversations` 프로퍼티; `InMemoryPlayRepository`에 네 메서드(`@_synchronized`) + `_STATE`에 `_conversations`·`_messages` 추가(롤백이 대화를 되돌리도록) + `_MemoryUnitOfWork.conversations` 프로퍼티.
- [x] 4.3 테스트: `tests/play/test_repository_contract.py`·`test_postgres_repo.py` 확장 — 중복 생성 시 `ConversationExistsError`, 메시지 순서와 시각 단조, 세션 범위 조회, **UoW 롤백이 대화·메시지를 되돌린다**.
- [x] 4.4 `locus/play/region_knowledge.py`: `RegionSources` DTO + `region_sources(session_id, region_id)`(없는 지역은 `LookupError("region not found: …")`); `knowledge_for_region`이 그것으로 지금과 같은 `QueryResult`를 만든다. `locus/play/player/service.py`: 생성자에 `region_knowledge` 필수 위치 인자, `current_region`은 **플레이어 지역 존재 확인을 먼저** 해서 기존 문구(`player region no longer exists`)를 유지하고(이월 NFR R-05 / `test_player_mode.py:736`) 그 뒤 `region_sources`를 쓴다. **같은 하위 단계에서** 생성처 둘을 고친다: `locus/play/wiring.py:96`(인자 순서 주의 — `params`는 네 번째가 된다), `tests/play/test_player_mode.py:641`(`_services`에 `SessionKnowledgeService` 추가).
- [x] 4.5 `locus/play/rumor/service.py`: `regenerate_region` 반환형 → `RegenerateResult`. **같은 하위 단계에서** 호출처 6곳: `api/routers/gm.py:135`(→ `result.rumors`), `tests/play/test_play_services.py` 84·100·181·203, `tests/play/test_player_mode.py:935`.
- [x] 4.6 `locus/play/npc/dialogue.py`: `NpcDialogueService(repo, snapshots, region_knowledge, llm, tuning, *, default_lang, supported_langs)`; `start`/`say`/`history`는 business-logic-model §2 그대로. `say`의 경합 복구(이월 NFR R-03): 저장 UoW에서 `ConversationExistsError`가 나면 **UoW 밖에서** 잡고 `get_conversation`으로 재조회한 뒤 append만 하는 두 번째 UoW를 연다(PostgreSQL은 제약 위반이 트랜잭션을 중단시키고 인메모리 UoW는 예외 시 상태를 복원하므로 같은 UoW 안에서는 복구할 수 없다).
- [x] 4.7 `locus/play/turn/advancer.py`: `EndTalk` 분기에 `NPC_TALKED` 타임라인(business-logic-model §5 그대로; 대화는 UoW의 `conversations`로 읽으므로 새 의존은 없다).
- [x] 4.8 `locus/play/wiring.py`: `PlayContainer += dialogue: NpcDialogueService`; `assemble_play(..., dialogue_llm: LLMProvider | None = None)`를 더해 **대화용 LLM 주입 지점**을 만든다(기본은 `shared.llm`). `region_knowledge`를 먼저 만들어 `play`와 `dialogue`에 넘기고, `default_lang=shared.settings.translation_target_lang`·`supported_langs=shared.settings.supported_langs`를 전달. `locus/play/__init__.py` 공개 이름 추가. 테스트 조립도 같은 단계에서: `tests/play/helpers.py::compose_play(..., dialogue_llm=None)`, `tests/api/play_fixtures.py::play_container(..., dialogue_llm=RumorLLM())`(그 가짜에 이미 `complete`가 있다) — 이것이 없으면 `say` 200 테스트와 TP-U5-5를 조립할 수 없다.
- [x] 4.9 테스트 `tests/play/test_dialogue.py`: EX-1~3, EX-6, EX-10~12, TP-U5-5(호출 1회), 동시 첫 `say` 재조회(두 번째 UoW로 append, 답을 잃지 않는다), `EndTalk` → `NPC_TALKED`(`messages` 수·`region_name`).

### Step 5 — 번역 정리·언어
- [x] 5.1 `locus/localization/ports.py`·`storage/{postgres_repo,memory_repo}.py`: `purge(*, kind=None, ids=None, world_id=None, session_id=None) -> int`(필터 없으면 `ValueError`). `service.py`: 같은 시그니처로 감싸고 in-flight 키 정리.
- [x] 5.2 `api/deps.py`: `display_lang(lang: str | None = None, shared=Depends(get_shared)) -> str`(지원 집합 밖 400).
- [x] 5.3 `api/schemas.py`: `SOURCE_LANG = "en"`; `enrichment_for(..., lang: str | None = None)`는 **요청 언어가 원문 언어와 같으면 곧바로 `{}`를 돌려준다**(BR-U5-19; 그래야 en→en 워밍이 생기지 않는다 — 이월 검토 R-09). `localize_query_result(..., lang=None)`, `localize_region_view(..., lang=None)`. `lang=None`은 "서버 기본값"을 뜻하고 쓰기 경로(`_rumors_out(enrich=False)` 등)는 지금처럼 번역을 부르지 않으므로 영향이 없다.
- [x] 5.4 테스트 `tests/localization/test_purge.py`: TP-U5-6(필터별·필터 없음), in-flight 정리, 없는 원본; `enrich`가 `lang="en"`에 호출되지 않음. `tests/play/test_dialogue.py`에 구조 단언(이월 NFR R-02): 정상 `say` 한 번에 `complete` 1회 · `uow()` 1회 · `SnapshotSource.get` ≤ 2 · 그래프·검색 호출 0(경합 복구 경로는 `uow()` 2회를 허용).

### Step 6 — API
- [x] 6.1 `api/routers/play.py`: 새 라우트 4개(`GET npcs`, `POST npcs/{n}/start`, `POST npcs/{n}/say`, `GET npcs/{n}/history`). `api/schemas.py`에 `ConversationOut`·`NpcReplyOut`·`NpcSummaryOut`·`SayIn(text)`. `say`는 `lang: str = Depends(display_lang)`.
- [x] 6.2 읽기 라우트 5개에 `lang` 추가: `play.py`의 `GET .../region`·`GET .../regions/{r}/knowledge`, `knowledge.py`의 `GET /worlds/{w}/regions/{r}`, `gm.py`의 `GET .../regions/{r}/rumors`·`GET .../events`. **`gm.py`의 `GET .../timeline`에는 넣지 않는다**(이월 FD R-04(2)). `_rumors_out`·`_events_out`에 `lang: str | None = None`을 더해 흘린다(쓰기 라우트는 `enrich=False`라 그대로 `None`).
- [x] 6.3 `api/routers/world.py`: `_close_if_replaced`(92행) → `_after_replace(report, open_ids, play, loc, world_id)`. 세션 종료는 지금 조건 그대로, 정리는 `report.replaced`만 보고 **따로** 돈다. 호출처는 **5곳**(147·189·291·354·381)이고 그중 291은 `/file`과 `/file/upload`가 공유하는 `_import` 헬퍼(271행) 안이다 → `_import`에 `loc` 매개변수를 더하고 그 **두 호출자**도 함께 고친다. 라우트 다섯 개(`build`, `build/upload`, `file`, `file/upload`, `demo/{name}`, `demo/{name}/build` — 여섯 라우트가 다섯 호출처를 공유)에 `loc: LocalizationContainer | None = Depends(get_localization)` 주입.
- [x] 6.4 `api/routers/gm.py`: `regenerate_region`이 `result.rumors`를 돌려주고 `result.deleted_ids`가 비어 있지 않을 때만 `purge(kind="rumor", ids=…)`를 부른다.
- [x] 6.5 테스트 `tests/api/test_dialogue_api.py`: EX-1·3·4·6~12, `?lang=fr` 400(lang을 받는 라우트 전부), `lang=en` → `*_ko` null이고 번역 호출 0, LLM 없는 컨테이너에서 `start` 200·`say` 503, 진행 중 턴에도 `say` 200. `tests/api/test_world_api.py`에 "열린 세션 없는 교체에서도 정리가 돈다"(이월 FD R-13). 기존 `test_play_gm_api.py`·`test_localization_api.py`·`test_knowledge_api.py`는 변경 없이 GREEN.

### Step 7 — 프론트엔드·문서
- [x] 7.1 `web/src/i18n.ts`: `Lang`·`dicts.ko/en`·`lang()`·`setLang()`·`useLang()`; 남은 영어 라벨을 키로 옮기고(`toolbar.*`·`region.*`·`session.*`·`augment.*`·`editor.*`·`nav.*`) `en`을 채운다. `timeline.npc_talked` 두 언어. `web/src/api/http.ts`에 `withLang`(**타임라인 조회는 제외** — 백엔드가 `lang`을 받지 않는다). `api/play.ts`·`gm.ts`·`knowledge.ts`에 `?lang=`·새 함수 4개. `types.ts`에 `Conversation`·`Message`·`NpcReply`·`Lang`.
- [x] 7.2 `features/play/{LangToggle,NpcList,DialoguePanel}.tsx` + `RegionScene`에서 NPC 카드 분리 + "들은 이야기" 안내 한 줄 + `PlayPage` 연결(`activeNpcId`, 언어 변경 시 재조회). `AppNav`에 토글.
- [x] 7.3 테스트 `web/src/__tests__/dialogue.test.tsx`: 대화 열기·전송·실패 되돌림·LLM 없음·대화 끝내기; `ko`/`en` 키 집합 동일; 토글 뒤 `?lang=en`과 재조회. 기존 프론트 테스트는 라벨 단언만 키 기반으로 갱신.
- [x] 7.4 문서: `env.example`(env 5개), `operations.md` — 대화 절 신설(라우트, 호출 1회, **93초**, 컨텍스트 한도, 표시 언어, 정리 시점과 CLI 공백, 주입·빈도 제한 감수: 이월 NFR R-01/R-04/R-05) **그리고 U4 절의 "≈97초"(125·127행)를 93초로 정정**. `CLAUDE.md`(Status·`play/npc/`·테스트 수).

### Step 8 — 검증·요약
- [x] 8.1 전체: `pytest -q --no-cov`(기존 475 + 신규 GREEN, 회귀 0), `npx vitest run`, `ruff check`, `black --check`, `mypy locus api`(≤ 11), `tsc --noEmit`, `vite build`, `docker build`. 라이브(Neo4j/PG/OpenAI) 시나리오는 운영자 실행으로 남기고 명령을 code-summary에 적는다(지역 A·B의 NPC가 같은 사건을 다르게 말하는 US-6.1 확인 포함).
- [x] 8.2 `construction/U5-npc-dialogue-language/code/code-summary.md`: 기준선/결과 수치, 파일 목록, 설계 이탈 완결 목록(FD domain-entities §7의 10건 + 이 플랜이 확정한 값 + Step 1.3의 승인 산출물 정정), 이월 결정별 구현 위치, 남긴 것(U6·U7 인계).
- [ ] 8.3 코드 게이트 제시 → 승인 뒤 `/code-review`.

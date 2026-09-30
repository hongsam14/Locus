# U5 NPC 대화·언어 — Code Generation Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U5 — 플레이어가 지역 NPC에게 묻고 NPC는 자기 지역에서 알 수 있는 것만 답하게 만든다. 먼 곳 일은 그 지역 소문대로 틀리게 말한다. 화면은 한국어, 저장 텍스트는 영어이며 NPC는 표시 언어로 직접 말한다. US-6.1이 이 유닛에서 완성된다.

> 근거: `construction/U5-npc-dialogue-language/functional-design/*`(승인 2026-09-30T12:11Z; 검토 02의 R-04·R-12·R-13은 Accepted risk), `construction/U5-npc-dialogue-language/nfr/nfr-light.md`(승인 2026-09-30T12:19Z; 검토 01의 R-01~R-06은 Accepted risk). 두 게이트의 이월 결정은 아래 표가 단일 기준이다. 이 플랜이 코드 생성의 단일 기준이다.

---

## 유닛 컨텍스트

- **스토리**: US-4.1(지역 NPC와 대화), US-4.2(자기 지역에서 알 수 있는 것만 안다), US-4.3(소문은 왜곡된 대로), US-6.1(**완성**: 같은 사건을 다른 지역에서 다르게 듣는다), US-9.1~9.4(화면은 한국어·저장은 영어, NPC는 표시 언어로, 번역은 어느 경계에서도, UI 라벨 통일), US-1.4(키 없이 둘러보기: 대화 부분).
- **의존**: U2(스냅샷·캐시), U4(플레이어·턴·가드·UoW·`EndTalk`·`RegionView`·`LlmUnavailableError`). 뒤 유닛이 기대하는 것: `NpcScope.build_context`(U6가 "자기 판단 행적"을 더한다), `NpcDialogueService`(U6 `appraise`), `Conversation`/`Message`(U6 행적 요약), `RegionSources`(U7 GM 화면), `display_lang`·`en` 사전(U3·U7 새 화면).
- **DB 엔티티(PostgreSQL, 추가만)**: `conversations`(`UNIQUE (session_id, npc_id)`), `messages`. `init-schema --play`/기동 시 `ensure_play_schema`가 만든다.
- **바뀌는 외부 계약**: (1) 새 라우트 4개(`npcs`, `npcs/{n}/start`, `npcs/{n}/say`, `npcs/{n}/history`). (2) 읽기 라우트 6개에 선택 `?lang=` 추가(기존 호출은 기본값으로 동작, 응답 형태 불변). (3) `GET /api/gm/sessions/{s}/timeline`은 `lang`을 받지 않는다(번역 필드가 없다 — NFR R-01/R-04 이월). (4) `RumorService.regenerate_region` 반환형 `list[SessionRumor]` → `RegenerateResult`(응답 형태는 불변: 라우터가 `result.rumors`를 돌려준다).
- **바꾸지 않는 것**: 합의 계산 값, 소문·사건·턴 규칙, `QueryResult` 형태(FR-F5), GM 라우트 응답 형태, U4 플레이 화면의 동작(내부 계산만 공유로 바뀐다), 임베딩·검색 텍스트는 영어 유지(C-1).

## 이월 결정 (두 게이트에서 확정 — 이 플랜에서 닫는다)
| 출처 | 결정 | 단계 |
|---|---|---|
| FD R-04 (1) | 기동 시 `translation_target_lang ∈ supported_langs`를 검증한다. 어긋나면 `Settings` 검증 오류로 기동을 막는다(조용한 400 폭풍보다 낫다) | 2.2 |
| FD R-04 (2) | `GET /api/gm/sessions/{s}/timeline`에서 `lang`을 **빼고** 설계 표의 그 행도 지운다(번역 필드가 없다) | 6.2 |
| FD R-12 | `build_context`는 **소문을 먼저 고른 뒤** 선택된 소문에서만 `shadowed`를 계산한다. 잘려 나간 소문이 자기 원본을 가리지 못한다. TP-U5-1의 기준식도 같은 순서를 쓴다 | 3.1, 3.4 |
| FD R-13 | 번역 정리는 `_close_if_replaced`의 조기 반환과 **독립**이다. `_after_replace(report, open_ids, play, loc, world_id)`로 넓혀 세션 종료와 정리를 각각의 조건으로 돌린다(정리 조건은 `report.replaced`만). 여섯 호출처에 `loc` 주입 | 6.3 |
| NFR R-01 | 두 provider에 `max_retries=0`을 지정해 SDK 자체 재시도를 끈다. 그러면 호출당 상한은 `with_retry` 층의 **93초**(30×3 + 1 + 2)다. 설계·NFR 노트·operations.md의 숫자를 93초로 맞춘다 | 2.3, 7.2 |
| NFR R-02 | 구조 단언을 다시 쓴다: `LLM.complete` 정확히 1회, `repo.uow()` 진입 정확히 1회, `SnapshotSource.get` **2회 이하**, 그래프·검색 저장소 직접 호출 0회 | 5.4 |
| NFR R-03 | 같은 NPC의 첫 `say`가 겹치면 제약 위반을 잡아 대화를 재조회하고 그 대화에 append한다(진 쪽도 답을 잃지 않는다) | 4.2, 5.4 |
| NFR R-04 | 프롬프트 주입 서술에 "오염은 그 대화의 이후 턴으로 이어질 수 있음"과 "요청 빈도 제한 없음(로컬 데모 전제로 감수)"을 적는다 | 7.2 |
| NFR R-05 | 지연 목표는 운영자 실행으로 남기고, 오프라인 게이트는 구조 단언이다 | 5.4, 7.2 |
| NFR R-06 | `PlayService.__init__(repo, snapshots, region_knowledge, params=…, *, guard, turns, tuning)` — `region_knowledge`는 **필수 위치 인자**. 직접 생성하는 곳은 `tests/play/test_player_mode.py::_services`(641행) 한 곳 | 4.3, 6.1 |

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. 복사본·`_v2` 없음.
- 각 단계는 **그 단계의 테스트가 GREEN인 상태로** 끝낸다. 예외: 4단계(`regenerate_region` 반환형)는 4.4의 호출처 갱신까지 한 단계 안에서 끝낸다.
- 규칙 번호(BR-U5-n)·검증 번호(TP-U5-n, EX-n)를 테스트 이름이나 docstring에 적는다.
- 새 외부 의존 없음.
- 각 단계 완료 즉시 체크박스를 [x]로 바꾼다.

---

## Steps

### Step 1 — 베이스라인과 뼈대
- [ ] 1.1 `./.venv/bin/python -m pytest -q --no-cov`(기대 475) / `cd web && npx vitest run`(39) / `mypy locus api`(11) 실측을 `construction/U5-npc-dialogue-language/code/code-summary.md` 초안에 기준선으로 기록.
- [ ] 1.2 새 파일(전부 신규, 빈 docstring): `locus/play/npc/{scope,dialogue,prompts}.py`, `tests/play/test_npc_scope.py`, `tests/play/test_dialogue.py`, `tests/api/test_dialogue_api.py`, `tests/localization/test_purge.py`, `web/src/features/play/{NpcList,DialoguePanel,LangToggle}.tsx`, `web/src/__tests__/dialogue.test.tsx`.

### Step 2 — 모델·조정값·설정 (domain-entities §1~2)
- [ ] 2.1 `locus/play/models.py`: `Conversation`(id, session_id, npc_id, started_turn, messages, created_at), `Message`(id, conversation_id, role `Literal["player","npc"]`, text, lang, turn, created_at), `NpcContext`, `ScopeLimits`, `NpcReply`, `RegenerateResult`(+`rumors` property), `TimelineKind += NPC_TALKED`. `RegionSources`는 `locus/play/region_knowledge.py`에 둔다(그 서비스가 만든다).
- [ ] 2.2 `locus/shared/config/tuning.py::PlayTuning += npc_max_facts=12, npc_max_rumors=8, npc_max_recent_messages=10 (ge=0), npc_max_message_chars=500 (ge=1)` + `scope_limits()` 메서드. `settings.py += supported_langs: tuple[str, ...]`(env `SUPPORTED_LANGS`, 쉼표 구분; 비면 `("ko","en")`) + env 4개 alias + `play_tuning()`에 전달. **모델 검증자**로 `translation_target_lang ∈ supported_langs`를 확인(이월 FD R-04(1)).
- [ ] 2.3 `locus/shared/llm/openai_provider.py`: 두 `ChatOpenAI(...)`에 `max_retries=0` 추가(이월 NFR R-01). `retry.py`의 docstring에 "호출당 상한 93초(30×3 + 대기 1+2)"를 적는다.
- [ ] 2.4 테스트: `tests/play/test_models.py`에 새 모델 왕복(`Message.role` 판별, 길이·범위), `RegenerateResult.rumors`; `tests/shared/test_config.py`(또는 기존 설정 테스트)에 env 5개와 기본 언어 정합 검증 실패 케이스.

### Step 3 — 아는 범위 (순수) (business-logic-model §1)
- [ ] 3.1 `locus/play/npc/scope.py`: `build_context(*, npc, facts, rumors, recent, limits) -> NpcContext`. **순서**: 소문 정렬·절단 → 선택된 소문에서 `shadowed` 계산 → facts에서 제외 → facts 정렬·절단 → `recent` 뒤 `limits.recent_messages`개(0이면 빈 목록). `allowed_ids`는 선택 뒤 남은 facts와 선택된 소문의 id.
- [ ] 3.2 `locus/play/npc/prompts.py`: `system_prompt(npc, lang)`, `user_prompt(ctx, question, lang)`, `fallback_text(lang)`, `LANG_NAMES`. 소문 태그는 `known`(승격) / `uncertain rumor`(왜곡도 ≥ 0.5) / `rumor`.
- [ ] 3.3 `tests/play/strategies.py` 확장: `regional_worlds()`(두 지역, 각 지역 전용 문장 표지, 전언 유발 약한 연결), `rumors_from(knowledge_ids)`.
- [ ] 3.4 테스트 `tests/play/test_npc_scope.py`: TP-U5-1(독립 기준 — `ConsensusEngine`으로 직접 계산 + 저장소 소문에서 기준식을 만든다), TP-U5-2(한도·순서, 한도 0), TP-U5-3(결정성), TP-U5-4(프롬프트 문자열에 다른 지역 문장·소문 원본·전언 없음), EX-5(지식 20·소문 12 → 12·8), EX-7(왜곡도 0.7 소문의 원본 제외 + 태그), 그리고 **소문이 한도를 넘는 경우**에 잘려 나간 소문의 원본이 facts에 남는다(이월 FD R-12).

### Step 4 — 저장·서비스 (domain-entities §3~4, business-logic-model §1.1·§2)
- [ ] 4.1 `locus/play/storage/schema.py`: `conversations`·`messages` 테이블. `locus/play/ports.py`: `ConversationStore`(`create_conversation`/`get_conversation`/`append_message`/`list_conversations`), `PlayUnitOfWork += conversations`, `PlayRepository += ConversationStore`.
- [ ] 4.2 어댑터 둘: `_PgStores`에 네 메서드(메시지 시각은 `next_timestamp()`, 조회는 `ORDER BY created_at, id`; `create_conversation`은 세션·NPC 중복이면 `ValueError`), `InMemoryPlayRepository`에 같은 계약(락·열림 규칙 U4 그대로). `tests/play/test_repository_contract.py`·`test_postgres_repo.py` 확장(중복 생성, 메시지 순서, 세션 범위).
- [ ] 4.3 `locus/play/region_knowledge.py`: `RegionSources` DTO + `region_sources(session_id, region_id)`; `knowledge_for_region`이 그것으로 지금과 같은 `QueryResult`를 만든다. `locus/play/player/service.py`: 생성자에 `region_knowledge` **필수 위치 인자**를 넣고 `current_region`이 `region_sources`를 쓴다(동작 동일).
- [ ] 4.4 `locus/play/rumor/service.py`: `regenerate_region` 반환형 → `RegenerateResult`(건너뛴 두 갈래는 `deleted_ids=[]`, `skipped_reason` 채움). 호출처 6곳 갱신: `api/routers/gm.py:135`(→ `result.rumors`), `tests/play/test_play_services.py` 84·100·181·203, `tests/play/test_player_mode.py:935`.
- [ ] 4.5 `locus/play/npc/dialogue.py`: `NpcDialogueService`(생성자·세 메서드는 business-logic-model §2 그대로). `say`는 LLM을 UoW 밖에서 1회 부르고, 저장 UoW에서 (필요하면) 대화 생성 + 메시지 둘. 대화 생성이 제약 위반이면 재조회해 그 대화에 append(이월 NFR R-03). `_resolve_lang`는 남긴다.
- [ ] 4.6 `locus/play/session_service.py`·`turn/advancer.py`: `EndTalk` 분기에 `NPC_TALKED` 타임라인(business-logic-model §5 그대로). `TurnAdvancer`는 대화 저장소를 UoW로 읽으므로 새 의존은 없다.
- [ ] 4.7 `locus/play/wiring.py`: `PlayContainer += dialogue`; `assemble_play`가 `region_knowledge`를 먼저 만들어 `play`와 `dialogue`에 넘긴다. `locus/play/__init__.py` 공개 이름 추가.
- [ ] 4.8 테스트 `tests/play/test_dialogue.py`: EX-1~3, EX-6, EX-10~12, TP-U5-5(호출 1회), 동시 첫 `say` 재조회(NFR R-03), `EndTalk` → `NPC_TALKED`(`messages` 수·`region_name`).

### Step 5 — 번역 정리·언어 (business-logic-model §3·§6)
- [ ] 5.1 `locus/localization/ports.py`·`storage/{postgres_repo,memory_repo}.py`: `purge(*, kind=None, ids=None, world_id=None, session_id=None) -> int`(필터 없으면 `ValueError`). `service.py`: 같은 시그니처로 감싸고 in-flight 키 정리.
- [ ] 5.2 `api/deps.py`: `display_lang(lang: str | None = None, shared=Depends(get_shared)) -> str` 의존성(지원 집합 밖 400).
- [ ] 5.3 `api/schemas.py`: `enrichment_for(..., lang: str | None = None)` → `enrich(lang=lang)`; `localize_query_result(..., lang=None)`, `localize_region_view(..., lang=None)`.
- [ ] 5.4 테스트 `tests/localization/test_purge.py`: TP-U5-6(필터별·필터 없음), in-flight 정리, 없는 원본. `tests/play/test_dialogue.py`에 구조 단언(이월 NFR R-02): `say` 한 번에 `complete` 1회 · `uow()` 1회 · `SnapshotSource.get` ≤ 2 · 그래프·검색 호출 0.

### Step 6 — API (business-logic-model §7)
- [ ] 6.1 `api/routers/play.py`: 새 라우트 4개(`GET npcs`, `POST npcs/{n}/start`, `POST npcs/{n}/say`, `GET npcs/{n}/history`). `api/schemas.py`에 `ConversationOut`·`NpcReplyOut`·`NpcSummaryOut`·`SayIn(text)`. `say`는 `lang: str = Depends(display_lang)`.
- [ ] 6.2 읽기 라우트에 `lang` 추가: `play.py`의 `GET .../region`·`GET .../regions/{r}/knowledge`, `knowledge.py`의 `GET /worlds/{w}/regions/{r}`, `gm.py`의 `GET .../regions/{r}/rumors`·`GET .../events`. **`gm.py`의 `GET .../timeline`에는 넣지 않는다**(이월 FD R-04(2)). `_rumors_out`·`_events_out`에 `lang`을 흘린다.
- [ ] 6.3 `api/routers/world.py`: `_close_if_replaced` → `_after_replace(report, open_ids, play, loc, world_id)`. 세션 종료는 지금 조건 그대로, 정리는 `report.replaced`만 보고 따로 돈다. 여섯 호출처(147·189·291·354·381 + 나머지 하나)에 `loc: LocalizationContainer | None = Depends(get_localization)` 주입.
- [ ] 6.4 `api/routers/gm.py`: `regenerate_region`이 `result.rumors`를 돌려주고 `purge(kind="rumor", ids=result.deleted_ids)`를 부른다(빈 목록이면 부르지 않는다).
- [ ] 6.5 테스트 `tests/api/test_dialogue_api.py`: EX-1·3·4·6~12, `?lang=fr` 400(모든 lang 라우트), `lang=en` → `*_ko` null, LLM 없는 컨테이너에서 `start` 200·`say` 503, 진행 중 턴에도 `say` 200. `tests/api/test_world_api.py`에 "열린 세션 없는 교체에서도 정리가 돈다"(이월 FD R-13). 기존 `test_play_gm_api.py`·`test_localization_api.py`·`test_knowledge_api.py`는 변경 없이 GREEN.

### Step 7 — 프론트엔드·문서 (frontend-components.md, NFR-8)
- [ ] 7.1 `web/src/i18n.ts`: `Lang`·`dicts.ko/en`·`lang()`·`setLang()`·`useLang()`; 남은 영어 라벨을 키로 옮기고(`toolbar.*`·`region.*`·`session.*`·`augment.*`·`editor.*`·`nav.*`) `en`을 채운다. `timeline.npc_talked` 두 언어. `web/src/api/http.ts`에 `withLang`. `api/play.ts`·`gm.ts`·`knowledge.ts`에 `?lang=`·새 함수 4개. `types.ts`에 `Conversation`·`Message`·`NpcReply`·`Lang`.
- [ ] 7.2 `features/play/{LangToggle,NpcList,DialoguePanel}.tsx` + `RegionScene`에서 NPC 카드 분리 + "들은 이야기" 안내 한 줄 + `PlayPage` 연결(`activeNpcId`, 언어 변경 시 재조회). `AppNav`에 토글.
- [ ] 7.3 테스트 `web/src/__tests__/dialogue.test.tsx`: 대화 열기·전송·실패 되돌림·LLM 없음·대화 끝내기; `ko`/`en` 키 집합 동일; 토글 뒤 `?lang=en`과 재조회. 기존 프론트 테스트는 라벨 단언만 키 기반으로 갱신.
- [ ] 7.4 문서: `env.example`(env 5개), `operations.md` 대화 절(라우트, 호출 1회, **93초**, 컨텍스트 한도, 표시 언어, 정리 시점과 CLI 공백, 주입·빈도 제한 감수 — 이월 NFR R-01/R-04/R-05), `CLAUDE.md`(Status·`play/npc/`·테스트 수).

### Step 8 — 검증·요약
- [ ] 8.1 전체: `pytest -q --no-cov`(기존 475 + 신규 GREEN, 회귀 0), `npx vitest run`, `ruff check`, `black --check`, `mypy locus api`(≤ 11), `tsc --noEmit`, `vite build`, `docker build`. 라이브(Neo4j/PG/OpenAI) 시나리오는 운영자 실행으로 남기고 명령을 code-summary에 적는다(지역 A·B의 NPC가 같은 사건을 다르게 말하는 US-6.1 확인 포함).
- [ ] 8.2 `construction/U5-npc-dialogue-language/code/code-summary.md`: 기준선/결과 수치, 파일 목록, 설계 이탈 완결 목록(FD domain-entities §7의 10건 + 이 플랜이 확정한 값), 이월 결정별 구현 위치, 남긴 것(U6·U7 인계).
- [ ] 8.3 코드 게이트 제시 → 승인 뒤 `/code-review`.

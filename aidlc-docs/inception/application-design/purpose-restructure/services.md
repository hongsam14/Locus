# Services — Purpose Restructure (2026-09-29)

> 서비스 = 유스케이스를 실행하는 애플리케이션 계층. 경계마다 컨테이너 하나가 서비스들을 담고, 라우터는 `Depends`로 컨테이너를 받아 서비스를 직접 호출한다(AD-R2 = A, AD-R4 = A). 파사드는 없다.

## 1. 조립 (Composition)

```
Settings ──▶ assemble_shared ──▶ SharedContainer(graph, search, llm, vlm, embedding, sql_engine, settings)
                                     │
                    ┌────────────────┼────────────────────┐
                    ▼                ▼                     ▼
          assemble_knowledge   assemble_localization   (shared만 필요)
                    │                │
        KnowledgeContainer     LocalizationContainer
                    │
         ┌──────────┴──────────┐
         ▼                     ▼
   assemble_world         assemble_play
   WorldContainer         PlayContainer
```

- `api/main.create_app`은 lifespan에서 위 순서로 조립한다. 테스트는 원하는 컨테이너만 만들어 `create_app(play=fake_play)`처럼 넘긴다. 넘기지 않은 경계는 설정으로 조립을 시도하고, 실패하면 `None`으로 두어 그 라우터만 503이 된다(FR-A3).
- CLI(`locus/__main__.py`)는 같은 `assemble_*`를 써서 `world build|import|export|demo`, `init-schema [--world|--play|--localization]`를 제공한다.

## 2. 경계별 서비스 정의

### world
| 서비스 | 책임 | 협력 |
|---|---|---|
| `WorldBuilder` | 자료 → 월드(재빌드 시 교체) | Ingestion, TopologyBuilder, OntologyBuilder, Wiki(Distiller·Linker·CommonsenseWiki), persist_graph, WorldCache |
| `WorldEditor` | 지역·연결·지식·스코프·NPC 편집, 월드 목록 | GraphRepository, SearchRepository, WorldCache |
| `AugmentationService` | 보강 run: 탐지 → 질문 → 답 적용 → 되돌리기 | WorldCache(스냅샷), WorldEditor, QuestionGenerator(LLM), RunStore |
| `NpcDraftService` | 지역 NPC 초안 제안 | WorldCache, LLM |
| `WorldFileExporter` / `WorldFileImporter` | World File 저장·로드 | WorldCache / GraphRepository, SearchRepository, persist_graph, WorldCache |
| `DemoWorlds` | 패키지 내 데모 World File 로드 | WorldFileImporter |
| `WikiAdmin`, `CrossWorldWikiExplorer` | prior 관리·근거 조회 / 교차 월드(진행 중) | GraphRepository, SearchRepository |

### knowledge
| 서비스 | 책임 | 협력 |
|---|---|---|
| `QueryEngine` | 캐노니컬 지역 지식, 비교, `region_known`, `region_briefs` | WorldCache, ConsensusEngine |
| `WorldCache` | 스냅샷 캐시·무효화 | WorldLoader |

### play
| 서비스 | 책임 | 협력 |
|---|---|---|
| `SessionService` | 세션 시작(플레이어 포함)·종료·조회·타임라인, 지역 동기화 | PlayUnitOfWork, WorldCache |
| `PlayService` | 현재 지역 화면, 행동 검증·위임, 플레이 로그 | WorldCache, QueryEngine, RumorService, TurnAdvancer, movement |
| `TurnAdvancer` | 시간 진행의 유일한 진입점(행동 또는 수동), 턴 루프, 가드, 상한 | RumorService, EventService, RumorFeedbackService, DistortionService, dynamics·rumor_dynamics·promotion, TurnGuard, PlayUnitOfWork |
| `RumorService` | 소문 생성·재생성·지지도·턴 내 추가(상한) | RumorGenerator(LLM), QueryEngine, RumorStore |
| `EventService` | 사건 CRUD·제안·승인·해결·폐기 | EventSuggester(LLM), QueryEngine(`region_briefs`), EventStore, TimelineStore |
| `DistortionService` | 지역 왜곡도 | DistortionStore |
| `NpcDialogueService` | NPC 대화 | NpcScope(순수), SessionKnowledgeService, ConversationStore, LLM |
| `SessionKnowledgeService` | 세션 지역 지식(외부 계약 + 내부 입력) | WorldCache, QueryEngine, RumorStore |

### localization
| 서비스 | 책임 | 협력 |
|---|---|---|
| `TranslationService` | 캐시 읽기, 백그라운드 워밍(중복 억제), 정리 | TranslationStore, Translator(LLM), Executor |

## 3. 오케스트레이션 흐름

### 3.1 월드 빌드 (US-2.1, 2.7)
1. 라우터 `/api/world/{wid}/build`(multipart 또는 base64 JSON) → `WorldInputs`.
2. `WorldBuilder.build(wid, inputs, replace=True)`:
   - `replace`이고 월드가 있으면 `graph.delete_world` + `search.delete_world`.
   - 수집(병합 시 힌트·id 재매핑 보존) → 토폴로지(경고 수집) → prior 증류·연결·저장 → 온톨로지(미해석 지식 id 수집) → `persist_graph`(NPC 없음) → `WorldCache.invalidate(wid)`.
   - `BuildReport(counts, warnings, unscoped_knowledge_ids, llm_calls, ok)`.
3. 열린 세션이 있는 월드의 교체는 라우터가 먼저 `PlayContainer.sessions.list(wid)`로 확인하고 `confirm=true` 없이는 409를 돌려준다(NFR-9). play가 없으면 확인 없이 진행.

### 3.2 World File 불러오기 (US-6.3)
1. 라우터가 파일을 `WorldFile`로 파싱(버전 검사 → 지원하지 않으면 422).
2. 열린 세션 확인(3.1과 같음) → 확인되면 `SessionService.close`를 각 세션에 호출.
3. `WorldFileImporter.import_(wid, file, replace=True)`: `delete_world` → `persist_graph`(NPC·관계·prior 포함) → 캐시 무효화 → `ImportReport`.

### 3.3 세션 시작 (US-3.1)
1. `/api/play/worlds/{wid}/sessions` `{name, start_region_id}`.
2. `SessionService.start`: `WorldCache.get(wid)`에서 지역 확인 → **UoW 하나**로 세션 생성 + 플레이어 생성 + 지역 왜곡도 초기화 + `SESSION_STARTED` 타임라인.
3. 응답: 세션 + 플레이어. 프론트는 `/play/{sid}`로 이동.

### 3.4 플레이어 행동 (US-3.3, 3.4) — AD-R5 = B
1. `/api/play/sessions/{sid}/act` `{type: "move", to_region_id}` | `{type: "wait"}` | `{type: "end_talk", npc_id}`.
2. `PlayService.act`: 스냅샷으로 행동 검증(도달 가능·통과 가능; 아니면 400) → `TurnAdvancer.advance(sid, action)`.
3. `TurnAdvancer.advance`:
   - `TurnGuard.acquire(sid)`(실패 → 409).
   - 비용 = `movement.move_cost`(Move) / 1(Wait, EndTalk) / 1(None = GM 수동).
   - 비용만큼 반복: 한 턴 처리(기존 6단계, 상한·씨앗 규칙 적용, `LlmBudget` 소진 시 소문 추가 중단) → 각 `TurnResult` 누적.
   - Move면 마지막에 플레이어 위치 갱신 + `PLAYER_MOVED` 타임라인.
   - **저장은 UoW 하나**(소문 upsert, 왜곡도, 사건, 플레이어, 타임라인, 턴 번호). LLM 호출은 UoW 밖에서 먼저 끝낸다(호출 결과를 모아 두고 한 번에 저장).
   - `ActionResult(turns, player, changes(지역 이름 포함), llm_calls, narration)`.
4. 라우터는 `changes`에 번역을 입혀 응답. 프론트는 `RegionScene`을 즉시 갱신(`current_region` 재조회는 캐시라 빠름).

### 3.5 NPC 대화 (US-4.1~4.3)
1. `/api/play/sessions/{sid}/npcs/{npc_id}/say` `{text}`.
2. `NpcDialogueService.say`:
   - 플레이어가 NPC의 지역에 있는지 확인(아니면 400).
   - `SessionKnowledgeService.for_region(sid, npc.home_region_id)` → known(캐노니컬 direct+inherited+global) + 활성 소문.
   - `NpcScope.build_context(npc, known, rumors, recent_messages, limits)` — 순수, 불변식 검증 대상.
   - 프롬프트(가드 + 컨텍스트 + 표시 언어) → `LLM.complete` 1회.
   - `ConversationStore.append_message` ×2(player, npc), `NPC_TALKED`는 `EndTalk` 행동 때 기록.
3. 응답 `NpcReply`. 번역 없음(A-1).

### 3.6 GM 사건 제안 (US-5.2)
1. `/api/gm/sessions/{sid}/events/suggest?n=` (`n ≤ 5`, 아니면 400).
2. `EventService.suggest`: `QueryEngine.region_briefs(wid)` + 최근 사건 → `EventSuggester.suggest` → SUGGESTED로 저장 + `EVENT_SUGGESTED` 타임라인.
3. 승인 `approve` → ACTIVE + `EVENT_APPROVED`; 폐기 → 삭제 + `EVENT_DISCARDED`; 해결은 ACTIVE만.

### 3.7 GM 수동 턴 (US-5.1, 8.3)
- `/api/gm/sessions/{sid}/advance` → `TurnAdvancer.advance(sid, None)`. 플레이어 행동과 같은 경로·가드.

### 3.8 응답 번역 (US-9.1)
- 라우터가 `LocalizationContainer.translations.enrich(items, kind=..., fields=[...])`를 호출해 `dict[id][field]`를 받아 `api/schemas`의 `*_ko` 필드에 넣는다. localization이 없으면 원문만. play·world·knowledge 코드는 번역을 모른다.

### 3.9 편집 → 캐시 (US-2.2~2.4)
- `WorldEditor`의 모든 쓰기는 마지막에 `WorldCache.invalidate(wid)`. 다음 `current_region`·`for_region`은 새 스냅샷을 읽는다. 열린 세션의 `sync_regions`는 세션 조회 때 lazily 호출한다(C12).

## 4. 트랜잭션·동시성 원칙
- PostgreSQL 쓰기는 `PlayUnitOfWork`로 묶는다(세션 시작, 턴 진행, 대화 메시지).
- Neo4j는 다중 문 트랜잭션이 제한적이므로 "삭제 → 저장" 순서와 리포트로 부분 실패를 드러낸다.
- 턴 진행은 세션당 하나(TurnGuard). 프로세스 하나(uvicorn 단일 워커)를 전제로 in-process 락을 쓰고, 이 전제를 README·operations에 적는다.
- LLM 호출은 어떤 DB 트랜잭션 안에서도 하지 않는다.

## 5. 변경 (2026-09-29): 행적·판단·전파 흐름

### 5.1 행동 선언 (US-4.5)
1. `/api/play/sessions/{s}/act {type:"declare", text}` (길이 ≤ `declare_max_chars`).
2. `PlayService.act(Declare)`: `current_region` 스냅샷 → `GmNarrator.narrate(declaration, region_view)`(LLM 1회, 판정 없음) → `DeedService.record(kind=declared_action, text=narration, witnessed=지역 NPC)` → `TurnAdvancer.advance(s, Declare)`(1턴).
3. 응답 `ActionResult.narration`에 서술이 들어간다. 이 행적은 아직 소문이 아니다.

### 5.2 대화 마침과 NPC 판단 (US-4.4)
1. `/api/play/sessions/{s}/act {type:"end_talk", npc_id}`.
2. `PlayService.act(EndTalk)`: 대화 이력에서 플레이어 발언을 요약해 `statement` 행적 기록(LLM 요약은 판단 호출에 합침) → `DeedService.pending_for(s, region)`(도착·발언·선언 중 판단 없는 것) → `NpcDialogueService.appraise(s, npc_id, deeds)`: NPC 페르소나 + 지역 지식으로 각 행적에 `noteworthy/salience/slant/retelling`(LLM 1회) → `DeedService.attach_appraisals` → `TurnAdvancer.advance(s, EndTalk)`(1턴).
3. 판단하지 않은 행적(아무와도 대화하지 않음)은 씨앗이 되지 않는다(A-6).

### 5.3 턴 루프의 새 단계 (US-6.5, 8.6) — `TurnAdvancer` 한 턴
1. 사건 적용·전파(기존).
2. 캐노니컬 소문 추가(기존, 상한).
3. **행적 씨앗**: `DeedService.seeds_for_turn`의 (행적, 판단)마다 `RumorService.seed_from_appraisal` — NPC 지역에 `retelling` 원문의 소문 체인, `origin_kind=deed`, 탄생 지지도 = `birth_support × salience` 보정. 예산 소진 시 다음 턴으로.
4. **소문 전파**: `RumorStore.list_session_origin`의 활성 소문마다 `plan_spread(snapshot, rumor, reached)` → 지역당 `max_spread_per_region_turn` 이내로 `RumorService.spread`(왜곡 체인 1단, LLM 1회/대상) → `RUMOR_SPREAD` 타임라인. `reached`는 `(origin_deed_id, region_id)`로 추적한다.
5. 되먹임 → 지지도 → 가지치기 → 승격(기존; 전파 소문도 같은 규칙).
6. 저장은 UoW 하나. LLM 호출은 전부 저장 전에 끝낸다.

### 5.4 GM 행적 관리 (US-5.6)
- `GET /api/gm/sessions/{s}/deeds` → `DeedService.list` (행적 + 판단 + 도달 지역).
- `POST .../deeds/{d}/void` → `DeedService.void` → `RumorStore.deactivate_by_deed` → `DEED_VOIDED` 타임라인.
- 사건 제안(3.6)의 컨텍스트에 최근 행적 요약을 넣는다.

### 5.5 원칙 보강
- **캐노니컬 기원 소문은 전파하지 않는다.** 지역 사이의 캐노니컬 지식 흐름은 knowledge의 hearsay 계산이 맡는다. 전파 단계는 `origin_kind == deed`만 본다.
- **재생성은 세션 기원 소문을 지우지 않는다.** 플레이어의 흔적은 GM 취소로만 사라진다.
- **모든 새 LLM 호출(판단·서술·전파)은 턴 예산 안에 든다.**

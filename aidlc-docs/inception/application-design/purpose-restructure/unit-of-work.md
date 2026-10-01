# Units of Work — Purpose Restructure (2026-09-29)

> 근거: `plans/purpose-restructure-unit-of-work-plan.md`(UOW-R1=A 8유닛, UOW-R2=A 플레이 먼저), `application-design.md`(+§7b 행적), `stories.md`(48), `requirements` §7 + 부록 A, `execution-plan.md`.
> 단일 배포 모놀리스. 유닛 = 작업 묶음. 번호는 의존 그림을 따르고, **실행 순서는 U1 → U2 → U4 → U5 → U6 → U7 → U3 → U8**이다.

## 0. 한눈에

| # | 유닛 | 한 줄 | 실행 순서 | Construction 단계 |
|---|---|---|---|---|
| U1 | 경계 재정리 | 다섯 패키지·포트 분할·컨테이너·접두어·용어 — **의미 불변** | 1 | FD SKIP · NFR SKIP · CodeGen |
| U2 | World File·캐노니컬 기반 | NPC 모델, World File 저장·로드, WorldCache, 관계 재독, 수집 결함, 교체 빌드 | 2 | FD · NFR-light · CodeGen |
| U3 | 월드 에디터 | 업로드·지도 편집·지식·NPC·보강 통합·wiki 근거·월드 목록 (UI 포함) | 7 | FD · NFR-light · CodeGen |
| U4 | 플레이어 모드 | Player·이동·`advance(action)`·가드·예산·상한·현재 지역 화면 | 3 | FD · NFR-light · CodeGen |
| U5 | NPC 대화·언어 | NpcScope·대화·번역 경계 완성·UI 라벨 | 4 | FD · NFR-light · CodeGen |
| U6 | 행적·전파 | Deed·NPC 판단·선언·씨앗·전파·gm 행적·선언 UI — 레거시와 갈라지는 지점 | 5 | FD · NFR-light · CodeGen |
| U7 | GM 모드·안정화 | GM 화면 5패널·모드 전환·사건 제안 컨텍스트·세계 상태·E2/E4~E6 | 6 | FD · NFR-light · CodeGen |
| U8 | 데모·배포·문서 | TRPG 데모 월드·원클릭·Docker·메타·README·진행 중 표시·(P2) CI | 8 | FD-light · Infra-light · CodeGen → Build&Test |

산출물 위치: `aidlc-docs/construction/<unit-id>/{functional-design,nfr,infrastructure-design,code}/`, 코드 위치는 각 유닛 "코드 위치" 절.

---

## U1 — 경계 재정리 (Boundary Restructure)

- **목적**: `locus/`를 shared / knowledge / world / play / localization 다섯 경계로 옮기고, 역방향 의존을 끊고, 포트를 나누고, 조립을 컨테이너로 바꾸고, API 접두어·용어를 정리한다. **동작(의미)은 바꾸지 않는다.** 이름·위치·경로만 바뀐다. 이 유닛이 끝나면 기존 305 테스트가(경로·이름 갱신 뒤) 전부 GREEN이어야 한다.
- **책임 (컴포넌트)**: S1 models 이동 + 이름 정리(hearsay·path_decay·SourceKind 중립·`_ko` 제거→`api/schemas`) · S2 config → `Tuning` dataclass 분리(값 불변) · S3 llm 이동 · S4 storage 이동(미사용 메서드 제거, `Relation` 제약 제거) · S5 `sql.py` · K1·K2·K3·K5 이동(`region_known`) · K6 wiring · W1~W5 이동(`AugmentationRun` 개명) · W6 `WorldBuilder`(생성자 주입, 빌드마다 새 인스턴스; `replace`는 U2) · W7 `WorldEditor` 개명 · W9 `export.py`(옛 Exporter) · W10 `demo/`(원자료 빌드 경로) · W11 wiring · W12 진행 중 docstring · P1 models 이동(`Translation`·`_ko` 제거) · P2 포트 8개 중 6개(Session·Rumor·Event·Distortion·Timeline + UoW; Player·Conversation·Deed는 뒤 유닛) · P3 `PostgresPlayRepository`(포트 구현, `ON CONFLICT`), 인메모리, `schema.py` · P4·P8·P9·P10·P11·P14 이동(`SessionKnowledgeService`, 번역 호출 제거) · P7 `TurnAdvancer.advance(session_id)`(옛 `advance_turn`; `action`은 U4) · `GameMasterService` 제거 · P15 wiring · L1~L5(자체 `TranslationStore`, PG·인메모리·schema) · A1 lifespan 조립 + 컨테이너 · A2 deps · A3 schemas(`_ko` DTO) · A4~A7 라우터(기존 엔드포인트를 새 접두어로 재배치) · CLI `init-schema [--world|--play|--localization]` · F1 react-router 스켈레톤(`/`, `/editor/:worldId`에 기존 패널, `/gm/:sessionId`에 기존 SessionPanel, `/play/:sessionId` 자리) · F5 `api/{world,knowledge,play,gm}.ts` · `tests/` 경계별 재배치 + `test_boundaries.py` + 포트 계약 테스트 · Dockerfile `api/` 포함 + `.dockerignore`.
- **인터페이스**: 새 API 접두어(경로만 변경, DTO 의미 동일), 컨테이너 넷, `create_app(**containers)`.
- **코드 위치**: `locus/{shared,knowledge,world,play,localization}/`, `api/`, `web/src/{routes,api}/`, `tests/{shared,knowledge,world,play,localization,api}/`.
- **PBT**: 기존 hypothesis 테스트 이동. 새 속성 없음.
- **완료 기준**: pytest 281 + vitest 24 GREEN(경로·이름만 갱신), `test_boundaries` 통과, ruff/black/tsc clean, `docker compose --profile service` 앱 기동(US-1.1 일부).

## U2 — World File·캐노니컬 기반 (World File & Canonical Foundation)

- **목적**: 플레이와 에디터가 공통으로 딛는 캐노니컬 기반을 완성한다. NPC가 월드의 일부가 되고, 월드를 파일로 저장·로드할 수 있으며, 스냅샷 캐시로 플레이가 즉시 응답하고, 빌드가 데이터를 조용히 잃지 않는다.
- **책임**: S1 `NPC`·`WorldSnapshot`·`ImportReport`·`BuildReport` 확장 · S4 `npc_to_node`/`lives_in_edges`/`node_to_npc`/`edge_to_relation`, `persist_graph(npcs=…)`, `delete_world` 사용, `list_world_ids` · K3 loader(NPC·`RELATED_TO`·`LIVES_IN` 재독, 이름 색인) · K4 `WorldCache` · K5 `QueryEngine`(캐시 사용, `title` 채움 A8, `region_briefs`) · W1 수집 결함(A1 힌트 보존, A2 id 재매핑, A7 base64 이미지, A11 결정적 해석, 정규화 헬퍼 통일) · W2 경고 노출(A13) · W3 미해석 지식 id 노출(A4) · W6 `WorldBuilder.build(replace=)`(A3), 리포트에 경고·미해석·`llm_calls`, 캐시 무효화 · W9 `WorldFile` v1 schema/export/import(교체 → 저장 → 무효화, 버전 검사) · W10 `DemoWorlds.list/load`(기존 Aldermoor를 World File로 변환해 패키지에 동봉; TRPG 콘텐츠는 U8) · CLI `world export|import|demo` · A4 world 라우터: build(multipart/base64), `GET/POST /worlds/{w}/file`, `POST /worlds/{w}/demo/{name}`, `GET /worlds` · A5 knowledge 라우터 `briefs`.
- **인터페이스**: `WorldFile` v1(형식 계약), `WorldSnapshot`, `WorldCache.get/invalidate`.
- **코드 위치**: `locus/shared/models`, `locus/shared/storage`, `locus/knowledge/{loader,cache,query}.py`, `locus/world/{ingestion,topology,ontology,build.py,worldfile/,demo/}`, `api/routers/{world,knowledge}.py`, `web/src/api/world.ts`(파일·데모 호출만).
- **PBT**: World File 저장→로드→저장 동일(PBT-02, 도메인 생성기 `tests/world/strategies.py`), 병합 시 연결 힌트·엔티티 참조 보존 불변식(PBT-03).
- **완료 기준**: US-6.2·6.3·2.7 수용 기준, US-2.1 백엔드 부분, 데모 World File 로드 시 LLM 0회.

## U3 — 월드 에디터 (World Editor) — 실행 순서 7

- **목적**: 제작자가 자료를 올려 자동 구성하고, 지도 위에서 직접 그리고, 지식·스코프·NPC를 편집하고, 보강 Q&A로 빈틈을 채우고, wiki 근거를 보고, 월드를 고른다.
- **책임**: W7 `WorldEditor` 전 연산(지역·연결·지식·스코프·NPC, cascade 정책, OpenSearch 동반 삭제, `list_unscoped`, `list_worlds`, 캐시 무효화) · W8 `NpcDraftService` · W5 보강 run 통합·수리(B1~B5, 끊긴 관계 탐지 실동작) · W4 `WikiAdmin.list_priors/prior_refs` · A4 world 라우터 편집·보강·wiki·NPC 엔드포인트 · F2 editor feature(`MapCanvas` 편집 모드, `RegionInspector`, `UploadPanel`, `AugmentPanel`(run·대상 표시·되돌리기), `WikiPanel`, `BuildReportPanel`, `WorldFileBar`) · `/` 월드 목록 화면 · 에디터의 캐노니컬 지식 번역 표시(U5의 `enrich` 재사용).
- **인터페이스**: `WorldEditor` 메서드, world 라우터 편집 계약.
- **코드 위치**: `locus/world/{editor.py,npc_drafts.py,augmentation/,wiki/}`, `api/routers/world.py`, `web/src/features/editor/`, `web/src/routes/`.
- **PBT**: 편집 연산의 불변식(연결 upsert는 항상 양방향 2개, 삭제 뒤 참조 없음) — advisory.
- **완료 기준**: E2 스토리 8개 + US-6.4 수용 기준. 보강 Q&A가 UI에서 실제로 반영·되돌리기된다.

## U4 — 플레이어 모드 (Player Mode)

- **목적**: 플레이어가 캐릭터로 세션에 들어가, 연결을 따라 이동하고, 행동으로 시간을 흐르게 하며, 현재 지역을 한 화면에서 본다. 턴 엔진이 행동을 입력으로 받는 단일 진입점이 되고, 폭주 상한·동시성 가드·LLM 예산을 갖는다.
- **책임**: P1 `Player`·`PlayerCreate`·`PlayerAction(Move/Wait/EndTalk)`·`ActionResult`·`MoveOption`·`RegionView`, `TimelineKind` +`SESSION_STARTED/CLOSED`, `PLAYER_MOVED` · P2 `PlayerStore` · P3 `players` 테이블 · P4 `SessionService.start(world_id, player)`(UoW 하나, 타임라인) · P5 `movement.py`(순수: `move_options`, `move_cost`, `is_passable`; blocked 통과 불가 A-2) · P6 `PlayService.current_region/act/log` · P7 `TurnAdvancer.advance(session_id, action|None)`: 비용만큼 턴 루프, `TurnGuard`(C3), `LlmBudget`·지역당 새 소문 상한·이미 파생된 캐노니컬 씨앗 제외(E1), 저장 UoW 하나, LLM은 트랜잭션 밖, `llm_calls` · P11 지역 이름 주입(D3) · S2 `PlayTuning`(이동·상한·예산 값) · A6 play 라우터(세션 시작(플레이어)·종료·목록·`region`·`act`·`log`·세션 지역 지식 유지) · A7 gm `advance` → `advance(None)` · F3 play feature(`RegionScene`, `MovePanel`, `ActionBar`(기다리기), `TurnSummaryToast`, `PlayLog`) · `/play/:sessionId` 실화면.
- **인터페이스**: `advance(session_id, action)`, `ActionResult`, play 라우터 계약.
- **코드 위치**: `locus/play/{models.py,ports.py,storage/,session_service.py,player/,turn/}`, `api/routers/play.py`, `web/src/features/play/`.
- **PBT**: 이동 비용 단조성·범위(PBT-03), "턴당 새 소문 ≤ 상한", "LLM 호출 ≤ 예산" 불변식(PBT-03), 도메인 생성기 `tests/play/strategies.py`(PBT-07).
- **완료 기준**: US-3.1~3.4, US-8.1, US-8.3 수용 기준; US-6.1의 기반(이동 뒤 지역 화면에서 hearsay·소문이 지역마다 다르게 보임).

## U5 — NPC 대화·언어 (NPC Dialogue & Language)

- **목적**: 플레이어가 지역 NPC와 대화하고, NPC는 자기 지역에서 알 수 있는 것만 안다. 번역 경계가 완성되어 화면은 한국어, 저장 텍스트는 영어이며, NPC는 표시 언어로 말한다.
- **책임**: P12 `NpcScope.build_context`(순수, 불변식) · P13 `NpcDialogueService.start/say/history`(프롬프트 가드, 표시 언어 직접 생성 A-1, LLM 1회/턴) · P2 `ConversationStore` · P3 `conversations`·`messages` 테이블 · P14 `source` 태그(`rumor:promoted`) · `play/npc/prompts.py` · A6 play 라우터 `npcs/{n}/start|say|history` · L4 `enrich` 중복 억제·`purge`(G4), 캐노니컬 지식 번역을 knowledge·world 응답에 적용(G2) · A3 DTO 확장 · F3 `NpcList`·`DialoguePanel` · F6 i18n 전 라벨 + en 사전(G5), 원문 토글 유지 · 표시 언어 설정 UI.
- **인터페이스**: `NpcContext`, 대화 API, `enrich` 반환 매핑.
- **코드 위치**: `locus/play/{npc/,region_knowledge.py}`, `locus/localization/service.py`, `api/{schemas.py,routers/play.py,routers/knowledge.py,routers/world.py}`, `web/src/{features/play/,i18n/}`.
- **PBT**: NPC 아는 범위 불변식 — 컨텍스트 지식 id ⊆ known ∪ 지역 활성 소문(PBT-03), 생성기 재사용.
- **완료 기준**: US-4.1~4.3, US-9.1~9.4 수용 기준; **US-6.1 완성**(지역 A와 B의 NPC가 같은 사건을 다르게 말함).

## U6 — 행적·전파 (Deeds & Spread) — 레거시와 갈라지는 지점

- **목적**: 플레이어의 도착·발언·선언이 행적으로 남고, 대화한 NPC가 그 소문 가치를 정하며, 전하기로 한 행적이 소문이 되어 토폴로지를 따라 턴마다 왜곡되며 퍼진다. GM은 행적을 보고 취소한다.
- **책임**: P1 `Deed`·`DeedAppraisal`·`PlayerAction.Declare`·`SessionRumor.origin_kind/origin_deed_id/spread_from_region_id`·`Narration`·`SpreadTarget`, `TimelineKind` +`DEED_RECORDED/APPRAISED/VOIDED`, `RUMOR_SPREAD`, `ACTION_DECLARED` · P2 `DeedStore`, `RumorStore.list_session_origin/deactivate_by_deed` · P3 `deeds`·`deed_appraisals` 테이블, `session_rumors` 열 추가 · P16 `DeedService`(record/pending_for/attach_appraisals/seeds_for_turn/void/list) · P17 `GmNarrator`(선언 서술, 판정 없음 A-7) · P19 `plan_spread`(순수) · P8 `seed_from_appraisal`·`spread`, 재생성이 세션 기원 소문을 보존 · P13 `appraise`(NPC 페르소나, LLM 1회) · P6 `act`: `Move`→arrival 기록, `Declare`→서술→기록→1턴, `EndTalk`→발언 요약 기록→판단→1턴 · P7 턴 루프 두 단계(행적 씨앗 → 전파; 상한·예산) · P9 제안 컨텍스트에 최근 행적 · P12 컨텍스트에 자기 판단 행적 · S2 `spread_min_weight`·`deed_seed_min_salience`·`max_spread_per_region_turn`·`declare_max_chars` · A6 `act{declare}` · A7 `GET /deeds`, `POST /deeds/{d}/void` · F3 `ActionBar` 선언 입력 + `NarrationCard`, 소문 "행적 기원" 표시 · F4 `DeedPanel`(gm 화면 스켈레톤에 추가).
- **인터페이스**: `DeedService`, `plan_spread`, gm 행적 API.
- **코드 위치**: `locus/play/{deeds/,gm/narrator.py,rumor/spread.py,rumor/service.py,turn/advancer.py,npc/dialogue_service.py,player/play_service.py}`, `api/routers/{play,gm}.py`, `web/src/features/{play,gm}/`.
- **PBT**: 전파 불변식 — 대상 가중치 ≥ 기준, 왜곡도 단조, `(origin_deed_id, region_id)` 중복 없음, 캐노니컬 기원 소문은 전파 대상 아님(PBT-03); NPC 아는 범위 불변식 확장.
- **완료 기준**: US-4.4·4.5·5.6·6.5·8.6 수용 기준; **US-6.5 동작**(내 행적을 먼 지역에서 다르게 듣는다).

## U7 — GM 모드·안정화 (GM Mode & Hardening)

- **목적**: GM 모드가 플레이 화면에서 드나드는 모드로 자리 잡고, 사건 제안이 월드를 보며, 세계 상태가 지도 위에 보이고, 시뮬레이션의 남은 결함이 닫힌다.
- **책임**: F4 gm feature 분할(`EventPanel`, `RumorPanel`, `DistortionPanel`, `TimelinePanel`, `WorldStateOverlay`, `ManualTurnButton`) + 플레이↔GM 전환 · P9 `EventSuggester(briefs, recent_events, deeds)`(D2), `n` 상한(NFR-6), `EVENT_APPROVED/DISCARDED/SUGGESTED` 타임라인, SUGGESTED 해결 거부(E4) · P8 `rumor_dynamics` 승격 면제 축소 + 되먹임 복원/상한(E2), 재생성 부모 비활성화(E5) · P4 `sync_regions`(E6) · P10 응답은 저장 행 · A7 `GET /state`(D4) · F4 슬라이더 키보드·터치 저장(D5) · 타임라인·알림 지역 이름(D3 완성) · 플레이 로그 필터(C6) · S2 조정값 집약 완성: `ConsensusParams` 단일 생성(A7).
- **인터페이스**: gm 라우터 전 계약, `WorldStateOut`.
- **코드 위치**: `locus/play/{event/,rumor/dynamics.py,session_service.py,distortion_service.py}`, `api/routers/gm.py`, `web/src/features/gm/`.
- **PBT**: E2 시나리오(사건 해결 뒤 비승격 소문 감쇠) 예시 테스트 + 감쇠 단조 속성(advisory).
- **완료 기준**: US-5.1~5.5, US-8.2, US-8.4, US-8.5 수용 기준.

## U8 — 데모·배포·문서 (Demo, Deploy, Docs)

- **목적**: 관람자가 `.env` 두 값과 명령 하나로 띄워 5분 안에 플레이한다. README가 목적을 말하고, 저장소 메타가 맞고, 진행 중 기능이 표시된다.
- **책임**: W10 TRPG 데모 월드 콘텐츠(지역 10~15개 `[A-4]`, 계층 2~3단, 막힌 길·강·길, 지역별 지식, NPC 1~3명/지역, 사건 씨앗 2~3개) — World File로 패키지 동봉, 에디터(U3)로 저작 · `/` 원클릭 로드 UI · API 키 없는 둘러보기 안내(NFR-4) · `.dockerignore`·compose 프로파일 정리·`requirements.txt` 정합·라이선스·peer 의존(H2·H4) · README 전면 갱신(H1), `CLAUDE.md`, `operations.md`, `web/README.md`, 진행 중 기능 절(H3) · (P2) GitHub Actions(H5, PBT seed 로그) · Build&Test 라이브 시나리오 스크립트(기동 → 데모 → 세션 → 이동 → 대화 → 선언 → GM 사건 → 턴 → 다른 지역 대화; US-6.1·6.5).
- **인터페이스**: 데모 World File, README 절 구성.
- **코드 위치**: `locus/world/demo/*.world.json`, `Dockerfile`, `.dockerignore`, `docker-compose.yml`, `requirements.txt`, `pyproject.toml`, `README.md`, `CLAUDE.md`, `aidlc-docs/operations/`, `.github/workflows/`(P2), `web/src/routes/Home.tsx`.
- **완료 기준**: US-1.1~1.4, US-7.3, US-7.5, US-7.6(P2) 수용 기준; Build&Test 통합 GREEN.

---

## 코드 조직 원칙 (모든 유닛 공통)
- 코드는 워크스페이스 루트(`locus/`, `api/`, `web/`, `tests/`)에, 설계 문서는 `aidlc-docs/`에.
- 각 유닛은 자기 경계 디렉터리 안에서만 새 파일을 만든다. 경계 행렬(`component-dependency.md` §1)을 어기는 import는 `test_boundaries`가 막는다.
- 유닛마다 오프라인 전체 테스트(pytest + vitest) GREEN, ruff/black/tsc clean, PBT blocking 규칙(02/03/07/08/09) 확인 뒤 승인 요청.
- 유닛마다 커밋 하나(또는 PR). 스키마는 `init-schema --play` 재실행으로 재생성(마이그레이션 없음, Q4=A).

# Application Design — Purpose Restructure (2026-09-29)

**원하시는 것**: 월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG로 Locus를 다시 짜는 것(포트폴리오·데모).
**지금 하는 것**: Application Design — 경계·컴포넌트·서비스·의존을 확정한다. 이 문서는 `components.md`, `component-methods.md`, `services.md`, `component-dependency.md`를 한 장으로 묶은 것이다. Units Generation이 이 설계를 유닛 7개로 나눈다.

## 1. 설계 결정 (AD-R1~R8)

| ID | 결정 | 결과 |
|---|---|---|
| AD-R1 | **A** 다섯 패키지 | `locus/{shared,knowledge,world,play,localization}` — 최상위 5개 |
| AD-R2 | **A** 경계별 wiring + 타입 컨테이너 | `assemble_<boundary>() -> <Boundary>Container`, 라우터는 `Depends` |
| AD-R3 | **A** Protocol 분할, PG 어댑터 하나 | play 포트 7개 + `PlayUnitOfWork`; `PostgresPlayRepository` 하나 |
| AD-R4 | **A** GM 파사드 제거 | 라우터가 단일 책임 서비스를 직접 받음 |
| AD-R5 | **B** 턴 엔진이 행동을 입력으로 | `TurnAdvancer.advance(session_id, action \| None)` 단일 진입점 |
| AD-R6 | **A** 접두어 넷 | `/api/world`, `/api/knowledge`, `/api/play`, `/api/gm` |
| AD-R7 | **A** hearsay | `ScopeType.HEARSAY`, `ConsensusView.hearsay`, `path_decay` |
| AD-R8 | **A** react-router 화면 3개 | `/editor/:worldId`, `/play/:sessionId`, `/gm/:sessionId` (+ `/` 월드 목록) |
| AD-R9 (변경) | **B + NPC 판단** 자동 행적(도착·발언) + 자유 텍스트 선언; **소문 가치는 대화한 NPC가 정함** | `Deed`, `DeedAppraisal`, `Declare(text)`, `GmNarrator`, `NpcDialogueService.appraise` — 판단 없는 행적은 소문이 되지 않음(A-6) |
| AD-R10 (변경) | **A** 토폴로지를 따라 턴마다 왜곡되며 전파 | `plan_spread`(순수) + `RumorService.spread`; `origin_kind=deed`만 전파, 캐노니컬 기원은 hearsay가 담당 |

## 2. 패키지 트리

```
locus/
├── __init__.py, __main__.py            CLI: world build|import|export|demo, init-schema [--world|--play|--localization]
├── shared/
│   ├── models/    enums.py graph.py(+NPC) io.py(+WorldSnapshot) reports.py(+ImportReport) util.py(clamp01)
│   ├── config/    settings.py tuning.py(WorldTuning KnowledgeTuning PlayTuning LocalizationSettings)
│   ├── llm/       base.py factory.py openai_provider.py retry.py
│   └── storage/   base.py neo4j_repo.py opensearch_repo.py graph_mapping.py persistence.py schema.py sql.py
├── knowledge/     consensus.py propagation.py loader.py cache.py query.py wiring.py
├── world/
│   ├── ingestion/ topology/ ontology/ wiki/ augmentation/
│   ├── build.py(WorldBuilder) editor.py(WorldEditor) npc_drafts.py
│   ├── worldfile/ schema.py export.py import_.py
│   ├── demo/      __init__.py(DemoWorlds) aldermoor.world.json
│   └── wiring.py
├── play/
│   ├── models.py ports.py
│   ├── storage/   postgres_repo.py memory_repo.py schema.py
│   ├── session_service.py distortion_service.py region_knowledge.py
│   ├── player/    movement.py actions.py play_service.py
│   ├── turn/      advancer.py guard.py changes.py
│   ├── rumor/     service.py generator.py dynamics.py promotion.py feedback.py
│   ├── event/     service.py suggester.py dynamics.py
│   ├── npc/       scope.py dialogue_service.py prompts.py
│   └── wiring.py
└── localization/  models.py ports.py translator.py service.py storage/(postgres_repo.py memory_repo.py schema.py) wiring.py
api/               main.py deps.py schemas.py routers/{world,knowledge,play,gm}.py
web/src/           App.tsx routes/ features/{editor,play,gm}/ api/{world,knowledge,play,gm}.ts i18n/ ui/
tests/             test_boundaries.py + 경계별 디렉터리(shared/ knowledge/ world/ play/ localization/ api/)
```

## 3. 경계 개요

| 경계 | 한 줄 | 저장소 | 핵심 컴포넌트 |
|---|---|---|---|
| **shared** | 모델·설정·포트·어댑터 | Neo4j·OpenSearch 어댑터 | S1 models(+NPC, hearsay), S2 Tuning, S3 llm, S4 storage, S5 sql |
| **knowledge** | 지역별 "아는 것"을 계산하는 순수 읽기 코어 | 읽기 전용 | K1 consensus, K3 loader, **K4 WorldCache**, K5 QueryEngine(`region_known`, `region_briefs`) |
| **world** | 월드를 만들고 고치고 저장·로드 | Neo4j·OpenSearch 쓰기 | W6 WorldBuilder(교체 빌드), W7 WorldEditor, W5 Augmentation(run), **W9 WorldFile**, **W10 DemoWorlds**, W8 NpcDrafts |
| **play** | 세션·플레이어·턴·소문·사건·NPC 대화·GM 도구 | PostgreSQL(play 테이블) | P4 SessionService, **P6 PlayService**, **P7 TurnAdvancer(action)**, P8 rumor, P9 event, **P12 NpcScope**, **P13 NpcDialogue**, P14 SessionKnowledge |
| **localization** | 번역 캐시(읽기 비차단) | PostgreSQL(translations) | L4 TranslationService |
| **api** | 조립 + 라우터 넷 | – | A1 lifespan 조립, A2 deps, A3 schemas(_ko·이름), A4~A7 라우터 |
| **web** | 화면 셋 | – | F1 라우터, F2 editor, F3 play, F4 gm |

## 4. API 라우터 (요약)

| Router | Prefix | 주요 엔드포인트 | 화면 |
|---|---|---|---|
| world | `/api/world` | `GET /worlds` · `POST /worlds/{w}/build` (multipart) · `POST /worlds/{w}/demo/{name}` · `GET/POST /worlds/{w}/file` (export/import) · `PUT/DELETE regions, connections, knowledge, scopes, npcs` · `GET /worlds/{w}/knowledge/unscoped` · `POST /worlds/{w}/npcs/suggest` · `POST /worlds/{w}/augmentation/runs`, `POST /augmentation/runs/{r}/answer`, `POST .../revert` · `GET /worlds/{w}/priors`, `GET .../prior-refs` | editor |
| knowledge | `/api/knowledge` | `GET /worlds/{w}/regions/{r}` (include_hearsay) · `GET /worlds/{w}/diff` · `GET /worlds/{w}/briefs` | (외부·에디터) |
| play | `/api/play` | `POST /worlds/{w}/sessions` {name,start_region_id} · `GET /worlds/{w}/sessions` · `POST /sessions/{s}/close` · `GET /sessions/{s}/region` · `POST /sessions/{s}/act` · `POST /sessions/{s}/npcs/{n}/start`, `.../say`, `GET .../history` · `GET /sessions/{s}/log` · `GET /sessions/{s}/regions/{r}/knowledge` (FR-F5) | play |
| gm | `/api/gm` | `events` (list/create/suggest?n≤5/approve/resolve/discard) · `rumors` (list/generate/regenerate/support) · `distortions` (list/set) · `POST /sessions/{s}/advance` · `GET /sessions/{s}/timeline` · `GET /sessions/{s}/state` | gm |

정확한 경로·DTO는 각 유닛 FD와 Code Generation에서 확정하며, 프론트 타입은 OpenAPI에서 생성한다(F5).

## 5. 용어 매핑 (옛 → 새)

| 옛 | 새 | 이유 |
|---|---|---|
| `ConsensusView.rumors`, `include_rumors`, `KnowledgeView.is_rumor`(캐노니컬) | `hearsay`, `include_hearsay`, `is_hearsay` | rumor는 세션 소문에만 |
| `KnowledgeView.distortion_degree` | `path_decay` | 세션 왜곡도와 구분 |
| `AugmentationSession`, `SessionStatus`(보강), `SessionStore` | `AugmentationRun`, `RunStatus`, `RunStore` | session은 게임 세션에만 |
| `SourceKind.SESSION_RUMOR/SESSION_EVENT` | `SIMULATION`, `DIALOGUE` | 경계 중립 |
| `KnowledgeView.statement_ko/title_ko`, `SessionRumor.statement_ko`, `SessionEvent.description_ko` | `api/schemas`의 `*_ko` | 도메인 모델 청결 |
| `PipelineOrchestrator` / `GraphEditor` / `Exporter` | `WorldBuilder` / `WorldEditor` / `WorldFileExporter` | 역할이 드러나는 이름 |
| `commonsense_wiki` | `world.wiki` | 경계 안 |
| `SessionRepository`, `postgres_session_repo` | `play.ports.*Store` + `PlayUnitOfWork`, `play.storage.postgres_repo` | 분할·이동 |
| `GameMasterService` | (제거) | 파사드 |
| `SessionQueryEngine`, `canonical_known` | `SessionKnowledgeService`, `QueryEngine.region_known` | 일반화 |
| `advance_turn(session_id)` | `TurnAdvancer.advance(session_id, action=None)` | 행동 입력 |
| `locus/demo.py`, `examples/demo_world` | `world/demo/` (패키지 내 World File) + `examples/`는 원자료 보관 | Docker에서 동작 |

## 6. 의존 규칙과 조립
- 허용: `knowledge→shared`, `world→knowledge→shared`, `play→knowledge→shared`, `localization→shared`, `api→전부`. `world↔play` 금지, `play→localization` 금지(번역은 API 계층). `tests/test_boundaries.py`가 검사한다.
- 조립: `assemble_shared(settings)` → `assemble_knowledge(shared)` → `assemble_world(shared, knowledge)` / `assemble_play(shared, knowledge)` / `assemble_localization(shared)`. `create_app`은 lifespan에서 조립하고, 넘겨받은 컨테이너는 그대로 쓴다. 한 경계 조립 실패 = 그 라우터만 503.
- 트랜잭션: PostgreSQL 쓰기는 `PlayUnitOfWork` 하나로; LLM 호출은 트랜잭션 밖; 턴 진행은 세션당 하나(`TurnGuard`, 단일 워커 전제).
- 캐시: `WorldCache`는 world의 쓰기 서비스만 무효화한다. play는 읽기만.

## 7. 새 컴포넌트 목록 (신규만)
K4 WorldCache · W8 NpcDraftService · W9 WorldFile(schema/export/import) · W10 DemoWorlds · W11/K6/P15/L5 wiring · S5 sql · P1 Player/Conversation/PlayerAction/ActionResult · P2 ports + UoW · P5 movement · P6 PlayService · P7 TurnGuard · P12 NpcScope · P13 NpcDialogueService · **P16 Deed/DeedAppraisal/DeedService · P17 GmNarrator · P19 plan_spread** (변경 2026-09-29) · A2 deps · A3 schemas · A5 knowledge router · A7 gm router · F1 routes · F2 editor feature · F3 play feature(+ActionBar 선언·NarrationCard) · F4 DeedPanel · `tests/test_boundaries.py`.

## 7b. 변경 (2026-09-29): 플레이어 행적이 소문이 된다 — 레거시 Locus와 갈라지는 지점
- **왜**: 사용자 피드백. 지금까지 소문 원천은 캐노니컬 지식과 사건뿐이라 플레이어는 관찰자였다. 이제 플레이어의 도착·발언·선언 행동이 **행적(Deed)**으로 남고, **대화한 NPC가 그것을 전할지(noteworthy)·얼마나(salience)·어떤 시각으로(slant)·어떤 문장으로(retelling) 정한다**. 전하기로 한 행적은 그 NPC의 지역에서 소문으로 태어나 토폴로지를 따라 턴마다 더 왜곡되며 퍼진다.
- **어디가 바뀌나**: play 경계 안에서만. `deeds/`(P16), `gm/narrator.py`(P17), `rumor/spread.py`(P19), `TurnAdvancer` 두 단계 추가(행적 씨앗 → 전파), `PlayerAction.Declare`, `SessionRumor.origin_kind`, 포트 8개(`DeedStore`), gm 라우터 행적 엔드포인트, play 화면 선언 입력, gm 화면 행적 패널. 경계 행렬은 변하지 않는다.
- **지키는 것**: 캐노니컬 불변(행적은 세션 레이어), 캐노니컬 기원 소문은 전파하지 않음(hearsay와 중복 금지), 모든 새 LLM 호출은 턴 예산 안, 재생성은 세션 기원 소문을 지우지 않음, 판단 없는 행적은 소문이 되지 않음(A-6), 선언은 판정 없이 서술만(A-7).
- **문서 반영**: 요구사항 부록 A(FR-C8·C9·C10·E7·D6), 스토리 +5(US-4.4·4.5·5.6·6.5·8.6 → 48), 페르소나 P-Player·P-GM 보강, 설계 4문서 "변경" 절.
- **FD로 넘기는 것 추가**: 판단 프롬프트와 salience 기준, 탄생 지지도 보정식, `spread_min_weight`·지역당 전파 상한 값, 발언 요약 규칙, 선언 서술 프롬프트, 취소 시 전파 소문 처리 상세.

## 8. 커버리지 검증

### FR-A (경계)
| FR | 충족 |
|---|---|
| A1 다섯 경계 | §2 트리 |
| A2 역방향 의존 제거 | §6 규칙 + `component-dependency.md` §5 매핑 + boundaries 테스트 |
| A3 경계별 조립 | AD-R2, A1·A2 |
| A4 어댑터 위치·포트 분할 | P2·P3, L2 |
| A5 용어 분리 | §5 |
| A6 API 경로 | §4 |
| A7 조정값 집약 | S2 Tuning |

### 스토리 E7 (읽히는 구조)
US-7.1(배치·용어·접두어) §2·§4·§5 · US-7.2(의존 방향·조립·포트·스키마 분리) §6, P2, S4 · US-7.3(진행 중 표시) W12 · US-7.4(테스트 GREEN) 이동 규칙 = 동작 불변 유닛 U1 · US-7.5·7.6은 U7.

### 스토리 E2~E6 → 컴포넌트
E2 편집 → W1·W6·W7·W8·W5·W4·W9·W10 + A4 + F2 · E3 이동 → P4·P5·P6·P7 + A6 + F3 · E4 대화 → P12·P13·P14 + A6 + F3 · E5 GM → P7·P9·P8·P10·P11 + A7 + F4 · E6 저장·다시 보기 → W9·W7(list_worlds)·P13 + A4 · E8 안정화 → P7(가드·예산)·P8·P9 · E9 언어 → L1~L5 + A3.

### RE 부채
`component-dependency.md` §5 표 — 항목 15개 모두 새 위치가 있다.

## 9. Functional Design으로 넘기는 것
- 이동 비용 공식과 파라미터(P5), blocked 처리(A-2 확정됨).
- 소문 상한·씨앗 제외·LLM 예산 규칙과 값(P7·P8), 승격 면제 축소 규칙(P8 dynamics).
- NPC 프롬프트 가드 문구, 컨텍스트 크기 제한, 대화 이력 N(P12·P13).
- World File v1 필드 상세와 버전 정책(W9), 삭제 cascade 정책(W7).
- 합의 특이점 A10 규칙(K1), 지역 이름 충돌 규칙 A11(W2).
- 데모 월드 콘텐츠(W10).
- 프론트 컴포넌트 상세(F2~F4).

## 10. Extension Compliance (Application Design)
- Security Baseline: 비활성 — N/A.
- PBT (Partial): 이 단계에 blocking 규칙 없음. 순수 컴포넌트(K1, K2, P5, P11, P12, W9 왕복)를 PBT 대상으로 표시했다 — compliant.

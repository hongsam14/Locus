# API Documentation

> Reverse Engineering — Follow-up Cycle (2026-10-07). 기준 커밋 `240e82d`. 2026-09-29 판을 대체한다. 그 판의 `/api/query`·`/api/authoring` 구성(34개)은 더 이상 없다.
> 라우트 수는 OpenAPI에서 뽑았다: **77개**, 인증 없음. 경로는 저장소 루트 기준이다.

## REST APIs

### 오류 형식 (`api/errors.py`, `api/deps.py`, `api/main.py`, `api/uploads.py`)
- 기본은 `{"detail": "<문자열>"}`이다.
- 매핑:
  - **503**: `ExecutorShutdownError`, `LlmUnavailableError`, `LlmCallFailedError`.
  - **409**: `SessionClosedError`, `WorldExistsError`, `BuildInProgressError`, `TurnInProgressError`, `AugmentationConflict`, `SeedAlreadyRunningError`.
  - **404**: `LookupError`(KeyError 포함).
  - **422**: `UnsupportedWorldFile`.
  - **400**: `ValueError`(`InvalidActionError`, 서비스 안 pydantic `ValidationError` 포함).
  - 그 밖은 500이다. play·gm 라우터는 `PLAY_ERRORS`만 잡는다.
- 경계가 없으면 `{"detail": "<name> boundary unavailable"}`(503), 서비스가 없으면 `{"detail": "<name> unavailable"}`(503)이다.
- 409 객체 detail:
  - 월드 교체 관문: `{message, open_sessions | busy_sessions, session_ids}`.
  - 지역 삭제: `{message, session_ids}`.
- 422: `{"detail": [pydantic 오류…]}`. NaN·Inf·bytes는 글로 바꿔 되돌린다. 외톨이 서로게이트는 500이 된다(RE-P12).
- 413: `{"detail": "request body too large (limit N MiB)"}` 또는 칸별 문장.
- 표시 언어 `?lang=`: 없으면 `TRANSLATION_TARGET_LANG`(기본 ko)이고, `SUPPORTED_LANGS`에 없으면 400이다. 응답의 `*_ko` 칸은 캐시에 있을 때만 채워진다. 이름과 달리 "기본 대상 언어" 칸이다(RE-P14).

### 메타 (`api/main.py`)
| M | 경로 | 목적 | 응답 |
|---|---|---|---|
| GET | `/health` | 경계 상태 | `{status: ok\|degraded, boundaries:{world,knowledge,play,localization}}`. 전부 없으면 503 |
| GET | `/api/capabilities` | 공급자 유무 | `{llm, vlm, embedding}` |
| GET | `/api/langs` | 표시 언어 | `{default, supported[]}` |

### `/api/play` (`api/routers/play.py`)
| M | 경로 | 목적 | 입력 | 응답 | 오류 |
|---|---|---|---|---|---|
| POST | `/worlds/{w}/sessions` | 세션 시작 | 본문 없음(GM 세션) 또는 `PlayerCreate{name 1..40, start_region_id}` | 200 `GameSession` / 201 `SessionStartOut{session, player}` | 404 월드 없음·빈 월드, 400 시작 지역 없음 |
| GET | `/worlds/{w}/sessions` | 세션 목록 | – | `list[GameSession]` | 없는 월드도 `[]` |
| GET | `/sessions/{s}` | 세션 | – | `GameSession` | 404 |
| POST | `/sessions/{s}/close` | 닫기(멱등) | – | `GameSession` | 404, 409 턴 중 |
| GET | `/sessions/{s}/player` | 플레이어 | – | `Player` | 404 |
| GET | `/sessions/{s}/region` | 플레이어 화면 | `?lang` | `RegionViewOut`(사실·전해 들음·활성 소문·이동 선택지·NPC·`turn_running`·`llm_available`·`declare_max_chars`) | 404 세션·지역 사라짐, 400 플레이어 없음 |
| POST | `/sessions/{s}/act` | 행동 | `?lang`, `{"type": move\|wait\|end_talk\|declare, …}` | 202 `TurnRun`(running) | 400 검증, 404, 409 닫힘·턴/GM 보유, 503 실행기 종료 |
| GET | `/sessions/{s}/turn-runs` | run 목록 | `?status`(검증 없음) | `list[TurnRun]` | 404 |
| GET | `/sessions/{s}/turn-runs/{id}` | run 조회(폴링) | – | `TurnRun`(result=`ActionResult`) | 404 |
| GET | `/sessions/{s}/log` | 플레이어 여정 기록 | `?limit` 1..1000 | `list[TimelineEntry]` | 404 |
| GET | `/sessions/{s}/regions/{r}/knowledge` | 세션 지역 지식 | `?lang` | `QueryResultOut` | 404 |
| GET | `/sessions/{s}/npcs` | 지금 지역 NPC | – | `list[NpcSummaryOut{npc, has_conversation, message_count}]` | 404, 400 |
| POST | `/sessions/{s}/npcs/{n}/start` | 대화 열기(LLM 없음) | – | `Conversation` | 404, 400 다른 지역, 409 닫힘 |
| POST | `/sessions/{s}/npcs/{n}/say` | 한 줄 | `?lang`, `SayIn{text}`(≤500) | `NpcReply{message, lang, llm_calls=1, context_ids}` | 400, 404, 409, 503 LLM 없음·호출 실패 |
| GET | `/sessions/{s}/npcs/{n}/history` | 대화 기록 | – | `Conversation` | 404 |

### `/api/gm` (`api/routers/gm.py`) — ✱ = GM 리스 `_idle`(턴 중이면 409, GM끼리는 공유)
| M | 경로 | 목적 | 입력 | 응답 |
|---|---|---|---|---|
| GET | `/sessions/{s}/timeline` | 전체 타임라인(상한 없음) | – | `list[TimelineEntry]` |
| GET | `/sessions/{s}/regions/{r}/rumors` | 지역 활성 소문 | `?lang` | `list[RumorOut]` |
| POST ✱ | `/sessions/{s}/regions/{r}/rumors` | 소문 생성(LLM, 상한을 보지 않음) | – | `list[RumorOut]` |
| POST ✱ | `/sessions/{s}/regions/{r}/rumors/regen` | 재생성(승격·행적 소문 보존) | – | `list[RumorOut]` |
| PUT ✱ | `/sessions/{s}/rumors/{id}/support` | 지지도 | `SupportUpdate{support}`(clamp) | `RumorOut` |
| PUT ✱ | `/sessions/{s}/regions/{r}/distortion` | 왜곡도 설정 | `DistortionUpdate{degree}`(clamp) | `RegionDistortion` |
| GET | `/sessions/{s}/state` | 지도 겹쳐 보기 | – | `WorldState` |
| GET | `/sessions/{s}/distortions` | 왜곡도 목록 | – | `list[RegionDistortion]` |
| POST | `/sessions/{s}/advance` | 수동 턴(요청 스레드에서 동기) | – | `TurnResult` |
| GET | `/sessions/{s}/events` | 사건 목록 | `?status`, `?lang` | `list[EventOut]` |
| POST ✱ | `/sessions/{s}/events` | 사건 생성 | `EventCreate{region_id, category, description, magnitude, lifecycle?}` | `EventOut` |
| GET | `/sessions/{s}/seeds` | 씨앗 목록 | – | `list[SeedView]` |
| POST ✱ | `/sessions/{s}/seeds/{id}/start` | 씨앗 시작 | – | 201 `EventOut`(진행 중이면 409, 겹치면 둘 다 201 — #12) |
| POST ✱ | `/sessions/{s}/events/suggest` | LLM 제안 | `?n` 1..5 | `list[EventOut]`(SUGGESTED) |
| POST ✱ | `/sessions/{s}/events/{e}/approve` | 승인 | – | `EventOut` |
| POST ✱ | `/sessions/{s}/events/{e}/resolve` | 해소·복원(멱등) | – | `EventOut` |
| DELETE ✱ | `/sessions/{s}/events/{e}` | 제안 폐기 | – | 204 |
| GET | `/sessions/{s}/deeds` | 행적 보기 | `?lang` | `list[DeedViewOut]` |
| POST ✱ | `/sessions/{s}/deeds/{d}/void` | 행적 취소(멱등) | – | `VoidResult` |

### `/api/knowledge` (`api/routers/knowledge.py`)
| M | 경로 | 목적 | 입력 | 응답 |
|---|---|---|---|---|
| GET | `/worlds/{w}/regions/{r}` | 캐노니컬 지역 지식 | `?include_hearsay`, `?lang` | `QueryResultOut` |
| GET | `/worlds/{w}/diff` | 두 지역 비교 | `region_a`, `region_b` | `RegionDiff` |
| GET | `/worlds/{w}/briefs` | 지역 brief | `?top_k` 0..20 | `list[RegionBrief]` |

### `/api/world` (`api/routers/world.py`, `world_editor.py`)
| M | 경로 | 목적 | 응답 | 주요 오류 |
|---|---|---|---|---|
| POST | `/worlds/{w}/build` (`?replace&confirm`, `WorldInputs`) | 빌드 | `BuildReport` | 503 LLM, 409 열린 세션·턴 중·빌드 중·있음 |
| POST | `/worlds/{w}/build/upload` (multipart) | 업로드 빌드 | `BuildReport` | 413, 422, 409, 503 |
| GET | `/worlds/{w}/graph` | 그래프 요약 | `GraphSummary` | 503 |
| GET | `/worlds` | 월드 목록(+열린 세션 수) | `list[WorldInfo]` | 503 |
| GET | `/worlds/{w}/export` | World File + `world_id` + `unscoped_knowledge_ids` | dict | 404 |
| GET | `/worlds/{w}/file` | World File 내려받기 | 첨부 | 404 |
| POST | `/worlds/{w}/file` (`?replace&confirm&remap`) | World File 불러오기 | `ImportReport` | 422, 409, 413(21 MiB) |
| POST | `/worlds/{w}/file/upload` | 같은 것(multipart) | `ImportReport` | 413, 422, 409 |
| GET | `/demos` | 매니페스트 데모 | `list[DemoInfoOut]` | 503 |
| POST | `/worlds/{w}/demo/{name}` (`?replace&confirm`) | 데모 불러오기(LLM 없음) | `ImportReport` | 404, 409 |
| POST | `/worlds/{w}/demo/{name}/build` (`?replace&confirm&with_map`) | 데모 소스로 빌드 | `BuildReport` | 404, 409, 503 |
| POST/GET | `/worlds/{w}/priors` | prior 저장·목록 | `WikiPrior` / list | 400, 503 |
| GET | `/worlds/{w}/related-priors` (`?query&k`) | 교차 월드 prior(진행 중, 늘 0건) | list | 503 |
| GET | `/worlds/{w}/prior-refs` | prior 인용 지도 | `PriorRefsOut` | 404 |
| DELETE | `/worlds/{w}/priors/{p}` | prior 삭제 | 204 | 404 |
| POST | `/worlds/{w}/augmentation/runs` | 보강 run 시작 | `AugmentationRun` | 404 |
| GET | `/augmentation/runs/{id}` | run 조회 | `AugmentationRun` | 404(재시작하면 사라짐) |
| POST | `/augmentation/runs/{id}/answer` | 답 | `AnswerResult` | 400, 404, 409 |
| POST | `/augmentation/runs/{id}/revert` (`?change_id`) | 되돌리기(최신부터) | `AugmentationRun` | 400, 404, 409 |
| POST | `/augmentation/runs/{id}/unignore` | 다시 묻기 | `AugmentationRun` | 409 |
| GET | `/worlds/{w}/regions/{r}/editor` (`?lang`) | 인스펙터 보기 | `EditorRegionViewOut` | 404 |
| POST/PUT | `/worlds/{w}/regions`, `/worlds/{w}/regions/{r}` | 지역 추가·교체 | 201/200 `Region` | 400, 404 |
| GET | `/worlds/{w}/regions/{r}/delete-plan` | 삭제 계획 | `RegionDeletePlan`(+`blocked_by_sessions`) | 404 |
| DELETE | `/worlds/{w}/regions/{r}` | 지역 삭제 | `RegionDeleteReport` | 409 플레이어가 선 지역·턴 중, 404 |
| PUT/DELETE | `/worlds/{w}/connections` (`ConnectionSave` / `?a&b&kind`) | 연결 저장·삭제 | `list[ConnectionEdge]` / `{deleted}` | 400, 404 |
| POST | `/worlds/{w}/regions/{r}/knowledge` | 지식 추가 | 201 `Knowledge` | 400, 404 |
| PUT/DELETE | `/worlds/{w}/knowledge/{k}` | 지식 교체·삭제 | `Knowledge` / 204 | 400, 404 |
| PUT | `/worlds/{w}/knowledge/{k}/scopes` | 스코프 지정 | `{region_ids}` | 400, 404 |
| GET | `/worlds/{w}/knowledge/unscoped` (`?lang`) | 스코프 없음 목록 | `list[LocalizedKnowledge]` | 404 |
| POST/PUT/DELETE | `/worlds/{w}/npcs`, `/worlds/{w}/npcs/{n}` | NPC 추가·교체·삭제 | 201 `NPC` / `NPC` / 204 | 400, 404 |
| POST | `/worlds/{w}/regions/{r}/npc-drafts` (`?n`) | NPC 초안(LLM 1, 저장 안 함) | `NpcDraftResult` | 503, 400, 404 |

### 업로드 한도 (`api/uploads.py`)
- `BodyLimitMiddleware`(순수 ASGI): World File 경로는 21 MiB(20 + 1), 나머지는 48 MiB다. `Content-Length`가 넘으면 바로 413이고, 없으면 받는 동안 센다.
- 라우터 안의 칸 검사: 개수·크기·메모 글자 수는 413, 이미지 매직 바이트(PNG/JPEG/WebP)가 맞지 않으면 422다.
- `WorldInputs`: 메모 ≤20 × 60,000자, 지도 그림 ≤4, 구조화 지도 ≤5, 컨셉 아트 ≤8, 그림 base64 ≤8 MiB.

## Internal APIs

### 캐노니컬 포트 (`locus/shared/storage/base.py`, `locus/shared/llm/base.py`, `locus/localization/ports.py`)
- **`GraphRepository`**:
  - 연결·스키마: `connect/disconnect/health_check/ensure_schema`.
  - 쓰기: `upsert_nodes`(MERGE + `SET +=`), `upsert_edges`, `replace_nodes`(`SET =`), `replace_edges`, `delete_edges(world_id, keys)`.
  - 읽기: `edges_touching(world_id, node_ids, types)`, `get_node(world_id, id)`(라벨 없음), `find_nodes(world_id, label, filters)`, `get_edges(world_id, types)`.
  - 삭제·목록: `delete_node(world_id, id)`(라벨 없음, DETACH), `delete_world`, `list_world_ids`.
  - 엣지 identity: 속성 `id`가 있으면 그것, `CONNECTED_TO`면 `kind`, 그 밖은 끝점 쌍이다.
- **`SearchRepository`**: `index(docs)`, `hybrid_search(world_id|None, text, embedding, k, filters)`, `delete(world_id, ids)`, `delete_world`.
- **`LLMProvider`**: `complete(prompt, *, system)`, `structured(prompt, schema, *, system)`. **`VLMProvider`**: `analyze_image(bytes, prompt)`. **`EmbeddingProvider`**: `dimension`, `embed(texts)`.
- **`TranslationStore`**: `get_many(keys, target_lang)`, `upsert_many`, `purge(*, kind, ids, world_id, session_id)`.
- **`SnapshotSource`** `get(world_id)`, **`SnapshotCache`** `invalidate(world_id)`, **`RunStore`** `save/get`.

### 플레이 포트 (`locus/play/ports.py`)
| Protocol | 메서드 |
|---|---|
| `PlayStorage` | `connect`, `disconnect`, `health_check`, `ensure_schema` |
| `SessionStore` | `create_session`, `get_session`, `list_sessions`, `close_session`(멱등), `bump_turn` |
| `RumorStore` | `upsert_rumor(s)`, `get_rumor`, `list_rumors(region?, include_pruned)`, `list_rumors_by_origin(deed?, include_inactive)` |
| `DistortionStore` | `set_region_distortion(…, feedback_share)`, `get_region_distortion`, `list_region_distortions` |
| `TimelineStore` | `append_timeline`, `list_timeline` |
| `EventStore` | `create_event`, `get_event(for_update)`, `list_events(status?, for_update)`, `update_event`, `update_event_contributions(…, status)`, `delete_event` |
| `PlayerStore` | `create_player`, `get_player`, `update_player` |
| `TurnRunStore` | `create_run`, `get_run`, `update_run`, `list_runs`, `fail_stale_runs` |
| `ConversationStore` | `create_conversation`, `get_conversation`, `append_message`, `list_conversations`, `message_counts` |
| `DeedStore` | `record_deed`, `get_deed`, `list_deeds(…)`, `update_deed`, `save_appraisals`, `list_appraisals`, `mark_seeded`, `seed_candidates`, `delete_by_run` |
| `PlayUnitOfWork` | 위 9개 저장소를 속성으로 가지고, 정상이면 커밋, 예외면 롤백한다 |
| `PlayRepository` | 위 전부의 합집합 + `uow()` |

- `PostgresPlayRepository`: 공개 메서드마다 자기 트랜잭션을 연다. 그래서 UoW 밖의 `for_update`는 무시된다. `uow()`는 연결 하나에 묶인 `_PgStores`다.
- 인메모리 쌍둥이: 메서드마다 RLock을 쓰고, UoW 동안 깊은 복사를 해 두었다가 예외면 복원한다.

### 서비스·조립
- `assemble_shared(settings, *, graph, search, llm, sql, strict)` → `SharedContainer`.
- `assemble_knowledge` → `KnowledgeContainer(loader, cache, query, params)`.
- `assemble_world` → `WorldContainer(cache, editors, exporter, importer, demo, catalog, builder?, augmentation, npc_drafts?, wiki_admin, cross_world)`.
- `assemble_play` → `PlayContainer(repo, sessions, distortions, world_state, region_knowledge, feedback, turns, play, guard, executor, rumors, events, seeds, dialogue, deeds)`.
- `assemble_localization` → `LocalizationContainer(translations?, executor?)`.
- API는 `Containers{shared, knowledge, world, play, localization, owned}`를 `Depends(get_*)`로 받는다.
- 턴 진입점 `TurnAdvancer.advance(session_id, action|None)`(동기)와 `begin`(배경).

## Data Models

### 캐노니컬 도메인 모델 (`locus/shared/models/graph.py`, `LocusModel`: `extra="forbid"`, `use_enum_values=True`)
| 모델 | 필드 |
|---|---|
| `Region` | `id`, `world_id`, `name`, `level`(continent/province/town/district/terrain), `parent_id`, `description`, `attributes`(자유 dict — 빌드 힌트가 남음, RE-W05), `position: Coord{x,y∈[0,1]}`, `provenance` |
| `Entity` | `id`, `world_id`, `name`, `entity_type`, `description`, `confidence`, `located_in`, `provenance` |
| `Relation` | `id`, `source_id`, `target_id`, `relation_type`, `confidence` |
| `Knowledge` | `id`, `statement`, `title`(필수), `topic`, `confidence`, `is_global`, `region_hint`, `about_entity_ids`, `derived_from_prior_ids`, `provenance` |
| `WikiPrior` / `WikiPriorLink` | `prior_type`, `condition`, `effect`, `domains`, `confidence` / `source_id`, `target_id`, `relation`, `weight`, `cross_domain` |
| `ConnectionEdge` | `source_region_id`, `target_region_id`, `kind`(adjacent/route/river/blocked), `weight∈[0,1]`, `rationale`, `wiki_prior_ref` |
| `ScopeLink` | `knowledge_id`, `region_id`, `scope_type`(저장은 DIRECT만), `confidence`, `is_rumor`(옛 필드) |
| `WorldMeta` | `id`(=world_id), `name`, `description`, `format_version`, `updated_at`, `last_writer∈{build,import,edit}` |
| `NPC` | `id`, `name`, `role`, `description`, `home_region_id`, `traits` |
| `EventSeed` | `id`, `region_id`, `title`(1~80), `description`(≤500), `category`, `magnitude`, `lifecycle?` |
| `WorldSnapshot` | `meta`, `kg`(엔티티·관계·지식·스코프·prior·링크), `topo`(지역·연결), `npcs`, `event_seeds`, `load_warnings` + 색인(`regions_by_id/name`, `npcs_by_region`) |
| 합의 뷰 | `KnowledgeView(scope_type, is_hearsay, path_decay, distortion, source, region_id)`, `ConsensusView`(direct/inherited/global/propagated/hearsay + `unknown_count`), `QueryResult`, `RegionDiff`, `RegionBrief` |

### Neo4j
- **라벨 7종**: `Region`, `Entity`, `Knowledge`, `WikiPrior`, `NPC`, `EventSeed`, `WorldMeta`. 중첩 필드는 JSON 문자열이고, provenance는 `prov_*`로 평탄화한다.
- **관계 9종**: `CONTAINS`(부모→자식), `CONNECTED_TO`(양방향 쌍, identity=kind), `SCOPED_TO`, `ABOUT`, `DERIVED_FROM`, `RELATED_TO`(identity=id), `LOCATED_IN`, `PRIOR_RELATED_TO`, `LIVES_IN`.
  - 로더는 이 가운데 CONNECTED_TO·SCOPED_TO·RELATED_TO·PRIOR_RELATED_TO·LIVES_IN만 읽는다. 나머지는 속성과 중복 저장된다(RE-W11).
- **제약·인덱스**: 라벨마다 `id IS UNIQUE`(월드를 넘어 전역)와 `world_id` 인덱스가 있다. (world_id, id) 복합 키는 없다.

### OpenSearch
- 단일 인덱스 `OPENSEARCH_INDEX`(기본 `locus_search`): shards 1, replicas 0.
- 매핑: `id`/`world_id`/`label` keyword, `text` text, `embedding` knn_vector(1536, HNSW, cosinesimil, nmslib), `meta` object.
- 문서 `_id`는 노드 id다(접두 없음, RE-W15). label은 Knowledge·Entity·WikiPrior·NPC다.
- 질의는 bool이다: world_id filter + match text + knn.

### PostgreSQL — 세션 (`locus/play/storage/schema.py`, FK 없음, JSON은 PG에서 JSONB)
| 테이블 | 키·제약 | 주요 열 |
|---|---|---|
| `game_sessions` | PK id | world_id, status, turn, created_at, closed_at |
| `session_rumors` | PK id | session_id, region_id, distorted_from_id/kind, statement, distortion_degree, support, confidence, promoted, active, provenance, origin_kind, origin_deed_id, origin_appraisal_id, spread_from_region_id |
| `region_distortions` | PK (session_id, region_id) | distortion_degree, feedback_share |
| `timeline_entries` | PK id | session_id, turn, kind, summary, payload, created_at(앱 단조 시각) |
| `session_events` | PK id | session_id, region_id, category, description, magnitude, lifecycle, status, created_turn, resolved_turn, contributions, provenance |
| `players` | PK id, UNIQUE session_id | name, region_id, turns_spent |
| `turn_runs` | PK id | session_id, status, action, cost_turns, started_turn, result, error, lang, turns_charged, from_region_id |
| `conversations` | PK id, UNIQUE (session_id, npc_id) | started_turn |
| `messages` | PK id | conversation_id, role, text, lang, turn |
| `deeds` | PK id | session_id, player_id, region_id, turn, kind, text, declaration, messages_through, witnessed_npc_ids, voided, voided_turn, run_id |
| `deed_appraisals` | PK id, UNIQUE (deed_id, npc_id) | noteworthy, salience, slant, retelling, turn, seeded_rumor_id, run_id |

- **잠금**: `SELECT … FOR UPDATE`는 두 곳뿐이다. 해소가 잠그는 사건 한 행, 그리고 GM 왜곡도 설정이 잠그는 ACTIVE 사건 전부다. 지역 왜곡도·소문·행적 행은 잠그지 않는다.
- **트랜잭션 경계**: UoW 16곳이다. 나머지 쓰기는 호출마다 자기 트랜잭션이다(RE-P05).
- 오래된 DB를 위해 열 10개와 색인 2개를 inspector로 더한다.

### PostgreSQL — 번역 (`locus/localization/storage/schema.py`)
`translations`: PK id, `source_kind`, `source_id`, `source_field`, `target_lang`, `text`, `source_hash`(sha256), `world_id`, `session_id`, `created_at`. 유일 키는 `(source_kind, source_id, source_field, target_lang)`이고, upsert는 `ON CONFLICT … DO UPDATE`다.

### World File v1 (`locus/world/worldfile/schema.py`)
```text
{ format_version: 1, world: {id, name, description?}, exported_at?,
  regions[], connections[], entities[], relations[], knowledge[], scopes[],
  priors[], prior_links[], npcs[], event_seeds[] }
```
- 형식 번호가 없는 옛 export는 v0로 읽는다(5절). 알 수 없는 키는 제거한다.
- 파일 `world.id`가 대상과 다르거나 `remap`이면 모든 id를 `uuid5(NAMESPACE_LOCUS, "{target}:{old}")`로 바꾼다.
- 참조 검증은 끊긴 항목을 error로 버린다. 절 사이 중복 id(#10)와 한 방향 연결(RE-W12)은 보지 않는다.

### 데모 매니페스트 (`locus/world/demo/worlds/manifest.json`)
```text
[ { name: ^[a-z0-9-]{1,40}$, title <=60, description? <=300, file, start_region_id,
    credits? <=200, sources?: { memos[], maps[], map_images[] } } ]
```
검사 항목은 셋이다: 파일을 파싱할 수 있는가, 소스 파일이 있는가, 시작 지역에 막히지 않은 연결이 하나 있는가. `name`과 파일 `world.id`가 같은지는 보지 않는다(#11).

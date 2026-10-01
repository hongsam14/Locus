# U3 월드 에디터 — Code Generation Plan

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3의 코드를 만드는 순서를 정합니다. 단계별로 고정하는 것은 다음과 같습니다.
- 제작자가 자료를 올려 월드를 만들고, 지도에서 지역·연결을 그립니다.
- 지식·스코프·NPC를 고치고, 보강 Q&A로 빈틈을 채우고, wiki 근거를 봅니다.
- World File을 저장·불러오기하고, `/` 월드 목록에서 고릅니다.
- U7에서 넘어온 결함·정리를 함께 닫습니다.

> 근거
> - **FD**: `construction/U3-world-editor/functional-design/*`. 승인 2026-10-01. 검토 02의 R-08·R-11은 Accepted risk이고, 게이트에서 정한 처리로 이 플랜이 닫는다.
> - **NFR**: `construction/U3-world-editor/nfr/nfr-light.md`. 승인 2026-10-01. 검토 01의 R-01~R-08은 Accepted risk이고, 게이트에서 정한 처리로 이 플랜이 닫는다.
> - **U7 코드 리뷰**: `construction/U7-gm-mode-hardening/code/reviews/code-review-01.md` §8. 사람의 선택 A에 따라 다음을 U3로 넘겼다.
>   - §1 #6~#10·#12~#15
>   - §2 정리 C1~C19
>   - §3 12건
>   - §5 문서 메모
> - 아래 이월 표가 두 게이트와 리뷰 이월의 단일 기준이다. 이 플랜이 코드 생성의 단일 기준이다.

---

## 유닛 컨텍스트
- **스토리**: US-2.1~2.8(빌드·지도·지식·NPC·초안·보강·병합·wiki), US-6.2~6.4(World File 저장·불러오기, 월드 목록)
- **의존**
  - U2: World File, `WorldCache`, `persist_graph`, `touch_world_meta`, 교체 확인 규칙
  - U4: `TurnGuard.hold`(GM 리스), `SessionService`, `features/play/NewSessionForm.tsx`
  - U5: `enrich`(번역 붙이기), `purge_translations(loc, *, kind, ids, world_id, session_id)`
  - U7: `WorldTuning`, `one_line`, `conflictKind`, `CommitRange`
- **뒤 유닛이 기대하는 것**: U8은 다음을 데모·배포 문서에 쓴다.
  - `/` 월드 목록과 [데모 불러오기]
  - 빌드 화면
  - 업로드 상한
  - operations.md의 "월드 에디터" 절
- **DB(PostgreSQL)**: 바뀌지 않는다. Q6=A는 기존 `events.contributions`를 고친다.
- **그래프·검색 포트(추가만)**: `GraphRepository.replace_nodes`, `GraphRepository.delete_edges`, `SearchRepository.delete`
- **단계 의존 방향**: 포트(2) → wiki(3) → 편집 패키지(4) → NPC 초안(5) → 보강(6) → U7 이월 백엔드(7) → API(8) → 프론트엔드(9, 10)
  - 편집 패키지의 `ConnectionView`는 wiki의 `PriorRefView`를 쓴다.
  - 보강은 편집 패키지와 wiki의 `fallback=`·`llm=None`을 쓴다.
  - 그래서 wiki를 편집 패키지보다 먼저 만든다.
- **바뀌는 외부 계약**
  1. 새 경로(BLM §7과 Step 1.3의 정정)
     - 에디터 지역 보기
     - 지역 추가·교체·삭제 계획·삭제
     - 연결 저장·삭제
     - 지식 추가·교체·스코프·삭제·스코프 없음
     - NPC 추가·교체·삭제·초안
     - prior 목록·참조·삭제
     - 보강 run 읽기, `unignore`
  2. `DELETE /api/world/worlds/{w}/nodes/{n}`은 없어진다(이탈 2).
  3. `PUT …/regions/{r}`·`PUT …/knowledge/{k}`는 교체 쓰기다. 경로·본문 id가 다르면 400이다.
  4. 보강
     - `answer`는 `AnswerResult`를 준다. ignore면 `change`는 null이다.
     - `revert`는 204 대신 200과 다시 탐지한 `AugmentationRun`을 준다. 거절은 409 셋이다.
     - 질문은 `issue_key`·`target`·`actions`를 싣는다. `options`·`kind`는 없어진다.
     - run은 `issues`·`ignored_keys`·`answers`·`llm_calls`·`llm_budget_exhausted`를 싣는다. `round`는 `answers`가 된다.
     - LLM이 없어도 run을 열 수 있다.
  5. 빌드
     - `BuildReport.priors_created`가 생긴다.
     - `build/upload`에 `concept_arts` 칸이 생긴다.
     - 업로드 상한을 넘으면 413, 이미지 형식이 틀리면 422다.
     - 지도 JSON 422 문구는 예외 문장 없는 고정 문구다.
  6. GM·타임라인
     - `set_distortion` 줄에 `event_contributions_cleared`가 붙는다.
     - `deed_voided` 페이로드에 `region_names`가 붙는다.
     - `rumor_spread` summary가 이름을 쓴다.
     - `GET …/state`의 `WorldState`에 `max_event_suggestions`가 붙는다(U7 #15).
     - GM 값 필드의 NaN·Infinity는 422다(U7 §3).
  7. 플레이: `GET …/log?limit=`(U7 C6)
  8. env: `TOPOLOGY_DEFAULT_BASE`가 없어진다(A3-15).
- **바뀌는 내부 계약** (호출처는 각 단계에 전수로 적는다)
  - `locus/world/editor.py`의 `WorldEditor`는 `locus/world/editor/` 패키지가 된다.
    - 일곱 클래스(domain-entities §2.0)
    - 묶음 `Editors`(`editor/bundle.py`)
  - `WorldContainer.editor` → `editors: Editors | None`과 `catalog: WorldCatalog | None`
  - 보강
    - `AugmentationEngine`·`AugmentationService`의 생성자와 반환형
    - `apply_answer(question, answer, *, world_id, editors)`, `revert(change, *, world_id, editors)`
    - 탐지기 시그니처(`prior_ids` 인자)
  - wiki
    - `CommonsenseWiki(llm=None)` 허용, `lookup_similar(..., fallback=)`, `created_priors`
    - `WikiAdmin.list_priors` 반환형, `prior_refs`·`broken_refs`·`delete_prior`
  - `MATERIAL`이 `shared/text.py`로 옮겨 간다.
  - play
    - `SessionService.open_player_regions`
    - `DistortionService.set_region_distortion`의 UoW
    - `region_sources(lineage=)`
    - `plan_spread`의 이웃 인자
    - `play/base.py`의 `region_name`·`where`
  - web: `http()`가 `HttpError`를 던진다(C16).
- **바꾸지 않는 것**
  - 빌드·불러오기의 병합 쓰기(`upsert_nodes`)
  - 캐노니컬 합의 계산
  - 세션 스키마
  - 소문·사건 엔진 규칙(U7 이월 정정만)
  - 번역 경계(NPC 글은 번역하지 않음)

## 이월 결정 (두 게이트와 U7 리뷰 — 이 플랜에서 닫는다)
### FD 검토 02
| 출처 | 결정 | 단계 |
|---|---|---|
| FD R-08 | ignore는 기록(`history`)에 쌓지 않는다. 그래서 LIFO 순서에서 빠진다 | 1.3, 6.1, 6.6, 6.7, 6.9 |
| | `unignore(run_id, issue_key)`가 `ignored_keys`에서 키를 뺀다(`POST /augmentation/runs/{id}/unignore`). 상태 전이는 아래 FD R-08a다 | |
| | `ChangeSet.nodes_after`(바뀐 뒤 노드 속성)를 기록한다 | |
| | 되돌리기 거절의 검사 순서: 없는 변경 404 → 이미 되돌림 `ChangeAlreadyRevertedError` 409 → 가장 나중이 아님 `RevertOrderError` 409 → run 밖 편집 `RevertConflictError` 409 | |
| | run 밖 편집 판정: 지금 노드가 `nodes_after`와 다르거나, `added_ids` 노드가 없다. 거절이면 아무것도 쓰지 않는다 | |
| | TP-U3-4는 ignore와 run 밖 편집이 섞인 열로 넓힌다 | |
| FD R-08a | BLM §4.3 상태 전이에 다음 행을 더한다(〔Step 1.3 정정〕) | 1.3, 6.7, 6.9 |
| | ignore는 쓰지 않지만 답으로 센다(`answers += 1`). 되돌리기·unignore는 `answers`를 바꾸지 않는다 | |
| | `unignore`: open·converged에서 받는다. 다시 탐지해 이슈가 있고 `answers < 30`이면 open, 이슈가 없으면 converged다. stopped에서는 409다(새 run을 연다) | |
| FD R-11 | 목록 속성(`derived_from_prior_ids`·`about_entity_ids`)은 끊긴 id마다 이슈를 따로 만든다. `Issue.broken_id`와 `QuestionTarget.broken_id`에 담고, 이슈 키에 넣는다 | 1.3, 4.4, 6.2, 6.5 |
| | 연결 대상은 `connection`이다. `wiki_prior_ref` 편집·비우기는 `ConnectionEditor.set_prior_ref`로 두 방향을 함께 쓴다 | |
| | 부모 편집(dangling/edit 포함)은 `RegionEditor.upsert_region`을 거쳐 BR-U3-7 순환 검사를 받는다 | |

### NFR 검토 01
| 출처 | 결정 | 단계 |
|---|---|---|
| NFR R-01 | **FD BLM §1.3과 BR-U3-8 범위 변경**(〔Step 1.3 정정〕). 원칙: 각 단계 안에서 재시도 계획의 선별 기준이 되는 쓰기를 마지막에 한다 | 1.3, 4.3, 4.8 |
| | ① 새 `CONTAINS`(새 부모 → 자식) → 자식 `parent_id` 교체 → 옛 `CONTAINS` 삭제 | |
| | ② `LOCATED_IN` 삭제 → 엔티티 `located_in=None` 교체 | |
| | ④ NPC 검색 문서 → NPC 노드(DETACH) | |
| | ①의 `parent_id` 교체 뒤에 끊기면 옛 `CONTAINS`가 남는다. 재시도 계획은 그것을 찾지 못하지만 ⑥의 DETACH가 지운다. 그래서 재시도 완료 뒤 상태는 끊김 없는 삭제와 같다 | |
| | 종류별 삭제(지식·NPC·엔티티·prior)는 그래프 먼저다. 노드가 이미 없어도 검색 삭제를 부른 뒤 404를 준다 | |
| | TP-U3-2a: 가짜가 n번째 쓰기 호출에서 한 번만 던지고, 그 뒤 호출은 성공한다. 쓰기 호출은 graph·search 쓰기와 `_written`의 meta `upsert_nodes`를 센다. 모든 n을 시험한다. 단언은 둘이다. 끊긴 직후 끊긴 id 속성이 0이다. 재시도 완료 뒤 그래프·검색이 끊김 없는 삭제와 같다 | |
| NFR R-02 | 구조 단언의 범위를 고친다 | 1.3, 4.8, 8.6 |
| | ⑤ 캐시 적중 = 스냅샷 로드 0회(라벨별 `find_nodes`·`get_edges` 0), WorldMeta 버전 읽기 1회 | |
| | ①~③은 FD 단계의 쓰기 포트 호출(graph·search)만 센다. `_written`의 `find_nodes` 1 + `upsert_nodes` 1은 따로 센다. 스냅샷 로드는 세지 않는다 | |
| | 지역 삭제는 9 + NPC 수다. NPC 삭제는 DETACH라 `LIVES_IN` 삭제가 따로 없다 | |
| NFR R-03 | 보강 변경을 선언한다. C-3에 더하는 것은 아래와 같다 | 1.3, 3.1, 6.3, 6.4, 6.7 |
| | `CommonsenseWiki.lookup_similar(query, k, *, fallback=True)`를 둔다. 보강은 `fallback=False`로 부른다. `CommonsenseWiki(llm=None)`을 허용하고, 폴백에는 LLM이 필요하다 | |
| | 근거 prior가 없으면 판정하지 않는다. LLM이 없거나 예산이 다 되었으면 wiki_conflict는 빈 결과다 | |
| | 다듬기는 탐지마다 새 질문 5개까지다 | |
| | run 예산 60회를 둔다. 근거: 첫 탐지 최대 25 + 답 30개 동안 답마다 새 다듬기·판정 1회꼴 = 55 → 60 | |
| | `AugmentationRun.llm_calls`·`llm_budget_exhausted`는 모델·`api/schemas`·웹 타입·AugmentPanel 안내 문구에 나타난다 | |
| | 판정 단위는 (지식, 지역 `terrain_kind`) 쌍이다. 같은 지형의 지역 셋에 붙은 지식은 1쌍이다. 탐지마다 20쌍까지다 | |
| | 캐시 키는 `(지식 id, 진술, terrain_kind)`다 | |
| | 임베딩 호출(wiki 검색)은 예산 밖이다. `(terrain_kind, 지역 이름)` 질의마다 run 안에서 한 번이다 | |
| NFR R-04 | 업로드 표를 고친다 | 1.3, 8.1 |
| | 요청 상한 48 MiB가 모든 칸 합을 다스린다. 칸 상한은 파일 하나와 개수다 | |
| | 호출 수 44는 개수 상한이 정하므로 작은 파일로는 도달한다 | |
| | 칸 검사는 수신 뒤 검사다(Starlette가 multipart를 먼저 받는다) | |
| NFR R-05 | `api/uploads.py`(새 모듈)에 순수 ASGI 미들웨어 `BodyLimitMiddleware`를 둔다. `BaseHTTPMiddleware`는 쓰지 않는다 | 1.3, 8.1 |
| | 경로별 한도 표 `(method, path 정규식) → bytes`를 둔다. World File 두 경로(`POST …/file`, `POST …/file/upload`)는 20 MiB, 나머지는 48 MiB다 | |
| | `Content-Length`가 한도를 넘으면 곧바로 413을 준다 | |
| | 헤더가 없으면 `receive`를 감싸 받은 바이트를 센다. 넘으면 `HTTPException(413)`을 던진다. FastAPI 0.141은 본문 파싱 중의 HTTPException을 다시 던진다(`fastapi/routing.py:442·466`) | |
| | 본문은 `{"detail": "request body too large (limit N MiB)"}`다 | |
| | 테스트: 헤더 있음, 청크(헤더 없음), 경로별 한도, `/health`·JSON 라우트 무사 | |
| NFR R-06 | 새 어댑터 메서드는 UNWIND 일괄 쿼리 하나다(`delete_edges`는 엣지 종류마다 하나). 기존 `upsert_edges`의 엣지별 왕복은 데모 규모에서 받아들인다 | 2.2, 2.4 |
| | `replace_nodes`는 `id`·`world_id`를 props에 합쳐 `SET n = row.props`로 쓴다. `upsert_nodes`와 같은 `ConstraintError` → `ConstraintViolation` 번역을 한다(`neo4j_repo.py:92-98`) | |
| | 계약 테스트가 id·world_id의 보존과 빠진 속성의 삭제를 본다 | |
| NFR R-07 | `MATERIAL`을 `shared/text.py`로 옮긴다. 호출처: `play/npc/prompts.py:23`(정의와 사용), `play/event/suggest_context.py:18`(중복 정의 삭제), `play/gm/narrator.py:13`(import), `tests/play/test_gm_events.py:9`(import 경로) | 1.3, 2.5, 6.3, 6.4 |
| | 질문 다듬기 입력은 템플릿 문장 + `QuestionTarget` 필드(이름 60·지역 이름 60·속성 30·진술 200)다. `issue.description`이 아니다 | |
| | wiki_conflict의 LLM `reason`은 `one_line(…, 200)`으로 `Issue.description`에 둔다 | |
| NFR R-08 | §4에 두 줄을 더한다 | 1.3, 4.7, 8.2, 6.9 |
| | 지도 JSON 422는 `map {filename!r} is not valid JSON` 고정 문구다(C-9) | |
| | `list_worlds`가 `WorldCatalog`로 옮겨도 응답은 같다(`WorldInfo` 그대로) | |
| | 보강 `apply`/`revert`의 테스트 인용은 Step 6.9에 전수로 적는다 | |

### U7 코드 리뷰 이월 (§1·§3·§5)
| 출처 | 결정 | 단계 |
|---|---|---|
| U7 #6 | `GmHub`: `refreshRef = useRef(refresh)`를 두고, 쓰기 뒤에 `await refreshRef.current()`를 부른다. 쓰는 중 지역을 바꾸는 vitest | 10.1 |
| U7 #7 | `ActionBar`: textarea는 `closed \|\| sending`, 버튼은 `busy \|\| closed`로 끈다. 턴 중 입력 vitest | 10.2 |
| U7 #8 | `CommitRange`에 `onDraft`를 두고, `DistortionPanel` 이름표가 초안을 보인다 | 10.1 |
| U7 #9 | `rumor/dynamics.py`: `evolve_support`·`decay_support`·`adjust_support`가 `round(clamp01(x), 6)`을 돌려준다. 예제: 0.35 + 0.1 = 0.45가 강한 소문 | 7.2 |
| U7 #10 | `timelineText`: 표시가 있는 지난 `event_created` 줄은 `payload.category`가 있을 때만 새 템플릿을 쓴다. 채우지 못한 `{param}`이 남으면 요약으로 돌아간다. fixture를 실제 모양으로 바꾼다 | 10.3 |
| U7 #12 | `DialoguePanel`의 `start`·`say` catch가 `conflictKind`를 쓴다. "closed"면 `play.sessionClosed`를 보이고 `onClosed`로 PlayPage가 `refresh()`한다. 백엔드 테스트가 409 본문의 `session is closed`·`turn in progress`를 고정한다 | 7.6, 10.2 |
| U7 #13 | `world_state.py:49`·`event/service.py:289·297`: `EventStatus(ev.status) is EventStatus.ACTIVE`로 비교하고 `.value`를 찍는다. 인메모리 제안 → 승인 → 상태·프롬프트 테스트 | 7.3 |
| U7 #14 | `suggestion_context`: 머리말·사건·행적을 먼저 넣고, 남은 예산에 지역 줄을 통째로 더한다. 줄 중간을 자르지 않는다. 단언: 지역 60곳 + 모든 글자를 상한까지 채워도 사건 5·행적 5가 모두 있다 | 7.3 |
| U7 #15 | `locus/play/models.py:641` `WorldState.max_event_suggestions`(`api/schemas.py:382` `WorldStateOut = WorldState`라 DTO는 따라온다). `WorldStateService`가 `tuning.max_event_suggestions`를 싣는다. `ManualTurnPanel`이 `maxSuggest`로 쓴다 | 7.3, 10.1, 11.3 |
| U7 §3 NaN 지형 | `topology_terrain_modifiers`·`topology_base_weights`를 `dict[str, FiniteFloat]`로 두고, NaN·Infinity·`1e400`은 기동 실패다 | 7.1 |
| U7 §3 제안 지역 | 초안의 지역은 월드 기준으로 맞춘다. id는 `regions_by_id`, 이름은 모든 brief에서 같은 모호성 규칙이다 | 7.3 |
| U7 §3 `act` 폴링 | `act`가 첫 await 전에 `gen`을 잡고, await마다 확인하며, `poll`에 넘긴다 | 10.2 |
| U7 §3 NaN 값 | `DistortionUpdate.degree`·`SupportUpdate.support`·`EventCreate.magnitude`에 `allow_inf_nan=False` → 422 | 7.6 |
| U7 §3 `PlayerStrip` | 404만 "플레이어 없음"이다. 다른 오류는 마지막 플레이어를 두고 한 줄 오류를 보인다 | 10.1 |
| U7 §3 `TOPOLOGY_DEFAULT_BASE` | 없앤다(A3-15, BR-U3-40). C10 별칭도 함께 지운다 | 7.1 |
| U7 §3 `pick_brief_regions` | 잎 여부(부모 id 집합)를 넘긴다. 정렬 키는 (부모 여부, −경로 길이, 이름)이다. 순위 없는 단계는 경로 길이를 깊이로 쓴다 | 7.3 |
| U7 §3 이름 summary | `rumor_spread` summary를 이름으로 쓴다. `deed_voided` 페이로드에 `region_names`를 더한다 | 7.4 |
| U7 §3 `EDGE_SPACE` | 뒤쪽 갈래를 lookbehind로 선형으로 바꾼다. textarea `maxLength`는 상한의 2배다 | 10.2 |
| U7 §3 `ID_MAX` | 지역 id는 자르지 않는다 | 7.3 |
| U7 §3 빈 `shown` | `suggest_events`는 보인 지역이 없으면 LLM 전에 `[]`를 돌려준다. 죽은 `if not context` 갈래를 지운다 | 7.3 |
| U7 §3 `say` try | 프롬프트 두 문자열을 try 앞에서 만들고 `complete`만 감싼다. 판단·서술도 같게 맞춘다 | 7.5 |
| U7 §5 문서 | `operations.md:317·319·346`, `env.example:70`, `tuning.py:50`, `deeds/service.py:3`, `play/wiring.py:100`, U7 frontend-components:113, X3 BR-X3-5, U7 code-summary §4("U6 #10·#11 → DeedPanel")·§5 8.7 정정 | 11.3 |

### U7 코드 리뷰 이월 (§2 정리 C1~C19)
| 출처 | 결정 | 단계 |
|---|---|---|
| C1 | "전체 생성"은 `api.getWorldState(sid)` 한 번으로 `active_rumors - deed_rumors === 0`인 지역을 고른다. X3 BR-X3-5 문구를 고친다 | 10.1, 11.3 |
| C2 | `region_sources(..., lineage: bool = True)`. 호출처 | 7.4 |
| | 계보 필요(그대로 `True`): `advancer.py:467`(장면), `npc/dialogue.py:154·235` | |
| | 활성만(`lineage=False`): `player/service.py:61`(플레이어 `/region`), `region_knowledge.py:87`(세션 지역 지식) | |
| C3 | `_neighbour_weights`를 지우고 `neighbour_map`만 쓴다. 평행 간선·자기 고리 예제를 더한다 | 7.4 |
| C4 | `play/base.py`에 `region_name(snapshot, rid)`·`where(snapshot, rid)`를 둔다. `require_region`이 지역을 돌려준다. 서비스는 스냅샷을 한 번 읽는다 | 7.4 |
| | 호출처: `rumor/service.py:81-84`, `event/service.py:263-266·285·308`, `distortion_service.py:49-50`, `advancer.py:247`(`names`)·`:564`(`names` + `_where`) | |
| | 엔진은 `:564`의 `names`를 넘긴다. 사라진 지역 폴백 테스트를 더한다 | |
| C5 | `_draft_spread`는 `list_deeds(session.id, deed_ids=…)`를 쓴다 | 7.4 |
| C6 | `/log?limit=`(player_log 뒤 꼬리). 화면은 30을 넘긴다 | 7.4, 10.2 |
| C7 | PlayPage 마운트: `listTurnRuns`를 첫 읽기와 함께 하고, `turn_running`인데 실행이 없을 때만 다시 읽는다 | 10.2 |
| C8 | `runBulk`를 `mapLimit(ids, BULK_LIMIT, …)`로 바꾼다 | 10.1 |
| C9 | `events.distortions.get(region_id, DEFAULT_DISTORTION_DEGREE)`로 쓰고 늘 참인 조건을 지운다 | 7.4 |
| C10 | `weights.py`의 세 별칭을 지운다(A3-15와 같이) | 7.1 |
| C11 | `EventSuggester.system()`을 지우고 `prompt`를 `_prompt`로 되돌린다. `MATERIAL`은 NFR R-07대로 한다 | 2.5, 7.3 |
| C12 | 순수 도우미 `region_rows(regions, stored)`와 상수 `FRESH`를 왜곡도 목록·세계 상태·되먹임이 함께 쓴다 | 7.4 |
| C13 | `match_region`은 `normalize_name`으로 비교한다 | 7.3 |
| C14 | 한 줄 글은 `one_line(…, 상한)`으로만 자른다. `cap`은 여러 줄 서술에만 쓴다. 호출처: `gm/narrator.py:32·80`, `event/suggest_context.py:95` | 7.5 |
| C15 | `CommitRange`에서 `onMouseUp`과 주석의 "mouse"를 지운다 | 10.1 |
| C16 | `http()`가 `HttpError(status, body)`를 던지고 `statusOf(err)`를 함께 쓴다 | 9.1 |
| | 호출처: `api/http.ts:20-24`(`conflictKind`), `DialoguePanel.tsx:55·103`, `GmHub.tsx:94·112`, `DeedPanel.tsx:57`, `PlayPage.tsx:219`, `EditorPage.tsx:88`(9.8에서 다시 씀) | |
| | 거절 fixture를 `new HttpError(…)`로 바꾼다: `gm.test.tsx:136·263-265·418·431·443`, `deeds.test.tsx:131·211`, `dialogue.test.tsx:250·272·293·309`, `components.test.tsx:449` | |
| C17 | `save_appraisals`가 `retelling`을 `strip()`해 저장하고, 비교는 `retelling != ''`다. 계약 테스트에 탭·줄바꿈·NBSP를 더한다 | 7.5 |
| C18 | `UtcDateTime.process_bind_param`이 `astimezone(timezone.utc)`로 바꾼다. +09:00 왕복 테스트 | 7.5 |
| C19 | `CommitRange`는 호출자의 `onBlur`·`onKeyUp`·`onPointerUp`을 먼저 부른다 | 10.1 |

### U3 FD에서 정한 U7 이월
| 출처 | 결정 | 단계 |
|---|---|---|
| Q6=A (BR-U3-38) | `set_region_distortion`의 UoW 하나에서 다음을 한다: 왜곡도 설정, 몫 지우기, ACTIVE 사건의 그 지역 기여 지우기(`update_event`), 타임라인 줄(`event_contributions_cleared`). EX-12 | 7.2 |
| A3-14 (BR-U3-39) | 지역 id가 없는 U7 이전 지역 줄은 `summary`를 보인다 | 10.3 |
| A3-15 (BR-U3-40) | U7 §3과 같다 | 7.1 |

### 알려진 한계 (code-summary 설계 이탈에 적는다)
- 지역 삭제의 GM 리스는 삭제를 시작할 때 열린 세션에만 걸린다(검토 01 R-09). 막지 못하는 경합이 둘 있다.
  - 리스를 잡은 뒤 새로 시작한 세션: `SessionService.start`는 가드를 쓰지 않는다. 시작 지역 검사는 스냅샷으로 한다.
  - GM 쓰기: GM 쓰기는 리스를 서로 나눈다.
- 그 결과는 사라진 지역을 가리키는 세션 행이고, 화면은 U7의 이름 폴백(C4)과 404로 다룬다. 제작자 한 명 전제(A-4)에서 받아들인다.

## 실행 원칙
- 기존 파일은 그 자리에서 고친다. 복사본이나 `_v2`는 없다. `locus/world/editor.py`는 같은 이름의 패키지로 바뀐다(모듈과 패키지는 함께 있을 수 없다).
- 각 단계는 그 단계의 테스트가 GREEN인 상태로 끝낸다. 단계 안의 붉은 구간은 그 단계에 적고, 커밋은 단계 끝에 한다.
- 시그니처를 바꾸는 하위 단계는 호출처 전부를 같은 하위 단계에서 고친다.
- 의도된 동작 변경(NFR §4 C-1~C-10과 Step 1.3의 추가)으로 바꾸는 테스트에는 `# U3 intended change: <BR>`을 단다. 지우는 테스트는 없다. 옮긴 컴포넌트의 테스트는 import만 바꾼다.
- 규칙 번호(BR-U3-n)와 검증 번호(TP-U3-n, EX-n)를 테스트 이름이나 docstring에 적는다.
- PBT는 속성마다 변이 한 번으로 잡는지 확인하고 결과를 code-summary에 적는다.
- 새 외부 의존은 없다(백엔드·npm 모두).
- 각 단계를 마치면 곧바로 체크박스를 [x]로 바꾸고 단계마다 커밋한다.

---

## Steps

### Step 1 — 기준선·뼈대·승인 산출물 정정
- [ ] 1.1 실측값을 `construction/U3-world-editor/code/code-summary.md` 초안의 기준선으로 적는다. 기대값은 `pytest -q --no-cov` 735, `npx vitest run` 94, `mypy locus api` 11이다.
- [ ] 1.2 새 파일을 만든다(빈 docstring).
  - 백엔드
    - `locus/world/editor/`: `__init__.py`, `models.py`, `writes.py`, `regions.py`, `connections.py`, `knowledge.py`, `npcs.py`, `entities.py`, `catalog.py`, `bundle.py`
    - `locus/world/npc_drafts.py`, `api/uploads.py`
  - 프론트엔드
    - `web/src/routes/HomePage.tsx`
    - `web/src/features/editor/`
      - 화면: `WorldFileBar.tsx`, `MapCanvas.tsx`, `ConfirmDelete.tsx`, `UnscopedPanel.tsx`, `AugmentPanel.tsx`, `WikiPanel.tsx`, `BuildPanel.tsx`, `BuildReportPanel.tsx`
      - 인스펙터: `RegionInspector.tsx`(조합), `RegionForm.tsx`, `ConnectionList.tsx`, `KnowledgeList.tsx`, `NpcEditorList.tsx`, `NpcDraftCards.tsx`
      - 순수 판정: `drag.ts`
    - `web/src/features/gm/RegionKnowledgePanel.tsx`
  - 테스트
    - `tests/world/editor/__init__.py`, `tests/world/editor/test_editors.py`, `tests/world/editor/test_region_delete.py`
    - `tests/world/test_npc_drafts.py`
    - `tests/shared/storage/test_port_contract.py`
    - `tests/api/test_world_editor_api.py`, `tests/api/test_uploads.py`
    - `web/src/__tests__/editor.test.tsx`, `web/src/__tests__/home.test.tsx`
  - 지울 것
    - `locus/world/editor.py`: 4.7
    - `web/src/Toolbar.tsx`, `web/src/AugmentPanel.tsx`, `web/src/RegionPanel.tsx`: 9.8
- [ ] 1.3 **승인 산출물 정정**: 각 곳에 "〔Step 1.3 정정〕"을 붙이고 audit에 한 줄 남긴다.
  - FD BLM
    - §1.3: ①·②·④ 쓰기 순서와 재시도 원칙(NFR R-01)
    - §4.2: ignore 행(기록 없음, 답으로 셈), dangling 목록 속성은 `broken_id`로
    - §4.3: FD R-08a 전이 행(unignore), 되돌리기 검사 순서, `nodes_after` 비교
    - §7 API 표
      - `POST …/augmentation/runs/{id}/unignore` 추가
      - `revert`는 200 + `AugmentationRun`이고, 409 사유는 셋이다.
      - `POST runs`는 LLM 없이 200이다.
      - `answer` → `AnswerResult`
  - FD domain-entities
    - §4.2: `Issue.broken_id`, `QuestionTarget.broken_id`, `AugmentationQuestion`의 `options`·`kind` 제거, `AugmentationRun.llm_calls`·`llm_budget_exhausted`
    - §4.3: `ChangeSet.nodes_after`
    - §4.4: `AnswerResult.change: ChangeSet | None`(ignore면 None)
    - §6 오류 표: `RevertOrderError`·`RevertConflictError`(409), `unignore`의 stopped 409
    - §8 설계 이탈 목록에 "8. U3 코드 계획에서 더한 계약"을 추가한다: `unignore`, `nodes_after`, `broken_id`, `revert` 응답, `Editors` 묶음, `WorldContainer.editors`·`catalog`, `max_event_suggestions`, `/log?limit`, `deed_voided.region_names`
  - business-rules
    - BR-U3-8(쓰기 순서), BR-U3-23(목록 속성은 id마다), BR-U3-27(검사 순서, run 밖 편집 409), BR-U3-28(ignore는 답으로 셈, 풀기)
    - BR-U3-41: 단위, 60회 예산, 검색 전용 조회, 근거·LLM 없으면 판정 없음
    - TP-U3-4(ignore·run 밖 편집이 섞인 열), TP-U3-2a 신설(포트 쓰기 호출 단위, 재시도 완료 뒤 비교)
  - nfr-light
    - §1 NFR-3: ⑤와 센 범위(R-02)
    - §1.1: 표·미들웨어 방법·경로별 한도(R-04·R-05)
    - §1 NFR-5·§4 C-3: 추가 변경(R-03)
    - §3·§5: UNWIND, 제약 오류 번역, `MATERIAL` 호출처, 다듬기 입력(R-06·R-07)
    - §4: 두 줄(R-08)
    - §2: ①·②·④ 순서와 종류별 삭제 재시도(R-01)

### Step 2 — 저장 포트 (domain-entities §1, NFR R-06)
- [ ] 2.1 `locus/shared/storage/base.py`
  - `EdgeKey(type, source_id, target_id, identity: dict = {})`. identity 규칙은 `edge_identity_field`와 같다.
  - `GraphRepository.replace_nodes(nodes)`, `GraphRepository.delete_edges(world_id, edges) -> int`
  - `SearchRepository.delete(world_id, doc_ids) -> int`
- [ ] 2.2 어댑터. 2.1부터 2.3 끝까지 프로토콜 검사 테스트는 붉고, 2.3 끝에 GREEN이 된다.
  - `neo4j_repo.py`
    - `replace_nodes`: 라벨마다 `UNWIND $rows AS row MERGE (n:L {id: row.id, world_id: row.world_id}) SET n = row.props`다. props에 id·world_id를 합친다. `ConstraintError`는 `upsert_nodes`(`:92-98`)와 같게 `ConstraintViolation`으로 바꾼다.
    - `delete_edges`: 엣지 종류마다 UNWIND 하나다. identity가 있으면 그 키로 MATCH한다.
  - `opensearch_repo.py`: `delete`는 `world_id` 필터 + ids의 `delete_by_query` 하나다.
- [ ] 2.3 가짜
  - `tests/shared/storage/fakes.py`: `InMemoryGraphRepository.replace_nodes/delete_edges`, `InMemorySearchRepository.delete`
  - 테스트 안 임시 가짜(`test_services.py`의 `_GraphRepo`·`_SearchRepo`, `test_augmentation.py:120`의 `_GraphRepo`, `test_wiki_build.py`의 `_Recording*`)는 새 경로가 그것을 쓸 때만 메서드를 더한다. 어느 것을 더했는지 code-summary에 적는다.
- [ ] 2.4 테스트 `tests/shared/storage/test_port_contract.py`
  - 인메모리 동작
    - TP-U3-3: 교체 왕복. 빠진 속성은 사라지고 id·world_id는 남는다.
    - 없는 엣지·문서는 넘기고 지운 수를 돌려준다.
    - identity가 다른 평행 엣지는 하나만 지운다.
  - Neo4j Cypher 모양(가짜 드라이버, `test_storage.py` 방식): `SET n = row.props`, props의 id·world_id, UNWIND, 종류별 쿼리 수, 제약 오류 번역
  - OpenSearch 삭제 본문(가짜 클라이언트)
- [ ] 2.5 `locus/shared/text.py`에 `MATERIAL`을 둔다(NFR R-07, C11).
  - 호출처: `play/npc/prompts.py:23`(정의 삭제, import), `play/event/suggest_context.py:18`(정의 삭제, import), `play/gm/narrator.py:13`(import 경로), `tests/play/test_gm_events.py:9`(import 경로)
  - 경계 테스트 GREEN

### Step 3 — wiki 근거 (BLM §5, Q4=A)
- [ ] 3.1 `locus/world/wiki/base.py` `CommonsenseWiki`
  - `llm: LLMProvider | None`
  - `lookup_similar(…, fallback=True)`. `fallback=False`거나 `llm`이 없으면 검색 결과만 돌려준다. `lookup_terrain_rule`은 그대로다.
  - `created_priors`: 정규화 질의(`casefold` + 공백 접기)로 묶고, `WIKI_FALLBACK_MAX = 40`이다. 넘으면 빈 결과와 경고 한 줄이다.
- [ ] 3.2 빌드
  - `locus/shared/models/reports.py` `BuildReport.priors_created: int = 0`
  - `locus/world/build.py`
    - 참조 정리: `증류 ∪ created`에 없을 때만 버린다(이탈 4).
    - 커밋은 BLM §5.1의 다섯 단계 순서다. 토폴로지 단계 `created_priors` → 온톨로지 → 새로 생긴 것 → 나머지.
  - 호출처: `locus/__main__.py`, `api/routers/world.py`, `demo/__init__.py`의 `build_from_sources`(시그니처는 그대로)
- [ ] 3.3 `locus/world/wiki/schemas.py`·`admin.py`
  - `PriorRefView`, `PriorUsage`, `BrokenRef`(domain-entities §5)
  - 순수 계산 `prior_ref_view(prior_id, priors_by_id)`, `usages(snapshot, priors)`. 편집 패키지(4.3)가 이것을 쓴다.
  - `WikiAdmin.list_priors -> list[WikiPrior]`, `prior_refs -> list[PriorUsage]`, `broken_refs -> list[BrokenRef]`
  - `delete_prior`: 노드 → 검색이다. 노드가 없어도 검색 삭제를 부른 뒤 404다. 참조는 그대로 둔다.
- [ ] 3.4 테스트(`tests/world/wiki/test_wiki_build.py` 고침 + 추가, `test_wiki.py`)
  - EX-10
  - 같은 질의 두 번 → 폴백 LLM 1회. 41번째 → 0회 + 경고
  - `fallback=False` → LLM 0회, `llm=None` → LLM 0회
  - 빌드 뒤 `DERIVED_FROM` 끝점 누락 0, 연결 `wiki_prior_ref` 끊김 0(NFR-9)
  - 의도된 변경(C-4) 표시

### Step 4 — 편집 패키지 `locus/world/editor/` (BLM §1, domain-entities §2)
- [ ] 4.1 `models.py`
  - `ConnectionKey`, `NameRef`, `RegionDeletePlan`, `RegionDeleteReport`
  - `EditorRegionView`, `ConnectionView`(`prior: PriorRefView | None`, 3.3), `ScopedKnowledge`, `WorldSummary`
  - 오류 `RegionInUseError(region_id, session_ids)`
- [ ] 4.2 `writes.py` `EditorWrites(graph, search, embedding, cache)`
  - `replace(nodes)`, `index(docs)`(임베딩 실패 무시, 지금 규칙), `unindex(world_id, ids)`
  - `written(world_id)`: `finally`에서 `touch_world_meta` + 캐시 무효화. 지금 `_written`과 같다(review #12 동작 유지).
  - `snapshot(world_id)`
  - 검사 도우미: 경로·본문 id(BR-U3-5 → `ValueError`), 참조 지역 존재(BR-U3-6 → `LookupError`)
- [ ] 4.3 `regions.py` `RegionEditor(writes)`
  - `create_region`, `upsert_region`(BR-U3-7 순환 400, `CONTAINS` 다시 쓰기, BLM §1.2)
  - `plan_region_delete`(BLM §1.3)
  - `delete_region(world_id, region_id, *, protected)`: 쓰기 순서는 정정된 BR-U3-8이다.
    1. 새 `CONTAINS` → `parent_id` 교체 → 옛 `CONTAINS`
    2. `LOCATED_IN` 삭제 → 엔티티 교체
    3. `SCOPED_TO` 삭제
    4. NPC 검색 문서 → NPC 노드(DETACH)
    5. 연결 두 방향(`delete_edges` 한 번)
    6. 지역 노드(DETACH)
  - `editor_view(world_id, region_id) -> EditorRegionView`: prior는 3.3의 `prior_ref_view`를 쓴다.
- [ ] 4.4 `connections.py` `ConnectionEditor(writes)`
  - `upsert_connection` → 두 방향 목록(BR-U3-10·11)
  - `change_connection_kind`(새 쌍 먼저, 옛 쌍 삭제, 같은 쌍이 있으면 400)
  - `delete_connection(key) -> int`(없으면 404)
  - `set_prior_ref(key, prior_id | None)`: 두 방향을 함께 쓴다(FD R-11)
- [ ] 4.5 `knowledge.py` `KnowledgeEditor(writes)`
  - `create_knowledge(k, region_id)`
  - `upsert_knowledge(k)`: 스코프 유지, `region_hint`는 저장하지 않는다.
  - `set_scopes(world_id, kid, region_ids)`: DIRECT만 다룬다.
  - `delete_knowledge`: 그래프 → 검색. 노드가 없어도 검색 삭제를 부른 뒤 404다.
  - `list_unscoped`
- [ ] 4.6 나머지와 묶음
  - `npcs.py` `NpcEditor`: `create/upsert/delete`, `LIVES_IN` 다시 쓰기, 검색 문서. 삭제는 4.5와 같은 재시도 규칙이다.
  - `entities.py` `EntityEditor`: `update_entity`, `delete_entity`. 삭제는 4.5와 같은 재시도 규칙이다.
  - `catalog.py` `WorldCatalog.list_worlds() -> list[WorldSummary]`: 지금 라우터 `world.py:231-259`의 계산을 옮긴다(월드마다 `find_nodes` 2회).
  - `bundle.py` `@dataclass(frozen=True) Editors(regions, connections, knowledge, npcs, entities, graph)`
    - `delete_any(world_id, node_id)`: 라벨로 종류별 삭제를 나눠 부른다(지역은 `protected=∅`). 보강 REMOVE만 쓴다(FD 이탈 1).
    - `prior_ids(world_id) -> set[str]`: `find_nodes(world, "WikiPrior")` 1회
    - `get_node(world_id, id)`: 되돌리기 비교용 읽기
- [ ] 4.7 조립과 옛 모듈(이 하위 단계 안에서 호출처를 모두 고쳐 GREEN으로 닫는다)
  - `locus/world/editor.py`를 지운다.
  - `locus/world/__init__.py:13·19`: `WorldEditor` export를 일곱 클래스 + `Editors` export로 바꾼다.
  - `locus/world/wiring.py`
    - `:19·28·49`: `WorldContainer.editor` → `editors`, `catalog`
    - `:82`: 엔진이 `editors`를 받는다(`AugmentationEngine(cache, editors, …)`). 보강은 아직 LLM이 있을 때만 조립한다. LLM 없는 조립은 6.8에서 한다.
  - `locus/world/augmentation/engine.py`·`apply.py:61·82`: `editor.delete_node` → `editors.delete_any`, `editor.upsert_knowledge` → `editors.knowledge.upsert_knowledge`. 동작은 같고 쓰기는 교체다(C-1).
  - `api/routers/world.py`
    - `:231-259` `GET /worlds`는 `w.catalog`를 쓴다(응답 그대로).
    - `:442` → `w.editors.regions.upsert_region`, `:449` → `w.editors.knowledge.upsert_knowledge`
    - `:452-456` `DELETE …/nodes/{n}`을 지운다(C-2).
  - 테스트 호출처
    - `tests/world/services/test_services.py:22·319·369·394·427·448`
      - `:317`·`:427`은 C-1·C-2 의도된 변경이다.
      - `:356`·`:385`·`:433`의 캐시·메타 규칙은 `EditorWrites`로 옮겨 그대로 지킨다.
    - `tests/api/test_world_api.py`
      - `:47` `_Editor` 가짜 → 인메모리 가짜 위의 실제 `Editors`
      - `:161-170` `WorldContainer(editor=…)` → `editors=…, catalog=…`
      - `:212` `GET /worlds`는 `catalog`가 있는 픽스처를 쓴다.
      - `:345` C-1, `:351` C-2 의도된 변경
    - `tests/api/test_augment_api.py:30-32` `WorldContainer(editor=None, …)` → `editors=None`
    - `tests/world/augmentation/test_augmentation.py:226` `AugmentationEngine(cache, editor, graph, llm=None)` → `editors`
    - 〔검토 02 처리 R-14〕 `test_augmentation.py:107`의 `_Editor` 가짜를 인메모리 그래프 위의 실제 `Editors`로 바꾼다. 이것을 넘기는 `:137-157`의 `apply_answer`·`revert`, `:225-226`의 엔진 생성도 함께 바꾼다. 4.7은 `apply_answer`·`revert`의 인자 이름(`editor` → `editors`)만 바꾼다. 나머지 시그니처는 6.5·6.6에서 바꾼다.
- [ ] 4.8 테스트
  - `tests/world/strategies.py`를 넓힌다: 계층 숲 + 연결 쌍 + 스코프 0~3 지식 + NPC + `located_in` 엔티티를 가진 월드, 편집 연산 열.
  - `test_editors.py`
    - TP-U3-1, TP-U3-3(편집 경로 왕복)
    - TP-U3-6: 무작위 편집 연산 열 뒤 World File 저장 → 불러오기 → 저장이 같다(U2 PBT-02 유지)
    - EX-1, EX-4, EX-5
    - BR-U3-5·6의 400·404
    - 종류별 삭제 재시도: 검색 삭제가 실패한 뒤 다시 부르면 404이고 문서가 없다.
    - 구조 단언 ②·③(NFR R-02 범위)
  - `test_region_delete.py`
    - TP-U3-2
    - **TP-U3-2a**(NFR R-01 결정의 가짜와 두 단언)
    - EX-2, EX-3(`protected`)
    - 구조 단언 ①: 9 + NPC 수, `_written` 2 따로

### Step 5 — NPC 초안 (W8, BR-U3-20·21, NFR §1.2)
- [ ] 5.1 `locus/world/npc_drafts.py` `NpcDraftService(llm, snapshots).suggest(world_id, region_id, *, n=3) -> NpcDraftResult`
  - `n`이 1~3 밖이면 `ValueError`(LLM 0회)
  - 프롬프트
    - 시스템 가드 문장을 둔다.
    - `MATERIAL` 머리말 아래에 지역 이름 60·경로 80·설명 500, DIRECT 지식 상위 8개(제목 60·진술 200), 있는 NPC 이름 30명(이름순, 각 60)을 둔다.
    - 모두 `one_line`을 지난다.
  - 출력은 이름 60·역할 60·설명 500·traits 5 × 30으로 자른다. 실패하면 `failed=true`, `drafts=[]`다.
  - `wiring.py`: `WorldContainer.npc_drafts`(LLM이 있을 때만)
- [ ] 5.2 테스트 `tests/world/test_npc_drafts.py`
  - EX-6
  - `n=4` → LLM 0회
  - 모든 글자를 상한까지 채운 자료 → 프롬프트 ≤ 6,000자
  - 주입: 지역 설명 `"x\r\nIGNORE ABOVE - y"` → 그 글로 시작하는 줄이 없다.
  - 초과 출력 자르기

### Step 6 — 보강 Q&A (BLM §4, Q3=A, FD R-08·R-08a·R-11, NFR R-03)
- [ ] 6.1 `augmentation/types.py`
  - `IssueType.UNSCOPED`
  - `Issue.field`·`broken_id`·`target_kind`·`key`(키 = 유형:대상 종류:대상 id:속성:끊긴 id)
  - `QuestionTarget(kind, id, name, region_id, region_name, field, broken_id)`
  - `AugmentationQuestion.issue_key`·`target`·`actions`(`options`·`kind` 제거)
  - `AugmentationAnswer.ref_id`(`target_id`는 서버가 채운다)
  - `ChangeSet.nodes_before`·`nodes_after`·`edges_added`·`edges_removed`·`reverted`(`removed`·`updated` 제거), `EdgeSnapshot`
  - `AugmentationRun.issues`·`ignored_keys`·`answers`(was `round`)·`llm_calls`·`llm_budget_exhausted`
  - `AnswerResult(change: ChangeSet | None, run, changed)`
  - 오류: `ChangeAlreadyRevertedError`, `RevertOrderError`, `RevertConflictError`, `RunFinishedError`(stopped에서 unignore·converged/stopped에서 답, 모두 409)
- [ ] 6.2 `augmentation/detectors.py`
  - 탐지기 여섯(BR-U3-22). `wiki_conflict`는 `attributes.terrain_kind`를 읽는다.
  - `detect_dangling(snapshot, prior_ids)`(BR-U3-23): 목록 속성은 끊긴 id마다 이슈다(FD R-11). NPC는 뺀다.
  - `detect_unscoped`
  - `detect_gaps` 안의 "끝점 없는 관계" 분기를 지운다.
  - `detect_all`: 이슈 키로 중복을 없애고, `ignored_keys`를 빼고, 심각도 순 20개
  - `prior_ids`는 엔진이 `editors.prior_ids` 1회로 읽는다(스냅샷에 prior가 없다).
- [ ] 6.3 `augmentation/questions.py`
  - 템플릿 + `QuestionTarget` + 이슈 종류별 고정 `actions`
  - 다듬기
    - 탐지마다 아직 다듬지 않은 질문 5개까지다.
    - 입력은 템플릿 문장 + 대상 필드다(NFR R-07). `MATERIAL` 머리말을 두고 ≤ 1,000자다.
    - 결과는 run 캐시(이슈 키)에 둔다.
    - LLM은 문장만 바꾼다.
- [ ] 6.4 `wiki_conflict` 판정
  - LLM이 없거나 run 예산이 다 되었으면 빈 결과다.
  - 단위는 (지식, terrain_kind) 쌍이고 탐지마다 20쌍까지다.
  - 근거는 `wiki.lookup_similar(…, k=2, fallback=False)`이다. 같은 `(terrain_kind, 지역 이름)` 질의는 run에서 한 번만 조회한다.
  - prior가 없으면 판정하지 않는다.
  - 캐시 키는 `(지식 id, 진술, terrain_kind)`다. 프롬프트는 ≤ 1,500자다.
  - `reason`은 `one_line(…, 200)`이다.
- [ ] 6.5 `augmentation/apply.py` `apply_answer(question, answer, *, world_id, editors) -> ChangeSet | None`
  - BLM §4.2 표를 따른다. 대상은 `question.target`에서 읽는다(B1). ignore는 None이다.
  - Entity confirm·edit는 `editors.entities`를 쓴다(B3).
  - dangling/edit
    - `ref_id`의 종류를 검사한다. 지역·엔티티는 스냅샷에서 보고, prior는 `editors.prior_ids`에서 본다. 맞지 않으면 400이다.
    - 부모는 `editors.regions.upsert_region`을 거쳐 순환 검사를 받는다(FD R-11).
    - 연결 `wiki_prior_ref`는 `editors.connections.set_prior_ref`로 두 방향을 쓴다.
    - 목록 속성은 `target.broken_id`만 바꾸거나 뺀다.
  - 노드 쓰기는 교체다. `nodes_before`·`nodes_after`·`edges_*`를 기록한다.
- [ ] 6.6 `revert(change, *, world_id, editors)`
  - 먼저 검사한다(FD R-08): `editors.get_node`로 읽은 지금 노드가 `nodes_after`와 다르거나 `added_ids` 노드가 없으면 `RevertConflictError`이고 쓰지 않는다.
  - 그다음 BLM §4.3의 순서로 쓴다. 검색 문서는 다시 색인하거나 지운다.
- [ ] 6.7 `augmentation/service.py` `AugmentationService(engine, store, *, max_answers=30, llm_budget=60)`
  - `start_run`
  - `answer -> AnswerResult`: ignore도 `answers += 1`(FD R-08a)
  - `revert -> AugmentationRun`: 검사 순서는 FD R-08이다.
  - `unignore -> AugmentationRun`: FD R-08a 전이를 따른다.
  - `get_run`
  - BLM §4.3 상태 전이 표 + FD R-08a 행을 따른다.
  - LLM 호출을 세고, 예산이 다 되면 템플릿만 쓰고 판정을 쉰다.
  - `run_store.py`: run마다 `threading.Lock`을 둔다(NFR N3-7). 월드마다 최근 20개만 남긴다(BR-U3-42).
- [ ] 6.8 `augmentation/engine.py`·`wiring.py`
  - 엔진은 `editors`와 `wiki_provider`를 받는다.
  - `assemble_world`는 보강을 LLM 없이도 조립한다(NFR-4). 이때 `CommonsenseWiki(search, llm=None, …)`(3.1)를 쓴다. LLM이 있으면 다듬기·판정을 켠다.
  - `augmentation/graph.py`(LangGraph 보기, 미배선)는 새 시그니처에 맞춘다.
- [ ] 6.8a 〔검토 02 처리 R-15〕 보강 라우터(`api/routers/world.py:459-485`)를 6.9 전에 바꾼다.
  - `POST runs`는 LLM 없이도 200이다.
  - `answer`는 `response_model=AnswerResult`다.
  - `revert`는 200 + `AugmentationRun`이다.
  - `unignore` 경로를 더한다.
  - 409 매핑(8.5의 보강 오류)도 여기서 한다.
  - 8.4에는 wiki·초안 경로만 남는다.
- [ ] 6.9 테스트
  - 의도된 변경(C-3), `tests/world/augmentation/test_augmentation.py`
    - `:101` 질문 `options`, `:155` `ChangeSet.removed/updated`, `:175` `_StubEngine`의 `options=["add"]`, `:193` `max_rounds=5` → `max_answers`
    - `terrain` 키 fixture
    - 고친 테스트 이름을 code-summary에 전수로 적는다.
  - 의도된 변경(C-3), `tests/api/test_augment_api.py`
    - `:16` 스텁의 `AugmentationQuestion(…, options=…)`, `:24` 스텁 `revert`의 반환
    - `:53-54` `answer`가 `ChangeSet`이라는 가정 → `AnswerResult`
    - `:63-65` revert 204 → 200 + run
  - TP-U3-4: 무작위 이슈·답 1~5개, ignore가 섞인 열, run 밖 편집 하나 → 그 변경이 가장 나중이면 `RevertConflictError`이고 상태가 그대로다. 아니면 `RevertOrderError`다.
  - TP-U3-5: 신탁은 목록 속성을 id마다 센다.
  - EX-7, EX-8, EX-9
  - FD R-08a: converged에서 unignore → open, stopped에서 unignore → 409, ignore가 `answers`를 올린다.
  - NFR-5 단언
    - 같은 스냅샷 다시 탐지 → LLM 0
    - 지식 하나 고침 → 판정 ≤ 1
    - 61번째 호출 없음
    - 근거 없음 → 판정 0
  - 잠금: 같은 run에 답 둘을 동시에 → 하나씩, 기록 둘
  - LLM 없는 run 시작 → 템플릿, 호출 0

### Step 7 — U7 이월: 백엔드
- [ ] 7.1 설정
  - `TOPOLOGY_DEFAULT_BASE`·`WorldTuning.default_base`·`weights.py:15-17` 별칭 셋을 지운다(A3-15, C10).
    - `weights.py:22`는 `base_weights[str(kind)]`다. 빌더가 이미 모르는 종류를 `adjacent`로 바꾼다.
    - 호출처: `settings.py:110·213`, `tuning.py:50`, `tests/shared/test_config.py:148·157`, `tests/world/topology/test_topology.py:170-174`
  - 지형·가중치 표를 `FiniteFloat`로 바꾼다(§3 NaN).
  - `tests/shared/test_config.py`의 `_clean_env` fixture가 U7 키 전부를 지운다(U7 테스트 메모).
- [ ] 7.2 왜곡도와 지지도
  - Q6=A(BR-U3-38): `DistortionService.set_region_distortion`의 UoW 하나에서 설정, 몫, 사건 기여(`update_event`), 타임라인 `event_contributions_cleared`를 쓴다.
    - EX-12
    - 롤백 테스트: 타임라인 쓰기 실패 → 셋 모두 그대로
    - 의도된 변경 C-5: `tests/play/test_play_services.py:140`, `tests/api/test_play_gm_api.py:86`
  - #9: 지지도 반올림. 예제 0.35 + 0.1 → 강한 소문
- [ ] 7.3 사건 제안과 세계 상태
  - #13 enum 비교
  - #14 예산 순서
  - #15 `WorldState.max_event_suggestions`(`play/models.py:641`), `WorldStateService`가 채운다.
  - §3: 월드 기준 지역 맞추기, `pick_brief_regions` 정렬, `ID_MAX` 없음, 빈 `shown`
  - C11 `system()` 삭제·`_prompt`, C13 `normalize_name`
  - 테스트: `tests/play/test_gm_events.py`, `tests/play/test_world_state.py`
- [ ] 7.4 엔진·지식 읽기
  - C2 `region_sources(lineage=)`(호출처는 이월 표)
  - C3 `neighbour_map`만
  - C4 `region_name`·`where`(호출처는 이월 표)
  - C5 `deed_ids=`, C6 `/log?limit=`, C9 기본값, C12 `region_rows`·`FRESH`
  - §3 이름 summary: `rumor_spread`, `deed_voided.region_names`
  - 테스트: 사라진 지역 이름 폴백, 평행 간선·자기 고리, `limit`
- [ ] 7.5 대화·저장
  - §3 `say` try 좁히기(판단·서술 같게)
  - C14 `one_line` 자르기 하나로(`narrator.py:32·80`, `suggest_context.py:95`)
  - C17 `retelling` 정규화와 계약 테스트(탭·줄바꿈·NBSP)
  - C18 `UtcDateTime` 쓰기 변환과 +09:00 왕복
- [ ] 7.6 API 쪽 이월
  - §3 NaN 값 → `Field(allow_inf_nan=False)`, 422 테스트 셋
  - #12 409 본문 고정 테스트(`session is closed`, `turn in progress`)

### Step 8 — API (BLM §7과 Step 1.3 정정)
- [ ] 8.1 `api/uploads.py`(NFR §1.1, R-04·R-05)
  - `BodyLimitMiddleware`(경로별 한도 표)를 `api/main.py`에 단다.
  - 칸별 상수와 `read_capped(file, limit)`, 이미지 매직 바이트 판별(PNG·JPEG·WebP)
  - `build/upload`: `concept_arts` 칸, 칸 검사(개수·크기·메모 60,000자·형식)
  - 지도 JSON 422 고정 문구(R-08)
- [ ] 8.2 편집 경로 `api/routers/world.py`
  - BLM §7 표 전체를 단다.
    - `PUT regions/{r}`·`POST regions`·`GET regions/{r}/editor`
    - 연결 둘
    - 지식 다섯
    - NPC 셋
  - `GET /worlds` 응답은 그대로다(4.7에서 `catalog`로 옮김).
- [ ] 8.3 지역 삭제와 세션(BLM §2, BR-U3-16)
  - `locus/play/session_service.py::open_player_regions(world_id) -> dict[str, list[str]]`
  - 라우터
    - 열린 세션의 GM 리스(`play.guard.hold`)를 `ExitStack`에 잡는다. 턴 중이면 409이고 `ExitStack`이 잡은 것을 놓는다(`hold`는 기다리지 않으므로 교착이 없다).
    - `protected`를 만든 뒤 `delete_region`을 부른다.
    - `RegionInUseError` → 409와 `session_ids`
  - `delete-plan`은 같은 계산으로 `blocked_by_sessions`를 채운다(리스 없음, 표시용).
  - play가 없으면 보호 집합은 비고 리스도 없다.
  - 알려진 한계는 위 절과 같다.
- [ ] 8.4 보강·wiki·초안 경로
  - `POST runs`(LLM 없이도 200), `GET runs/{id}`, `POST answer`(→ `AnswerResult`), `POST revert`(200 + run, 409 셋), `POST unignore`
  - `GET priors`·`GET prior-refs`·`DELETE priors/{p}`
  - `POST regions/{r}/npc-drafts`: LLM 없으면 503, `n` 범위 밖이면 400
- [ ] 8.5 `api/schemas.py`·`errors.py`
  - `EditorRegionView` DTO: 지식 진술에만 `*_ko`를 붙인다(`enrich`). NPC는 원문이다.
  - 지식 삭제 라우터는 `purge_translations(loc, kind="knowledge", ids=[k])`를 부른다(BR-U3-3).
  - 오류 매핑: `RegionInUseError`, `ChangeAlreadyRevertedError`, `RevertOrderError`, `RevertConflictError`, `RunFinishedError` → 409, 고정 문구
- [ ] 8.6 테스트
  - `tests/api/test_world_editor_api.py`
    - 경로마다 정상·400·404·409
    - 지역 삭제: 플레이어가 있으면 409와 세션 id, 턴 중이면 409, 리스를 쥔 사이 이동 시도 → 409
    - LLM 없는 컨테이너(NFR-4): 편집 200, 초안 503, 보강 200·LLM 0
    - 구조 단언 ④: 월드마다 `find_nodes` 2회, `get_edges` 0회
    - 구조 단언 ⑤: 캐시 적중 = 스냅샷 로드 0, 버전 읽기 1
  - `tests/api/test_uploads.py`
    - 상한 + 1바이트 → 413, 다른 칸 무사
    - PNG 이름의 텍스트 → 422
    - 49 MiB(헤더 있음) → 413, 라우터 미호출
    - 청크(헤더 없음) → 413
    - World File 21 MiB → 413
    - `/health`·JSON 라우트 무사
  - `tests/api/test_augment_api.py`: 6.9의 의도된 변경, unignore·revert 409 경로

### Step 9 — 프론트엔드: 에디터 (frontend-components.md)
붉은 구간: 9.2의 타입 변경부터 9.8 끝까지 `tsc`·vitest가 붉을 수 있다. 옛 `RegionPanel`·루트 `AugmentPanel`·`EditorPage`가 옛 API와 타입을 쓰기 때문이다. Step 9는 9.10 끝에 GREEN이고, 커밋은 Step 9 끝에 한 번이다.
- [ ] 9.1 `api/http.ts`: `HttpError(status, body)`, `statusOf(err)`(C16). `conflictKind`는 `HttpError`의 본문을 읽는다.
  - 〔검토 02 처리 R-16〕 `HttpError.message`는 지금 형식 `${status} ${statusText}: ${body}`를 유지한다. 그래서 `String(e)`·`includes("404")`를 쓰는 곳은 바뀌지 않는다. 문자열만 쓰는 거절 fixture(`deeds.test.tsx:125`, `dialogue.test.tsx:250·293`, `play.test.tsx:169`)는 그대로 둔다.
  - 호출처와 fixture는 이월 표 C16에 있다.
  - 이 하위 단계는 단독으로 GREEN이다(타입 변경 없음).
- [ ] 9.2 `api/world.ts`·`types.ts`
  - frontend §3의 API를 더한다. `revert`는 run을 받고 `unignore`를 더한다.
  - `deleteNode`, 옛 `startAugment`·`submitAnswer`·`revertAugment` 이름을 없앤다.
  - 새 타입, `WorldExport.npcs`, `BuildReport.backup_path`·`priors_created`, 보강 타입 갱신(`actions`, `target`, `answers`, `llm_budget_exhausted`)
- [ ] 9.3 `features/editor/drag.ts`(순수: 4px 판정)와 `MapCanvas.tsx`
  - 도구 셋
  - `MapOverlay`에 `onSelectConnection`·`onBackground`를 더한다. 지금 `onMove` 저장 경로는 판정을 지난 뒤에만 부른다(EX-11).
- [ ] 9.4 인스펙터와 삭제 확인
  - `RegionInspector.tsx`(조합), `RegionForm.tsx`(부모 후보에서 자기·자손 제외), `ConnectionList.tsx`(상세·prior/끊김), `KnowledgeList.tsx`(번역 + 원문 토글, 스코프), `NpcEditorList.tsx`(원문), `NpcDraftCards.tsx`
  - `ConfirmDelete.tsx`: 삭제 계획 대화. `blocked_by_sessions`면 확인을 끈다.
- [ ] 9.5 `UnscopedPanel.tsx`, `AugmentPanel.tsx`, `WikiPanel.tsx`
  - AugmentPanel
    - run 유지, 서버 `actions`만 버튼
    - 가장 나중 변경에만 되돌리기, ignore한 이슈는 "다시 묻기"(unignore)
    - 409·404 안내, `llm_budget_exhausted` 안내
- [ ] 9.6 `BuildPanel.tsx`·`BuildReportPanel.tsx`, `WorldFileBar.tsx`
  - 교체·세션 닫기 확인, 413·422 서버 문구 표시, 내려받기, "열린 세션 N개" 띠
- [ ] 9.7 `routes/HomePage.tsx`와 `App.tsx`(BR-U3-34, C-7)
  - `/` 넘김을 없애고 `*`는 `/`로 보낸다.
  - [편집] → `/editor/:w`
  - [세션 시작]은 `exportWorld` → `NewSessionForm` → `startSession(w, body)` → `/play/:sid`다.
  - 빈 목록
    - [데모 불러오기]: `api.loadDemo("aldermoor", …)` → `/editor/aldermoor`
    - [자료로 만들기]: world id 입력 → `BuildPanel`(9.6) 모달 → 성공하면 `/editor/:w`
- [ ] 9.8 `routes/EditorPage.tsx` 다시 쓰기(조합만)
  - `web/src/Toolbar.tsx`, 루트 `AugmentPanel.tsx`를 지운다.
  - `RegionPanel.tsx`는 `features/gm/RegionKnowledgePanel.tsx`가 되고 ✕와 `deleteNode`가 없어진다(BR-U3-33, C-8).
  - 호출처: `routes/GmPage.tsx:4`, `routes/EditorPage.tsx:3·5·7`, `__tests__/components.test.tsx:5·20-23`(`upsertRegion`·`startAugment`·`submitAnswer` mock)
- [ ] 9.9 `i18n.ts`: frontend §4의 키(ko·en 같은 집합) + `augment.budget`·`augment.unignore`·`build.tooLarge`
- [ ] 9.10 테스트
  - `editor.test.tsx`, `home.test.tsx`: frontend §6 표 전부, EX-11, 빈 목록의 데모·만들기
  - `components.test.tsx:85·104·376`: import 경로와 ✕ 없음(C-8)

### Step 10 — 프론트엔드: U7 이월
- [ ] 10.1 GM: #6 `refreshRef`, #8 `onDraft`, #15 `maxSuggest`, C1 `getWorldState`, C8 `mapLimit`, C15 `onMouseUp` 삭제, C19 핸들러 합치기, §3 `PlayerStrip` 404(`statusOf`)
- [ ] 10.2 플레이: #7 prop 나누기, #12 `DialoguePanel` `conflictKind`·`onClosed`, §3 `act` gen, §3 `EDGE_SPACE` 선형, C6 `limit=30`, C7 마운트 읽기
- [ ] 10.3 타임라인: #10 지난 `event_created` 줄, A3-14 지역 id 없는 지난 줄은 `summary`
- [ ] 10.4 테스트(`gm.test.tsx`, `play.test.tsx`, `dialogue.test.tsx`): 각 항목 하나 이상, 지난 줄 fixture는 실제 모양

### Step 11 — 문서
- [ ] 11.1 `aidlc-docs/operations/operations.md`
  - "월드 에디터" 절을 새로 쓴다(nfr §1 NFR-8의 항목 + 알려진 한계).
  - U7 절의 `TOPOLOGY_DEFAULT_BASE`·제안 맥락 문장을 고친다(U7 §5).
- [ ] 11.2 `env.example`
  - `TOPOLOGY_DEFAULT_BASE`를 뺀다(`:70`).
  - 업로드 상한은 상수라고 한 줄 적는다.
- [ ] 11.3 문서 정확도(U7 §5)
  - `locus/shared/config/tuning.py:50` 주석(필드와 함께 사라짐)
  - `deeds/service.py:3`, `play/wiring.py:100` docstring
  - U7 frontend-components:113, U7 frontend-components §2.2·§4의 "1~5" → "1~서버 상한"(#15)
  - X3 BR-X3-5(C1과 같이)
  - U7 code-summary §4("U6 #10·#11 → DeedPanel")·§5 8.7 정정. 각 곳에 "〔U3 정정〕"을 단다.
- [ ] 11.4 `CLAUDE.md`(Status, 레이아웃: `locus/world/editor/`, `npc_drafts.py`, `features/editor/`, `routes/HomePage.tsx`, 테스트 수)와 `web/README.md`(`/`, 에디터 도구)

### Step 12 — 검증·요약
- [ ] 12.1 전체 게이트
  - `pytest`, `vitest`, `ruff`, `black --check`, `tsc --noEmit`, `mypy`(≤ 11)
  - `npm audit --omit=dev`(기록만)
  - 줄 수: `features/editor/*`·`routes/EditorPage.tsx`·`routes/HomePage.tsx`·`locus/world/editor/*` 각각 ≤ 250
  - `web/src`에 `dangerouslySetInnerHTML` 0곳
- [ ] 12.2 운영자 실행 명령을 code-summary에 적는다.
  - compose 기동 후 데모 월드에서 다음을 실제 Neo4j·OpenSearch로 돌린다: 지역 삭제(자식·NPC·연결), 연결 종류 바꾸기, 보강 한 바퀴, 업로드 빌드
  - `replace_nodes`·`delete_edges`의 실제 Cypher 확인
  - 편집 p95 측정 조건(N3-1)
- [ ] 12.3 `construction/U3-world-editor/code/code-summary.md`
  - 기준선과 결과, 바뀐 파일
  - 검증 번호와 테스트, 이월 결정의 구현 위치
  - 설계 이탈(알려진 한계 포함), 변이 확인 결과
  - 넘기는 것(U8)

### Step 13 — 게이트
- [ ] 13.1 코드 게이트를 제시한다. 승인 뒤 `/code-review`를 돌린다.

## 스토리 추적
| 스토리 | 단계 |
|---|---|
| US-2.1 | 3.2, 8.1, 9.6 |
| US-2.2 | 4.3, 4.4, 8.2, 8.3, 9.3, 9.4 |
| US-2.3 | 4.5, 8.2, 9.4, 9.5 |
| US-2.4 | 4.6, 8.2, 9.4 |
| US-2.5 | 5.1, 8.4, 9.4 |
| US-2.6 | 6.1~6.9, 8.4, 9.5 |
| US-2.7 | U2 회귀 테스트 유지(TP-U3-6, 4.8) |
| US-2.8 | 3.1~3.3, 8.4, 9.5 |
| US-6.2·6.3 | 8.1, 9.6 |
| US-6.4 | 4.6, 4.7, 9.7 |

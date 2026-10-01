# U3 월드 에디터 — Code Summary

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3 코드 생성을 마쳤습니다(Step 12). 월드를 만들고 고치는 화면이 생겨, 세계관 자료로 만든 월드를 사람이 다듬어 플레이에 넘길 수 있습니다. 이 문서는 바뀐 것과 그 검증을 모읍니다.

플랜: `construction/plans/U3-world-editor-code-generation-plan.md` (13단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `9228861`) | 결과 (Step 12.1) |
|---|---|---|
| pytest (`-q --no-cov`) | 735 | **850** (+115) |
| vitest | 94 | **124** (+30) |
| mypy (`locus api`) | 11 (6 파일) | 11 (같은 6 파일, U3 코드에는 0) |
| ruff · black · tsc | clean | clean |
| `npm audit --omit=dev` | moderate 2 (react-router) | 같음(의존성 변경 없음). 기록만, CI 강제는 U8 |
| 줄 수 ≤ 250 | — | 가장 큰 것: `locus/world/editor/regions.py` 233, `features/editor/MapCanvas.tsx` 212 |
| `dangerouslySetInnerHTML` | 0 | 0 |

## 2. 단계별 기록
- **Step 1**
  - 1.2 뼈대: `locus/world/editor/` 패키지는 4.1에서 만든다. 지금 만들면 같은 이름의 `editor.py`를 가려 `WorldEditor` import가 깨진다.
  - 1.2 뼈대: vitest 파일 둘(`editor.test.tsx`, `home.test.tsx`)은 9.10에서 만든다. 빈 테스트 파일은 vitest가 실패로 센다.
  - 1.3 정정은 다음 문서에 했다.
    - FD BLM §1.3·§4.2·§4.3·§7
    - domain-entities §4.2·§4.3·§4.4·§6·§8
    - business-rules BR-U3-8·23·27·28·41, TP-U3-2a(새로)·TP-U3-4
    - nfr-light §6(새 절)과 표시
- **Step 2**
  - `EdgeKey`, `GraphRepository.replace_nodes`·`delete_edges`, `SearchRepository.delete`를 더했다.
  - 어댑터
    - Neo4j: 라벨마다, (종류, identity 키)마다 UNWIND 하나. 제약 오류는 `ConstraintViolation`으로 바꾼다.
    - OpenSearch: `delete_by_query` 하나
    - 인메모리 가짜 둘
  - 임시 가짜는 아직 고칠 곳이 없다(새 경로가 쓰지 않는다).
  - `MATERIAL`을 `shared/text.py`로 옮겼다. 호출처는 넷이다.
  - 테스트 `test_port_contract.py` 13개
  - 변이: 가짜 `replace_nodes`를 병합으로 바꾸면 TP-U3-3이 실패한다(잡음).
  - pytest 748
- **Step 3**
  - `CommonsenseWiki`
    - `llm`을 선택 인자로 바꿨다.
    - `lookup_similar(…, fallback=)`, `created_priors`, `fallback_capped`
    - 정규화 질의로 중복을 없앤다. 상한은 `WIKI_FALLBACK_MAX = 40`이다.
  - 빌드
    - 참조 정리는 `증류 ∪ 생성`이다.
    - 토폴로지 단계 prior는 온톨로지 전에, 온톨로지 단계 prior는 지식 전에 저장한다.
    - 상한에 닿으면 경고를 남긴다. `BuildReport.priors_created`(shared/models/reports.py)를 더했다.
    - 빌드가 받는 wiki가 대역 객체일 수 있어 `_created_priors(wiki)`는 `getattr`로 읽는다(기존 `test_world_builder_passes_world_wiki_to_fresh_builders`).
  - `locus/world/refs.py`(`ConnectionKey`, `NameRef`): 플랜 이탈이다. wiki가 편집 패키지보다 먼저라서다.
  - wiki 모델과 관리
    - `wiki/schemas.py`: `PriorRefView`·`PriorUsage`·`BrokenRef`
    - `WikiAdmin.list_priors`(모델), `prior_refs`, `broken_refs`, `delete_prior`(그래프 → 검색, 없어도 검색 삭제 뒤 404)
    - 순수 `prior_ref_view`·`usages`·`broken`
  - 테스트 `test_wiki_evidence.py` 8개(EX-10, 중복·상한, 검색 전용, 참조·끊김, 재시도 삭제)
  - 변이
    - 빌드 참조 필터에서 생성 prior를 빼면 EX-10이 실패한다.
    - 질의 중복 제거를 끄면 정규화 테스트가 실패한다.
    - 둘 다 잡았다.
  - pytest 756
- **Step 4**
  - `locus/world/editor/` 패키지: `models`·`writes`·`regions`·`connections`·`knowledge`·`npcs`·`entities`·`catalog`·`bundle`
    - 가장 긴 모듈은 `regions.py` 233줄이다.
  - 옛 `editor.py`를 지웠다. `WorldContainer.editor` → `editors` + `catalog`
  - 라우터
    - `GET /worlds`는 `WorldCatalog`를 쓴다(응답 그대로).
    - `PUT` 지역·지식은 새 클래스를 부른다.
    - `DELETE /nodes`를 지웠다(C-2).
  - 보강: `apply`·`revert`·엔진 인자를 `editors`로 바꿨다(R-14). REMOVE는 `Editors.delete_any`다.
  - 의도된 변경(`# U3 intended change`)
    - `test_services.py`: `test_graph_editor_upsert_and_delete`, `test_deleting_a_region_cascades_to_its_npcs`
    - `test_world_api.py`: `test_delete_node_endpoint`
  - 픽스처 교체(동작 불변)
    - `test_services.py`의 캐시·메타 테스트 셋
    - `test_world_api.py`의 `_Editor` → 실제 `Editors`, `catalog`
    - `test_augment_api.py`의 `editors=None`
    - `test_augmentation.py`의 `_Editor` → 실제 `Editors`(R-14), 그것을 쓰는 테스트 셋
  - 새 테스트
    - `tests/world/editor/` 22개: `test_editors.py` 16, `test_region_delete.py` 6
    - 도우미 `helpers.py`: `Meter`, 끊는 가짜, `Stack`
    - 생성기 `editable_worlds`·`edit_ops`
  - 변이(모두 잡음)
    - TP-U3-2a: ① 순서를 옛 순서로 되돌림, ④ 순서를 노드 먼저로 바꿈
    - TP-U3-3: 교체를 병합으로 바꿈
    - set_prior_ref: 옛 쌍을 지우지 않음
  - pytest 778
- **Step 5**
  - `locus/world/npc_drafts.py`: `NpcDraftService`, `NpcDraft`, `NpcDraftResult`, `draft_prompt`
  - 상한
    - 지역: 이름 60, 경로 80, 설명 500
    - 지식: 상위 8개(신뢰도 순), 제목 60·진술 200
    - 이름: 30개(그 지역 먼저, 이름순)
  - `MATERIAL` 시스템 가드를 둔다. 출력은 자른다.
  - `WorldContainer.npc_drafts`(LLM이 있을 때만)
  - 테스트 7개: EX-6, 실패, `n`·지역 검사, 6,000자, 주입, 자르기
  - pytest 785
- **Step 6**
  - 보강 모델(`types.py`)
    - `Issue.key`·`target_kind`·`field`·`broken_id`, `QuestionTarget`, `actions`
    - `ChangeSet.nodes_after`·`edges_*`, `AnswerResult`
    - `AugmentationConflict` 계열 409 넷
  - 탐지기(`detectors.py`)
    - 스냅샷 위 순수 다섯(dangling은 id 속성·목록은 id마다, unscoped 새로)
    - `conflict_pairs`(지식, 지형) 쌍과 `select`(키·무시·심각도 20)
  - 질문(`questions.py`)
    - 대상 이름, 고정 행동
    - 다듬기는 탐지마다 5개, 이슈 키 캐시, 입력은 템플릿 + 대상 필드
  - 엔진(`engine.py`)
    - 편집 클래스를 주입받는다.
    - wiki_conflict: 검색 전용(`fallback=False`), 근거가 없으면 판정 없음, 쌍 20, 판정 캐시(지식 id, 진술, 지형)
    - 실패한 판정은 캐시하지 않는다.
  - run 저장(`run_store.py`): `RunState`(run, 잠금, 캐시 셋), 월드마다 20개
  - 서비스(`service.py`)
    - 답 상한 30, LLM 예산 60
    - 상태 전이와 R-08a
    - 되돌리기 검사 순서: 404 → 이미 → 순서 → 충돌
  - `apply.py`: 위 실행 메모의 방식이다. 되돌리기는 충돌 검사 뒤에 노드·엣지·검색 문서를 되살린다.
  - 조립: 보강은 LLM 없이도 조립한다. LLM이 있으면 wiki는 `CommonsenseWiki(search, None, …)`(검색 전용)이다.
  - 라우터(6.8a, R-15)
    - `answer` → `AnswerResult`, `revert` → 200 + run, `GET runs/{id}`, `unignore`
    - 409 매핑(`api/errors.py`), `UnignoreIn`(`api/schemas.py`)
  - 의도된 변경(`# U3 intended change`)
    - `test_augmentation.py`: `test_detect_gaps_empty_region_and_dangling`, `test_question_generator_template`, `test_run_store_roundtrip`, `test_service_loop_converges`, `test_engine_apply_and_revert_invalidate_cache`
    - `test_augment_api.py` 전체 머리말(C-3): answer·revert 단언 바뀜
  - 같은 이름으로 API만 바꾼 테스트: `test_detect_low_confidence`, `test_detect_orphans`, `test_apply_*` 둘(4.7에서 바뀜)
  - 새 테스트(보강 25 + API 6)
    - TP-U3-4·5, EX-7·8·9
    - B1 대상 무시, 허용되지 않은 행동, 바깥 편집 충돌, R-08a 전이
    - 동시 되돌리기 잠금
    - LLM 캐시·상한·예산, 근거 없음, LLM 없는 run
  - 변이(모두 잡음)
    - 되돌리기에서 엣지 복원을 빼면 TP-U3-4가 실패한다.
    - 충돌 검사를 빼면 바깥 편집 테스트가 실패한다.
    - 순서 검사를 빼면 TP-U3-4가 실패한다.
  - pytest 803
- **Step 7** (U7 이월, 백엔드)
  - 7.1
    - `TOPOLOGY_DEFAULT_BASE`·`default_base`·`weights.py` 별칭 셋을 없앴다(A3-15·C10). 표에 없는 종류는 `adjacent` 값이다.
    - 표 env는 `FiniteFloat`다. NaN·Infinity·`1e400`이면 기동이 실패한다.
    - `_clean_env`는 Settings의 모든 env를 지운다.
  - 7.2: Q6=A(EX-12), 같은 UoW 롤백. #9 `settle`(반올림은 변화 방향을 거스르지 않는다)
  - 7.3
    - #13 enum 비교, #14 예산 순서, #15 `WorldState.max_event_suggestions`
    - §3: 월드 기준 지역 맞추기, 잎·깊이·이름 정렬(`parent_ids`), id 자르지 않음, 빈 지역이면 호출 없음
    - C11 `system()` 삭제·`_prompt`, C13 `normalize_name`
  - 7.4
    - C2 `region_sources(lineage=)`, C3 `neighbour_map`만, C4 `base.names_of`·`region_name`·`where`·`SnapshotNames`
    - C5 `deed_ids`, C6 `/log?limit`, C9 기본값, C12 `region_rows`·`FRESH`
    - §3 `rumor_spread` 이름 summary, `deed_voided.region_names`
  - 7.5: `say`·판단·서술의 try 좁히기, C14 `one_line` 자르기, C17 `retelling` 정규화(모델 검증기, 두 어댑터 `!= ""`), C18 UTC 쓰기 변환
  - 7.6: NaN 422 셋(+ 422 처리기), 409 본문 고정
  - 테스트
    - `tests/play/test_u3_carry.py` 22개, `tests/api/test_u3_carry_api.py` 6개
    - 기존 테스트 의도된 변경: `test_config.py`(기본값 단언·env 표), `test_topology.py`(A3-15)
  - 변이(모두 잡음): #13 문자열 비교로 되돌림, #14 옛 자르기, C17 검증기 제거, C18 변환 제거
  - pytest 833
- **Step 8**
  - `api/uploads.py`
    - 순수 ASGI `BodyLimitMiddleware`(48 MiB, World File 두 경로 20 MiB, 헤더·청크 두 경로)
    - 칸 상한·`read_capped`·`read_memo`·`read_image`(PNG·JPEG·WebP 앞 바이트)
  - `build/upload`에 `concept_arts`. 지도 JSON 422와 World File 422는 고정 문구다.
  - `api/routers/world_editor.py`(새 모듈, `world.py`가 include)
    - BLM §7 전 경로
    - 지역 삭제는 열린 세션 GM 리스를 `ExitStack`으로 잡고, `protected`(지역 → 세션 id)로 409를 낸다.
    - `delete-plan`의 `blocked_by_sessions`
  - `SessionService.open_sessions`·`open_player_regions`
  - `api/schemas.py`: `LocalizedKnowledge`, `EditorRegionViewOut`(지식만 `*_ko`), `ConnectionSave(previous_kind)`, `ScopesIn`, `PriorRefsOut`, `localize_editor_view`·`localize_knowledge`
  - 테스트 17개
    - `test_world_editor_api.py` 10: 경로, 409 둘, 리스 중 이동 시도 회귀, 구조 단언 ④⑤, LLM 없는 조립
    - `test_uploads.py` 7
  - 변이: 청크 세기를 끄면 청크 테스트가 실패한다(잡음).
  - pytest 850
- **Step 9** (프론트엔드 에디터)
  - 9.1 `HttpError`·`statusOf`(메시지 형식 유지, R-16). `conflictKind`가 이것을 쓰고, `DialoguePanel`의 404·503 판정도 바꿨다. C16 거절 fixture 12곳을 `HttpError`로 바꿨다.
  - 9.2
    - `api/world.ts`: 편집 경로 전부, `startRun`·`getRun`·`answer`·`revert`·`unignore`. `deleteNode`·`startAugment`·`submitAnswer`·`revertAugment`·`upsertRegion`은 지웠다.
    - `types.ts`: 에디터·보강·wiki 타입, `BuildReport.backup_path`·`priors_created`
  - 9.3
    - `features/editor/drag.ts`(4px)
    - `MapOverlay`: 실제로 끌었을 때만 `onMove`, `draggable`, `onBackground`, `onSelectConnection`, 선택된 연결 굵게
    - `MapCanvas`: 도구 셋, 지역·연결 폼
  - 9.4~9.6: `RegionInspector`(조합) + `RegionForm`·`ConnectionList`·`KnowledgeList`(스코프 고르기)·`NpcEditorList`·`NpcDraftCards`, `ConfirmDelete`, `UnscopedPanel`, `AugmentPanel`, `WikiPanel`, `BuildPanel`·`BuildReportPanel`, `WorldFileBar`(열린 세션 띠 → SessionBar 피커)
  - 9.7: `routes/HomePage.tsx`. `/`가 목록이고 `*`는 `/`로 간다.
  - 9.8
    - `EditorPage`는 조합만 한다.
    - `Toolbar.tsx`·루트 `AugmentPanel.tsx`를 지웠다.
    - `RegionPanel.tsx` → `features/gm/RegionKnowledgePanel.tsx`(✕ 없음)
  - 9.9: i18n 키 약 150개(ko·en 같은 집합). `augment.status`는 답 수를 보인다.
  - 9.10
    - `editor.test.tsx` 14, `home.test.tsx` 3
    - `components.test.tsx` 의도된 변경(`# U3 intended change` 주석)
      - RegionPanel 두 묶음(import·✕ 없음)
      - AugmentPanel
      - App 라우팅 둘(C-7)
      - 데모 불러오기 → World File 불러오기의 두 단계 확인
  - 변이: `MapOverlay`가 매번 `onMove`를 부르게 하면 EX-11이 실패한다(잡음).
  - 줄 수: `features/editor/*`·`EditorPage`·`HomePage` 모두 250 이하이고, 가장 큰 것은 `MapCanvas` 212줄이다.
  - `dangerouslySetInnerHTML` 0곳
  - vitest 111
- **Step 10** (U7 이월, 프론트엔드)
  - 10.1
    - `GmHub`: #6 `refreshRef`, #15 서버 상한 `maxSuggest`(`getWorldState` 한 번), C1 "전체 생성"이 `getWorldState` 한 번, C8 `mapLimit`
    - `CommitRange`: C15 `onMouseUp` 삭제, C19 호출자 핸들러 먼저, #8 `onDraft`
    - `DistortionPanel`: 이름표가 초안을 따른다.
    - `PlayerStrip`: 404만 "플레이어 없음"
  - 10.2
    - `ActionBar`: #7 `closed` 분리(입력은 턴 중에도 됨), `EDGE_SPACE` 선형, `maxLength`
    - `DialoguePanel`: #12 닫힌 세션 문구 + `onClosed`
    - `PlayPage`: §3 `act`의 gen 확인, C6 `getLog(sid, 30)`, C7 마운트 한 번 읽기
  - 10.3: `timelineText`
    - #10 옛 표시 줄은 category가 있을 때만 새 템플릿을 쓴다.
    - A3-14 지역 없는 지역 줄은 summary를 보인다.
    - 못 채운 `{param}`이 남으면 summary를 보인다.
  - 테스트
    - gm 7, play 4, dialogue 1
    - 의도된 변경: `gm.test`·`components.test`의 전체 생성 둘(C1), `play.test`의 폴링 순서(C7)
  - 변이(모두 잡음): #6 낡은 `refresh`, `EDGE_SPACE`의 옛 정규식
  - vitest 123
- **Step 11** (문서)
  - 11.1 `operations.md`: "World editor" 절(NFR-8 항목, 업로드 상한, 지역 삭제 순서와 재시도, 알려진 한계). U7 절의 `TOPOLOGY_DEFAULT_BASE`·제안 맥락 줄에 〔U3 정정〕
  - 11.2 `env.example`: `TOPOLOGY_DEFAULT_BASE` 삭제, 업로드 상한은 상수라는 한 줄
  - 11.3 〔U3 정정〕: `deeds/service.py` docstring, `play/wiring.py` 주석, U7 frontend-components(재생성 개수, "1~서버 상한" 둘), X3 BR-X3-5(C1), U7 code-summary §4(#11)·§5(8.7). `tuning.py:50` 주석은 필드와 함께 Step 3에서 사라졌다.
  - 11.4 `CLAUDE.md`(Status, 레이아웃, 테스트 974), `web/README.md`(화면, 에디터 도구)
  - **바로잡음(계획 밖)**: Step 9.8에서 `Toolbar`를 지울 때 이 브라우저에서만 쓰는 배경 지도 고르기도 빠졌다. FD는 이것을 없애기로 정하지 않았다. README를 맞추다 찾았고, `EditorPage`에 GM 화면과 같은 고르기를 되살렸다. 테스트 1(`components.test`), 변이(`mapImageUrl` 빼기) 잡음.
  - vitest 124

## 3. 바뀐 파일
- **새로 만든 것**
  - 백엔드: `locus/world/refs.py`, `locus/world/editor/`(10개 모듈, 옛 `editor.py` 대신), `locus/world/npc_drafts.py`, `api/uploads.py`, `api/routers/world_editor.py`
  - 웹: `features/editor/`(14개 + `drag.ts`), `routes/HomePage.tsx`, `features/gm/RegionKnowledgePanel.tsx`(옛 `RegionPanel`에서 옮김)
  - 테스트: `tests/shared/storage/test_port_contract.py`, `tests/world/wiki/test_wiki_evidence.py`, `tests/world/editor/`, `tests/world/test_npc_drafts.py`, `tests/play/test_u3_carry.py`, `tests/api/{test_world_editor_api,test_uploads,test_u3_carry_api}.py`, `web/src/__tests__/{editor,home}.test.tsx`
- **고친 것**
  - shared: 저장 포트·어댑터(`base`·`neo4j_repo`·`opensearch_repo`), `text.py`(`MATERIAL`), `models/reports.py`, `config/{settings,tuning}.py`
  - world: `wiki/`, `build.py`, `augmentation/`(전부), `wiring.py`, `topology/weights.py`
  - play(U7 이월): `distortion_service`, `rumor/`, `event/`, `world_state`, `models`, `base`, `turn/advancer`, `deeds/service`, `region_knowledge`, `player/service`, `npc/`, `gm/narrator`, `storage/`, `session_service`, `wiring`
  - api: `main.py`(미들웨어, 422 처리기), `errors.py`, `schemas.py`, `routers/{world,play}.py`
  - 웹: `api/{http,world,play}.ts`, `types.ts`, `i18n.ts`, `App.tsx`, `MapOverlay.tsx`, `routes/{EditorPage,GmPage,PlayPage}.tsx`, `features/gm/*`, `features/play/{ActionBar,DialoguePanel}.tsx`, `ui/CommitRange.tsx`, `setupTests.ts`
- **지운 것**: `locus/world/editor.py`, `web/src/Toolbar.tsx`, `web/src/AugmentPanel.tsx`(루트), `web/src/RegionPanel.tsx`, `DELETE /worlds/{w}/nodes/{n}`, `TOPOLOGY_DEFAULT_BASE`
- **문서**: `operations.md`, `env.example`, `CLAUDE.md`, `web/README.md`, 〔U3 정정〕 다섯 곳(Step 11)

## 4. 검증 번호와 테스트
| 번호 | 테스트 |
|---|---|
| TP-U3-1 (연결 쌍) | `tests/world/editor/test_editors.py` (생성기 `tests/world/strategies.py`) |
| TP-U3-2 (지역 삭제 뒤 끊긴 id 0) | `tests/world/editor/test_region_delete.py` |
| TP-U3-2a (n번째 쓰기에서 끊고 재시도) | `tests/world/editor/test_region_delete.py` (끊는 가짜 `helpers.py`) |
| TP-U3-3 (교체 왕복) | `tests/shared/storage/test_port_contract.py`, `test_editors.py` |
| TP-U3-4 (답 k개 → 모두 되돌림) | `tests/world/augmentation/test_augmentation.py::test_tp_u3_4_answers_then_undo_restore_the_world` |
| TP-U3-5 (dangling 신탁) | `test_augmentation.py::test_tp_u3_5_dangling_matches_a_direct_count` |
| TP-U3-6 (편집 뒤 World File 왕복) | `test_editors.py` |
| EX-1·4·5 | `test_editors.py` |
| EX-2·3 | `test_region_delete.py`, API 409는 `tests/api/test_world_editor_api.py` |
| EX-6 | `tests/world/test_npc_drafts.py` |
| EX-7·8·9 | `test_augmentation.py` (`test_ex7_…`, `test_ex8_…`, `test_ex9_…`) |
| EX-10 | `tests/world/wiki/test_wiki_evidence.py` |
| EX-11 | `web/src/__tests__/editor.test.tsx` (MapCanvas) |
| EX-12 | `tests/play/test_u3_carry.py` |
| BR-U3 화면 규칙(9·14·24·30·31·33~36) | `editor.test.tsx`, `home.test.tsx`, `components.test.tsx` |

## 5. 이월 결정의 구현 위치
| 출처 | 위치 |
|---|---|
| FD R-08·R-08a (ignore, unignore, 되돌리기 검사 순서) | `locus/world/augmentation/service.py`, `types.py`(`AugmentationConflict` 계열), `api/errors.py`, `POST …/runs/{id}/unignore` |
| FD R-11 (목록 id마다 이슈, 연결 대상, 부모 편집 순환 검사) | `augmentation/detectors.py`, `apply.py` → `ConnectionEditor.set_prior_ref`, `RegionEditor.upsert_region` |
| NFR R-01 (선별 기준 쓰기를 마지막에) | `locus/world/editor/regions.py` `delete_region` |
| NFR R-02 (구조 단언) | `tests/world/editor/test_region_delete.py`, `tests/api/test_world_editor_api.py` |
| NFR R-03 (보강 LLM: 검색 전용, 쌍 20, 다듬기 5, 예산 60) | `wiki/base.py` `lookup_similar(fallback=)`, `augmentation/{engine,questions,service}.py` |
| NFR R-04·R-05 (업로드 상한, 순수 ASGI) | `api/uploads.py`, `api/main.py` |
| NFR R-06 (UNWIND 일괄) | `shared/storage/neo4j_repo.py` `replace_nodes`·`delete_edges`, `opensearch_repo.py` `delete` |
| NFR R-07 (`MATERIAL`, 다듬기 입력) | `shared/text.py`, `augmentation/questions.py` |
| NFR R-08 (지도 JSON 422, 목록 응답 그대로) | `api/routers/world.py`, `editor/catalog.py` |
| U7 #6·#8·#15·C1·C8·C15·C19·§3 PlayerStrip | `features/gm/{GmHub,DistortionPanel,PlayerStrip}.tsx`, `ui/CommitRange.tsx` |
| U7 #7·#12·§3 act·EDGE_SPACE·C6·C7 | `features/play/{ActionBar,DialoguePanel}.tsx`, `routes/PlayPage.tsx` |
| U7 #9 | `play/rumor/dynamics.py` `settle` |
| U7 #10·A3-14 | `i18n.ts` `timelineText` |
| U7 #13·#14·§3 제안 | `play/world_state.py`, `event/{service,suggester,suggest_context}.py` |
| U7 §3 NaN·A3-15·C10 | `shared/config/{settings,tuning}.py`, `world/topology/weights.py`, `api/schemas.py`(`allow_inf_nan=False`) |
| C2~C5·C9·C12 | `region_knowledge.py`, `rumor/spread.py`, `play/base.py`, `turn/advancer.py`, `distortion_service.py` |
| C11·C13·C14 | `event/suggester.py`, `gm/narrator.py`, `event/suggest_context.py` |
| C16 | `web/src/api/http.ts` `HttpError`·`statusOf` |
| C17·C18 | `play/models.py`(검증기), `storage/{memory_repo,postgres_repo,schema}.py` |
| Q6=A (BR-U3-38, EX-12) | `play/distortion_service.py`, 타임라인 `event_contributions_cleared` |
| U7 §5 문서 | Step 11.3의 〔U3 정정〕 다섯 곳 |

## 6. 설계 이탈과 알려진 한계
- **이탈**(모두 플랜의 〔실행 메모〕에 적었다)
  1. `ConnectionKey`·`NameRef`가 `locus/world/refs.py`에 있다. wiki(Step 3)가 편집 패키지(Step 4)보다 먼저 이것을 쓴다.
  2. 편집 경로가 새 모듈 `api/routers/world_editor.py`에 있다. `world.py`가 include하므로 URL은 그대로다.
  3. `delete_region(…, protected)`의 `protected`는 `Mapping[region_id, session_ids]`다. 409 본문에 세션 id를 싣는다.
  4. `apply_answer(issue, question, answer, …)`가 이슈를 함께 받는다. 질문에는 이슈 종류·속성이 없다.
  5. `api/main.py`에 422 처리기를 더했다. NaN·Infinity가 든 422 본문이 JSON으로 쓰이지 못해 500이 되었다.
  6. `setupTests.ts`에 `PointerEvent` shim, `WorldFileBar`에 `FileReader` 폴백을 두었다(jsdom 한계).
  7. 표에 없는 연결 종류는 그 표의 `adjacent` 값이다(노브 없음, A3-15).
  8. 계획 밖: Step 9.8에서 함께 빠진 배경 지도 고르기를 Step 11에서 되살렸다.
- **알려진 한계**
  - 지역 삭제의 GM 리스는 시작 시점에 열린 세션에만 걸린다. 그 사이 새로 시작한 세션이나 GM 쓰기는 막지 못한다. 결과는 사라진 지역을 가리키는 세션 행이고, 화면은 이름 폴백과 404로 다룬다(제작자 한 명 전제 A-4).
  - 보강 run은 프로세스 메모리에 있다(월드마다 20). 재시작하면 사라지고 화면이 새 탐색을 권한다.
  - 업로드 상한은 상수다(env 아님).
  - `upsert_edges`는 엣지마다 왕복한다(데모 규모에서 받아들임, NFR R-06).

## 7. 변이 확인 (모두 잡음)
| 단계 | 변이 | 실패한 테스트 |
|---|---|---|
| 2 | 가짜 `replace_nodes`를 병합으로 | TP-U3-3 |
| 3 | 빌드 참조 필터에서 생성 prior 빼기 / 질의 중복 제거 끄기 | EX-10 / 정규화 테스트 |
| 4 | ① 옛 순서 / ④ 노드 먼저 / 교체를 병합으로 / `set_prior_ref`가 옛 쌍을 남김 | TP-U3-2a / TP-U3-2a / TP-U3-3 / 연결 테스트 |
| 6 | 되돌리기에서 엣지 복원 빼기 / 충돌 검사 빼기 / 순서 검사 빼기 | TP-U3-4 / 바깥 편집 / TP-U3-4 |
| 7 | #13 문자열 비교 / #14 옛 자르기 / C17 검증기 제거 / C18 변환 제거 / #9 반올림(PBT가 먼저 찾음) | 각 이월 테스트 |
| 8 | 청크 세기 끄기 | 청크 업로드 테스트 |
| 9 | `MapOverlay`가 매번 `onMove` | EX-11 |
| 10 | #6 낡은 `refresh` / `EDGE_SPACE` 옛 정규식 | gm·play 테스트 |
| 11 | `EditorPage`에서 `mapImageUrl` 빼기 | 배경 지도 테스트 |

## 8. 운영자 실행 (실제 Neo4j·OpenSearch, 이 호스트에서는 돌리지 않음)
이 호스트에서는 다른 컨테이너 `sigraph-neo4j-1`이 7474/7687을 쥐고 있어 compose 확인을 운영자가 한다(그 컨테이너는 멈추지 않는다).
```bash
docker compose up -d neo4j opensearch postgres
locus init-schema --world --play
locus world demo --name aldermoor --world aldermoor
uvicorn api.main:app --port 8000
W=http://localhost:8000/api/world/worlds/aldermoor
# 연결 종류 바꾸기: Riverton–Highcrag blocked → route (무게·근거·prior 유지, 엣지는 여전히 2개)
curl -s -X PUT $W/connections -H 'content-type: application/json' -d '{"world_id":"aldermoor","source_region_id":"region-riverton","target_region_id":"region-highcrag","kind":"route","weight":0.6,"previous_kind":"blocked","provenance":{"source":"input","generated_by":"designer"}}'
# 지역 삭제: 계획을 본 뒤 Frostreach(자식 Highcrag, NPC Sorrel)와 Highcrag(NPC 둘, 연결 한 쌍)
curl -s $W/regions/region-frostreach/delete-plan
curl -s -X DELETE $W/regions/region-frostreach
curl -s -X DELETE $W/regions/region-highcrag
curl -s $W/prior-refs        # broken이 비어 있어야 한다
# 보강 한 바퀴: run 열기 → 질문 하나 답 → 되돌리기
curl -s -X POST $W/augmentation/runs
# 업로드 빌드(LLM 필요): 메모 하나와 지도 이미지 하나
curl -s -X POST $W/build/upload -F memos=@notes.md -F images=@map.png
```
- Cypher 확인: Neo4j 쿼리 로그(`db.logs.query.enabled=INFO`)에서 `replace_nodes`가 라벨마다 `UNWIND … MERGE … SET n = row.props` 하나, `delete_edges`가 엣지 종류·키 모양마다 UNWIND 하나인지 본다.
- 편집 p95(N3-1): 데모 월드, 캐시가 따뜻한 상태에서 지역 `PUT` 100회의 응답 시간을 잰다. 기준은 p95 ≤ 150ms다(nfr-light NFR-3, N3-1).

## 9. 넘기는 것 (U8)
- `npm audit`의 react-router moderate 2건을 CI에서 다룬다(NFR R-07).
- 위 §8 운영자 실행 결과를 U8 배포 문서에 싣는다.
- `operations.md`의 "Web UI (U10)" 절 한 줄(검토/편집/보강 UI)은 U8 문서 정리에서 화면 넷(`/`, 에디터, GM, 플레이어)으로 고친다.
- 지역 삭제 리스 경합(§6)은 여러 제작자를 받을 때 다시 본다.

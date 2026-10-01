# U2 World File·캐노니컬 기반 — 생성 코드 리뷰 01 (`/code-review`, effort max)

- **대상**: U2 변경분(커밋되지 않은 작업 트리에서 U1 이동분 제외, 약 90개 파일)
- **일시**: 2026-09-29T23:30Z 요청 → 2026-09-30T00:23Z 결과 (10 finder angles → 76 candidates → 15 verified + tail)
- **처리 일시**: 2026-09-30 — 15/15 처리(15 수정), tail 항목 대부분 수정, 나머지는 기록
- **검증 후 상태**: pytest **388** (373 → +15 회귀 테스트), vitest **31** (30 → +1), ruff/black/tsc/vite clean, mypy **12** (변동 없음)

| # | 파일 | 요지 | 처리 | 테스트 |
|---|---|---|---|---|
| 1 | `shared/storage/persistence.py` | 그래프 제약 위반 뒤에도 검색 문서를 색인해 다른 월드 문서를 덮어씀 | **수정** — 그래프 저장 실패 시 검색 색인을 건너뜀 | `test_storage.py::test_persist_failures_are_errors_not_warnings` |
| 2 | `world/build.py` | 삭제 뒤 커밋 단계 예외가 리포트 없이 빠짐(500); 온톨로지의 LLM 실패는 조용히 degrade | **수정** — 커밋 단계 예외 → `ok=False, replaced=True, backup_path` 리포트; 임포터 동일. 코로보레이션·dedup·reconciler의 graceful degrade는 U1 이전 설계(기록: U8 hardening) | `test_build.py::test_commit_failure_after_delete_is_reported_not_raised` |
| 3 | `web/.../EditorPage.tsx` | 데모 버튼이 `confirm=true`를 박아 열린 세션을 묻지 않고 닫음 | **수정** — confirm=false 호출 → 409면 Modal로 확인 뒤 재시도 | vitest "asks before closing open sessions…" |
| 4 | `shared/storage/neo4j_repo.py` | 같은 두 노드 사이 관계/연결이 종류가 달라도 MERGE로 합쳐져 왕복에서 유실 | **수정** — 엣지 identity: 관계는 `id`, 연결은 `kind`로 MERGE 키; 인메모리 가짜 동일 | `test_edges_of_different_identity_coexist`, `test_upsert_edges_cypher_merges_on_identity` |
| 5 | `world/topology/hierarchy.py` | 레벨 없는 구조화 지도가 전부 town이 되어 계층이 사라짐 | **수정** — 수집기가 parent 사슬에서 레벨을 추론(leaf=town, 그 위 province, continent) + 경고. 같은 레벨로 라벨된 부모는 설계대로 경고 | `test_merge.py::test_level_less_structured_map_infers_a_hierarchy` |
| 6 | `api/routers/world.py` | 세션을 검증·실행 전에 닫아 실패해도 되돌릴 수 없음 | **수정** — 확인은 먼저(409), 닫기는 실제 교체 성공 뒤; 데모 이름·입력 파일은 게이트 전에 검증; CLI 동일 | `test_replace_with_open_sessions_needs_confirm_and_closes_only_open` |
| 7 | `api/routers/world.py` + `play/wiring.py` | LLM 없으면 play 미조립 → 열린 세션 게이트가 사라짐 | **수정** — `assemble_play`가 LLM 없이 세션·왜곡도·지역 뷰를 조립, 소문·사건·턴은 None → gm 라우트 503 | `test_wiring.py::test_play_assembles_without_llm_and_gm_routes_answer_503` |
| 8 | `world/editor.py` | 지역 삭제 뒤 NPC `home_region_id`가 허공을 가리켜 왕복 실패 | **수정** — 지역 삭제가 그 지역 NPC를 함께 삭제(반환값에 id). NPC 검색 문서 정리는 U3 에디터 | `test_services.py::test_deleting_a_region_cascades_to_its_npcs` |
| 9 | `worldfile/export.py` + 로더 | 건너뛴 노드의 엣지가 그대로 export되어 재import 실패; `load_warnings` 미노출 | **수정** — 로더가 끝점 없는 엣지·NPC를 걸러 경고로 남김. UI 노출은 U3 | `test_loader.py::test_loader_drops_edges_to_missing_nodes` |
| 10 | `api/routers/world.py` | `async` 라우트에서 동기 빌드/임포트 → 이벤트 루프 정지 | **수정** — 업로드 라우트를 동기 `def`로(스레드풀), `file.file.read()` | (구조 변경; 기존 업로드 테스트 통과) |
| 11 | `shared/storage/opensearch_repo.py` | 빈 임베딩 벡터 색인·bulk 오류 무시 | **수정** — 빈 벡터는 필드 생략, bulk `errors`면 RuntimeError → persist-search error | `test_opensearch_bulk_omits_empty_vectors_and_reports_errors` |
| 12 | `world/editor.py`, `wiki/admin.py` | 색인 실패 시 캐시 무효화가 안 돼 낡은 스냅샷 유지 | **수정** — `finally`에서 메타 touch + 무효화; WikiAdmin도 메타 touch | `test_services.py::test_editor_invalidates_even_when_indexing_fails` |
| 13 | `api/routers/world.py` | 비ASCII 월드 id 다운로드 500 | **수정** — RFC 5987 `filename*=UTF-8''…` + ASCII fallback | `test_world_file_download_supports_non_ascii_ids` |
| 14 | `world/build.py` | 교체 빌드에서 옛 prior를 가리키는 `wiki_prior_ref`가 남음 | **수정** — 새 prior 집합에 없는 ref는 지우고 rationale 유지 + 경고; `validate_references`도 검사 | `test_build.py::test_replace_build_drops_prior_refs_into_the_old_world` |
| 15 | `knowledge/cache.py` | CLI 프로세스의 쓰기를 API 캐시가 영원히 모름 | **수정** — 히트마다 WorldMeta 버전 표식(1행 읽기)을 비교, 다르면 재로드; 메타 없는 옛 월드는 무효화만 | `test_cache.py::test_hit_is_refreshed_when_the_world_version_changes` |

**Tail (리뷰가 상한 밖으로 밀어낸 항목)** — 수정: 절이 리스트가 아니면 422, `position`의 알 수 없는 키 제거, 백업 파일명 충돌(µs+난수), `start_augmentation` 404, 로더 빈 월드 판정에 prior 포함, 구조화 지도 `connections` 비객체 항목 경고, `with_map` 복원, `region_briefs` 순위 정렬(`LEVEL_RANK`를 shared로), `validate_references`의 `located_in`/`about`/`derived_from`/`wiki_prior_ref`, WikiAdmin 메타 touch·LLM 없이 조립, `world export`가 OpenSearch 없이 동작, EditorPage 안내 문구, operations.md multipart 필드명(`memos`/`maps`/`images`), CLAUDE.md 테스트 수. 기록(미수정): 절 사이 id 유일성 검사(U3 에디터 검증과 함께), 엄격 base64(문서화), v0 파일의 `to_json`(export는 항상 v1), 가짜 저장소가 끝점 없는 엣지를 허용, CLI 게이트의 PostgreSQL 의존(strict CLI 설계), 재사용·효율 항목(builder/importer 커밋 시퀀스 통합, `GET /worlds` 라운드트립, 항목별 MERGE) → U8.

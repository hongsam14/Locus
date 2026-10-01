## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Code Generation Part 1 (unit code generation plan) — U2 World File·캐노니컬 기반
**Reviewed artifact:** `aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-09-29T17:14:10Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 7.2, 8.2, 2.1 | 조치 확인. `TopologyBuild(topology, warnings)`/`OntologyBuild(kg, warnings)` 반환형, `kg.unscoped_knowledge_ids`(2.1, io.py), 디둡 뒤 `remap`으로 정본 id 치환(7.2; 실제 `ontology/builder.py` 의 `dedupe`→`remap_scopes` 위치와 일치), Protocol·영향 테스트 목록이 모두 적혔다. | (없음) | Resolved |
| R-02 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 8.1, 8.2 | 조치 확인. `build()` 마다 `LLMCallCounter` 를 만들고 감싼 제공자를 ingestion/topology(wiki)/ontology/wiki/distiller/linker 팩토리에 넘기는 구조가 명시됐다. `IngestionService.from_factory` 가 llm·vlm 만 쓰고 embedding 은 ontology·wiki·persist 에서 쓰이는 현 코드와도 맞다. EX-16 이 카운트 정합을 검증한다. | (없음) | Resolved |
| R-03 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 11.2, 11.3 | 조치 확인. `apply.py:50`(ADD scope 엣지)·`:84`(revert 복원)의 직접 쓰기는 `AugmentationEngine.apply_answer/revert` 끝의 무효화로, `WikiAdmin.upsert_prior`(admin.py:28)는 자체 무효화로 덮인다. grep 으로 확인한 캐노니컬 쓰기 경로(editor 3, build 2, apply 2, admin 1, 라우터 delete → editor)가 모두 목록에 있다. 테스트도 계획됨. | (없음) | Resolved |
| R-04 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 3.2, 3.3, 8.2, 9.4 | 조치 확인. 포트 예외 `ConstraintViolation`, Neo4j `upsert_nodes` 에서 `ConstraintError` 변환, persist 실패 severity="error", 가짜 저장소의 유일 제약 흉내(EX-4)가 명시됐다. 실제 `MERGE (n:L {id, world_id})` + `id` 유일 제약 구조에서 타 월드 id 충돌이 ConstraintError 로 나오므로 성립한다. | (없음) | Resolved |
| R-05 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 9.3, 9.5 (TP-U2-2) | 조치 확인. TP-U2-2 를 (a) 결정성 (b) `world.id==T`·참조 해석 (c) 임포터의 비강제 분기 id 보존으로 나누고 이탈 기록 표에 적었다. | (없음) | Resolved |
| R-06 | Major | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 3.3, 4–6, 9.2, 9.5, 11.3, 12.4 | 조치 확인. `merge_entities` 호출부(text:39, concept_art:41, service:29, map_image:90)와 `.errors` 단언 7곳(110,126,167,176,256,257,278; grep 일치), 그래프 가짜 9개, `WorldFileExporter(_Loader())` (test_services:303), `WorldContainer(` (test_augment_api:30, test_world_api:46), `KnowledgeContainer(` (test_knowledge_api:41, play/helpers:52), `locus/world/__init__.py` 재노출이 목록에 들어갔다. | (없음) | Resolved |
| R-07 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 2.1 | 조치 확인. `WorldSnapshot`·`RegionBrief` 를 `io.py` 에 둔다. `io.py` 는 graph.py 만, `reports.py` 는 graph.py 만 import 하므로 `BuildWarning` 참조에 순환이 없다. | (없음) | Resolved |
| R-08 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > 바뀌는 외부 계약, Step 9.2, 14.1 | 조치 확인. `export_world` 호환 래퍼가 최상위 `world_id` 를 덧붙인다고 명시(9.2)돼 web `WorldExport.world_id` 가 유지된다. | (없음) | Resolved |
| R-09 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 9.1, 12.1 | 조치 확인. `parse` 가 항목 dict 의 알 수 없는 키를 걸러내고 `ValidationError` 를 `UnsupportedWorldFile` 로 감싸며, `http_error` 의 `ValueError→400` 보다 먼저 검사하도록 순서가 명시됐다. | (없음) | Resolved |
| R-10 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 12.2, 13.1 | 조치 확인. `list_sessions`/`close_session`(실제 `session_service.py` 이름과 일치)과 `status == "open"` 필터, EX-24 에 닫힌 세션 케이스가 들어갔다. | (없음) | Resolved |
| R-11 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 2.3, 15.2 | 조치 확인. 명명 볼륨 `locus_data:/app/data` 와 `LOCUS_DATA_DIR` 가 15.2 에 있고, 이미지는 root 로 실행돼 권한 문제도 없다. | (없음) | Resolved |
| R-12 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 6.2, 6.3, 이탈 기록 | 조치 확인. `connection_hints` 를 실제 키로 두고 설계 이탈로 기록했다. | (없음) | Resolved |
| R-13 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 11.3, 3.3 | 조치 확인. 11.3 에 EX-23 편집 부분(WorldMeta touch, 메타 없으면 미생성), 3.3 에 `delete_world` Cypher 단위 확인과 라이브 확인(16.2)이 추가됐다. | (없음) | Resolved |
| R-14 | Minor | aidlc-docs/construction/plans/U2-worldfile-foundation-code-generation-plan.md > Step 11.1, 12.2 | 부분 조치. LLM 의존 서비스를 Optional 로 하고 build 라우트에 503 을 둔 것은 좋다. 남은 두 가지: (1) 조립 조건이 "`shared.llm`/`factory` 가 있을 때만" 인데, `assemble_shared._llm` 은 `c.factory = factory` 를 먼저 대입한 뒤 `factory.llm()` 이 키 없음으로 예외를 던지므로 키가 없을 때 `factory is not None` 이고 `llm is None` 이다. `factory` 로 게이트하면 `WorldBuilder.from_factory` 가 다시 예외를 던져 world 컨테이너 전체가 None(=503)이 된다. (2) 다른 LLM 의존 라우트(`api/routers/world.py` 의 `w.wiki_admin`·`w.cross_world`·`w.augmentation`, 현 63/74/101/109/119행)는 Optional 이 되면 None 에 대한 AttributeError(500)가 나는데 12.2 는 build 만 503 을 적는다. | 11.1 의 게이트를 `shared.llm is not None`(또는 factory 이면서 llm 도 not None)으로 못 박고, 12.2/12.4 에 augmentation·wiki·cross_world 라우트도 None 이면 503 을 내며 테스트한다고 한 줄씩 추가. 구현 단계에서 닫을 수 있으므로 비차단. | Unresolved |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `grep -rn "\.errors\|merge_entities\|merge_regions"` 소스·테스트 | 소스 호출부 text:39-40, concept_art:41, map_image:90, service:29-30; 테스트 `.errors` 7곳 = 계획의 7곳 | R-06 목록 일치 |
| `grep` 컨테이너·빌더 생성 지점 (`KnowledgeContainer(`, `WorldContainer(`, `WorldFileExporter(`, `WorldBuilder(`, `TopologyBuilder(`, `OntologyBuilder(`, `WikiAdmin(`) | 계획이 언급한 위치 전부 존재(test_knowledge_api:41, play/helpers:52, test_augment_api:30, test_world_api:46, test_services:125/215/238/254/303, test_wiki_build:331) | 호출부 커버리지 양호 |
| 캐노니컬 쓰기 grep (`upsert_nodes\|upsert_edges\|persist_graph\|delete_node\|delete_world\|.index(`, storage 제외) | editor 4, build 2, apply 2(+editor 경유 2), admin 2, world 라우터 delete(→editor) | 11.2 의 무효화 목록 완전 (R-03) |
| `neo4j_repo.upsert_nodes`·`ensure_schema` | `MERGE (n:L {id, world_id})` + label 별 `id` 유일 제약 | ConstraintError 경로 성립 (R-04) |
| `persistence.persist_graph` 예외 처리 | `except Exception` 로 삼킴 → 3.2 가 error 등급·포트 예외 매핑 지정 | R-04 조치 타당 |
| `ontology/builder.py` dedup·remap 위치 | 빌더 내부에서 `dedupe`→`remap_scopes` | 7.2 의 unscoped remap 위치 타당 (R-01) |
| `shared/models` import 그래프 | io→graph, reports→graph (서로 무참조) | io.py 배치에 순환 없음 (R-07) |
| `SessionService`·`SessionStatus` | `list_sessions`, `close_session`, `SessionStatus.OPEN="open"` | R-10 조치 정확 |
| `assemble_shared._llm` / `ProviderFactory._require_openai_key` | factory 는 대입 후 llm() 에서 예외 | R-14 잔여 (1) |
| `api/routers/world.py` 의 `w.*` 사용처 | builder 2, wiki_admin 1, cross_world 1, augmentation 3 | R-14 잔여 (2) |
| `Dockerfile`·`docker-compose.yml` app 서비스 | root 실행, WORKDIR /app, 볼륨 없음(계획이 추가) | R-11 조치 타당 |

### Summary

이전 Major 6건과 Minor 7건은 모두 계획 문장 수준에서 정확히 닫혔고 grep 으로 확인한 호출부·쓰기 경로 목록과 일치한다. 남은 것은 Minor 1건(R-14: LLM 없는 조립의 게이트 조건이 `factory` 가 아니라 `llm` 이어야 하고 non-build LLM 라우트의 503 처리 누락)뿐이며 구현 단계에서 닫을 수 있어 READY.

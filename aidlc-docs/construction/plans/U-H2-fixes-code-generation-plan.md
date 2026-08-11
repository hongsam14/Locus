# U-H2 Fixes — Code Generation Plan

> **Single source of truth for U-H2.** 브라운필드 in-place. 소규모 독립 3건.
> 근거: FD `construction/U-H2-fixes/functional-design/*` (BR-H2-1..4), NFR `.../nfr/nfr-light.md`.

## FR-H6 — 프론트 refresh 병렬화
### Step 1 — SessionPanel.refresh Promise.all
- [x] **Modify** `web/src/SessionPanel.tsx`: `refresh()`의 순차 4-await를 `Promise.all([getTimeline, listEvents,
  listDistortions, regionId ? listRumors : Promise.resolve([])])`로 병렬화(BR-H2-1). setter/에러 처리 불변.
### Step 2 — vitest
- [x] **Modify/Create** `web/src/*.test.tsx`: refresh가 4 API 병렬 호출; regionId 없으면 rumors 빈 배열;
  에러 시 setError. (기존 SessionPanel 테스트 있으면 확장, 없으면 최소 신규.)

## FR-H7 — orchestrator set_wiki 순서
### Step 3 — build_world 순서 수정
- [x] **Modify** `locus/services/orchestrator.py::build_world`: wiki 생성 + `set_wiki`(topology/ontology)를
  `topology.build` **앞으로 이동**(BR-H2-2). LLM=None 가드 유지. distill/persist priors 순서 불변.
### Step 4 — pytest
- [x] **Modify/Create** `tests/services/test_orchestrator*.py`: mock으로 `topology.set_wiki`가 `topology.build`
  **전에** 호출됨을 검증(call-order); LLM=None이면 set_wiki 미호출. 기존 회귀 0.

## FR-H8 — barrier terrain 드롭 가시화
### Step 5 — map_image_ingestor 경고
- [x] **Modify** `locus/ingestion/map_image_ingestor.py`: barrier terrain `between != 2`를
  `IngestionResult.errors`에 skip 경고 기록(BR-H2-3). `==2` 힌트 / area terrain 승격 불변. `errors` 리스트를
  L48 graceful 경로와 합류시켜 최종 결과에 전달.
### Step 6 — pytest
- [x] **Modify/Create** `tests/ingestion/test_map_image_ingestor*.py`: barrier between=1/3 → errors 1건·힌트 없음;
  between=2 → 힌트·errors 없음; area terrain → Region 승격 불변.

## Summary / Lint
### Step 7 — 요약 + 린트
- [x] `source .venv/bin/activate && ruff check --fix . && black . && python -m compileall locus api`;
  `cd web && npm run -s test` (+tsc/build 가능 시).
- [x] **Create** `aidlc-docs/construction/U-H2-fixes/code/code-summary.md`.

## 파일 매니페스트
| 액션 | 경로 |
|---|---|
| Modify | `web/src/SessionPanel.tsx` |
| Modify | `locus/services/orchestrator.py` |
| Modify | `locus/ingestion/map_image_ingestor.py` |
| Modify/Create | web vitest · `tests/services/…orchestrator…` · `tests/ingestion/…map_image…` |
| Create | `aidlc-docs/construction/U-H2-fixes/code/code-summary.md` |

## 순서
- 세 항목 독립 — 임의 순서. U-H1과 무관.

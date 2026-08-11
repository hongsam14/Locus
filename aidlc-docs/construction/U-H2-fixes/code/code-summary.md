# U-H2 Fixes — Code Summary

> 브라운필드 in-place, 소규모 독립 3건. 백엔드 **249 offline pytest GREEN**(246→249, +3),
> 프론트 **19 vitest GREEN**(17→19, +2), ruff/black/compileall 클린. BR-H2-1..4.

## Modified (app code)
- `web/src/SessionPanel.tsx` — `refresh()`의 순차 4-await → `Promise.all`(timeline/events/distortions/
  rumors 병렬, rumors는 regionId 있을 때만). 왕복 깊이 4→1. 표시·에러 처리 불변(FR-H6/BR-H2-1).
- `locus/services/orchestrator.py` — `build_world`에서 wiki 생성 + `set_wiki`(topology/ontology)를
  `topology.build` **앞으로 이동**. topology가 이 월드의 영속 prior 반영 가능; 첫 빌드(빈 wiki)는 기존과
  동일; LLM=None 가드 유지(FR-H7/BR-H2-2).
- `locus/ingestion/map_image_ingestor.py` — barrier terrain `between != 2`를 조용히 버리지 않고
  `IngestionResult.errors`에 skip 경고 기록. `==2` 힌트 / area terrain 승격 불변(FR-H8/BR-H2-3).

## Modified (tests)
- `tests/services/test_services.py` — `test_orchestrator_injects_wiki_before_topology_build`(set_wiki가
  build **전** 호출 검증, call-order), `test_orchestrator_skips_wiki_when_no_llm`(LLM=None 가드).
- `tests/ingestion/test_ingestion.py` — `test_map_image_ingestor_barrier_wrong_arity_surfaced`(between=3/1 →
  errors 2건·barrier 힌트 없음).
- `web/src/__tests__/components.test.tsx` — refresh 병렬 4-read 호출; regionId=null 시 listRumors 미호출.

## 회귀 / 검증
- 정상 경로 산출물 동일. 달라진 것: (H7) 재빌드 시 topology의 wiki 반영, (H8) 비정상 barrier 가시화,
  (H6) 프론트 지연만.
- 백엔드 249 GREEN, 프론트 19 GREEN. ruff/black/compileall 클린.

## ⚠ 환경 노트 (코드 무관)
- 시스템 `/usr/bin/python3`가 3.14로 업그레이드되어 `.venv`(3.13.7)의 `python3` 심링크가 깨짐 →
  `python -m pytest`가 stdlib를 3.14로 잡아 실패. 테스트는 `PYTHONPATH=.venv/lib/python3.13/site-packages
  /usr/bin/python3.13 -m pytest`로 실행/검증함. 영구 복구: `.venv/bin/python3` 심링크를
  `/usr/bin/python3.13`로 재지정하거나 venv 재생성(`python3.13 -m venv .venv && pip install -e ".[dev]"`).

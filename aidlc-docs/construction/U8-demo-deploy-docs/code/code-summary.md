# U8 데모·배포·문서 — Code Summary (작성 중)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 코드 생성 중입니다. 이 문서는 단계마다 바뀐 것과 그 검증을 모읍니다(Step 16에서 마무리).

플랜: `construction/plans/U8-demo-deploy-docs-code-generation-plan.md` (17단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `589dc2b`) | 결과 (Step 16.1) |
|---|---|---|
| pytest | 857 | |
| vitest | 129 | |
| mypy (`locus api`) | 11 (6 파일) | |
| ruff · black · tsc | clean | |
| `npm ci` (깨끗한 설치) | 된다(202 패키지) | |
| `npm audit --omit=dev` | moderate 2 (react-router 6.30.6) | |

## 2. 단계별 기록
- **Step 1**
  - 1.1 기준선을 다시 쟀다(위 표).
  - 1.2 승인 산출물 정정(〔Step 1.2 정정〕).
    - FD BLM §7: 9a 기다리기(R-05).
    - FD frontend-components §3: `startSeed` 타입(R-12).
    - FD domain-entities §5.2·BR-U8-11: Ironcrag 전해 들음 목록(R-13).
    - FD BR-U8-35: react-router 7.18.x(사람의 결정).
    - Infra §1 web healthcheck 127.0.0.1(R-02), §3.1 package-data(R-04a), §3.2 nginx 49m(R-03), §5 설치본에서 확인(코드 플랜 R-02).
- **Step 2** (shared: 씨앗 모델과 저장)
  - `EventCategory`·`EventLifecycle`·`CATEGORY_DEFAULT_LIFECYCLE`·`default_lifecycle`을 `shared/models/enums.py`로 옮겼다(FR-A2 예외를 주석으로 남김). `play/models.py`는 같은 이름을 다시 내보낸다(호출처 무변경).
  - `EventSeed`(`shared/models/graph.py`), `WorldSnapshot.event_seeds`
  - 저장: `NODE_LABELS`에 `EventSeed`, `graph_mapping.seed_to_node`·`node_to_seed`, `persist_graph(seeds=)`
  - 로더가 씨앗을 싣고, 지역이 없는 씨앗은 dangling 경고와 함께 뺀다(NPC 집과 같은 규칙).
  - 테스트 `tests/shared/test_event_seed.py` 4개: 매핑 왕복, 범위, 로더, 재내보내기
  - pytest 861
- **Step 3** (World File `event_seeds`)
  - `schema.SECTIONS`·`WorldFile.event_seeds`(선택 절, 기본 `[]`, v1 그대로)
  - `remap`: `file_ids`·재매핑(씨앗 id·`region_id`)·`set_world_id`·`validate_references`(지역 없으면 error로 뺌)
  - `export`(정렬·스냅샷 씨앗), `import_`(`persist_graph(seeds=)`)
  - 생성기 `world_files`가 씨앗 0~2개를 뽑는다(U2 왕복 PBT·U3 편집 PBT도 씨앗과 함께 돈다).
  - 테스트 4: TP-U8-1, TP-U8-2, EX-5, EX-6
  - 변이(모두 잡음): 재매핑에서 `region_id` 빼기 → TP-U8-2 실패, 참조 검사 끄기 → EX-6 실패
  - pytest 865

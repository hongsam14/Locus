# U3 월드 에디터 — Code Summary (작성 중)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U3 코드 생성 중입니다. 이 문서는 단계마다 바뀐 것과 그 검증을 모읍니다(Step 12.3에서 마무리).

플랜: `construction/plans/U3-world-editor-code-generation-plan.md` (13단계, 승인 2026-10-01).

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, HEAD `9228861`) | 결과 (Step 12.1) |
|---|---|---|
| pytest (`-q --no-cov`) | 735 | |
| vitest | 94 | |
| mypy (`locus api`) | 11 (6 파일) | |
| ruff · black · tsc | clean | |

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

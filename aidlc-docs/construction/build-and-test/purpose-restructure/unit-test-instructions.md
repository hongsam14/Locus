# Unit Test Instructions — Purpose Restructure (U1~U8)

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: 이 주기의 Build & Test입니다. 이 문서는 오프라인 검사(외부 I/O는 모두 포트 뒤의 가짜)를 돌리는 방법과 기대값을 적습니다.

## 백엔드
```bash
ruff check locus api tests scripts && black --check locus api tests scripts
pytest                                   # 948 passed (U8 리뷰 후속 뒤)
mypy locus api                           # 11건 (기준선, 늘지 않음; CI에는 없음)
```
- hypothesis 프로필 `locus`(`print_blob=True`, deadline 없음). 실패를 다시 돌리려면 CI 로그의 seed로 `pytest --hypothesis-seed=<seed>`를 쓴다.
- 경계 import 행렬: `tests/test_boundaries.py`
- 데모는 데이터다(코드에 데모 이름 없음): `tests/test_demo_as_data.py`(`locus`·`api`·`web/src`)
- 패키지 메타데이터: `tests/test_packaging.py`(requirements 일치, SPDX MIT, Dockerfile이 LICENSE 복사, README 첫 줄, 프로필)
- 키 없는 서버: `tests/api/test_keyless_api.py`(LLM 경로 503, 나머지 2xx)
- 라이브 시나리오 스크립트: `tests/test_live_scenario.py`(실제 API를 프로세스 안에서 키 없이·가짜 LLM으로, 흉내 서버로 판정)

## 프런트엔드
```bash
cd web
npm ci
npx tsc --noEmit
npx vitest run                           # 202 passed
npm audit --omit=dev                     # 0 vulnerabilities
```

## CI
`.github/workflows/ci.yml`에 작업이 넷 있다(push, main 대상 PR).
- backend: ruff, black, pytest(seed를 찍는다)
- frontend: `npm ci`, tsc, vitest
- audit: `npm audit --omit=dev --audit-level=moderate`
- images: 두 빌드, 설치본의 `check_packaged()`, `import api.main`

첫 실행은 원격에 push해야 돈다.

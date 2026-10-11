# Unit Test Instructions — Follow-up 주기 (V1~V9)

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것.
**지금 하는 것**: 이 주기의 Build and Test다. 이 문서는 오프라인 게이트(외부 I/O는 모두 포트 뒤의 가짜)를 돌리는 방법과 이번 결과를 적는다.

## 실행
```bash
ruff check locus api tests scripts && black --check locus api tests scripts
mypy locus api                                   # 오류 0 (CI 단계)
pytest                                           # 오프라인; hypothesis 시드는 CI가 찍는다
cd web && npx tsc --noEmit && npx vitest run
cd web && npm audit --omit=dev --audit-level=moderate && npm audit
```
- pytest는 `filterwarnings`로 ResourceWarning과 그것이 바뀐 unraisable 경고를 오류로 본다(V9 코드 리뷰 01 #22). 닫지 않은 엔진·파일이 있으면 그 실행이 실패한다.
- 시험은 저장소의 `./data`에 쓰지 않는다. 세션 픽스처가 `LOCUS_DATA_DIR`을 임시 폴더로 돌린다(#7).
- 웹 시험 가운데 넷은 소스를 글자로 읽는다(`src/test/paths.ts`). 디자인 grep, 사전 말투, 모든 키의 쓰임, 문서 머리다.

## 결과 (2026-10-12, 코드 `5c8ec9b`)
| 항목 | 결과 |
|---|---|
| pytest | **1262 passed**(41 s), ResourceWarning 0, 가장 느린 시험 1.07 s(guard 상태 기계) |
| vitest | **825 passed**(40 파일) |
| mypy `locus api` | 0 (167 파일) |
| ruff · black (`locus api tests scripts`) · tsc | clean |
| npm audit 전체 · `--omit=dev` | 0 · 0 |
| 첫 화면 JS gzip | 119.39 kB (에디터 14.68, GM 11.98) |

주기 시작(`d570f00`, pytest 948 · vitest 202 · mypy 11 · dev audit 5)과 비교하면, pytest는 +314, vitest는 +623 늘었다.

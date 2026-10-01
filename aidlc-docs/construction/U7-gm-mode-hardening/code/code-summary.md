# U7 GM 모드·안정화 — Code Summary (초안)

## 1. 기준선과 결과
| 항목 | 기준선 (Step 1.1, 2026-10-01) | 결과 |
|---|---|---|
| pytest (`-q --no-cov`) | 636 | — |
| vitest | 74 | — |
| mypy (`locus api`) | 11 | — |

## 5. 설계 이탈 (진행 중 기록)
- **플랜 R-01 (승인 때 Accepted risk)**: 이름 변경·메서드 제거의 호출처 수정은 플랜의 원칙("같은 하위 단계에서 고친다")에 따라 앞당긴다. 옮긴 항목은 아래에 적는다.
- 웹 새 파일(`features/gm/*`, `ui/CommitRange.tsx`)은 Step 8에서 만든다. 빈 TSX 파일은 tsc `isolatedModules`와 vitest의 빈 스위트 규칙에 걸리기 때문이다.

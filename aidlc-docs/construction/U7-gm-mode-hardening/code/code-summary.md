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
- **Step 3로 당긴 것 (플랜 R-01)**: 6.1의 재생성 비활성화 전환(`rumor/service.py`의 `delete_rumor` → `active=False` 저장, `deactivated_ids`, 페이로드 `deactivated`)과 그 호출처(`api/routers/gm.py`, 테스트 다섯 곳)를 `delete_rumor` 제거·개명과 같은 단계(3)에서 고쳤다. 6.1에는 이름 페이로드만 남는다.
- **C2 질의 모양**: `DeedStore`에 `seed_candidates`를 두고, `npc_memories`·`recent_deeds` 대신 `list_deeds(kind=, deed_ids=, newest_first=, limit=)`로 넓혔다. 발언 커서(`last_statement`)는 NPC 필터가 JSON 열이라 SQL로 걸지 않고 `kind=statement`로 줄인 뒤 거른다.
- **`one_line`과 탭 (4.1)**: 플랜 이월 표는 "탭 제외"였으나 탭도 공백 하나로 접는다. 탭은 프롬프트 구역을 열지 못하지만, 공백 접기(`str.split`)가 이미 탭을 공백으로 다루므로 규칙을 하나로 둔다.
- **`region_feedback`의 분모 (4.2)**: 승격 소문은 강한 소문에서도, 밀도의 분모에서도 뺀다(FD BLM §1.2 그대로).

- **Step 5로 당긴 것**: GM 왜곡도 설정이 몫을 0으로 하고 `feedback_share_cleared`를 남기는 부분(6.3의 일부, BR-U7-5). 몫 통합 테스트와 같은 단계에서 GREEN이 되게 했다. 지역 확인(404)과 생성자 주입은 6.3에 남는다.
- **5.2 (플랜 검토 R-04)**: 새 키워드 인자는 `distortion_delta(max_delta=)` 하나다. `propagate_delta(min_weight=)`·`evolve_support(reinforce=)`는 이미 있었고 엔진이 tuning 값을 넘긴다.
- **5.4 장면 가리기 (플랜 검토 R-05)**: `pick_rumors` → `shadowed_sources(picked, [*src.rumors, *src.lineage])` → `pick_facts(hidden=)`.
- **5.4 C4**: `spread.neighbour_map(edges)`를 새로 두고, `plan_spread`가 `reach`·`neighbours`를 선택 인자로 받는다(엔진이 원점별로 메모).
- **5.4 C7**: 청구는 갈래 앞 한 곳에서 `run.cost_turns`로 한다. 대기·선언·대화 마침의 비용은 `action_cost`가 이미 1이다.

## 6. 변이 확인 (진행 중)
| 단계 | 변이 | 결과 |
|---|---|---|
| 4 | 상한 무시, 몫에 delta 기록, 복원이 덜 빠짐, 승격 소문 셈, 로그가 지역 무시, 사건 줄 중복, 비활성 소문 셈, 플레이어 지역 우선 없음, 모호한 이름 매칭 | 9/9 잡음 |
| 5 | #8 다시 읽기 없음, #9 장면이 try 안, #14 규칙이 validate_action 밖, 장면 가리기 없음, 되먹임 지역 면제, 몫 미기록, GM 설정이 몫 유지, one_shot 해소 줄 없음 | 8/8 잡음 |

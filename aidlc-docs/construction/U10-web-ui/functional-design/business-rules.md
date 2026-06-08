# U10 Web UI — Business Rules

## 시각화
- BR-U10-1: 지역 좌표는 `region.position {x,y}`(0~1 정규화). 없으면 `autoLayout` 결정적 폴백.
- BR-U10-2: 연결선 스타일 = weight 기반(굵기/투명도), kind=blocked → 빨강 점선.
- BR-U10-3: 마커 드래그 종료 시에만 `PUT region`(과도한 호출 방지).

## 편집
- BR-U10-4: 지식/지역 편집은 authoring API 경유(서버 검증). 실패 시 오류 표시(파괴적 액션 확인).
- BR-U10-5: 삭제는 확인 후 `DELETE node`.

## 보강
- BR-U10-6: 보강 답변 action ∈ {confirm, remove, add, edit, ignore}. add는 statement+region 필요.
- BR-U10-7: 세션 status=converged/stopped면 질문 패널 종료 표시. revert는 ChangeSet id로.

## 품질/자동화
- BR-U10-8: 모든 상호작용 요소에 안정적 `data-testid`(동적 id 회피, 목적 변경 시에만 변경).
- BR-U10-9: API 오류는 사용자에게 메시지로 표시(콘솔만 아님).
- BR-U10-10: 순수 로직(layout/viz)은 vitest 단위 테스트; 컴포넌트는 RTL + api mock.

## 범위
- BR-U10-11: 맵 이미지 영속화·다중 사용자·실시간 협업은 범위 외(차후).

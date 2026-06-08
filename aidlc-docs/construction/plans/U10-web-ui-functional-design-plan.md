# U10 Web UI — Functional Design Plan

U10은 기획자용 **검토·편집·보강 웹 UI**(FR-G, US-7.1~7.3): 토폴로지·지식그래프 시각화 + 노드/관계/지식 편집 + UI 내 보강 Q&A. U8 serving + U9/U7 authoring API를 소비합니다. 스택은 React(+Vite/TS).

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD10-Q1 — 프론트엔드 스택
구현 스택은?

A) **React + Vite + TypeScript**(참고 graph-universe-proto / Q8=B) + vitest 테스트 (Recommended)
B) React + CRA / 기타
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD10-Q2 — 토폴로지 시각화 방식(MVP)
지역 토폴로지/그래프 시각화는?

A) 경량 자체 SVG(지역 노드 + 연결 엣지, weight 표시) + 리스트 패널 (Recommended — 의존성 가벼움·빠른 MVP)
B) 그래프 라이브러리(reactflow/cytoscape 등) (풍부하나 의존성↑)
X) Other (please describe after [Answer]: tag below)

[Answer]: X. 지도 위에 오버레이로 그래프를 위치시키고 싶은데. 어떻게 구현할지 아이디어.

## Question FD10-Q3 — MVP 화면/컴포넌트 범위
어디까지 1차에 넣을까요?

A) World 선택+빌드 / **토폴로지 뷰** / **지역 지식 뷰(쿼리)** / **편집(지역·지식)** / **보강 Q&A 패널** 모두 (Recommended — FR-G2 편집 + G3 보강 포함, Q9=C)
B) 시각화+조회만(편집/보강은 차후)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD10-Q4 — 데이터/상태 계층
API 연동·상태 관리는?

A) fetch 기반 API 클라이언트 + React state/hooks(전역 상태 라이브러리 없음) (Recommended — MVP 단순)
B) React Query / Redux 등 도입
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD10-Q5 — 테스트
프론트 테스트는?

A) vitest + React Testing Library, API 클라이언트 mock(주요 컴포넌트 렌더·상호작용) (Recommended)
B) 테스트 생략(차후)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `frontend-components.md` — 컴포넌트 계층·props/state·상호작용·API 연동 지점
- [ ] `business-logic-model.md` — API 클라이언트·페이지 흐름·보강 루프 UI
- [ ] `business-rules.md` — UI 규칙(편집 검증·data-testid·오류 표시)

## Execution Checklist
- [x] 1. FD10-Q1~5 반영 (Q2=X 지도 오버레이)
- [x] 2. 산출물 3종 작성 (frontend-components 포함)

---

## Follow-up (좌표 모델 — 확인 필요)

지도 오버레이는 지역마다 좌표가 필요합니다. 어떻게 둘까요?

### Question FD10-CL1 — 좌표 저장 + 출처
A) **1급 필드 `Region.position {x,y}`(0~1) 추가** + 입력 지도에서 추출(Locus Map JSON의 x/y, **GeoJSON geometry→centroid 정규화**, VLM 근사) + 없으면 UI 자동 레이아웃·드래그로 지정 (Recommended — "좌표는 노드에, 지도에서 유래")
B) `attributes.layout`에만 저장(모델 변경 없음), 입력 지도에서 추출 안 함 — 수동 드래그/자동만
X) Other (please describe after [Answer]: tag below)

[Answer]: 

# U3 Topology — Functional Design Plan

U3는 U2의 `IngestionResult`(region_hints + terrain + connection_hints)를 받아 **계층 지역 그래프 + 연결(weight) 그래프** = `RegionTopology`를 만듭니다(FR-B, US-2.1~2.3). 상식 Wiki(U1 인터페이스)로 연결 강도를 가중합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD3-Q1 — 계층(CONTAINS) 구성 + 고아 처리
region_hints의 `parent_name`/`level`로 계층을 만들 때, 부모가 없는 지역은?

A) parent_name으로 CONTAINS 연결, 부모 미지정/미발견 지역은 **최상위(부모 없음)**로 둠(합성 루트 없음) (Recommended — 단순, 손실 없음)
B) 합성 루트(World 가상 노드) 아래에 모두 연결
C) level 순서로 자동 추정해 부모 부여
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD3-Q2 — 연결 엣지 소스
CONNECTED_TO 엣지는 무엇에서 만들까요?

A) 명시적 connection_hints(U2) + terrain.between(산맥/강/길→blocked/river/route) 에서만 생성 (Recommended — 근거 있는 엣지만)
B) 위 + 동일 부모 하위 형제 지역 자동 인접(adjacent) 추가
C) 모든 동일 level 지역 쌍 인접(과생성 위험)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD3-Q3 — 연결 강도(weight) 산정식
weight(0~1)는?

A) **kind 기본값 × Wiki 수정자** — 기본(adjacent 0.8/route 0.6/river 0.5/blocked 0.2)에 Wiki prior 기반 수정자 곱, 근거 기록 (Recommended)
B) kind 기본값만(Wiki 미반영)
C) 전적으로 Wiki/LLM 산정
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD3-Q4 — Wiki 수정자 도출 방식
Wiki prior(텍스트 effect)를 수치 weight 수정자로 어떻게?

A) **지형 kind→수정자 휴리스틱 표**(예: mountain×0.4, river×0.8) + Wiki lookup은 근거(rationale)·DERIVED_FROM 기록용 (Recommended — 결정적·테스트 용이)
B) LLM이 prior로부터 수치 수정자를 직접 산출(structured) — 유연하나 비결정적
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD3-Q5 — 연결 방향성
지역 연결은?

A) **대칭(무방향 의미)** — 쌍마다 양방향 CONNECTED_TO 2개 생성(순회 단순) (Recommended)
B) 단방향 1개 + 순회 시 양방향 처리
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — U3 입출력(RegionTopology) + weight 표/수정자
- [ ] `business-logic-model.md` — TopologyBuilder 흐름(식별·계층·엣지·가중), Wiki 사용
- [ ] `business-rules.md` — 계층 비순환, weight 범위, 엣지 근거, 대칭성 규칙

## Execution Checklist
- [x] 1. FD3-Q1~5 반영 (all A)
- [x] 2. 산출물 3종 작성

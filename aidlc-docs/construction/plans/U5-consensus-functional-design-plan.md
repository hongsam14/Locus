# U5 Consensus — Functional Design Plan

U5는 컨센서스·왜곡 모델링(FR-D, US-4.1~4.3): 지역의 **직접/상속/글로벌 지식** + **연결 강도 기반 전파/소문**을 계산해 `ConsensusView`를 만듭니다. 하이브리드(직접=정적, 전파/소문=쿼리 시점, Q3=C).

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD5-Q1 — 전파 알고리즘 + 임계값
연결 강도 기반 전파는?

A) **가중 BFS** — 시작 지역에서 CONNECTED_TO 순회, path_weight = 엣지 weight 곱. 이웃 지역의 직접 지식이 `confidence × path_weight`로 도달. 임계: propagated ≥0.5 / rumor 0.15~0.5 / unknown <0.15 (기본값, 조정 가능) (Recommended)
B) 1-홉만(직접 인접 지역까지) 전파
C) 임계 없이 전부 전파(감쇠만)
X) Other (please describe after [Answer]: tag below)

[Answer]: A. 결국 도로로 연결된 edge를 통할 땐 더 많이 뻗어나가고, 접근이 힘들 수록 덜 뻗어나가고 왜곡이 심해져야 함.

## Question FD5-Q2 — 소문(rumor) 표현 (쿼리 시점)
전파 중 왜곡된 지식은?

A) **ephemeral KnowledgeView**(is_rumor=true, confidence 감쇠) — 쿼리 결과에만 존재, 노드 미영속. 영속 `:Rumor` 노드는 기획자/보강이 만든 소문 전용(차순) (Recommended — 하이브리드 Q3=C 부합)
B) 쿼리 시 매번 `:Rumor` 노드 materialize(영속)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD5-Q3 — 상속(inherited)
상위 지역 지식의 상속은?

A) CONTAINS 조상 경로의 direct 지식을 inherited로 포함(쿼리 시 계산, FD1-Q3=A) (Recommended)
B) 상속 없음(직접만)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD5-Q4 — 데이터 소스(MVP)
resolve 계산은 무엇 위에서?

A) **in-memory** KnowledgeGraph + RegionTopology 위 순수 계산(소규모 NFR). 저장소 로딩은 U8/U9가 담당(전 세계 서브그래프 적재). (Recommended — 알고리즘 순수·테스트 용이)
B) GraphRepository 쿼리로 직접(전용 그래프 쿼리 메서드 추가)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD5-Q5 — precompute(정적) 역할
ConsensusEngine.precompute의 범위는?

A) 인덱스 구성(지역별 direct 지식·CONTAINS 조상·연결) 후 resolve가 이를 사용 (직접=정적 인덱스, 전파=쿼리). 별도 영속 캐시 없음(MVP) (Recommended)
B) 지역별 전체 컨센서스를 미리 계산·영속 캐시
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — ConsensusView 산출 + 파라미터/임계
- [ ] `business-logic-model.md` — compute_consensus(순수) + ConsensusEngine/PropagationResolver
- [ ] `business-rules.md` — 분류/감쇠/임계/대칭 규칙·불변식

## Execution Checklist
- [x] 1. FD5-Q1~5 반영 (all A; distortion_degree=1−path_weight)
- [x] 2. 산출물 3종 작성

# U1 Foundation — NFR Design Plan

NFR을 설계 패턴·논리 컴포넌트로 구체화합니다. 대부분 결정됨(소규모·베스트에포트·단일 인스턴스·재시도+graceful degrade). 아래 열린 선택만 확인합니다. 각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료".

> N/A로 처리(범위 외)되는 패턴: 오토스케일링, 회로차단기(circuit breaker), 분산 캐시, 큐 — MVP 단일 인스턴스라 불필요.

---

## Questions

## Question ND1-Q1 — 재시도/타임아웃 구체값
LLM/VLM/임베딩 외부 호출의 재시도 정책은?

A) 최대 3회, 지수 백오프(예: 1s→2s→4s), 호출당 타임아웃 30s, 초과 시 graceful degrade (Recommended)
B) 더 보수적(최대 5회, 타임아웃 60s)
C) 직접 지정 (X에 기재)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question ND1-Q2 — OpenSearch 인덱스 전략
의미 검색 인덱스 구성은?

A) 단일 인덱스 + `world_id` 필터 + kNN 벡터 필드(+BM25 텍스트) (Recommended — 단순, 교차 비교 쉬움; 쿼리는 항상 world_id 필터)
B) 세계별 인덱스 분리
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question ND1-Q3 — 임베딩/Wiki lookup 캐싱
중복 임베딩·Wiki 조회 비용 절감은?

A) 경량 캐시 — 텍스트 해시→임베딩 메모이즈(인메모리/로컬), Wiki lookup 결과 단기 캐시 (Recommended — 비용↓, MVP 적합)
B) 캐싱 없음(매번 호출) — 단순, 비용↑
X) Other (please describe after [Answer]: tag below)

[Answer]: B

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `nfr-design-patterns.md` — 적용 패턴(재시도/타임아웃/graceful degrade/캐시/포트-어댑터) + N/A 명시
- [ ] `logical-components.md` — 논리 컴포넌트(ProviderFactory, RetryPolicy, EmbeddingCache, Repository 어댑터, 설정 로더)

## Execution Checklist
- [x] 1. ND1-Q1~3 반영 (Q3=B 캐싱 없음)
- [x] 2. nfr-design-patterns.md 작성
- [x] 3. logical-components.md 작성

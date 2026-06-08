# U1 Foundation — NFR Design Patterns

결정 반영: ND1-Q1=A(재시도 3회·30s·graceful degrade) · Q2=A(단일 인덱스+world_id 필터+kNN) · **Q3=B(캐싱 없음)**.

## 적용 패턴

### 1. Ports & Adapters (Hexagonal)
- 코어는 `GraphRepository`/`SearchRepository`/`LLMProvider`/`VLMProvider`/`EmbeddingProvider` **포트**에만 의존.
- Neo4j/OpenSearch/OpenAI 어댑터가 구현. → 테스트 mock·교체 용이(NFR 유지보수).

### 2. Retry + Timeout (Resilience) — ND1-Q1=A
- 외부 호출(LLM/VLM/Embedding): 최대 **3회**, 지수 백오프 **1s→2s→4s**, 호출당 타임아웃 **30s**.
- 멱등 호출만 재시도. 재시도 소진 시 예외 → 상위에서 graceful degrade.

### 3. Graceful Degradation
- 항목 단위 실패는 빌드를 중단하지 않음 — 해당 항목 `confidence` 하향 + `source`/note 표시 + 보강 대상화, `BuildReport.warnings`에 기록.
- Wiki lookup 실패/공백 → LLM 폴백(grounding), 그것도 실패 시 기본값(중립 weight=0.5, 고증 생략).

### 4. Single-Index Hybrid Search — ND1-Q2=A
- OpenSearch 단일 인덱스 `locus_search`: 문서에 `world_id`, `label`, `text`, `embedding`(kNN vector), `meta`.
- 모든 검색은 `world_id` 필터 필수(BR-19). 하이브리드 = kNN(vector) + BM25(text) 결합 스코어.

### 5. Idempotent Upsert + world_id Scoping
- 그래프 쓰기는 유니크 제약 기반 upsert(BR-2). 모든 R/W는 world_id 스코프(누출 방지).

### 6. Config via Settings (12-factor)
- `pydantic-settings`로 `.env`/환경변수 로드. 비밀은 코드/리포에 두지 않음.

## N/A (범위 외 — MVP 단일 인스턴스)
- 오토스케일링 / 로드밸런싱 — N/A (단일 인스턴스, NFR1-Q2=A).
- Circuit Breaker — N/A (재시도+degrade로 충분, 외부 의존 소수).
- 분산 캐시 / 큐 — N/A (동기 순차, 베스트 에포트 NFR1-Q3=C).
- **임베딩/lookup 캐시 — 미적용(ND1-Q3=B)**: 매 호출 직접 수행.
- 고가용성/페일오버 — N/A (로컬 개발).

## 보안(확장 OFF) 기본 위생
- 비밀 `.env`, git 제외; 입력 크기/타입 기본 검증; world_id 스코프 격리.

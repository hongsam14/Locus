# U1 Foundation — NFR Requirements

결정 반영: NFR1-Q1=A(OpenAI embedding+추상화) · Q2=A(소규모) · **Q3=C(성능 목표 미설정/베스트 에포트)** · Q4=A(Neo4j 5.x+OpenSearch 2.x) · Q5=A(재시도+graceful degrade) · Q6=A(.env).

## Scalability (NFR1-Q2=A)
- 대상 규모: 한 세계 지역 수십~수백, 지식 수백~수천 노드. 단일 인스턴스(Docker Compose)로 충분.
- 샤딩/클러스터링은 범위 외(차기).

## Performance (NFR1-Q3=C)
- **하드 목표 없음 — 베스트 에포트.** MVP는 정확성·완결성 우선.
- 빌드는 배치(LLM/VLM 호출 시간 지배). 쿼리는 합리적 응답(측정·기록만, 목표치 강제 없음).
- 명시적 SLA/캐싱 튜닝은 도입하지 않음(필요 시 차기).

## Availability
- 로컬 개발 환경 가정. 고가용성·페일오버 범위 외.

## Reliability (NFR1-Q5=A)
- LLM/VLM/임베딩 호출: **지수 백오프 재시도 + 타임아웃**.
- 부분 실패 시 **graceful degrade** — 해당 항목 저신뢰 표시 + 보강 대상화(빌드 중단 없이 BuildReport에 경고).
- 저장소 쓰기 idempotent(upsert), world_id 스코프 격리.

## Security (확장 OFF)
- SECURITY 확장 미적용(PoC). 단, 기본 위생: 비밀은 `.env`/환경변수, git 제외; 입력 크기·타입 기본 검증.

## Maintainability / Quality
- 코어는 포트(Repository/Provider) 인터페이스 의존 → 단위 테스트 mock 용이.
- **PBT Partial** (NFR-C2): Pydantic 직렬화 round-trip, 순수 유틸(없으면 N/A)에 한해 property-based 테스트.
- 타입 힌트 + (선택) mypy, 포매팅/린트(black/ruff) — tech-stack-decisions 참조.

## Usability
- U1은 라이브러리 계층(직접 UX 없음). 인터페이스 명료성·문서화로 대체.

## Observability
- 구조적 로깅(빌드 단계·LLM 호출·저장 결과). 대시보드/알림은 범위 외.

# P1 Event Foundation — NFR (light)

> Phase 2 NFR-P1..P6 중 P1에 적용되는 항목. 별도 질문 라운드 없음(요구사항·FD에서 확정). Phase 1 nfr-light 패턴 계승.

| NFR | P1 적용 | 방법 |
|---|---|---|
| **NFR-P1 포트 추상화** | ✅ | Event CRUD를 `SessionRepository` Protocol에 additive 추가; PostgreSQL + in-memory 두 어댑터 동일 계약. 서비스는 포트에만 의존. |
| **NFR-P2 레이어 격리** | ✅(부분) | create_event의 region 검증은 캐노니컬 **읽기 참조만**(WorldLoader). 세션 쓰기가 캐노니컬 변경 안 함. |
| **NFR-P4 결정론/PBT** | ◐ | `default_lifecycle` 순수 매핑 + 모델 직렬화 round-trip PBT(Partial). 본격 진화 순수 로직은 P2. |
| **NFR-P5 회귀** | ✅ | 기존 SessionRepository 시그니처/라우트/모델 불변; 신규 메서드·필드·라우트·테이블만 추가. 177 backend 회귀 GREEN 목표. ruff/black/compileall 클린. |
| **NFR-P6 인프라 무변경** | ✅ | docker-compose 불변. `session_events`는 `_metadata`에 추가 → `ensure_schema`(=init-schema/앱부팅)가 멱등 생성. 신규 인프라 컴포넌트 0. |
| NFR-P3 LLM graceful | N/A | P1은 LLM 비의존(EventSuggester=P2). |

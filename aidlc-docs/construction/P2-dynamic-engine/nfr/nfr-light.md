# P2 Dynamic Engine — NFR (light)

| NFR | P2 적용 | 방법 |
|---|---|---|
| **NFR-P2 레이어 격리** | ✅ | advance_turn은 WorldLoader로 캐노니컬을 **읽기만**(topology/connections). 세션 쓰기만 발생. |
| **NFR-P3 LLM graceful** | ✅ | EventSuggester 실패 → 빈 리스트. distortion/전파/support/승격은 LLM 비의존(dynamics 순수). 소문 append는 RumorGenerator graceful 계승. |
| **NFR-P4 결정론/PBT** | ✅ | dynamics 전 함수 순수 — hypothesis(Partial)로 delta 범위/단조, propagate 임계, apply/restore 역대칭, evolve_support 부호 검증. |
| **NFR-P5 회귀** | ✅ | 기존 advance_turn 승격/턴/타임라인 동작 보존(회귀 테스트); TurnResult는 필드 추가만; 수동 소문/ NPC 쿼리 불변. ruff/black/compileall 클린. |
| NFR-P1 포트 | ◐ | P1에서 Event CRUD 추가 완료; P2는 그 포트 사용. |
| NFR-P6 인프라 | N/A | 신규 인프라 없음(P1에서 테이블 additive 완료). |

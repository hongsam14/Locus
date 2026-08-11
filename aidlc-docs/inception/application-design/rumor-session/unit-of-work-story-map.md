# Unit Story Map — Rumor Distortion / Game Session (Phase 1)

본 사이클은 User Stories를 SKIP했으므로 **FR(요구사항) ↔ 단위** 매핑으로 추적.

| FR | 설명 | 단위 |
|---|---|---|
| FR-R1.1~1.3 | GameSession 시작/종료/조회, 캐노니컬 id 참조, PostgreSQL 저장 | **S1** |
| FR-R2.1~2.7 | 리전별 소문 생성·원본(Knowledge/Rumor)·강도 체인·LLM 왜곡·강도 출처·confidence·재생성 | **S2** |
| FR-R3.1~3.4 | support 필드·승격·강등·턴 재평가 | **S2** |
| FR-R4.1~4.3 | GameMaster 턴 동작·Timeline 기록·(Event 제외) | **S2** |
| FR-R5.1~5.2 | 세션 NPC 쿼리 규칙(Knowledge+승격+Rumor, propagated 제외)·비세션 회귀 | **S2** |
| FR-R6.1~6.5 | 웹: 세션 생성/선택/종료·소문 생성 버튼·support/distortion 표시·과거 세션·타임라인 열람·dead buildWiki 정리 | **S3** |
| NFR-R1 | SessionRepository 포트 + mock | S1 |
| NFR-R2 | 레이어 격리(세션→캐노니컬 읽기) | S1·S2 |
| NFR-R3 | PostgreSQL 인프라 | S1 (Infra Design) |
| NFR-R4 | LLM graceful | S2 |
| NFR-R5 | 순수 로직/포트 분리·PBT | S1·S2 |
| NFR-R6 | 회귀 GREEN·lint 클린 | 전 단위 |

- **정리 항목**: 미사용 Neo4j `Rumor` 모델 제거 → S1.
- 모든 FR/NFR이 단위에 배정됨. 누락 없음.

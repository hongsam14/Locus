# U-H1 Rumor Dynamics — NFR (light)

| NFR | U-H1 적용 | 방법 |
|---|---|---|
| **NFR-H1 결정성** | ✅ | `rumor_dynamics` 전 함수(감쇠·prune 판정·증식 자격·피드백)는 순수·LLM 비의존. 파라미터는 `RumorDynamicsParams` 인자로 수령. 루머 텍스트만 LLM(graceful 계승). |
| **NFR-H2 호환/격리** | ✅ | 캐노니컬(Neo4j/OpenSearch) 읽기만; 피드백은 세션 `region_distortions`만 변경. NPC 쿼리 규칙 불변. `TurnResult`·포트·모델은 **필드/메서드 추가만**(기존 소비자 호환). |
| **NFR-H3 테스트/PBT** | ✅ | 순수 동역학 hypothesis(Partial): decay 단조·범위·면제, is_prunable 경계(floor·승격 예외), is_eligible_source 경계, region_feedback 밀도∈[0,1]·부호·clamp. advance_turn 통합(in-memory/mock LLM). 배치 어댑터 SQLite 오프라인. |
| **NFR-H4 인프라 무변경** | ✅ | 신규 인프라 없음. `session_rumors.active` idempotent 가산 컬럼만(`ADD COLUMN IF NOT EXISTS`, default TRUE). docker-compose 불변. |
| **NFR-H5 확장** | ✅ | Security Baseline off · PBT Partial on(순수 함수·직렬화 라운드트립 한정). |

## 회귀 관리 노트
- **의도된 변경**: [3] "빈 턴 감쇠 금지" → 매 턴 감쇠(FD-H Q1=A). `test_empty_turn_does_not_decay_support`를
  새 정책(빈 턴 감쇠 O; 승격 루머는 강등만/삭제 없음)으로 **명시적 갱신**. 그 외 Phase 1/2 동작 보존.
- ruff/black(line 100)/compileall 클린 유지. 오프라인 스위트 GREEN(회귀 0, 의도적 갱신 제외).

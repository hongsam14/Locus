# 하드닝 & 루머 동역학 — Story Map (요구사항 → 단위 커버리지)

> 신규 페르소나 없음(기존 GameMaster/월드빌더 페르소나가 커버, User Stories SKIP).
> FR/NFR을 단위에 직접 매핑해 **전수 배정(누락 0)** 을 검증한다.

## 기능 요구사항 (FR)

| FR | 요약 | 단위 | 컴포넌트 |
|---|---|:--:|---|
| FR-H1 | support 감쇠 & prune(바닥 미만 정리) | U-H1 | CH1(decay/partition_prunable) · CH4(_decay_and_prune) · CH5(active) · CH6(soft-flag 영속) |
| FR-H2 | support 기반 증식 자격(자동 append 게이트) | U-H1 | CH1(is_eligible_source) · CH3(min_source_support) · CH4(게이트 전달) |
| FR-H3 | 루머→지역 피드백 루프 | U-H1 | CH1(region_feedback) · CH2(RumorFeedbackService) · CH4(피드백 스텝) |
| FR-H4 | 결정적 튜닝 파라미터 | U-H1 | CH1(RumorDynamicsParams) · CH7(Settings) |
| FR-H5 | 배치 `upsert_rumors` | U-H1 | CH6(포트+어댑터) · CH4(턴당 1 트랜잭션) |
| FR-H6 | 프론트 `Promise.all` refresh | U-H2 | CH10(SessionPanel.refresh) |
| FR-H7 | orchestrator set_wiki 순서 조사/수정 | U-H2 | CH11(build_world) |
| FR-H8 | barrier terrain 드롭 조사/수정 | U-H2 | CH12(map_image_ingestor) |

## 비기능 요구사항 (NFR)

| NFR | 요약 | 단위 |
|---|---|:--:|
| NFR-H1 | 결정성(동역학 LLM 비의존) | U-H1 |
| NFR-H2 | 하위 호환/가산성, 캐노니컬·NPC 쿼리 규칙 불변 | U-H1, U-H2 |
| NFR-H3 | 오프라인 GREEN + PBT(Partial) + 배치 SQLite + vitest | U-H1, U-H2 |
| NFR-H4 | 인프라 무변경(`active` idempotent 가산 컬럼만) | U-H1 |
| NFR-H5 | 확장: Security off / PBT Partial on | U-H1, U-H2 |

## 커버리지 검증
- **FR**: H1·H2·H3·H4·H5 → U-H1 / H6·H7·H8 → U-H2. **8/8 배정, 누락 0.**
- **NFR**: H1..H5 전부 배정(H1/H4는 U-H1 전용, 나머지 두 단위 공통). **5/5 배정.**
- **컴포넌트**: CH1..CH9 → U-H1 / CH10..CH12 → U-H2. **12/12 배정.**
- **추적성**: 각 FR-H*는 요구사항 문서 §6 코드리뷰 finding 추적표와 1:1 연결됨.

## 단위별 완료 정의(DoD)
- **U-H1**: 순수 동역학 PBT GREEN + advance_turn 통합(감쇠/게이팅/피드백/배치/승격 예외) GREEN +
  배치 어댑터 오프라인(SQLite) GREEN + 기존 Phase 2 회귀 관리(무효화-근접 기본값 또는 명시적 기대치 갱신).
- **U-H2**: 프론트 vitest/tsc GREEN(표시 불변) + orchestrator/ingestor 조사 결론 문서화(+결함 시 수정·회귀).

# 하드닝 & 루머 동역학 — Application Design (통합)

> Rumor / Game-Session **Phase 2 하드닝 + Phase 3(부분) 루머 동역학**.
> 통합 문서 — 상세는 `components.md` / `component-methods.md` / `services.md` / `component-dependency.md`.
> 설계 결정: **AD-H Q1=B, Q2=B, Q3=A, Q4=B, Q5=B, Q6=A, Q7=A**.
> 요구사항: `rumor-phase2-hardening-requirements.md`(FR-H1..H8 / NFR-H1..H5).
> 캐노니컬(Neo4j/OpenSearch) 불변, 세션 레이어 additive, Phase 1/2 패턴 계승.

## 1. 개요
support(공신력)를 루머의 **생존·증식 지렛대**로 승격시켜 [2] 루머 지수 증가를 근본 해결하고,
미뤄둔 Phase 3 **루머→지역 피드백**을 도입한다. 신규 순수 엔진(`rumor_dynamics`) + 전용
피드백 서비스 + 포트 배치 메서드 + soft-flag prune으로, `advance_turn`이 **감쇠·정리·게이팅·
피드백**을 결정론적으로 수행한다. 신규 인프라 없음(가산 컬럼 `active` 1개).

## 2. 설계 결정 요약 (AD-H)
| Q | 결정 | 요지 |
|---|---|---|
| Q1 | **B** | 루머 동역학 순수 로직을 **신규 `rumor_dynamics.py`** 로 분리(이벤트 `dynamics.py`와 파일 분리) |
| Q2 | **B** | prune = **soft-flag**(`active=False`), 행 보존(이력/타임라인) |
| Q3 | **A** | 증식 게이트 = `RumorService`에 선택 파라미터 `min_source_support`(자동 append만 적용) |
| Q4 | **B** | 피드백 = 전용 **`RumorFeedbackService`** (SRP), 순수 집계는 `rumor_dynamics` 위임 |
| Q5 | **B** | 튜닝 파라미터(감쇠/바닥/증식임계/피드백가중)를 **`settings.py`** 중앙화 → `RumorDynamicsParams` 조립 |
| Q6 | **A** | `upsert_rumors(list) -> list[SessionRumor]` (단일 트랜잭션, 대칭) |
| Q7 | **A** | 승격 루머는 prune **예외** |

## 3. 컴포넌트 (요약)
| ID | 컴포넌트 | 신규/확장 | 위치 | 유닛 |
|---|---|---|---|---|
| CH1 | rumor_dynamics (순수) + RumorDynamicsParams | 신규 | `locus/session/rumor_dynamics.py` | U-H1 |
| CH2 | RumorFeedbackService | 신규 | `locus/session/rumor_feedback_service.py` | U-H1 |
| CH3 | RumorService (증식 게이트) | 확장 | `locus/session/rumor_service.py` | U-H1 |
| CH4 | TurnAdvancer (감쇠·prune·피드백·배치) | 확장 | `locus/session/turn.py` | U-H1 |
| CH5 | SessionRumor (`active` soft-flag) | 확장 | `locus/session/models.py` | U-H1 |
| CH6 | SessionRepository (`upsert_rumors`, `active`) | 확장 | `repository.py`(+memory/postgres) | U-H1 |
| CH7 | Settings (튜닝 파라미터) | 확장 | `locus/config/settings.py` | U-H1 |
| CH8 | GameMasterService (DI 조립) | 확장 | `locus/session/game_master.py` | U-H1 |
| CH9 | session API (피드백 표면화) | 확장 | `api/routers/session.py` | U-H1 |
| CH10 | web SessionPanel (`Promise.all` refresh) | 확장 | `web/src/` | U-H2 |
| CH11 | orchestrator (set_wiki 순서 조사) | 조사/수정 | `locus/services/orchestrator.py` | U-H2 |
| CH12 | map_image_ingestor (barrier drop 조사) | 조사/수정 | `locus/ingestion/…` | U-H2 |

## 4. 핵심 설계 원칙
- **순수/부수효과 분리**: 결정론 계산(감쇠·prune 판정·증식 자격·피드백 집계)은 `rumor_dynamics`
  순수 함수 → 서비스가 수집·영속(NFR-H1, PBT).
- **SRP + DI**: 피드백은 전용 `RumorFeedbackService`, `TurnAdvancer`에 주입. `GameMasterService`는
  thin coordinator로 조립만.
- **soft-flag 생존**: prune은 삭제가 아니라 `active=False` — 이력 보존·롤백 용이(NFR-H2).
- **게이트 파라미터화**: 자동 append만 `min_source_support` 적용, 수동 경로 불변(호환).
- **중앙 튜닝**: 값은 Settings(env), 순수 함수는 인자로 받아 결정성 유지(값 출처만 중앙화).
- **배치 영속화**: 턴당 support/prune 쓰기 1 트랜잭션(`upsert_rumors`).

## 5. advance_turn 통합 시퀀스 (상세=services.md)
이벤트 적용(기존) → 주 대상 루머 append(**증식 게이트**) → **루머→지역 피드백** →
**support 감쇠 + prune(승격 예외)** → 승격/강등 재평가 → **배치 upsert** → bump + 타임라인.

## 6. 데이터 모델 변경 (additive)
- 신규: `rumor_dynamics.RumorDynamicsParams`.
- 확장: `SessionRumor.active`(bool) / `session_rumors.active`(컬럼) / `SessionRepository.upsert_rumors`,
  `list_rumors(include_pruned)` / `Settings`(튜닝 필드) / `TurnResult`(pruned·feedback).
- mutate: `SessionRumor.support`(감쇠), `RegionDistortion`(피드백 갱신).
- 캐노니컬 모델 변경 없음.

## 7. FD에서 확정할 열린 파라미터
- 감쇠율·바닥 임계·증식 임계·피드백 가중·고-support 임계의 **구체 값**과 기본값.
- 피드백 **집계식**(고-support 밀도 vs 승격 수 vs 가중평균).
- advance_turn **스텝 순서**(피드백↔감쇠)와 **empty-turn 감쇠** 정책([3] 재결정).
- decay의 **reinforced 집합** 정의(이벤트 influenced ∪ 피드백 지역).
- [4]/[5]가 실제 결함인지의 **조사 결론**(U-H2 수정 분기).

## 8. NFR 정합
- **NFR-H1 결정론**: rumor_dynamics/feedback/prune/게이트 LLM 비의존.
- **NFR-H2 호환/격리**: additive, 캐노니컬 불변, NPC 쿼리 규칙 불변.
- **NFR-H3 테스트**: 오프라인 GREEN + 순수 동역학 PBT(Partial) + 배치 SQLite + vitest.
- **NFR-H4 인프라 무변경**: `active` 컬럼 idempotent 가산만.
- **NFR-H5 확장**: Security off, PBT Partial on.

## 9. 다음 단계
Units Generation(U-H1 Rumor Dynamics / U-H2 Fixes) → 유닛별 Construction(FD → NFR-light →
Code Gen) → Build & Test → Operations note.

# U-H1 Rumor Dynamics — Code Summary

> 브라운필드 in-place. 전체 오프라인 스위트 **246 passed**(219→246, +27), ruff/black/compileall 클린.
> FD-H Q1..Q7 = all A. BR-H1-1..21.

## Created
- `locus/session/rumor_dynamics.py` — 순수 모듈. `RumorDynamicsParams`(frozen dataclass, 6 knobs) +
  `DEFAULT_RUMOR_DYNAMICS`; `decay_support` / `is_prunable` / `partition_prunable` /
  `is_eligible_source` / `region_feedback`(고-support 밀도). 부수효과·LLM·DB 없음.
- `locus/session/rumor_feedback_service.py` — `RumorFeedbackService(SessionAppService)`;
  `apply_feedback(session, active_rumors)` 순수 집계 위임 + region_distortion 갱신, delta 맵 반환.
- `tests/session/test_rumor_dynamics.py` — 단위 + hypothesis PBT(Partial): decay 범위/단조/면제,
  prunable 정의, eligible 경계, feedback density∈[0,weight], frozen.

## Modified
- `locus/session/models.py` — `SessionRumor.active: bool=True`(soft-flag); `TimelineKind.PRUNE`.
- `locus/session/turn.py` — `TurnAdvancer(__init__ + feedback + params)`; `advance_turn` 확장
  (이벤트 → 게이트 append → **피드백 → evolve_support(decay=0) + decay_support → prune** →
  승격/강등(survivors) → **`upsert_rumors` 1회** → bump); `TurnResult`에 `pruned_rumor_ids`/
  `feedback_regions`; 구 `_set_promoted` 제거(배치로 대체).
- `locus/session/rumor_service.py` — `append_for_region`/`_generate_for_region`/`_collect_sources`에
  `min_source_support` 게이트(세션 루머 소스만); `birth_support` 주입 → generate_chain.
- `locus/session/rumor_generator.py` — `generate_chain(birth_support=0.0)` → 신생 루머 초기 support.
- `locus/session/game_master.py` — DI: `rumor_params`/`feedback` 조립, RumorService에 birth_support,
  TurnAdvancer에 feedback+params 주입. 공개 API 불변.
- `locus/session/repository.py` — 포트에 `upsert_rumors(list)->list`, `list_rumors(..., include_pruned=False)`.
- `locus/session/memory_repo.py` — `upsert_rumors`(배치), `list_rumors` active 필터.
- `locus/session/__init__.py` — export `rumor_dynamics`/`RumorDynamicsParams`/`DEFAULT_RUMOR_DYNAMICS`/
  `RumorFeedbackService`.
- `locus/storage/postgres_session_repo.py` — `session_rumors.active` 컬럼; `ensure_schema` idempotent
  `ADD COLUMN IF NOT EXISTS`(비-SQLite); `upsert_rumors`(단일 트랜잭션 배치, `_upsert_rumor_conn`);
  `list_rumors(include_pruned)`; `_rumor_to_values`/`_row_to_rumor`에 `active` 매핑.
- `locus/config/settings.py` — `rumor_*` 5 필드 + `rumor_birth_support`; `rumor_dynamics_params()` 팩토리.
- `api/main.py` — `GameMasterService(..., rumor_params=get_settings().rumor_dynamics_params())`.
- `tests/session/test_advance_turn.py` — 신규: prune/birth-grace/support-gate/feedback/배치 리포트.
  **의도적 갱신**: `test_empty_turn_does_not_decay_support` → `test_empty_turn_decays_unreinforced_support`
  (+ 승격 면제 테스트) — [3] 정책 반전 반영.
- `tests/session/test_repository_contract.py` / `tests/storage/test_postgres_session_repo.py` —
  배치 upsert + soft-flag(active) 라운드트립·필터 테스트.

## 핵심 설계 노트
- **이중 감쇠 회피**: `evolve_support`를 `decay=0.0`으로 호출(강화만) → 모든 감쇠는 `decay_support` 소유.
  피드백 지역은 reinforced로 감쇠 면제(Q2=A)와 정합.
- **birth support(0.2, Q7=A)**: 신생 루머 즉시 사멸 방지 — 강화 없으면 ~2~4턴 후 정리.
- **결정성**: 동역학 전 과정 LLM 비의존; 파라미터는 인자 주입(Settings 중앙화).
- **가산성**: `active` 컬럼만 스키마 추가(idempotent). 공개 API/포트/모델 시그니처 가산만.

## 회귀
- Phase 1/2 동작 보존. 유일한 의도적 변경 = [3](빈 턴 감쇠) 반전 — 해당 테스트 명시적 갱신.
- 246 offline pytest GREEN(프론트 vitest 별도). 라이브 Postgres는 Build & Test(operator-run).

## 남은 스텝(U-H1 API 표면화)
- `TurnResult`의 신규 필드는 advance-turn 응답에 자동 포함(라우트 추가 불필요). Build & Test에서 응답 확인.

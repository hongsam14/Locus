# U-H1 Rumor Dynamics — Code Generation Plan

> **Single source of truth for U-H1 code generation.** 브라운필드 — 기존 파일 **in-place 수정**(중복 파일 금지).
> 워크스페이스 루트: `/home/thinkpad/Desktop/src/Locus`. 앱 코드=루트, 문서(md)=`aidlc-docs/construction/U-H1-rumor-dynamics/code/`.
> 근거: FD `construction/U-H1-rumor-dynamics/functional-design/*` (BR-H1-1..20), NFR `.../nfr/nfr-light.md`.

## 컨텍스트
- **스토리/요구사항**: FR-H1(감쇠&prune) · FR-H2(증식 자격) · FR-H3(피드백) · FR-H4(파라미터) · FR-H5(배치) + NFR-H1..H5.
- **의존**: Phase 1/2 세션 레이어(모델·포트·서비스·TurnAdvancer). 캐노니컬 읽기 전용.
- **파라미터(FD-H Q3=A)**: decay 0.05 / prune_floor 0.05 / min_source_support 0.3 / feedback_weight 0.1 / high_support_threshold 0.6.
- **계약**: 공개 API·포트 시그니처는 **가산만**(기존 호출 호환). advance_turn 순서 = 피드백→감쇠→prune.

---

## Business Logic Generation

### Step 1 — `RumorDynamicsParams` + 순수 모듈 (신규 파일)
- [x] **Create** `locus/session/rumor_dynamics.py`:
  - `RumorDynamicsParams(LocusModel, frozen)` — 5필드(support_decay/prune_floor/min_source_support/feedback_weight/high_support_threshold), 기본값 상수 `DEFAULT_RUMOR_DYNAMICS`.
  - 순수 함수: `decay_support(rumors, reinforced_region_ids, *, decay)` (승격/강화 지역 면제, BR-H1-1/2/3), `is_prunable(r, *, floor)` (BR-H1-4), `partition_prunable(rumors, *, floor)`, `is_eligible_source(r, *, min_support)` (BR-H1-7), `region_feedback(rumors, *, weight, high_support_threshold)` (고-support 밀도, BR-H1-9), `_clamp`.
  - docstring에 BR-H1 참조. 부수효과·LLM·DB 없음(NFR-H1).

### Step 2 — `SessionRumor.active` 필드 (모델 확장)
- [x] **Modify** `locus/session/models.py`: `SessionRumor`에 `active: bool = True`(BR-H1-5/6). docstring 한 줄.

### Step 3 — Settings 파라미터 + 팩토리
- [x] **Modify** `locus/config/settings.py`: 5개 필드(alias `RUMOR_*`, 기본값 Q3=A) + `rumor_dynamics_params() -> RumorDynamicsParams` 헬퍼(BR-H1-15). import 순환 주의(지연 import 또는 TYPE_CHECKING).

### Step 4 — `RumorFeedbackService` (신규 파일)
- [x] **Create** `locus/session/rumor_feedback_service.py`: `RumorFeedbackService(SessionAppService)`, `__init__(repo, params=DEFAULT_RUMOR_DYNAMICS)`, `apply_feedback(session, active_rumors) -> dict[str,float]` (순수 집계 위임 + region_distortion 갱신, BR-H1-9/10). SRP.

### Step 5 — `RumorService` 증식 게이트
- [x] **Modify** `locus/session/rumor_service.py`: `append_for_region(..., *, min_source_support=None)`; `_generate_for_region`/`_collect_sources`에 `min_source_support` 전달; `_collect_sources`에서 세션 루머 소스만 `is_eligible_source`로 필터(BR-H1-7/8). 캐노니컬 소스 게이트 안 함. 수동 경로 불변.

### Step 6 — `TurnAdvancer` advance_turn 확장
- [x] **Modify** `locus/session/turn.py`:
  - `__init__(repo, loader, rumors, feedback, params=DEFAULT_RUMOR_DYNAMICS)`.
  - `advance_turn`: 스텝 순서(BR-H1-12) — 이벤트 적용 → 게이트 append(min_source_support) → 피드백(reinforced 확장) → evolve_support(이벤트) + decay_support(감쇠) → partition_prunable(soft-flag) → promotion.evaluate(survivors) → **`upsert_rumors(active)` 1회**(BR-H1-13) → bump → timeline.
  - `_decay_and_prune` 내부 헬퍼; `TurnResult`에 `pruned_rumor_ids`/`feedback_regions` 추가(BR-H1-14).

### Step 7 — `GameMasterService` DI 조립
- [x] **Modify** `locus/session/game_master.py`: `__init__`에 `feedback=None`, `rumor_params=None` 추가; `rumor_params ← settings 조립 or DEFAULT`; `feedback ← RumorFeedbackService(...)`; `turns ← TurnAdvancer(repo, loader, self._rumors, self._feedback, rumor_params)`. 공개 API 불변.

### Step 8 — `__init__.py` exports
- [x] **Modify** `locus/session/__init__.py`: `rumor_dynamics`, `RumorDynamicsParams`, `RumorFeedbackService` export(ruff import-sort).

## Repository Layer Generation

### Step 9 — 포트 + 인메모리 어댑터
- [x] **Modify** `locus/session/repository.py`: `upsert_rumors(rumors: list) -> list[SessionRumor]`; `list_rumors(session_id, region_id=None, *, include_pruned: bool=False)` (BR-H1-6, FR-H5).
- [x] **Modify** `locus/session/memory_repo.py`: `upsert_rumors`(루프 upsert, 리스트 반환); `list_rumors`에 `include_pruned` 필터(`active` False 제외 기본).

### Step 10 — Postgres 어댑터 + 스키마
- [x] **Modify** `locus/storage/postgres_session_repo.py`: `session_rumors`에 `Column("active", Boolean, nullable=False, default=True)`; `ensure_schema`에 idempotent `ADD COLUMN IF NOT EXISTS active`(BR-H1-16); `upsert_rumors`(단일 트랜잭션 배치); `list_rumors(include_pruned)` where; `_row_to_rumor`에 `active` 매핑.

## Business Logic Unit Testing

### Step 11 — 순수 동역학 테스트 + PBT
- [x] **Create** `tests/session/test_rumor_dynamics.py`: decay(면제/단조/범위), is_prunable(floor·승격 예외), partition, is_eligible_source(경계), region_feedback(밀도∈[0,1]·부호·clamp) + hypothesis(Partial) PBT.

### Step 12 — advance_turn 통합 + 생명주기 시나리오
- [x] **Modify** `tests/session/test_advance_turn.py`: 감쇠→prune(soft-flag), 승격 예외(강등만/삭제 없음), 게이트 append(자격 미달 소스 제외), 피드백 distortion↑+reinforced 면제, 배치 upsert 1회, TurnResult 신규 필드. **의도적 갱신**: `test_empty_turn_does_not_decay_support` → 새 정책(빈 턴 감쇠 O; 승격 루머 유지).

### Step 13 — 배치/포트 어댑터 테스트
- [x] **Modify** repo-contract + postgres(SQLite) 테스트: `upsert_rumors` 다건 1 트랜잭션·리스트 반환, `list_rumors(include_pruned)` 필터, `active` 컬럼 라운드트립.

## Summary / Docs

### Step 14 — 코드 요약 + 린트
- [x] `source .venv/bin/activate && ruff check --fix . && black . && python -m compileall locus api`.
- [x] **Create** `aidlc-docs/construction/U-H1-rumor-dynamics/code/code-summary.md` (수정/생성 파일, 테스트 수, 회귀 노트).

---

## 파일 매니페스트
| 액션 | 경로 |
|---|---|
| Create | `locus/session/rumor_dynamics.py` |
| Create | `locus/session/rumor_feedback_service.py` |
| Modify | `locus/session/models.py` · `rumor_service.py` · `turn.py` · `game_master.py` · `__init__.py` · `repository.py` · `memory_repo.py` |
| Modify | `locus/storage/postgres_session_repo.py` · `locus/config/settings.py` |
| Create | `tests/session/test_rumor_dynamics.py` |
| Modify | `tests/session/test_advance_turn.py` · repo-contract/postgres 테스트 |
| Create | `aidlc-docs/construction/U-H1-rumor-dynamics/code/code-summary.md` |

## 참고 — API 표면화(CH9)는 소규모
- `api/routers/session.py`의 advance-turn 응답에 `pruned_rumor_ids`/`feedback_regions`가 `TurnResult` 필드로 자동 포함(응답 모델이 TurnResult 파생이면 추가 작업 없음). 신규 라우트 없음 — Step 6에 포함되어 별도 스텝 불필요. 필요 시 Build&Test에서 응답 스키마 확인.

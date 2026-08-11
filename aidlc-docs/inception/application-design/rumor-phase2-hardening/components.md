# 하드닝 & 루머 동역학 — Components

> 입력: `rumor-phase2-hardening-requirements.md` (FR-H1..H8) + `design-questions.md`
> (AD-H Q1=B, Q2=B, Q3=A, Q4=B, Q5=B, Q6=A, Q7=A).
> 모든 변경은 **세션 레이어(PostgreSQL) additive**. 캐노니컬(Neo4j/OpenSearch) 불변.
> 구체 수치·공식·decay 타이밍은 per-unit Functional Design에서 확정.

## 컴포넌트 개요

| ID | 컴포넌트 | 신규/확장 | 위치 | 유닛 | FR |
|---|---|---|---|---|---|
| CH1 | rumor_dynamics (순수 모듈) | 신규 | `locus/session/rumor_dynamics.py` | U-H1 | H1·H2·H3·H4 |
| CH2 | RumorFeedbackService | 신규 | `locus/session/rumor_feedback_service.py` | U-H1 | H3 |
| CH3 | RumorService (확장) | 확장 | `locus/session/rumor_service.py` | U-H1 | H2 |
| CH4 | TurnAdvancer (확장) | 확장 | `locus/session/turn.py` | U-H1 | H1·H2·H3·H5 |
| CH5 | SessionRumor (모델 확장) | 확장 | `locus/session/models.py` | U-H1 | H1 |
| CH6 | SessionRepository (포트+어댑터 확장) | 확장 | `repository.py`(+memory/postgres) | U-H1 | H1·H5 |
| CH7 | Settings (확장) + RumorDynamicsParams | 확장/신규 | `locus/config/settings.py`, CH1 | U-H1 | H4 |
| CH8 | GameMasterService (코디네이터 확장) | 확장 | `locus/session/game_master.py` | U-H1 | H3·H4·H5 |
| CH9 | session API (확장, 소규모) | 확장 | `api/routers/session.py` | U-H1 | H3 |
| CH10 | web SessionPanel (병렬 refresh) | 확장 | `web/src/` | U-H2 | H6 |
| CH11 | orchestrator (조사/수정) | 조사·확장 | `locus/services/orchestrator.py` | U-H2 | H7 |
| CH12 | map_image_ingestor (조사/수정) | 조사·확장 | `locus/ingestion/…` | U-H2 | H8 |

---

## 신규 컴포넌트

### CH1. rumor_dynamics (순수 로직 모듈) — AD-H Q1=B
- **위치**: `locus/session/rumor_dynamics.py` (신규). `dynamics.py`(이벤트 동역학)와 **파일 분리** — 루머 생명주기 전용. `promotion.py`/`dynamics.py`와 동일한 순수·결정론 패턴(부수효과 없음, LLM/DB 비의존, PBT 대상 · NFR-H1).
- **책임**: FR-H1~H4의 결정론 계산.
  - **support 감쇠**(강화되지 않은 루머).
  - **prune 판정**: `support < floor` **그리고** `not promoted`(Q7=A 예외) → 정리 대상.
  - **증식 자격**: `support ≥ min_source_support` 여부(FR-H2, 자동 append 소스 게이트용).
  - **지역 피드백**: 지역별 루머 상태 집계 → 지역 distortion delta(FR-H3).
- **신규 타입**: `RumorDynamicsParams`(frozen LocusModel) — 감쇠율/바닥 임계/증식 임계/피드백 가중/고-support 임계를 담는 결정론 파라미터 묶음(`ConsensusParams` 패턴). 모듈 상수 `DEFAULT_RUMOR_DYNAMICS`. Settings에서 조립(CH7).
- **불변식**: 모든 함수 pure; support/degree clamp [0,1]; promoted 루머는 prune 대상에서 제외.

### CH2. RumorFeedbackService — AD-H Q4=B
- **위치**: `locus/session/rumor_feedback_service.py` (신규). `SessionAppService` 상속, 기존 SRP 서비스(`rumor_service`/`event_service`/`distortion_service`) 패턴 계승.
- **책임**: FR-H3 루머→지역 피드백 루프의 **소유자**. 순수 집계는 CH1의 `region_feedback`에 위임하고, 리포지토리로 지역 distortion을 갱신·타임라인 기록하는 부수효과만 담당(SRP).
- **의존(주입)**: `SessionRepository`, `RumorDynamicsParams`.
- **협력**: `TurnAdvancer`가 매 턴 새 스텝으로 호출.

---

## 확장 컴포넌트

### CH3. RumorService (확장) — AD-H Q3=A
- **추가 책임**: 자동 append 경로의 **증식 자격 게이트**. `_collect_sources`/`append_for_region`에 선택 파라미터 `min_source_support: float | None = None` 추가.
  - `None`(수동 `generate_rumors`/`regenerate_region`) → 기존 동작 불변.
  - 값 전달(TurnAdvancer) → 기존 **세션 루머 소스**를 `rumor_dynamics.is_eligible_source`로 필터(캐노니컬 direct/propagated 소스는 게이트 대상 아님).
- **불변식 유지**: 캐노니컬 읽기 전용(NFR-H2); 수동 경로 시그니처 호환.

### CH4. TurnAdvancer (확장) — advance_turn 시퀀스 강화
- **추가 책임**: advance_turn에 스텝 추가/변경(순서는 services.md 확정).
  - **support 감쇠 + prune**(FR-H1): CH1으로 감쇠 계산 → 바닥 미만 & 비승격 루머를 soft-flag(`active=False`)로 정리.
  - **증식 게이트 전달**(FR-H2): `append_for_region(..., min_source_support=params...)`.
  - **지역 피드백 스텝**(FR-H3): `RumorFeedbackService` 호출 → distortion 갱신·influenced 지역 확장.
  - **배치 영속화**(FR-H5): support 진화/정리 결과를 `upsert_rumors`로 **턴당 1 트랜잭션** 쓰기.
- **의존(주입) 추가**: `RumorFeedbackService`, `RumorDynamicsParams`.
- **불변식 유지**: 결정론(LLM 비의존, NFR-H1); 닫힌 세션 쓰기 금지.

### CH5. SessionRumor (모델 확장) — AD-H Q2=B
- **추가 필드**: `active: bool = True` (soft-flag). prune은 행 삭제가 아니라 `active=False`로 표시 → 이력/타임라인 보존(NFR-H2 가산성). 기본 True로 기존 데이터·직렬화 호환.
- **불변식**: pruned(`active=False`) 루머는 소스 수집·피드백 집계·기본 목록에서 제외.

### CH6. SessionRepository (포트 + 어댑터 확장) — AD-H Q6=A
- **신규 메서드**: `upsert_rumors(rumors: list[SessionRumor]) -> list[SessionRumor]` — 단일 트랜잭션 배치 upsert, 저장 리스트 반환(기존 `upsert_rumor`와 대칭).
- **시그니처 확장**: `list_rumors(session_id, region_id=None, *, include_pruned: bool = False)` — 기본은 `active=True`만 반환(호환: 기존 호출은 pruned 자동 제외).
- **스키마(가산, NFR-H4)**: `session_rumors`에 `active BOOLEAN NOT NULL DEFAULT TRUE` 컬럼 추가. `ensure_schema`는 `CREATE TABLE IF NOT EXISTS` + idempotent `ADD COLUMN IF NOT EXISTS`로 기존 DB에도 가산. `init-schema`가 함께 반영.
- **어댑터**: 인메모리 + Postgres(+ SQLite 오프라인 테스트) 모두 구현.

### CH7. Settings (확장) + RumorDynamicsParams 조립 — AD-H Q5=B
- **추가 필드**(env 튜닝 가능): 감쇠율/바닥 임계/증식 임계(`min_source_support`)/피드백 가중/고-support 임계. 필드명·기본값은 FD 확정.
- **조립**: Settings → `RumorDynamicsParams`(CH1) 팩토리. 순수 함수는 파라미터를 **인자로** 받으므로(기본값=DEFAULT_RUMOR_DYNAMICS) 결정성·PBT를 해치지 않음. 값의 출처만 Settings로 중앙화.

### CH8. GameMasterService (코디네이터 확장)
- **추가 책임**: DI 조립만 확장 — `RumorDynamicsParams`와 `RumorFeedbackService`를 생성/주입해 `TurnAdvancer`를 구성(미주입 시 default-construct). 공개 API 불변(thin coordinator 유지).

### CH9. session API (확장, 소규모)
- **추가**: `advance-turn` 응답의 `TurnResult`에 피드백으로 변화한 지역(또는 delta) 표면화(선택적, 표시용). 신규 라우트 없음, 기존 시그니처 호환.

### CH10. web SessionPanel (병렬 refresh) — FR-H6, U-H2
- **변경**: `SessionPanel.refresh()`의 독립 read(timeline/events/distortions/rumors)를 `Promise.all`로 병렬화(왕복 깊이 1). 동작·표시 불변. vitest 유지.

### CH11. orchestrator (조사/수정) — FR-H7, U-H2
- **조사**: `build_world`에서 `topology.build`가 wiki 주입 **전**에 실행되어 prior 미반영인지 확인. 실제 결함이면 주입 순서 조정(또는 동등 수정).

### CH12. map_image_ingestor (조사/수정) — FR-H8, U-H2
- **조사**: 연결 지역이 2개가 아닌 barrier terrain이 조용히 드롭되는지 확인. 실제 결함이면 orphan/경고로 표면화하거나 처리 규칙 보강(FD-B Q1=B 의도와 정합).

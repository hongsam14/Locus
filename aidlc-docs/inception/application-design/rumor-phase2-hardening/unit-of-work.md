# 하드닝 & 루머 동역학 — Units of Work

> 2 단위, 순차 빌드 **U-H1 → U-H2** (UOW-H Q1=A 단일 U-H1 / Q2=A 단일 U-H2 / Q3=A 순차).
> 모든 변경 additive — 캐노니컬(Neo4j/OpenSearch) 불변. 신규 디렉터리 없음
> (`locus/session/`, `locus/config/`, `locus/storage/`, `api/routers/`, `web/src/`, `locus/services/`, `locus/ingestion/` 내 additive).

## U-H1 — Rumor Dynamics
- **책임**: support(공신력)를 루머 생존·증식의 지렛대로 삼는 결정론 동역학 + 루머→지역 피드백 +
  배치 영속화. `advance_turn`이 감쇠·prune·증식 게이팅·피드백을 수행. U-H1 단독으로
  (in-memory repo + mock LLM) advance_turn 시퀀스 전체를 검증 가능.
- **컴포넌트**: CH1 `rumor_dynamics`(순수: decay_support/is_prunable/partition_prunable/is_eligible_source/
  region_feedback + `RumorDynamicsParams`) · CH2 `RumorFeedbackService` · CH3 `RumorService`(증식 게이트
  `min_source_support`) · CH4 `TurnAdvancer`(감쇠+prune·게이트 append·피드백 스텝·배치 upsert) ·
  CH5 `SessionRumor.active`(soft-flag) · CH6 `SessionRepository`(`upsert_rumors`·`list_rumors(include_pruned)`·
  `session_rumors.active` 컬럼; memory + postgres + SQLite) · CH7 `Settings`(튜닝 파라미터 → RumorDynamicsParams) ·
  CH8 `GameMasterService`(DI 조립) · CH9 session API(피드백/prune 표면화, 소규모).
- **요구사항**: FR-H1(감쇠&prune) · FR-H2(증식 자격) · FR-H3(루머→지역 피드백) · FR-H4(결정적 파라미터) ·
  FR-H5(배치 upsert) + NFR-H1(결정성) · NFR-H2(호환/격리) · NFR-H3(PBT/오프라인) · NFR-H4(가산 컬럼만).
- **산출물**: `locus/session/rumor_dynamics.py`(신규) · `rumor_feedback_service.py`(신규) ·
  `rumor_service.py`/`turn.py`/`game_master.py`/`models.py`/`__init__.py`(확장) ·
  `locus/session/repository.py`/`memory_repo.py` + `locus/storage/postgres_session_repo.py`(확장) ·
  `locus/config/settings.py`(확장) · `api/routers/session.py`(소규모 확장) · tests(PBT 포함).
- **독립 검증**: 순수 동역학 PBT(감쇠 단조성·prune 임계·자격 경계·피드백 불변식) + in-memory repo/mock LLM
  advance_turn 통합(감쇠/게이팅/피드백/배치/승격 예외) + 배치 어댑터 오프라인(SQLite).
- **FD 확정 항목**: 파라미터 값 · 피드백 집계식 · advance_turn 스텝 순서(피드백↔감쇠) · empty-turn 감쇠 정책 ·
  decay의 reinforced 집합 정의.
- **리스크**: Medium-High(세계 밸런스·기존 Phase 2 턴 동작 변경). 완화: "무효화-근접 기본값" + 파라미터화 +
  회귀 스위트 유지.

## U-H2 — Fixes (프론트 + 캐노니컬 빌드 조사)
- **책임**: 상호 독립적인 소규모 3건. H7/H8은 **조사 우선** → 실제 결함이면 수정.
- **컴포넌트**: CH10 web `SessionPanel.refresh()`(`Promise.all` 병렬화) · CH11 `orchestrator.build_world`
  (`topology.build` vs wiki 주입 순서 조사/수정) · CH12 `map_image_ingestor`(연결≠2 barrier terrain 드롭
  조사/수정).
- **요구사항**: FR-H6(프론트 병렬 refresh) · FR-H7(set_wiki 순서) · FR-H8(barrier terrain 드롭) +
  NFR-H2(호환) · NFR-H3(vitest/오프라인) · NFR-H5(확장).
- **산출물**: `web/src/`(SessionPanel, vitest) · `locus/services/orchestrator.py`(조사→필요 시 수정) ·
  `locus/ingestion/…`(조사→필요 시 orphan/경고/규칙 보강) · 관련 테스트/회귀.
- **독립 검증**: vitest + tsc(프론트); 오프라인 pytest로 orchestrator 순서·ingestor 엣지케이스 회귀.
- **비고**: 캐노니컬 빌드 경로 — U-H1(세션 레이어)과 **상호 의존 없음**. 조사 결과 결함이 아니면
  코드 변경 없이 결론 문서화(FD-B 정합).
- **리스크**: Low(프론트 표시 불변) ~ Medium(FR-H7 빌드 경로 수정 시 토폴로지 가중 영향).

## 순서 / 독립성
- **U-H1 → U-H2** (UOW-H Q3=A). 상호 의존 없음(U-H2를 먼저/병렬로 처리해도 무방하나 문서상 순차).
- U-H1이 핵심·고위험이라 선행; U-H2는 독립 소규모라 후행.

## 코드 조직 (브라운필드 — 신규 디렉터리 없음)
| 영역 | 경로 | 단위 |
|---|---|---|
| 순수 동역학 | `locus/session/rumor_dynamics.py` (신규) | U-H1 |
| 피드백 서비스 | `locus/session/rumor_feedback_service.py` (신규) | U-H1 |
| 세션 서비스/모델/포트 | `locus/session/*.py` (확장) | U-H1 |
| Postgres 어댑터 | `locus/storage/postgres_session_repo.py` (확장) | U-H1 |
| 설정 | `locus/config/settings.py` (확장) | U-H1 |
| API | `api/routers/session.py` (확장) | U-H1 |
| 프론트 | `web/src/` (확장) | U-H2 |
| 캐노니컬 빌드 | `locus/services/orchestrator.py`, `locus/ingestion/…` (조사/수정) | U-H2 |

# Rumor Dynamics & Phase 2 Hardening — Build & Test Summary

> Units U-H1 (Rumor Dynamics) + U-H2 (Fixes). additive; 캐노니컬 불변; 신규 인프라 없음.

## Build Status
- **Backend**: import/compile 클린 (`compileall locus api`). `locus init-schema`는 `session_rumors.active`를
  idempotent 가산(`ADD COLUMN IF NOT EXISTS`, 비-SQLite). 신규 인프라 없음(NFR-H4).
- **Frontend**: `tsc --noEmit` 클린; vitest 통과.
- **Lint**: ruff + black 클린 (line 100).

## Test Execution Summary
### Unit Tests — Backend
- **Total / Passed / Failed**: **249 / 249 / 0**
- **Status**: ✅ Pass (Phase 2 완료 시점 219 → +30: U-H1 +27, U-H2 +3)
- PBT (hypothesis, Partial): `rumor_dynamics` 순수 함수 3건 — decay 범위/단조/면제, prunable 정의,
  region_feedback 밀도 경계 (NFR-H1/H3).
- 주요 신규 커버리지: 감쇠·prune(soft-flag)·증식 게이트·루머→지역 피드백·birth support·배치 upsert·
  orchestrator set_wiki 순서·barrier terrain 가시화.

### Unit Tests — Frontend
- **Total / Passed / Failed**: **19 / 19 / 0** (5 pure + 14 component)
- **Status**: ✅ Pass (17 → +2: SessionPanel 병렬 refresh 2건)

### Integration Tests
- **Offline**: ✅ GameMasterService + FastAPI TestClient + in-memory/SQLite로 advance_turn 확장 시퀀스
  (피드백→감쇠→prune→배치), 배치 어댑터, orchestrator 빌드 경로, ingestor 엣지케이스 검증.
- **Live (operator-run)**: 실 PostgreSQL(active 컬럼 마이그레이션)/LLM/web은 운영자 실행 — 문서화, 자동 미실행.

### Performance
- 경량 노트만(로컬 저작 도구, SLA 없음). 동역학 스텝은 결정적·O(rumors) 무시 수준; 배치 upsert로 턴당
  DB 왕복 감소. 프론트 refresh 병렬화로 체감 지연 감소(왕복 4→1). LLM 루머 생성이 유일한 지연 요인.

### Additional
- Contract/Security/E2E: N/A(Security off, PBT Partial on).

## 회귀 (의도된 변경 1건)
- **[3] 반전**: "빈 턴 support 감쇠 금지" → 매 턴 감쇠(FD-H Q1=A). `test_empty_turn_does_not_decay_support`를
  새 정책 테스트로 명시적 갱신(+승격 면제 테스트). 그 외 Phase 1/2 동작·NPC 쿼리 규칙·캐노니컬 경로 불변.

## 환경 노트 (코드 무관)
- 시스템 `/usr/bin/python3` 3.14 업그레이드로 `.venv`(3.13.7) `python3` 심링크 파손 → `python -m pytest` 실패.
  검증은 `PYTHONPATH=.venv/lib/python3.13/site-packages /usr/bin/python3.13 -m pytest`로 수행.
  복구: `.venv/bin/python3` → `/usr/bin/python3.13` 재지정 또는 venv 재생성.

## Overall Status
- **Build**: ✅ Success
- **Tests**: ✅ **268 offline GREEN** (backend 249 + frontend 19), lint/compile/tsc 클린, 회귀 0(의도적 갱신 제외).

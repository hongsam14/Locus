# UX Improvement — Unit/Component Test Instructions

## Backend
```bash
.venv/bin/python -m pytest -q          # expect 281 passed, ~87% cov
.venv/bin/ruff check locus api tests
.venv/bin/black --check locus api tests
```
핵심 신규 테스트:
- `tests/translation/test_translator.py`, `test_translation_service.py`(PBT: source_hash, cache-only+warm, fail-safe, lang)
- `tests/session/test_turn_changes.py`(PBT), `test_translation_enrichment.py`/`test_localization_api.py`
- `tests/storage/test_translation_repo.py`(CRUD·batch·`statement_ko` 비영속)
- `tests/session/test_game_master.py::test_regenerate_preserves_promoted_rumors`(승격 보존 + 무증식 count==4)

## Frontend
```bash
cd web
npm test          # vitest — expect 24 passed
npx tsc --noEmit  # types clean
```
핵심 신규 테스트(`web/src/__tests__/components.test.tsx`):
- generate-all 빈지역만 · regen-all 확인 모달 · advance-turn 지역별 알림 · 원문 토글 · 타임라인 i18n · 기존 계약(data-testid) 보존.

## Expected
- **305 offline tests GREEN** (281 backend + 24 frontend), 0 회귀, lint/tsc clean.

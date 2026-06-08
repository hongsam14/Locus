# U7 Augmentation — Code Generation Plan

Code 위치 = `locus/augmentation/` + `api/routers/authoring.py`(증강 엔드포인트). Stories US-6.1~6.3.

## Steps  (ALL DONE — 104 tests pass, ruff/black clean)
- [x] **Step 1 — types** (`locus/augmentation/types.py`): IssueType/Issue, AugmentationQuestion, AugmentationAnswer(action), NodeSnapshot, ChangeSet, AugmentationSession (+ status).
- [ ] **Step 2 — detectors** (`locus/augmentation/detectors.py`): `detect_gaps`(빈/인접무공유/dangling) + `detect_low_confidence` (순수); `detect_wiki_conflicts(... wiki, llm)` (LLM, graceful); `detect_all`.
- [ ] **Step 3 — questions** (`locus/augmentation/questions.py`): `QuestionGenerator.generate(issue, llm=None)` — 템플릿(순수) + LLM structured 옵션.
- [ ] **Step 4 — apply/revert** (`locus/augmentation/apply.py`): `apply_answer(answer, world_id, editor, kg) -> ChangeSet`(confirm/remove/add/edit/ignore, snapshot) ; `revert(change_set, editor)`.
- [ ] **Step 5 — session store** (`locus/augmentation/session_store.py`): `SessionStore`(Protocol) + `InMemorySessionStore`. (PostgreSQL 차후.)
- [ ] **Step 6 — engine** (`locus/augmentation/engine.py`): `AugmentationEngine(loader, editor, wiki, llm)` detect_issues/generate_questions/apply_answer/revert.
- [ ] **Step 7 — service + graph** (`locus/augmentation/service.py` + `graph.py`): `AugmentationService(engine, store, max_rounds)` start_session/submit_answer/revert(루프·수렴) ; `graph.py` LangGraph 구성(설치 시) — graceful.
- [ ] **Step 8 — `__init__.py`**.
- [ ] **Step 9 — API**: `api/routers/authoring.py`에 augment session/answer/revert 엔드포인트 + app factory에 `augmentation_service` DI.
- [ ] **Step 10 — Tests** (`tests/augmentation/`): detectors(순수: gap/dangling/low-conf), questions 템플릿, apply/revert(mock editor, ChangeSet), session store, engine(mock loader/llm), service 루프(mock), API(TestClient, mock service). + LangGraph 빌드(설치 시) 또는 skip.
- [ ] **Step 11 — Docs**: `construction/U7-augmentation/code/code-gen-summary.md`.

## Story Coverage
US-6.1→Step2,3 · US-6.2→Step4,6,7 · US-6.3→Step4(revert).

## Notes
- 순수 detector/apply/템플릿 직접 테스트. LLM·LangGraph·HTTP mock/graceful. 생성 후 전체 pytest 회귀.

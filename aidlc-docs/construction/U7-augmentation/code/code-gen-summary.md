# U7 Augmentation — Code Generation Summary

**Date**: 2026-06-08
**Stories**: US-6.1 (issue→question), US-6.2 (interactive loop), US-6.3 (revert).
**Verification**: 104 tests PASS (93 prior + 11 U7, incl. augment API TestClient); ruff + black clean. Offline (LLM/LangGraph/HTTP mocked or graceful).

## Created files (`locus/augmentation/`)
- `types.py` — Issue/AugmentationQuestion/AugmentationAnswer/NodeSnapshot/ChangeSet/AugmentationSession + enums (IssueType/AnswerAction/SessionStatus).
- `detectors.py` — `detect_gaps` (empty regions + dangling relations, pure), `detect_low_confidence` (pure), `detect_wiki_conflicts` (LLM, graceful), `detect_all` (+dedup).
- `questions.py` — `QuestionGenerator` (per-type template + optional LLM structured draft).
- `apply.py` — `apply_answer` (confirm/remove/add/edit/ignore → graph mutation + ChangeSet snapshots), `revert`.
- `session_store.py` — `SessionStore` protocol + `InMemorySessionStore` (PostgreSQL-swappable per Q5 note).
- `engine.py` — `AugmentationEngine` (detect/generate/apply/revert over WorldLoader + GraphEditor + wiki + llm).
- `service.py` — `AugmentationService` (start_session / submit_answer loop w/ convergence / revert).
- `graph.py` — optional LangGraph detection graph (lazy import; AD-CL1=A).
- `__init__.py`.

## Modified files (additive)
- `api/routers/authoring.py` — augment session / answer / revert endpoints.
- `api/main.py` — `augmentation_service` state key + default wiring.

## Created tests (`tests/augmentation/`)
- `test_augmentation.py` — detectors (gap/dangling/low-conf), question template, apply ADD (+scope) / REMOVE+revert, session store, service loop convergence.
- `test_augment_api.py` — TestClient: start 200, answer 200, missing-session 404, revert 204.

## Key realizations
- **Three detectors** (CL5=A/B/C): deterministic gap/dangling/low-confidence + LLM wiki-conflict (graceful).
- **Loop** (AD-CL1=A): pure core (detect/generate/apply) + `AugmentationService` orchestration (the real human-in-the-loop), with an optional LangGraph view.
- **Revert** (US-6.3): every apply records a ChangeSet (before-snapshots) → reversible. Added knowledge carries `source=augmentation`.
- **SessionStore abstraction** keeps the door open for PostgreSQL (Q5 note) without touching the service.

## Stage notes
- NFR-R / NFR-D / Infrastructure Design SKIPPED for U7 (LangGraph already in stack; reuses U1/U8/U9; no new infra).

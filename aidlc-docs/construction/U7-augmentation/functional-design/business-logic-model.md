# U7 Augmentation — Business Logic Model

## Detectors (`locus/augmentation/detectors.py`)
순수(가능한 한): in-memory KnowledgeGraph + RegionTopology에서.
- `detect_gaps(kg, topo) -> [Issue]`: 직접 지식 0 지역(gap); CONNECTED_TO(weight≥θ) 인접인데 공유 지식 0(gap); 끊긴 관계(dangling: relation.source/target가 엔티티에 없음).
- `detect_low_confidence(kg, threshold) -> [Issue]`: confidence<threshold 지식/엔티티(low_confidence).
- `detect_wiki_conflicts(kg, topo, wiki, llm) -> [Issue]` (LLM): 지역 지형 + 지식을 prior와 대조, 모순이면 contradiction/wiki_conflict. 실패/LLM 없음 → [].

## QuestionGenerator (`locus/augmentation/questions.py`)
- `generate(issue, llm=None) -> AugmentationQuestion`: LLM structured(text+options) 또는 타입별 템플릿 폴백. 순수 템플릿부 테스트 가능.

## apply / revert (`locus/augmentation/apply.py`)
- `apply_answer(answer, *, world_id, editor, graph_repo) -> ChangeSet`:
  - confirm → 대상 지식 confidence 상향(edit) ; remove → editor.delete_node(+snapshot) ; add → 신규 Knowledge(+scope) upsert ; edit → statement/confidence 수정 ; ignore → no-op.
  - 변경 전 노드 스냅샷을 ChangeSet에 기록.
- `revert(change_set, *, editor, graph_repo)`: added 삭제, removed/updated 복원.

## AugmentationEngine (`locus/augmentation/engine.py`)
- `detect_issues(world_id) -> [Issue]`: WorldLoader.load → 모든 detector 합집합(중복 dedup).
- `generate_questions(issues) -> [AugmentationQuestion]`.
- `apply_answer(world_id, answer) -> ChangeSet` ; `revert(change_id)`.

## AugmentationGraph (LangGraph, `locus/augmentation/graph.py`, AD-CL1=A)
- 노드: detect → generate → (await answer; UI/API가 답 제공) → apply → re-detect → check(converged?).
- LangChain/LangGraph로 구성하되, 각 노드는 위 순수/엔진 함수 호출. (LangGraph 미설치 시 graceful: 엔진 직접 사용.)
- `AugmentationService.start_session(world_id) -> AugmentationSession`(detect+generate, SessionStore 저장) ; `submit_answer(session_id, answer) -> ChangeSet`(apply + re-detect + 다음 질문) ; `revert(session_id, change_id)`.

## SessionStore (`locus/augmentation/session_store.py`)
- `SessionStore`(Protocol): get/save/delete. `InMemorySessionStore`(dict). **PostgreSQL 구현은 차후 교체**(Q5 note).

## API/CLI 연계 (U9 authoring에 추가 — 별도 등록)
- `POST /api/authoring/worlds/{world_id}/augment/session` → start ; `POST .../augment/{session_id}/answer` → submit ; `POST .../augment/{session_id}/revert`.
- (U10 Web UI가 이 API 사용; U7은 백엔드까지.)

## 재사용
- WorldLoader(U8), GraphEditor(U9), CommonsenseWiki(U1), LLMProvider(U1). 신규 인프라 없음.

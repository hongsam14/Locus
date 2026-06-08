# U7 Augmentation — Business Rules

## 탐지 (CL5=A,B,C)
- BR-U7-1: detector는 world_id 스코프 in-memory 그래프에서만 동작.
- BR-U7-2: gap = 직접 지식 0 지역 또는 연결(weight≥θ, 기본 0.5) 인접인데 공유 지식 0.
- BR-U7-3: dangling = relation.source/target가 엔티티 집합에 없음.
- BR-U7-4: low_confidence = confidence < 0.5.
- BR-U7-5: wiki_conflict = LLM이 지식 vs 상식 prior 모순으로 판정(실패 시 생략, graceful).
- BR-U7-6: 동일 대상에 중복 이슈는 dedup.

## 질문 (FD7-Q3=A)
- BR-U7-7: 질문은 이슈에서 생성; LLM 실패/부재 시 타입별 템플릿 폴백(항상 질문 생성 가능).
- BR-U7-8: 질문에는 최소 1개 선택지 + free 입력 허용.

## 적용 / 되돌리기 (FD7-Q4=A, US-6.3)
- BR-U7-9: 모든 적용은 ChangeSet(before snapshot) 기록 — revert 가능.
- BR-U7-10: add로 생성된 지식은 source=augmentation, provenance.refs=[change_id] (BR-9 일관).
- BR-U7-11: remove/edit는 변경 전 노드 스냅샷 보존.
- BR-U7-12: revert는 added 삭제 + removed/updated 복원, world_id 스코프.

## 세션 / 수렴 (FD7-Q5=A)
- BR-U7-13: 세션은 SessionStore 경유(InMemory MVP; PostgreSQL 교체 가능 — 추상화 유지).
- BR-U7-14: 수렴 = 새 이슈 없음 또는 round ≥ max_rounds(기본 5) → status=converged/stopped.
- BR-U7-15: 답변 적용 후 재탐지하여 다음 질문 생성(루프).

## 결정성/테스트
- BR-U7-16: detect_gaps/detect_low_confidence/템플릿 질문/apply 매핑은 순수 → 단위 테스트. LLM(wiki_conflict·질문 생성)·LangGraph 루프는 mock/얇게.

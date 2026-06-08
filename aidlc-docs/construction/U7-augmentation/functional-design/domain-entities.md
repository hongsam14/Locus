# U7 Augmentation — Domain Entities & Schemas

결정: FD7 전부 A. 세션은 in-memory(추후 PostgreSQL 교체 가능 — SessionStore 추상화).

## 모델 (`locus/augmentation/types.py`, Pydantic)
```text
IssueType = gap | contradiction | dangling | wiki_conflict | low_confidence
Issue { id, type, description, target_ids:[..], region_id?, severity(0~1) }

AugmentationQuestion { id, issue_id, text, options:[str], kind(confirm|choose|free) }
AugmentationAnswer  { question_id, action(confirm|remove|add|edit|ignore), payload:{statement?, confidence?, region_id?} }

NodeSnapshot { id, label, properties }     # for revert
ChangeSet { id, description, added_ids:[..], removed:[NodeSnapshot], updated:[NodeSnapshot(before)] }

AugmentationSession {
  id, world_id, round, status(open|converged|stopped),
  open_questions:[AugmentationQuestion], history:[ChangeSet]
}
```

## 탐지(Issue) 규약 (CL5=A,B,C / FD7-Q1=A)
- **gap/contradiction/dangling (결정적)**: 직접 지식 0인 지역; 연결(weight≥θ) 인접인데 공유 지식 0; 끊긴 관계(존재하지 않는 엔티티 참조).
- **wiki_conflict (LLM)**: 지역 지형 attribute + 지식이 상식 prior와 모순되는지 LLM 판정.
- **low_confidence**: confidence < LOW_THRESHOLD(0.5) 지식/엔티티.

## 질문 생성 (FD7-Q3=A)
- 이슈 → `llm.structured(AugmentationQuestionDraft)`(text + options) ; 실패/LLM 없음 → 타입별 템플릿.

## 답변 적용 (FD7-Q4=A)
- action 매핑: confirm(=confidence 상향) / remove(=delete_node) / add(=신규 지식+스코프) / edit(=statement·confidence 수정) / ignore.
- 각 적용 → `ChangeSet` 기록(GraphEditor 재사용). revert(change_id) → 역적용.

## 세션/수렴 (FD7-Q5=A)
- `SessionStore`(추상): `InMemorySessionStore`(MVP). 추후 PostgreSQL 구현 교체 가능.
- 수렴: 새 이슈 없음 또는 round ≥ max_rounds(기본 5).

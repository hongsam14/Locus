# S2 (Rumor Engine) — Domain Entities (Functional Design)

Unit **S2**. FR-R2/R3/R4/R5. **S1의 `SessionRumor`/`TimelineEntry`/enums는 변경 없이 재사용** — S2는 그 위에 로직과 소수의 결과/스키마 타입만 추가한다.
확정 답: FD-S2 **Q1=A**(체인=리전 degree 스케일)/**Q2=direct+propagated+세션Rumor**/**Q3=A**(이전 단계 재왜곡)/**Q4=A**(재생성 시 전체 삭제)/**Q5=A**(support 초기 0.0·threshold 0.6)/**Q6=A**(승격=direct-like·is_rumor 유지)/**Q7=A**(query/engine.py 순수 helper).

---

## 1. 모델 변경 없음 (S1 계약 유지)
- `SessionRumor`(id/session_id/region_id/distorted_from_id/distorted_from_kind/statement/distortion_degree/support/confidence/promoted/provenance) — 모든 필드 그대로 사용.
- `TimelineEntry` + `TimelineKind`(GENERATE/REGENERATE/PROMOTE/DEMOTE/ADJUST_SUPPORT/ADVANCE_TURN/SET_DISTORTION) — 그대로.
- `SessionRepository` 포트 — 그대로(추가 메서드 없음).
- **캐노니컬 모델/`QueryEngine` 무변경** — `query/engine.py`에 순수 함수만 추가(아래 §5).

## 2. 신규: `RumorDraft` (LLM structured output, `locus/session/rumor_generator.py`)
한 단계의 왜곡 텍스트만 담는 구조화 출력 스키마.
```
RumorDraft(LocusModel):
  statement: str          # the distorted statement for one degree step
```
- LLM은 (원본/이전 텍스트 + degree)로 `statement`를 생성. 나머지 `SessionRumor` 필드는 코드가 채움.

## 3. 신규: `PromotionResult` (순수, `locus/session/promotion.py`)
승격/강등 **전이(transition)** 만 담는 순수 결과.
```
PromotionResult(LocusModel):
  promoted_ids: list[str]   # support>=threshold AND not yet promoted -> newly promote
  demoted_ids:  list[str]   # support<threshold  AND currently promoted -> demote
```
- `PromotionPolicy.evaluate(rumors, threshold) -> PromotionResult` (순수, PBT 대상, NFR-R5).

## 4. 신규: `TurnResult` (`locus/session/game_master.py`)
`advance_turn` 결과 요약(API 응답).
```
TurnResult(LocusModel):
  session_id: str
  turn: int                 # new turn after bump
  promoted_ids: list[str]
  demoted_ids: list[str]
```

## 5. 신규 순수 helper (Q7=A, `locus/query/engine.py` — 클래스 무변경, 함수만 추가)
```
def canonical_known(view: ConsensusView) -> list[KnowledgeView]:
    """NPC가 실제로 아는 캐노니컬 지식 = direct + inherited + global.
    propagated 와 auto-rumor(view.rumors)는 제외(기획자 전용, FR-R5.1)."""
    return view.direct + view.inherited + view.global_knowledge
```
- 기존 `view_items`(propagated 포함)와 **별개**. `QueryEngine` 클래스/메서드는 손대지 않음(NFR-R6 회귀 0).

## 6. 강도 체인 상수 (`rumor_generator.py` 또는 `game_master.py`)
```
DEFAULT_CHAIN_FRACTIONS = [1/3, 2/3, 1.0]   # Q1=A: degrees = [f * region_degree for f in fractions]
DEFAULT_PROMOTION_THRESHOLD = 0.6           # Q5=A
```
- 리전 distortion d 에 대해 체인 degrees = `[d/3, 2d/3, d]`(상한 = 리전 degree). d=0.3 → `[0.1, 0.2, 0.3]`.

## 7. 파생 규칙 요약 (상세는 business-logic-model / business-rules)
- **degree[i]** = fraction[i] × 리전 distortion (원본 사실로부터의 절대 왜곡도).
- **confidence[i]** = 원본(소스) confidence × (1 − degree[i]) (FR-R2.6; degree↑ → confidence↓, 단조).
- **distorted_from**(Q3=A, 텍스트 계보): step0 → 소스(knowledge|rumor), step i>0 → step i−1(kind=rumor). LLM은 step i 생성 시 step i−1 텍스트를 입력으로 받음.
- **support** 초기 0.0(Q5=A); 승격은 advance_turn에서만 평가.

## 8. 관계 요약 (Mermaid)
```mermaid
graph LR
  SRC["소스: direct Knowledge | propagated KnowledgeView | 기존 SessionRumor"]
  SRC -- "degree d/3" --> R0["SessionRumor step0 (distorted_from=소스)"]
  R0  -- "degree 2d/3" --> R1["SessionRumor step1 (distorted_from=step0, kind=rumor)"]
  R1  -- "degree d" --> R2["SessionRumor step2 (distorted_from=step1, kind=rumor)"]
  R2 -. promoted(support≥0.6) .-> KV["KnowledgeView (scope=direct, is_rumor=True)"]
```

# S2 (Rumor Engine) — Business Rules (Functional Design)

Unit **S2**. FR-R2/R3/R4/R5. 왜곡·체인·confidence·승격/강등·턴·타임라인·NPC 쿼리 규칙.
확정 답: FD-S2 Q1=A / Q2=direct+propagated+세션Rumor / Q3=A / Q4=A / Q5=A / Q6=A / Q7=A.

---

## 소문 생성 (FR-R2)

- **BR-S2-1 (리전별 생성)**: `generate_rumors`는 한 리전을 대상으로, 그 리전의 **direct Knowledge + propagated 지식 + 기존 세션 Rumor**를 원본으로 소문을 만든다. (FR-R2.1, Q2)
- **BR-S2-2 (강도 체인)**: 한 번 생성 시 강도 오름차순 다단계 체인을 만든다. degrees = `[f × d for f in [1/3, 2/3, 1]]`(d=그 리전 `distortion_degree`). 리전 degree가 체인의 상한이다. (FR-R2.3/2.5, Q1=A)
- **BR-S2-3 (텍스트 계보)**: 체인의 첫 단계는 원본을 왜곡(`distorted_from_kind`=knowledge 또는 rumor), 이후 각 단계는 **직전 단계 텍스트를 재왜곡**(`distorted_from_id`=직전 SessionRumor id, `kind=rumor`). LLM은 각 단계에서 직전 텍스트를 입력으로 받는다. (FR-R2.2/2.3, Q3=A)
- **BR-S2-4 (LLM 실제 왜곡)**: degree를 프롬프트에 명시하여 LLM이 statement를 실제로 변형한다(세부변경→과장→부분오류→거의 허구). (FR-R2.4)
- **BR-S2-5 (confidence)**: 각 단계 `confidence = 원본(소스) confidence × (1 − degree[i])`. degree↑ → confidence↓(단조). (FR-R2.6)
- **BR-S2-6 (재생성)**: `regenerate_region`은 그 리전의 세션 Rumor를 **전부 삭제(승격 포함)** 후 재생성한다(깨끗한 re-roll). (FR-R2.7, Q4=A)
- **BR-S2-7 (graceful)**: 한 단계 LLM 실패 시 그 단계와 이후 단계를 중단하고(체인이 직전 텍스트에 의존) 성공한 앞 단계만 저장·기록한다. 세션/턴 진행은 계속. (NFR-R4)

## 지지도 & 승격/강등 (FR-R3)

- **BR-S2-8 (초기 support)**: 생성 소문의 초기 `support`=0.0. 승격하려면 `adjust_support`로 올려야 한다(Phase 1 수동). (FR-R3.1, Q5=A)
- **BR-S2-9 (닫힌 세션 불변)**: CLOSED 세션에 대한 쓰기 동작(generate/regenerate/adjust_support/set_distortion/advance_turn)은 거부된다(409). (S1 BR-S1-5 연장)
- **BR-S2-10 (승격 기준)**: advance_turn에서 `support ≥ threshold`(기본 0.6)인 Rumor를 승격(`promoted=True`)한다. 승격은 그 세션·그 리전 한정이며 캐노니컬 Neo4j엔 기록하지 않는다. (FR-R3.2, Q5=A, NFR-R2)
- **BR-S2-11 (강등)**: 이전에 승격됐으나 `support < threshold`로 내려간 Rumor는 강등(`promoted=False`)된다. 승격은 비영속·가역. (FR-R3.3)
- **BR-S2-12 (평가 시점)**: 승격/강등은 **advance_turn에서만** 재평가되고 각 전이가 타임라인에 기록된다. adjust_support 자체는 승격 상태를 바꾸지 않는다. (FR-R3.4)
- **BR-S2-13 (전이 순수성)**: `PromotionPolicy.evaluate`는 순수 함수로 전이(promoted_ids/demoted_ids)만 산출한다. 이미 승격+여전히 충족이면 변화 없음(멱등). (NFR-R5)

## GameMaster · 턴 · Timeline (FR-R4)

- **BR-S2-14 (턴 동작)**: Phase 1 GameMaster는 턴 단위로 생성/재생성/승격/강등을 수행하고 리전별 distortion을 보유/설정한다. (FR-R4.1)
- **BR-S2-15 (타임라인 기록)**: 모든 동작은 정확히 하나의 `TimelineEntry`(현재 turn, 해당 `TimelineKind`, payload에 영향받은 id)를 남긴다. (FR-R4.2)
- **BR-S2-16 (turn 증가)**: `advance_turn`은 승격/강등 적용 후 `turn`을 1 증가시키고 ADVANCE_TURN 항목을 기록한다. (FR-R4.1)
- **BR-S2-17 (Event 제외)**: Event 상호작용·동적 distortion 진화는 Phase 2. S1/S2는 타임라인 구조와 GameMaster 골격만 갖춘다. (FR-R4.3)

## NPC 쿼리 규칙 (FR-R5)

- **BR-S2-18 (세션 NPC 뷰)**: 세션 컨텍스트 NPC 결과 = **direct + inherited + global Knowledge + 승격 Rumor(direct처럼) + 일반 Rumor**. 거리 기반 `propagated`와 auto-rumor 뷰는 NPC에 직접 노출하지 않는다(기획자 전용). (FR-R5.1, Q7=A)
- **BR-S2-19 (원거리=소문 only)**: 원거리(propagated) 정보는 NPC 뷰에서 제외되며, 그것을 원본으로 만든 (왜곡된) Rumor로만 리전에 도달한다(Q2 결정의 귀결). (FR-R5.1)
- **BR-S2-20 (승격 표현)**: 승격 Rumor는 `KnowledgeView(scope_type=direct, is_rumor=True)`로 노출 — direct처럼 취급하되 출처가 소문임을 `is_rumor`로 투명하게 표시한다. (FR-R3.2, Q6=A)
- **BR-S2-21 (비세션 회귀 없음)**: 세션이 지정되지 않은 캐노니컬 쿼리는 기존 `QueryEngine` 동작을 그대로 유지한다. (FR-R5.2, NFR-R6)
- **BR-S2-22 (QueryEngine 무변경)**: propagated/auto-rumor 제외는 `query/engine.py`의 신규 순수 helper `canonical_known`으로만 처리하고 기존 `QueryEngine` 클래스/메서드는 변경하지 않는다. (Q7=A, NFR-R6)

## 격리 / 회귀 (NFR)

- **BR-S2-23 (캐노니컬 read-only)**: S2의 모든 캐노니컬 접근(소스 수집·consensus 계산)은 읽기 전용이다. 소문/승격/턴 쓰기가 Neo4j/OpenSearch를 변경하지 않는다. (NFR-R2)
- **BR-S2-24 (세션 격리)**: 모든 동작은 `session_id`(필요 시 +`region_id`) 범위로 격리된다. (S1 BR-S1-15 연장)
- **BR-S2-25 (결정론/테스트)**: LLM/DB 포트와 순수 로직(degree/confidence 계산, 승격 판정)을 분리한다. 순수 부분은 PBT(Partial) 대상. (NFR-R5)
- **BR-S2-26 (회귀)**: 기존 캐노니컬/세션(S1) 테스트는 GREEN을 유지하고 ruff/black 클린이어야 한다. (NFR-R6)

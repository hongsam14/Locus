# U5 Consensus — Business Rules

## 분류 / 우선순위
- BR-U5-1: 한 knowledge는 한 지역 ConsensusView에서 한 번만 — 우선순위 direct > inherited > global > propagated > rumor.
- BR-U5-2: direct = 해당 지역 SCOPED_TO(direct); confidence = scope.confidence.
- BR-U5-3: inherited = CONTAINS 조상의 direct (scope_type=inherited).
- BR-U5-4: global = is_global 지식 전부, 모든 지역에 포함(CL1=A).

## 전파 / 감쇠 (Q1=A)
- BR-U5-5: path_weight = 경로 CONNECTED_TO weight 곱, 지역별 **최대(max-product)** 채택.
- BR-U5-6: 도달 confidence = knowledge.confidence × path_weight ∈ [0,1].
- BR-U5-7: pw ≥ PROPAGATE_MIN(0.5) → propagated; RUMOR_MIN(0.15) ≤ pw < 0.5 → rumor; pw < 0.15 → unknown_count.
- BR-U5-8: rumor view는 is_rumor=true, distortion_degree = 1 − pw (접근 어려울수록 왜곡↑).
- BR-U5-9: 전파는 자기 지역/이미 분류된 knowledge 제외.

## 표현 / 영속
- BR-U5-10: 전파·소문은 **쿼리 시점 계산(ephemeral)**, 노드 미영속(Q2=A). 직접 스코프는 정적(U4 저장분).
- BR-U5-11: U5는 in-memory KnowledgeGraph+RegionTopology에서만 계산(IO 없음, Q4=A).

## 결정성/테스트
- BR-U5-12: compute_consensus / best_path_weights 는 순수 함수 → 단위 테스트/PBT (confidence·pw ∈ [0,1] 불변).
- BR-U5-13: 파라미터(PROPAGATE_MIN/RUMOR_MIN)는 주입 가능(기본값 명시).

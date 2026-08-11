# P2 Dynamic Engine — Business Rules

> BR-P2-*. additive; 캐노니컬 불변; Phase 1 + P1 회귀 0.

| ID | 규칙 |
|---|---|
| **BR-P2-1** | `distortion_delta(m) = clamp(m) * MAX_EVENT_DELTA`(0.3). 순수·결정론 (FD-P2 Q1). |
| **BR-P2-2** | 전파: 이웃 delta = base × best_path_weight, `weight ≥ 0.15`(PROPAGATE_MIN_WEIGHT)인 이웃만. 주 대상=base(weight 1.0). (FD-P2 Q2) |
| **BR-P2-3** | distortion 적용은 누적 + [0,1] clamp. persistent는 활성 동안 매 턴 동일 delta 재적용(누적). (FR-P3.4 / CL1.2) |
| **BR-P2-4** | `one_shot`은 적용 턴 1회 후 status=RESOLVED(resolved_turn 기록), 복원 없음(영구 bump). (FD-P2 Q3=A) |
| **BR-P2-5** | persistent 해소 시 `contributions`(주 대상+전파 이웃)를 대칭 차감 복원 + clamp. (FR-P3.6 / CL1.2 / AD-P Q5=A) |
| **BR-P2-6** | Event 적용은 `advance_turn` 일괄. 순서: 적용→소문→support→승격/강등→one_shot resolve→bump→timeline. (FR-P3.3) |
| **BR-P2-7** | 주 대상 리전 소문은 append 생성(기존 소문/support 보존, wipe 없음). 전파 이웃은 distortion만(소문 미생성). (FD-P2 Q5=A / CL3.1=B / CL4.1=A) |
| **BR-P2-8** | support 진화: 영향 리전(주 대상+전파 이웃) 소문 `+0.1`, 그 외 `−0.05`, clamp [0,1]. 이후 promotion.evaluate(0.6). (FD-P2 Q4 / FR-P5.1/5.2) |
| **BR-P2-9** | "영향 리전" = 그 턴 distortion delta를 받은 모든 리전(주 대상 + 임계 이상 전파 이웃). |
| **BR-P2-10** | LLM 제안(suggest_events)은 `status=SUGGESTED`로 영속, provenance `llm:event`. 승인(approve) 시 ACTIVE. 유효하지 않은 region 제안은 무시. (CL2.1/2.2) |
| **BR-P2-11** | EventSuggester LLM 실패 시 빈 리스트 — 턴/세션 진행 무영향. distortion/support/승격은 LLM 비의존. (NFR-P3) |
| **BR-P2-12** | dynamics 전 함수는 순수(부수효과·LLM·DB 없음). PBT(Partial) 대상. (NFR-P4) |
| **BR-P2-13** | advance_turn은 ACTIVE Event만 적용(suggested/resolved 제외). suggest는 advance_turn에서 자동 호출하지 않음(분리, AD-P Q3=A). |
| **BR-P2-14** | 닫힌 세션 쓰기(advance/suggest/approve/resolve) 금지 → SessionClosedError. 읽기 허용. (P1 BR-P1-7 계승) |
| **BR-P2-15** | NPC 쿼리 규칙·수동 소문 경로(generate/regenerate)·Phase 1 동작 불변. TurnResult는 필드 추가만(기존 소비자 호환). (FR-P7 / NFR-P5) |
| **BR-P2-16** | `GameMasterService`에 EventSuggester는 옵셔널 주입(기본 None) — 기존 생성자 호출 호환. None이면 suggest_events는 빈 결과(또는 라우트 503). |

## 결정론/그레이스풀 시나리오
- 동일 Event 집합·토폴로지 → 동일 distortion/ support 결과(BR-P2-12).
- LLM 다운: suggest=[]; advance_turn은 정상(소문 append는 RumorGenerator graceful로 빈 체인 가능). (BR-P2-11)
- persistent 누적 → clamp 1.0 상한; 해소 → 누적분 복원(하한 0.0 clamp).

## 테스트 포인트 (P2)
- dynamics PBT: delta 단조·범위, propagate 임계, apply/restore 역대칭(±contributions clamp 내), evolve_support 부호.
- advance_turn 통합: 적용→소문 append(기존 보존)→support→승격/강등→one_shot resolve→timeline; applied/created ids.
- persistent 누적 다턴 + 해소 복원; one_shot 1회 영구.
- 전파 이웃 distortion만(소문 X), 영향 집합 support.
- suggest(graceful, region 검증)/approve 상태전이; 닫힌 세션 가드.
- Phase 1/P1 회귀(NPC 쿼리·수동 소문·기존 advance_turn 동작).

## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design (light) — U8 데모·배포·문서
**Reviewed artifact:** `aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-01T13:39:12Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/domain-entities.md > §6, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-29, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §1.1 | 표 형식 `{ text = "MIT" }`은 setuptools 61에서 유효하다(현재 pyproject도 같은 형식). package-data는 `*.json`·`*/*` 두 줄로 `**` 없이 적었고, 이미지 안 소스 폴더 확인은 Infra-light로 넘겼다. | 없음. | Resolved |
| R-02 | Major | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §4.1, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-24, TP-U8-8 | 의존 필드(`builder`·`npc_drafts`·소문/사건/대화 서비스의 `LlmUnavailableError`)를 둔 표로 다시 썼고, `priors`는 LLM 경로에서 빼서 2xx 대표 경로에 넣었다. 코드와 일치한다(`wiki/admin.py`는 임베딩 실패를 삼킨다; `world.py`의 `_need`는 builder만 LLM 의존). | 없음. | Resolved |
| R-03 | Major | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §2.2, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-22, EX-12·13·14 | `ok=false`(`ImportReport.ok`는 error 경고에서 계산됨), 시작 지역 없음, `busy_sessions`/`open_sessions` 두 409 모양이 정의되었고 EX와 vitest(`home.test.tsx`)에 걸렸다. `api/routers/world.py`의 detail 모양과 맞다. | 없음. | Resolved |
| R-04 | Major | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/domain-entities.md > §5.2·§5.5, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-11 | 합의·사건 번짐은 모든 연결, 행적 확산은 지나갈 수 있는 연결만 쓰도록 나눴고(`best_path_weights`는 막힌 연결도 쓰고 `spread.py`는 passable만 씀 — 코드로 확인) 최대 곱 무게표를 넣었다. 표 값을 손으로 다시 계산했고 맞다(예: Ambermeadow→Ironcrag 1.0×0.6×0.34=0.204, Ashen Dig→Sunstrand 0.8×0.204×0.8≈0.131<0.15). 남은 서술 어긋남은 R-13으로 뺐다. | 없음. | Resolved |
| R-05 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §7 단계 8~11 | 순서·위치·support 산수는 정리되었다(대화는 플레이어 지역, 먼 지역은 GM 읽기). 남은 것: 대화는 턴을 쓰지 않는데(`dialogue.py`는 세션 턴을 올리지 않음) 단계 10·11이 "T4"라고 적혀 있고 T3에서 T4로 올리는 행동이 표에 없다. 그대로면 스크립트가 T3에서 도는데 단언은 T4 기준이다. | T3→T4를 올리는 단계(예: 이동 없는 행동 또는 이웃 왕복)를 표에 넣거나, 단계 10·11의 턴을 T3로 고쳐 단언 기준(T2+1)을 맞춘다. 남은 범위가 작아 Major에서 Minor로 낮춘다. | Unresolved |
| R-06 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §3.3, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-17 | `SeedService`, `SeedAlreadyRunningError`, `create_event`의 `provenance`·`timeline_extra` 확장, 응답 `EventOut` 201이 이름 붙었다(현재 서명은 provenance 고정이라 확장 필요 — 코드로 확인). 클라이언트 쪽 불일치는 R-12. | 없음. | Resolved |
| R-07 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/domain-entities.md > §2 | 변경 지점 목록(`NODE_LABELS`, `graph_mapping`, `persist_graph`, 로더, `SECTIONS`·remap·export), FR-A2 예외 기록, `init-schema --world` 재실행 안내가 들어갔다. | 없음. | Resolved |
| R-08 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/frontend-components.md > §2.3 vs §3 | 둘 다 `loadDemo(worldId, name, options)`이고 vitest가 순서를 단언한다. | 없음. | Resolved |
| R-09 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §1.1, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/domain-entities.md > §1, BR-U8-2 | 조립 때 한 번 검사·보관으로 바뀌었고 소스 빌드가 World File과 같은 월드를 보장하지 않는다는 한계가 §8에 적혔다. | 없음. | Resolved |
| R-10 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §1.1, TP-U8-6 | 남은 도움말·docstring 목록(`__main__.py`, `npc_drafts.py:112`)과 옛 이름 검색어(`aldermoor`, `riverton` 등)가 추가되었다. | 없음. | Resolved |
| R-11 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §6, BR-U8-33·35 | audit이 별도 작업이라 다른 작업 결과가 가려지지 않고, 외부 자문으로 빨개질 위험이 기록되었으며 `npm ci` 전제가 명시되었다. 사람이 고른 "moderate에서 막기"(Q5=A)를 뒤집지 않고 위험을 드러낸 것으로 충분하다. | 없음. | Resolved |
| R-12 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/frontend-components.md > §3 `api.startSeed` vs aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-logic-model.md > §3.3 | 프런트 문서는 `startSeed`가 `SessionEvent`를 돌려준다고 적고, 백엔드 문서는 `EventOut`(기존 사건 라우트 응답)이라 적는다. 타입 이름이 갈린다. | `types.ts`와 `api.startSeed`의 반환 타입을 `EventOut`(웹의 기존 사건 타입)로 맞춘다. | New |
| R-13 | Minor | aidlc-docs/construction/U8-demo-deploy-docs/functional-design/domain-entities.md > §5.2·§5.5, aidlc-docs/construction/U8-demo-deploy-docs/functional-design/business-rules.md > BR-U8-11, EX-9 | "Ironcrag는 Saltwake·Gutterlight·Hollowdeep·Sunstrand만 전해 들음"이라 쓰지만 같은 표에서 Sylvarch·Ambermeadow(0.204)와 Ashen Dig 계열도 hearsay 구간(≥0.15)이다. 테스트가 이 문장대로 목록을 단언하면 틀린다. | 문장을 "표의 0.15 이상 마을 모두"로 고치거나 단언 목록을 표 값에서 계산하도록 적는다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| `api/routers/world.py` 409 detail 모양 | `busy_sessions`와 `open_sessions` 두 모양 존재 | R-03 설계와 일치 |
| `ImportReport.ok` | `not has_errors(warnings)`로 계산 | R-03 `ok=false` 처리 근거 맞음 |
| `EventService.create_event` 서명 | provenance 고정, payload 인자 없음 | R-06 확장 필요성 확인 |
| `best_path_weights`·`spread.py` | 합의는 모든 연결, 확산은 passable만 | R-04 두 그래프 분리 맞음 |
| §5.2 무게표 손 계산 | 표 값 일치, `event_propagate_min`=0.15 | 유물이 Sunstrand에 닿지 않음 맞음 |
| `pyproject.toml` | build-system setuptools>=61, license 표 형식, package-data 한 단계 glob | R-01 해결안이 하한과 맞음 |
| `wiki/admin.py` upsert_prior | 임베딩 없어도 예외 삼킴 | `priors`는 키 없이 2xx |
| `dialogue.py` 턴 | 대화는 세션 턴을 올리지 않음 | R-05 잔여 확인 |

### Summary

이전 Major 다섯과 Minor 대부분이 코드와 맞게 고쳐졌고 남은 Major는 없다. 라이브 시나리오의 T4 단계 공백(R-05)과 타입 이름·hearsay 목록 서술 어긋남(R-12·R-13)은 Minor로 Build 전에 손보면 된다.

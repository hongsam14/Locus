# S3 (Web UI) — Business Rules (Functional Design)

Unit **S3**. FR-R6. UI 동작/상태 규칙.
확정 답: Q1=A / Q2=GameMaster(SessionPanel) 중심 / Q3=A / Q4=A / Q5=A / Q6=A.

---

## 세션 생애주기 (FR-R6.1)
- **BR-S3-1**: SessionBar는 world별 세션 목록을 드롭다운으로 제공하고, New Session으로 생성(생성 즉시 현재 세션으로 선택), Close로 종료한다.
- **BR-S3-2**: worldId 변경 또는 world Load 시 세션 목록을 갱신하고 현재 세션 선택을 해제한다(다른 world의 세션을 들고 있지 않음).
- **BR-S3-3**: 닫힌(closed) 세션을 선택하면 **읽기 전용**이다 — generate/regenerate/support/distortion/advance-turn 컨트롤은 비활성화된다(서버 409도 graceful 표시). (FR-R6.4)

## 소문 생성/관리 = GameMaster 허브 (FR-R6.2, Q2)
- **BR-S3-4**: 소문 생성/재생성/support/distortion 컨트롤은 **SessionPanel(GameMaster 섹션)** 에 위치한다. RegionPanel에는 두지 않는다.
- **BR-S3-5**: GameMaster 컨트롤의 대상 리전은 **지도에서 선택한 리전**(`selected`)이다. 리전 미선택 시 "지도에서 리전을 선택하세요" 안내를 표시한다.
- **BR-S3-6**: "소문 생성"은 `generateRumors(sid, regionId)`, "재생성"은 `regenRumors`(기존 소문 전부 교체)를 호출하고, 응답/후속 `listRumors`로 목록을 갱신한다. (FR-R2)
- **BR-S3-7**: 소문 목록의 각 항목은 statement·`distortion_degree`·support·승격 상태를 표시한다. (FR-R6.2)
- **BR-S3-8 (support 슬라이더)**: support는 0~1 슬라이더로 조정하고 슬라이더를 놓을 때 `setSupport`를 호출한다(Q4=A). 표시값은 응답으로 동기화한다. (FR-R6.3)
- **BR-S3-9 (distortion 슬라이더)**: 리전 distortion은 0~1 슬라이더로 `setDistortion` 호출. 이후 생성되는 체인 강도에 반영됨(상한). (FR-R2.5)

## 턴 & 타임라인 (FR-R4, FR-R6.4)
- **BR-S3-10**: Advance Turn 버튼은 `advanceTurn`을 호출하고 결과의 승격/강등 요약을 표시하며, 턴 표시와 타임라인·소문 목록을 갱신한다.
- **BR-S3-11**: 타임라인은 SessionPanel에 turn·kind·summary 시간순 리스트로 표시한다. (FR-R6.4, Q5)
- **BR-S3-12**: 과거(닫힌) 세션도 드롭다운에서 선택해 타임라인·소문을 **열람**할 수 있다(쓰기 불가). (FR-R6.4)

## 승격 & NPC 지식 표시 (FR-R3/R5)
- **BR-S3-13 (승격 배지)**: `promoted=true` 소문은 목록에서 "PROMOTED" 배지로 구분한다. (FR-R3.2)
- **BR-S3-14 (세션 NPC 뷰)**: 세션이 선택되면 RegionPanel의 지식은 `sessionKnowledge`(세션 NPC 뷰)로 조회한다 — 승격 소문이 direct-like로, 일반 소문 포함, propagated/auto-rumor 없음. 세션 미선택 시 기존 캐노니컬 쿼리. (FR-R5.1, Q3)
- **BR-S3-15**: 소문(`is_rumor=true`) 항목은 캐노니컬 지식과 시각적으로 구분(배지/색)한다.

## 정리 & 품질 (FR-R6.5, NFR-R6)
- **BR-S3-16 (dead buildWiki 제거)**: `api.buildWiki`, `App.buildWiki`, `Toolbar.onBuildWiki`(prop/버튼)와 관련 테스트를 제거한다. 백엔드에 해당 엔드포인트는 없다. (FR-R6.5, Q6=A)
- **BR-S3-17 (graceful)**: 모든 API 실패는 상위 `run()`의 error 배너로 표시하고 앱은 동작을 계속한다(흰 화면 없음). (NFR-R4 정합)
- **BR-S3-18 (회귀)**: 기존 web 동작(world load/map/region edit/augment)과 vitest는 GREEN을 유지하고 tsc·vite build는 클린이어야 한다. (NFR-R6)
- **BR-S3-19 (세션 격리 표시)**: UI는 현재 world·현재 세션 범위만 다룬다(다른 world/세션 데이터 혼입 없음). 백엔드 격리(NFR-R2)를 UI도 위반하지 않음.

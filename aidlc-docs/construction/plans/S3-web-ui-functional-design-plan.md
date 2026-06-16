# S3 (Web UI) — Functional Design Plan

App Design: `inception/application-design/rumor-session/`. FR-R6(세션 웹 흐름) + FR-R6.5(dead buildWiki 정리).
의존: S2 세션 API(11 라우트). 기존 `web/`(App/Toolbar/MapOverlay/RegionPanel/AugmentPanel, api.ts/types.ts).

## 작업 체크리스트 (답변 후 생성)
- [x] domain-entities.md — TS 타입(GameSession/SessionRumor/RegionDistortion/TimelineEntry/TurnResult), api.ts 세션 메서드, additive GET rumors 엔드포인트
- [x] business-logic-model.md — 컴포넌트(SessionBar/SessionPanel=GameMaster 허브/RegionPanel 확장), 상태, API 클라이언트, dead buildWiki 제거
- [x] business-rules.md — UI 동작/상태 규칙(세션 컨텍스트, 소문=GameMaster, 승격 배지, graceful)

생성: `construction/S3-web-ui/functional-design/{domain-entities,business-logic-model,business-rules}.md` (2026-06-15). 답변: Q1=A/Q2=GameMaster(SessionPanel)중심/Q3=A/Q4=A/Q5=A/Q6=A.

---

## 설계 확인 질문 (S3 결정)

### FD-S3 Q1 — 세션 UI 배치
세션 생성/선택/종료를 어디에 둘까?

A) **Toolbar 옆 SessionBar**(world 선택 아래) + 별도 `SessionPanel`(현재 세션·턴·타임라인·advance-turn). RegionPanel은 세션 선택 시 소문 섹션 추가. 기존 레이아웃 확장(최소 변경)
B) 별도 "Session" 탭/페이지(라우팅 도입)
C) 모달 다이얼로그
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S3 Q2 — RegionPanel의 소문 섹션
리전 선택 시 소문 UI는?

A) **RegionPanel에 소문 섹션 추가**: "소문 생성" 버튼 + 소문 목록(각 항목: statement·distortion_degree·support 조정·승격 배지) + "재생성" 버튼 + 리전 distortion 슬라이더(set_distortion). 세션 미선택 시 비표시
B) 소문은 완전히 별도 RumorPanel로 분리(RegionPanel과 나란히)
X) Other (please describe after [Answer]: tag below)

[Answer]: X → 확정(clarify): **GameMaster(SessionPanel) 중심**. 소문 생성/재생성/support/distortion 컨트롤은 SessionPanel의 GameMaster 섹션에 위치, 대상 리전 = 지도에서 선택한 리전. RegionPanel은 그 리전의 지식(세션 NPC 뷰)만 표시. (소문 목록 로드용 additive read 엔드포인트 `GET .../rumors` 추가.)

### FD-S3 Q3 — 세션 컨텍스트의 지식 조회
세션이 선택되면 RegionPanel의 "지식" 표시는?

A) **세션 선택 시 세션 NPC 쿼리**(`/sessions/{sid}/regions/{rid}/knowledge`)로 전환 — 승격 소문이 direct-like로, 소문 포함; 세션 없으면 기존 캐노니컬 쿼리. (FR-R5.1)
B) 항상 캐노니컬 쿼리(세션 지식은 소문 섹션에서만)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S3 Q4 — support 조정 위젯
소문 support 조정 UI는?

A) **슬라이더(0~1)** + 현재값 표시, 놓을 때 PUT support. 직관적
B) 숫자 입력 + 적용 버튼
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S3 Q5 — 과거 세션·타임라인 열람
세션 이력/타임라인 표시는?

A) **SessionPanel 내 타임라인 리스트**(turn·kind·summary 시간순) + 세션 드롭다운으로 과거 세션 선택(닫힌 세션은 읽기 전용). (FR-R6.4)
B) 별도 history 페이지
X) Other (please describe after [Answer]: tag below)

[Answer]: A

### FD-S3 Q6 — dead buildWiki 정리 범위
FR-R6.5 정리는?

A) **api.ts `buildWiki` + App.tsx `buildWiki`/`onBuildWiki` + Toolbar `onBuildWiki` prop/버튼** 모두 제거(관련 테스트도). 더 이상 백엔드에 엔드포인트 없음
B) api.ts만 제거
X) Other (please describe after [Answer]: tag below)

[Answer]:A

---

## 참고 (S2 API 계약)
```
POST /api/session/worlds/{world_id}/sessions            (start) -> GameSession
GET  /api/session/worlds/{world_id}/sessions            (history) -> GameSession[]
GET  /api/session/sessions/{sid}                        -> GameSession
POST /api/session/sessions/{sid}/close                  -> GameSession
GET  /api/session/sessions/{sid}/timeline               -> TimelineEntry[]
POST /api/session/sessions/{sid}/regions/{rid}/rumors          (generate) -> SessionRumor[]
POST /api/session/sessions/{sid}/regions/{rid}/rumors/regen    (regen) -> SessionRumor[]
PUT  /api/session/sessions/{sid}/rumors/{rumor_id}/support  {support} -> SessionRumor
PUT  /api/session/sessions/{sid}/regions/{rid}/distortion   {degree}  -> RegionDistortion
POST /api/session/sessions/{sid}/advance-turn               -> TurnResult
GET  /api/session/sessions/{sid}/regions/{rid}/knowledge    -> QueryResult (NPC view)
```
- vitest 테스트는 작성(실행은 Build&Test). tsc/vite build 클린 유지(NFR-R6).

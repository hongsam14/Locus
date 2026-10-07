# User Stories Assessment — Purpose Restructure Cycle (2026-09-29)

## Request Analysis
- **Original Request**: "ai-dlc를 사용해서 현재 프로젝트를 다시 개편해서 조금 더 명료한 목적의 프로젝트로 바꾸고 싶어" → Requirements에서 "월드를 만들고 그 안에서 소문·사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 겪는 솔로 TRPG"로 확정 (`purpose-restructure-requirements.md` §0).
- **User Impact**: Direct — 플레이어 모드(신규), 월드 에디터(신규 UI), GM 모드(재배치), 원클릭 데모(관람자).
- **Complexity Level**: Complex — 새 도메인(플레이어·이동·NPC 대화)과 기존 두 축의 경계 재정리가 함께 감.
- **Stakeholders**: 사용자 본인(제작자·플레이어·GM), 포트폴리오 관람자, (2차) 외부 NPC 런타임.

## Assessment Criteria Met
- [x] High Priority — New User Features: 플레이어 모드, NPC 대화, 월드 에디터, 저장·로드, 원클릭 데모.
- [x] High Priority — User Experience Changes: GM 콘솔이 "모드"로 재배치되고 화면 중심이 플레이어로 바뀜.
- [x] High Priority — Multi-Persona Systems: P-Builder / P-Player / P-GM / P-Viewer (요구사항 §5) — 기존 페르소나 파일(P1·P2·P3)과 다름.
- [x] High Priority — Complex Business Logic: 이동 비용, 턴 소모, NPC 아는 범위, 소문 상한.
- [x] Medium Priority — Backend User Impact: 경계 재정리(FR-A)는 내부 변경이지만 관람자가 저장소를 읽을 때의 경험(목적이 코드 배치로 드러남)에 닿음.
- [x] Benefits: 기존 30개 스토리(2026-06)가 "기획자 → NPC 런타임" 모델로 쓰여 있어 새 목적과 맞지 않음. 스토리를 다시 쓰지 않으면 Units 분해와 수용 기준이 옛 목적을 따라감.

## Decision
**Execute User Stories**: Yes
**Reasoning**: 페르소나가 바뀌고(플레이어·관람자 신규, NPC 런타임 내부화), 데모 흐름(§6)이 곧 제품이므로 그 흐름을 스토리와 수용 기준으로 고정해야 Units·Functional Design·Build&Test가 같은 것을 겨눈다. 이전 두 사이클(루머 Phase 1·2, 하드닝, UX)은 기존 페르소나를 재사용해 건너뛰었지만, 이번에는 페르소나 자체가 바뀐다.

## Expected Outcomes
- 새 목적에 맞는 페르소나 4개(+내부화된 NPC 런타임 주석).
- §6 핵심 경험 흐름을 덮는 스토리 집합과 Given/When/Then 수용 기준.
- 기존 30개 스토리의 처리 표(유지·대체·보류) — 잃는 것이 없음을 보임.
- Units Generation의 직접 입력(스토리 ↔ FR ↔ 유닛 매핑).

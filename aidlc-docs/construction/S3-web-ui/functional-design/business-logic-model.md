# S3 (Web UI) — Business Logic Model (Functional Design)

Unit **S3**. FR-R6. 컴포넌트 구성·상태·API 사용. 기존 `web/` 최소 확장.
확정 답: Q1=A / Q2=GameMaster(SessionPanel) 중심 / Q3=A / Q4=A / Q5=A / Q6=A.

---

## 1. 상태 (App.tsx)
- 기존: `worldId`, `data`(WorldExport), `selected`(regionId), `mapUrl`, `busy`, `error`.
- **신규**: `sessionId: string | null`(현재 선택 세션), `session: GameSession | null`(상태/턴 표시용).
- `sessionId`가 자식(SessionBar/SessionPanel/RegionPanel)에 전달됨. 지도에서 선택한 `selected`(regionId)가 SessionPanel의 GameMaster 대상 리전.

## 2. SessionBar (신규, `web/src/SessionBar.tsx`)
- 책임: world의 세션 **생성/선택/종료** + 현재 세션 상태 한 줄.
- 표시: 세션 드롭다운(`listSessions(worldId)`; 라벨=짧은 id+turn+status), **New Session** 버튼(`startSession`→선택), **Close** 버튼(`closeSession`; 닫히면 읽기전용), 현재 `status·turn`.
- worldId 변경/Load 시 세션 목록 새로고침. 새 세션 시작 실패(404 등)는 상위 error로.
- 위치: Toolbar 아래(레이아웃 확장, Q1=A).

## 3. SessionPanel (신규, `web/src/SessionPanel.tsx`) — GameMaster 허브 (Q2)
세션 선택 시에만 렌더. 세 블록:
1. **턴/진행**: 현재 turn + **Advance Turn** 버튼(`advanceTurn`→`TurnResult`; 승격/강등 id 요약 토스트). 닫힌 세션이면 버튼 비활성.
2. **타임라인**(Q5): `getTimeline(sid)` 리스트(turn·kind·summary, 시간순). advance/generate 등 동작 후 새로고침.
3. **GameMaster 리전 컨트롤**(대상 = App의 `selected` regionId; 미선택 시 "지도에서 리전 선택" 안내):
   - **리전 distortion 슬라이더**(0~1, `setDistortion`).
   - **Generate** / **Regenerate** 버튼(`generateRumors`/`regenRumors`).
   - **소문 목록**: `listRumors(sid, regionId)` — 각 항목 = statement · `distortion_degree` · **support 슬라이더**(Q4=A, 놓을 때 `setSupport`) · **승격 배지**(promoted=true → "PROMOTED"). 생성/재생성/support/advance 후 새로고침.
- 모든 쓰기는 닫힌 세션에서 비활성(서버 409도 graceful 처리).

## 4. RegionPanel (수정, `web/src/RegionPanel.tsx`)
- Q3=A: prop `sessionId` 추가. `sessionId`가 있으면 `sessionKnowledge(sid, regionId)`로 지식 조회(승격 소문 direct-like + 소문 포함, propagated/auto-rumor 없음), 없으면 기존 `regionKnowledge`(캐노니컬).
- 소문은 `is_rumor` 플래그로 시각 구분(배지/색). 기존 삭제/편집 기능 유지.

## 5. App (수정) / Toolbar (수정)
- App: `sessionId`/`session` 상태 추가; `<SessionBar>` + (sessionId 있을 때)`<SessionPanel selected=… sessionId=…>` 배치; `<RegionPanel sessionId=… >` 전달.
- **dead buildWiki 제거(Q6=A)**: `App.buildWiki`, `Toolbar` `onBuildWiki` prop/버튼, `api.buildWiki`. 관련 테스트 정리.

## 6. API 클라이언트 (`web/src/api.ts`)
- §domain-entities 표면 추가. `http<T>` 재사용(JSON, 비-2xx → throw, 상위 `run()`가 error 표시 = graceful).
- PUT support/distortion body: `{ support }` / `{ degree }`.

## 7. 레이아웃 (요약)
```
Toolbar (worldId, Load, Build Demo, PickMap)         ← onBuildWiki 제거
SessionBar (세션 드롭다운 · New · Close · status/turn)   ← 신규
[graph-status]
┌ MapOverlay ┐  ┌ 우측 컬럼 ───────────────┐
│ regions    │  │ RegionPanel (세션 NPC 뷰)  │
│ connections│  │ SessionPanel (GameMaster) │ ← 세션 선택 시
└────────────┘  │ AugmentPanel (기존)        │
                └───────────────────────────┘
```

## 8. 테스트 (vitest, `web/src/__tests__/`)
- **components.test.tsx 확장**: SessionBar(목록/생성/종료 호출), SessionPanel(generate/advance/ support 슬라이더 onChange→setSupport, 승격 배지 렌더, 닫힌 세션 비활성), RegionPanel(sessionId 유무에 따른 엔드포인트 분기) — `api` mock.
- **pure.test.ts**: 필요 시 라벨/포맷 순수 함수.
- buildWiki 제거 회귀: 호출/버튼 부재 확인.
- tsc + vite build 클린(NFR-R6).

## 9. 와이어링/빌드
- 새 컴포넌트는 `App`에서 조립. 새 npm 의존성 없음(기존 React+Vite+TS).
- 백엔드 보강 1건(§domain-entities §3 GET rumors) — `api/routers/session.py`에 read 라우트 추가.

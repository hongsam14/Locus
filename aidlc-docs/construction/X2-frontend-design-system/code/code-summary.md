# X2 Frontend Design System — Code Summary

**결과**: 프론트 **19 vitest GREEN** (회귀 0), tsc clean, `vite build` 성공, `npm audit` **0 vulnerabilities**. 외부 CDN 호출 없음(폰트 자가호스팅).

## 코드 리뷰(high, 멀티에이전트) 반영 — 5건(수정 4 / 유지 1)
jsdom이 못 잡은 실제 UI 버그 포함:
- **#1 Range thumb 소실(correctness)**: `appearance-none`이 native thumb를 제거하고 대체 pseudo-element 없음 → 제거하고 native + `accent-ink` 유지(슬라이더 다시 보임/드래그 가능).
- **#2 SVG `var()` 미해석(correctness)**: 마커 `fill/stroke="var(...)"`는 SVG presentation 속성에서 미해석 → `style={{fill/stroke: var()}}`로 이동. 선택 대비도 개선(선택=ink / 비선택=paper-card, 둘 다 ink stroke).
- **#3 scope 색 구분 소실(correctness)**: 모노 팔레트라 다색 불가하나, `direct`(로컬 지식)를 solid ink 배지로 강조해 skim 구분 복원(scope 텍스트 라벨 유지).
- **#4 Card.interactive 미사용(cleanup)**: 데드 prop 제거.
- **#5 Toast/Modal 미사용(cleanup)**: **의도적 유지** — FD BR-X2-6대로 X2는 스타일만, 사용은 X3(다음 유닛). (no_change_needed)
- (refuted 3건: 마커 대비 2건·`.font-display` 중복 1건 — 무효/의도.)

## 신규
- **의존성**: `tailwindcss` + `@tailwindcss/vite` (Tailwind v4, CSS-first), `@fontsource/gaegu`(한글 손글씨, 자가호스팅), `@testing-library/dom`(react 테스트 peer — 설치 재정렬로 누락돼 명시 추가). `package.json`/`package-lock.json` 갱신.
- `web/src/index.css`: `@import "tailwindcss"` + Gaegu(korean/latin 400·700) + `@theme` 토큰(종이+잉크 모노: paper/paper-card/ink/ink-soft/line/highlight/danger, `--font-display`=Gaegu, radius/shadow) + base body + `.sketch-border`/`.sketch-shadow`/`.ink-underline`.
- `web/src/ui/`: `Button`(primary/ghost/danger) · `Panel` · `Card` · `Badge`(neutral/promoted/pruned/event/danger) · `Toast` · `Modal`(confirm) · `Field` · `Range` + `index.ts`.

## 수정 (restyle — 구조·`data-testid`·핸들러·검증 텍스트 보존, BR-X2-7/8/9)
- `web/vite.config.ts`: `@tailwindcss/vite` 플러그인.
- `web/src/main.tsx`: `import "./index.css"`.
- `App.tsx`·`Toolbar.tsx`·`SessionBar.tsx`·`MapOverlay.tsx`·`RegionPanel.tsx`·`SessionPanel.tsx`·`AugmentPanel.tsx`: 인라인 `style={{}}` → Tailwind 클래스/프리미티브. SVG 오버레이 로직 유지(마커 색만 잉크 토큰). 모든 `data-testid`·onClick·상태·API 호출·검증 텍스트("distortion x.xx"/"PROMOTED"/event status) 불변.

## 결정 반영
- Q1=A(제목 손글씨 Gaegu/본문 산세리프) · Q2=C(종이+잉크 모노) · Q3=A(은은한 스케치: 비대칭 라운드+하드섀도) · Q4=A(프리미티브 6종) · Q5=A(데스크톱 우선 + `flex-wrap` 최소 반응형). FR-UX1.1~1.5, BR-X2-1..12.
- SEC-B(폰트 로컬 번들·외부 호출 0) / SEC-D(공식 레지스트리·락 핀·`npm audit` 0).

## 비고
- Gaegu 한글 서브셋 woff2(400=284kB/700=479kB)를 번들 — 로컬 도구엔 허용. 추가 서브셋 최적화는 후속 여지(NFR-light).
- Toast/Modal은 스타일·컴포넌트만; 실제 사용(지역별 알림·재생성 확인)은 **X3**.
- 사전존재 peer 충돌(`@vitejs/plugin-react`↔vite8)로 설치는 `--legacy-peer-deps` 사용(기존 상태와 동일).

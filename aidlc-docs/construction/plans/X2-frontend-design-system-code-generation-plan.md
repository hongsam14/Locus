# X2 Frontend Design System — Code Generation Plan (brownfield, web/)

**Single source of truth for X2 code generation.** 앱 코드는 `web/`, 문서는 `aidlc-docs/`.

## Unit Context
- **유닛**: X2 (C9). **의존**: 없음. **후속**: X3가 프리미티브(Toast/Modal 등) 사용.
- **FR/BR**: FR-UX1.1~1.5, BR-X2-1..12. **SEC**: B(로컬 자산/헤더), D(의존성 락·공식 레지스트리).
- **결정**: Tailwind(AD-UX Q2=A) · Q1=A/Q2=C(종이+잉크 모노)/Q3=A/Q4=A/Q5=A. **Tailwind v4**(CSS-first, `@tailwindcss/vite`). 손글씨 한글 폰트 = `@fontsource/gaegu`(자가호스팅).

## Steps

### Step 1 — 의존성 설치 [x]
- `web/`에서 `npm install -D tailwindcss @tailwindcss/vite` + `npm install @fontsource/gaegu`.
- `package.json`/`package-lock.json` 갱신(핀 고정, SEC-D). 공식 레지스트리만.

### Step 2 — Vite 플러그인 [x]
- `web/vite.config.ts`: `@tailwindcss/vite` 플러그인 추가(react와 함께). test 설정 유지.

### Step 3 — 디자인 토큰 + 베이스 CSS [x]
- `web/src/index.css`: `@import "tailwindcss";` + `@theme { }`(색 paper/paper-card/ink/ink-soft/line/highlight/danger, `--font-display`=Gaegu, `--font-body`=system-ui, radius, shadow-soft) + `@import "@fontsource/gaegu"` + base(`body{background/font}`) + `.sketch-border`/`.sketch-shadow`/`.ink-underline` 컴포넌트 유틸(은은, Q3=A).
- `web/src/main.tsx`: `import "./index.css"`.

### Step 4 — 공용 프리미티브 (`web/src/ui/`) [x]
- `Button.tsx`(variant primary/ghost/danger, size, disabled, `data-testid` 통과) · `Panel.tsx`(title 헤더=display 폰트) · `Card.tsx` · `Badge.tsx`(tone neutral/promoted/pruned/event/danger) · `Toast.tsx`(tone/title/onClose) · `Modal.tsx`(open/title/onConfirm/onCancel, confirm) · 보조 `Field.tsx`/`Range.tsx`. `web/src/ui/index.ts` export.
- Toast/Modal은 스타일·컴포넌트만(사용은 X3, BR-X2-6).

### Step 5 — 컴포넌트 restyle (구조·`data-testid`·핸들러 보존, BR-X2-7/8) [x]
- `App.tsx`(종이 배경·헤더·flex 레이아웃, error/busy/hint 토큰화) · `Toolbar.tsx`(Field+Button) · `SessionBar.tsx`(Panel+Button) · `MapOverlay.tsx`(오버레이 로직 유지, chrome만 잉크) · `RegionPanel.tsx`(Panel+Card) · `SessionPanel.tsx`(Panel 섹션+Button/Range/Badge) · `AugmentPanel.tsx`(Panel+Card+Field). 인라인 `style={{}}` → Tailwind 클래스/프리미티브. 텍스트 값·로직 불변(BR-X2-9).

### Step 6 — 테스트/빌드 [x]
- 기존 `web/src/__tests__/{components.test.tsx,pure.test.ts}` GREEN 유지(필요 최소 수정, `data-testid` 보존). `npm test`(vitest) + `npm run build`(tsc+vite) + `npm run lint`(tsc) clean.

### Step 7 — 코드 요약 [x]
- `aidlc-docs/construction/X2-frontend-design-system/code/code-summary.md`.

## Story/FR Traceability
- FR-UX1.1→S1-3 · FR-UX1.2→S3-5 · FR-UX1.3(Doodly)→S3 · FR-UX1.4(라이트)→S3 · FR-UX1.5(계약보존)→S5-6 · SEC-B→S1/S3 · SEC-D→S1.

## Quality Gates
- vitest GREEN, tsc/vite build clean, `data-testid` 회귀 0, 외부 CDN 호출 없음(폰트 자가호스팅).

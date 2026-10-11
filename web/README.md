# Locus Web UI

React 18 + Vite + TypeScript + Tailwind v4 UI for the Locus API: the home screen, the player
screen, the GM screen and the world editor. Korean is the default display language; English is
one switch away.

## Run
```bash
cd web
npm ci             # the lock as committed (Node 22)
npm run dev        # http://localhost:5173 (proxies /api -> http://localhost:8000)
# (start the backend separately: uvicorn api.main:app --port 8000 --workers 1)
```
In compose, the `web` service builds this image (`node:22-alpine`, `npm ci`) and serves it from
nginx on `${WEB_PORT:-3000}`, proxying `/api` to the app (build routes wait up to 600 s, the
rest 130 s; `nginx.conf`).

## Test / build
```bash
npm test           # vitest (jsdom, Testing Library, fast-check) — the API is mocked
npx tsc --noEmit   # types
npm run build      # tsc -b + vite build -> dist/ (the editor and GM screens are lazy chunks)
```
Some tests read the source as text (`src/test/paths.ts`): the design grep (no raw colours, the
body face on controls, none of the old classes or the old overlay), the dictionary register and
that every dictionary key is used, and the document head (`index.html`).

## Screens
- `/` — home (`routes/HomePage.tsx`, `features/home/`): the opening lines (`HomeHero`), a card
  per demo in the server's manifest (`DemoCards`, `DemoCard` — no demo name in this code;
  [play now] loads the demo if it is not there — or, loaded with no open session, starts one at
  once — at its start region and opens the player screen; with open sessions [continue] the
  latest or [new session]; [edit]; [reload demo]) and
  "my worlds" (`MyWorlds`, `WorldRow`: regions, last edit, open sessions, [continue],
  [new session], [edit]; [build a world from sources] in the list's head).
- `/play/:sessionId` — the player screen (`routes/PlayPage.tsx`, `features/play/`): the region
  scene with its people and what is known (`RegionScene`, `NpcList`), the last turn's result
  (`ResultBand`), actions (`ActionBar`; `ActionDock` fixed to the bottom on a phone), moves
  (`MovePanel` — the list is the only way to move; `PlayMap` only points), the journey log
  (`PlayLog`) and the talk (`DialoguePanel`, in `TalkSheet` on narrow screens). `PlayLayout`
  places each part once per width.
- `/gm/:sessionId` — the GM screen (`routes/GmPage.tsx`, `features/gm/`): the map with the
  world-state overlay (`MapPane`, `WorldStateOverlay`) beside a panel with the turn tools and
  the result band (`TurnTools`, `TurnBand`) over five tabs (`GmTabs`: region, events, seeds,
  record, deeds), and the player strip (`PlayerStrip`). `GmSessionView` holds one session.
- `/editor/:worldId` — the world editor (`routes/EditorPage.tsx`, `features/editor/`): the head
  (`EditorHeader`, `FileActions`: World File save and load, build from sources), the map with
  its tools (`EditorMapPane`, `MapTools`: select and drag, add a region, connect two) beside a
  panel of four tabs — region (`RegionInspector`: fields, connections, knowledge and scopes,
  NPCs and LLM drafts, delete with what it takes along), unscoped knowledge, augmentation Q&A
  (`AugmentPanel`, `AugmentQuestion`) and the wiki priors (`WikiPanel`).

## Source layout
- `layout/` — the frame of every screen (`AppShell`: top bar, menu, `LangSwitch`, the one
  LLM-off band), `SplitView`, `Section` and `MapPanelLayout` (GM and editor).
- `map/` — `WorldMap` (fits its container, 0..1 positions in a 1000 × 625 map), `geometry`,
  `labels` (plates that keep apart), `edgeStyle` (kind and weight), `focus` (play close-up),
  `autoLayout`.
- `ui/` — the design-system primitives (`Button`, `Card`, `Dialog`, `ConfirmDialog`, `Tabs`,
  `Field`, `Select`, `Range`, `CommitRange`, `StatusView`, `Toaster`, …). Colours and type come
  from the tokens in `index.css` only (fonts: `@fontsource` Noto Sans KR, Nanum Myeongjo,
  IM Fell English SC).
- `hooks/` — `useResource` (reads safe against late answers), `useAction` (one write at a
  time), `useTurnRun` (an action's 202 run, polled), `usePlaySession`, `useWorldNames` (the
  world's name map in the display language), `useMedia`, `useMounted`.
- `api/` — one module per server boundary (`world`, `knowledge`, `play`, `gm`, `meta`) over
  `http.ts` (`HttpError`, `useReplaceConfirm`, `openSessionsOf`).
- `errors/` — `describeError`: a failed request as a sentence, by the server's `code`, then the
  status. `format/` — server enums and 0..1 measures as words, dates in the display language.
- `i18n/` — `ko.ts`, `en.ts` and `t()`; the display language lives in `i18n` and
  localStorage and sets `<html lang>`. A line's register follows its key's first segment
  (`i18n.style.test.ts`).
- `capabilities.ts` — `GET /api/capabilities`, read once per page load.

## Without an LLM key
`capabilities.ts` reads what the server can do. When it has no LLM, `AppShell` shows one band
("AI 키가 없어 NPC 대화와 소문 생성은 쉬고 있어요…") and the LLM buttons (build, NPC drafts,
event suggestion, rumor generate/regenerate) are off with "AI 키가 있어야 해요"; a talk shows
its history and says it cannot answer. A failed read turns nothing off; a 503 naming the
provider shows the same words.

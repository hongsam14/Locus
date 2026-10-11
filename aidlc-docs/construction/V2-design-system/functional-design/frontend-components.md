# V2 디자인 시스템 — Frontend Components

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기를 포함한다.
**지금 하는 것**: V2 Functional Design. 디자인 기반의 컴포넌트 구조와 props, 옮길 파일, 갈아 끼울 곳, 테스트 계획을 정한다.

근거:
- 설계 `inception/application-design/follow-up/component-methods.md` § 1
- `business-logic-model.md`, `business-rules.md`(BR-V2-*), `domain-entities.md`

**설계와 달라진 곳**은 [정정]으로 표시한다.

---

## 1. 폴더와 파일 이동 (Units 리뷰 R-01)

### 1.1 새로 만드는 폴더
| 폴더 | 담는 것 |
|---|---|
| `web/src/layout/` | `AppShell.tsx`, `SplitView.tsx`, `Section.tsx`, `LangSwitch.tsx`, `index.ts` |
| `web/src/map/` | `WorldMap.tsx`, `geometry.ts`(좌표·행렬), `labels.ts`(`labelWidth`·`placeLabels`), `edgeStyle.ts`, `autoLayout.ts`, `focus.ts`(play 줌 상자), `index.ts` |
| `web/src/format/` | `enums.ts`(값 목록), `labels.ts`(`enumLabel`), `bands.ts`(단계 표·`degreeWord`·`decayWord`·`numberWithMeaning`), `dates.ts`(`formatDate`·`turnLabel`·`turnAt`), `index.ts` |
| `web/src/errors/` | `describe.ts`(`describeError`), `index.ts` |
| `web/src/hooks/` | `useResource.ts`, `useAction.ts`, `index.ts` |
| `web/src/i18n/` | `index.ts`(지금 `i18n.ts`의 상태·`t`·`timelineText`·`logText`), `ko.ts`, `en.ts` |

### 1.2 옮기거나 지우는 파일
| 지금 파일 | 어디로 | import 영향 |
|---|---|---|
| `web/src/i18n.ts` | `web/src/i18n/index.ts` + `ko.ts` + `en.ts` | `from "./i18n"`·`"../i18n"`는 폴더의 `index.ts`로 그대로 풀린다. 고칠 import 0 |
| `web/src/layout.ts`(`autoLayout`) | `web/src/map/autoLayout.ts` | `layout/` 폴더 이름과 겹치지 않게 한다. import 하는 곳(MapOverlay, 테스트)을 고친다 |
| `web/src/viz.ts`(`edgeStyle`, `toPixels`) | `web/src/map/edgeStyle.ts`(색은 토큰 변수), `toPixels`는 `geometry.ts` | 원색 값이 없어진다(FR-D2) |
| `web/src/MapOverlay.tsx` | `web/src/map/WorldMap.tsx`(새로 씀). V2 동안 `MapOverlay`는 `WorldMap`을 감싸는 얇은 어댑터로 남는다. 지금 props를 받아 새 props로 넘긴다. 화면 유닛(V4·V6·V8)이 직접 `WorldMap`으로 옮긴 뒤 V8 끝에서 지운다 | 화면 코드 무변경 |
| `web/src/features/editor/drag.ts`(`isDrag`, `toNorm`) | `isDrag`는 그대로 둔다. `toNorm`은 `map/geometry.ts`의 행렬 함수로 바뀌고, 어댑터가 쓴다 | 에디터 무변경 |
| `web/src/routes/AppNav.tsx` | **V2에서 지운다.** `web/src/layout/AppShell.tsx`가 대신하고, 네 라우트가 `AppNav` 대신 `AppShell`로 감싼다 | 라우트 4곳, `components.test.tsx:14·561-579`(AppShell 테스트로 옮김) |
| `web/src/features/play/LangToggle.tsx` | `web/src/layout/LangSwitch.tsx` | 쓰는 곳: AppNav(없어짐), 테스트 |
| `web/src/capabilities.ts` | 그 자리에 둔다. 안쪽만 고친다(RE-F09, Units 리뷰 R-05(c)) | 없음 |
| `web/src/types.ts` | 그대로 둔다 | 없음 |
| `web/src/ui/Modal.tsx`, `Toast.tsx`, `NotificationCenter.tsx` | **V2에서 지운다.** props가 달라 별칭으로 맞출 수 없다(BLM § 10). V2가 쓰는 곳을 직접 `ConfirmDialog`·`Dialog`(아홉 곳)와 `toast()`(GmHub, PlayPage)로 바꾼다 | 대화상자 아홉 곳, GmHub, PlayPage |
| `web/src/ui/Panel.tsx` | `Card`의 별칭으로 남긴다(props `title`·`children`·`className`가 Card와 맞음). V9가 지운다 | 없음 |
| `web/src/ui/LlmNotice.tsx` | AppShell 안 띠로 옮기고 화면에서 쓰지 않는다. testid `llm-notice`는 유지 | HomePage, PlayPage, EditorPage, GmHub |

### 1.3 다른 유닛과 겹치는 파일 (Units 리뷰 R-04 대응)
`unit-of-work-dependency.md` § 4의 공유 파일 표에 없는 겹침이다. V2는 아래 파일을 **기계적으로만** 바꾼다. 배치와 문구는 소유 유닛이 바꾼다. 이 표는 승인된 상위 표를 고치는 대신, 이 FD에서 조정을 기록한 것이다.

| 파일 | V2가 하는 일 | 소유 유닛 |
|---|---|---|
| `routes/HomePage.tsx`, `routes/PlayPage.tsx` | AppShell로 감싸기, 옛 클래스, LlmNotice 제거, PlayPage 알림을 `toast()`로 | V4 |
| `routes/GmPage.tsx`, `features/gm/*` | AppShell, 옛 클래스, GmHub 알림·LLM 안내, DeedPanel·GmHub 대화상자 | V6 |
| `routes/EditorPage.tsx`, `features/editor/*` | AppShell, 옛 클래스, 대화상자 다섯 곳, select, 파일 입력 | V8 |
| `routes/AppNav.tsx` | 지움(AppShell로) | unit-of-work V4의 코드 목록에 있던 `AppNav.tsx`는 V2 뒤에는 `layout/AppShell.tsx`를 뜻한다. 메뉴 문구와 배치는 V4가 고친다 |

## 2. 프리미티브 `ui/`

모든 프리미티브는 토큰 유틸만 쓴다. 접근성 동작은 Radix가 맡는다(설계 Q5=A). 어떤 Radix 패키지를 쓸지는 NFR light가 크기와 함께 확정한다(후보: dialog, tabs, toast, collapsible). **select는 Radix가 아니라 브라우저 `<select>`다**(BLM § 10 정정). 확인 대화상자도 alert-dialog가 아니라 dialog로 만든다(지금 테스트의 `role="dialog"`, § 8.1).

```ts
Button(props: { variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md";
               busy?: boolean; icon?: ReactNode } & ButtonHTMLAttributes)
  // [정정] 지금 "ghost"가 하던 테두리 있는 기본 버튼은 "secondary"가 된다. "ghost"는 테두리 없는 버튼이다.
  // 기본 variant = "secondary". busy이면 aria-busy + disabled + 회전 표시. 비활성은 토큰(BR-V2-06).
  // 높이: md 44px, sm 36px. 휴대폰 폭에서 sm도 44px(BR-V2-08).
Badge(props: { tone?: "neutral" | "event" | "danger" | "success" | "info" | "promoted" | "deed" | "pruned" })
  // [정정] tone을 늘린다: success·info·deed. promoted = accent 바탕, deed = danger 테두리.
Card(props: HTMLAttributes & { as?: "div" | "section" | "article"; title?: ReactNode; actions?: ReactNode })
  // 지금 Panel과 Card를 하나로 합친다. Panel은 Card의 별칭으로 남는다.
Field(props: InputHTMLAttributes & { label: ReactNode; hint?: ReactNode; error?: ReactNode })
  // [정정] label이 필수다(FR-S6). hint·error는 aria-describedby로 잇는다.
Textarea(props: TextareaHTMLAttributes & { label: ReactNode; hint?: ReactNode; maxLength?: number })
  // maxLength가 있으면 "0 / 300자" 카운터를 보인다(aria-live 없음, 보조 글).
Select<T extends string>(props: { label: string; value: T | ""; options: { value: T; label: string }[];
               onChange(v: T): void; placeholder?: string; disabled?: boolean; hideLabel?: boolean;
               "data-testid"?: string })
  // [정정] 브라우저 <select> + 토큰 모양 + 펼침 표시 아이콘. data-testid는 안쪽 <select>에 단다(fireEvent.change 유지).
FileInput(props: { label: string; accept?: string; multiple?: boolean; onFiles(files: File[]): void;
               hint?: string; chosen?: string[] })
  // 숨긴 <input type=file> + "파일 고르기" 버튼 + 고른 이름/"아직 고른 파일이 없어요". 브라우저 기본 문구가 보이지 않는다(UX-09).
  // data-testid는 숨긴 input에 단다(지금 테스트의 fireEvent.change(…, {target: {files}}) 유지).
Tabs(props: { value: string; onValueChange(v: string): void; label: string;
               tabs: { value: string; label: ReactNode; content: ReactNode; badge?: ReactNode }[] })
Range(props) / CommitRange(props)      // props 유지, 모양만 토큰(accent-color: accent)
Dialog(props: { open: boolean; onOpenChange(open: boolean): void; title: ReactNode;
               description?: ReactNode; children?: ReactNode; footer?: ReactNode; size?: "sm" | "md" | "lg" })
ConfirmDialog(props: { open: boolean; title: ReactNode; body?: ReactNode; confirmLabel: string;
               cancelLabel?: string; tone?: "default" | "danger"; busy?: boolean; error?: DescribedError;
               onConfirm(): void | Promise<void>; onCancel(): void })
Toaster(): JSX.Element                 // AppShell에 하나. 자리 testid "notification-center", 카드 testid "notif-<key 또는 id>" + data-region
toast(n: { tone?: "info" | "event" | "danger"; title: string; body?: string; key?: string;
           action?: { label: string; onClick(): void } }): void
  // key가 같은 카드가 보이면 내용을 바꾸고 6초를 다시 센다(동작 변경, BLM § 10). key 없으면 쌓인다.
  // key 규칙: 턴 알림 "turn:<region_id>", 플레이 경고 "play:run|budget|llm|busy".
StatusView(props: { state: "loading" | "empty" | "error" | "ready"; error?: DescribedError;
               emptyText?: string; emptyHint?: string; onRetry?(): void; skeleton?: "lines" | "cards";
               children?: ReactNode })
InlineError(props: { error: DescribedError; onRetry?(): void })
LocalizedText(props)                   // props 유지. 원문 보기 단추만 토큰 모양으로
LlmNotice(props)                       // AppShell이 쓰는 띠로 바뀐다. 화면에서 직접 그리지 않는다(BR-V2-20)
InProgressBadge(props)                 // 유지, 토큰 모양
```

## 3. 배치 틀 `layout/`

```ts
AppShell(props: { worldId?: string | null; sessionId?: string | null; children: ReactNode })
  // [정정] 설계는 children만 받았다. 메뉴의 열림·잠김에 worldId·sessionId가 필요해서 받는다(지금 AppNav와 같다).
  // 메뉴 순서: 월드(/) · 플레이 · GM · 에디터. 640px 미만은 [메뉴] 버튼 뒤로 접힌다.
  // capabilities가 LLM 꺼짐이면 머리띠 밑에 안내 띠 하나(testid "llm-notice", 문장 notice.llmOff). Toaster 하나.
SplitView(props: { main: ReactNode; aside: ReactNode; asideLabel: string;
                   stackOrder?: "main-first" | "aside-first"; asideWidth?: "narrow" | "wide" })
  // narrow = clamp(320px, 28vw, 380px), wide(기본) = clamp(320px, 32vw, 420px). 1024px 미만에서는 1열이다.
Section(props: { title: ReactNode; collapsible?: boolean; defaultOpen?: boolean;
                 actions?: ReactNode; level?: 2 | 3; children: ReactNode })
LangSwitch(props: { compact?: boolean })   // 지금 LangToggle. compact = "한/EN" 한 버튼
```

## 4. 지도 `map/`

```ts
WorldMap(props: {
  regions: MapRegion[]; connections: MapConnection[];
  mode: "edit" | "gm" | "play";
  selectedId?: string | null; playerRegionId?: string | null;
  reachableIds?: string[];                       // play
  focus?: { id: string; neighbors: string[] } | null;   // play: 그 둘레로 줌
  overlay?: Record<string, RegionOverlay>;        // gm: { ring?: "event" | "danger" | "info"; badge?: string }
  draggable?: boolean;                            // edit에서만 의미, 기본 false
  selectedConnection?: ConnectionKey | null;
  background?: string | null;                     // 지도 그림 URL(지금 mapImageUrl)
  label: string;                                  // aria-label 문장(화면이 만든다)
  onSelect?(id: string): void;
  onSelectConnection?(c: ConnectionKey): void;
  onMove?(id: string, pos: Norm): void;           // 0..1로 자름
  onAddAt?(pos: Norm): void;                      // 그림 밖이면 부르지 않음
})
normalizeFromMatrix(client: { x: number; y: number }, inverse: DOMMatrixLike, vb: ViewBox): Norm
toClient(p: Norm, matrix: DOMMatrixLike, vb: ViewBox): { x: number; y: number }
labelWidth(text: string, size: number): number
placeLabels(anchors: { id: string; x: number; y: number; r: number }[],
            labels: { id: string; text: string; size: number }[],
            occupied: Box[]): LabelBox[]
edgeStyle(kind: ConnectionKind, weight: number): { width: number; opacity: number;
            stroke: string /* "var(--color-map-…)" */; dash?: string; cross: boolean }
focusBox(regions: MapRegion[], focus: { id: string; neighbors: string[] }, pad?: number): ViewBox
autoLayout(regions: Region[]): Record<string, Norm>     // 옮기기만, 동작 유지
```
- `MapRegion`은 `{ id, name, level, position? }`, `MapConnection`은 `{ source, target, kind, weight }`다. 화면이 서버 타입에서 만든다.
- **V2에서 화면 적용**:
  - 세 화면은 `MapOverlay` 어댑터를 거쳐 새 지도를 그린다. 지도는 줄어들고, 단계 모양과 라벨 받침이 생긴다.
  - play의 작은 지도(`focus`)와 gm의 `overlay` 배지는 V4·V6가 화면에 붙인다.

## 5. 표기·오류·도우미

```ts
// format/
enumLabel(kind: EnumKind, value: string, lang?: Lang): string
degreeWord(distortion: number | null | undefined, lang?: Lang): string
decayWord(pathDecay: number | null | undefined, lang?: Lang): string
bandOf(kind: MeasureKind, value: number | null | undefined): string   // 단계 사전 키 또는 "—"
numberWithMeaning(kind: MeasureKind, value: number | null | undefined, lang?: Lang): string
formatDate(iso: string, lang?: Lang): string
formatDateTime(iso: string, lang?: Lang): string
turnLabel(n: number, lang?: Lang): string        // "4턴째"
turnAt(n: number, lang?: Lang): string           // "4턴", 0 → "시작"
// lang을 빼면 지금 표시 언어

// errors/
describeError(err: unknown, lang?: Lang): DescribedError

// hooks/
useResource<T>(key: readonly unknown[] | null, load: (signal: AbortSignal) => Promise<T>):
    { data: T | undefined; state: "loading" | "ready" | "error"; error?: DescribedError; reload(): void }
useAction<A extends unknown[], R>(run: (...a: A) => Promise<R>, opts?: { onDone?(r: R): void }):
    { run(...a: A): Promise<R | undefined>; busy: boolean; error?: DescribedError; clearError(): void }

// api/http.ts
http<T>(path: string, init?: RequestInit & { signal?: AbortSignal }): Promise<T>   // signal 전달
class HttpError { status; code?; detail; body }      // code·detail 가산
conflictKind(err), needsLlm(err), openSessionsOf(err), detailOf(err)  // 이름·반환 유지, 안쪽은 code 우선
```

## 6. 화면에서 바꾸는 것 (V2 범위만)

| 화면·파일 | V2가 하는 일 | 하지 않는 일 |
|---|---|---|
| 네 라우트(`HomePage`, `PlayPage`, `GmPage`, `EditorPage`) | `AppNav` → `AppShell` 감싸기, 옛 토큰 클래스 바꾸기(BLM § 2.4) | 배치·문구(V4·V6·V8) |
| `features/**/*` | 옛 토큰 클래스 바꾸기, 원색 값 제거 | 배치·문구·`String(e)` 정리(V4·V6·V8) |
| 대화상자 아홉 곳(BLM § 10) | `ConfirmDialog`/`Dialog`로 갈아 끼우기(요구사항 리뷰 R-01) | 대화상자의 문구(화면 유닛) |
| `<select>` 13곳(9파일), 파일 입력 넷(`EditorPage`, `GmPage`, `BuildPanel`, `WorldFileBar`) | `Select`, `FileInput`으로 갈아 끼우기 | |
| `NotificationCenter`를 쓰는 곳(GmHub, PlayPage) | 화면의 알림 목록 상태를 지우고 `toast({key})`로 갈아 끼우기(key 규칙 § 2) | |
| `LlmNotice`를 쓰는 곳(홈·플레이·에디터 라우트, GM 허브) | 지우고 AppShell 띠 하나로 | 버튼 보조 글(화면 유닛) |

- "V2가 끝난 뒤에도 네 화면은 새 모습으로 그대로 동작한다"(unit-of-work V2)는 위 표로 지킨다. 지금 vitest 202개는 GREEN을 유지해야 한다. 고쳐야 하는 기존 단언은 § 8.1에 목록으로 둔다.

## 7. 사용자 흐름 (V2가 만드는 공통 흐름)

1. **첫 읽기**: 화면이 열리면 `useResource`가 `loading`이고 `StatusView`는 스켈레톤을 보인다. 성공하면 내용(`ready`), 비었으면 빈 문장(`empty`)을 보인다. 실패하면 오류 문장, [다시 시도], 접힌 자세히를 보인다.
2. **쓰기 버튼**: 누르면 `useAction.busy`가 되고 버튼은 진행 표시와 함께 비활성이 된다. 두 번 눌러도 한 번만 실행된다. 끝나면 지정한 읽기만 다시 하고 알림을 보인다. 실패하면 위험 알림이 뜬다(code 문장).
3. **확인이 필요한 쓰기**: `ConfirmDialog`가 열린다. 확인하면 `busy`가 되고, 실패하면 대화상자 안에 오류를 보이고 닫지 않는다. 성공하면 닫히고 연 버튼으로 초점이 돌아온다.
4. **LLM 꺼짐**: 머리띠 밑 띠 하나가 나온다. LLM이 필요한 버튼은 꺼지고 보조 글("AI 키가 있어야 해요")이 붙는다.

## 8. 테스트 계획 (TP-V2-*)

| ID | 대상 | 종류 | 무엇을 단언하나 | 규칙 |
|---|---|---|---|---|
| TP-V2-1 | `tokens.contrast.test.ts` | 예시(표 전체) | `index.css`에서 값을 읽어 § 1의 (글, 바탕) 쌍 대비가 기준 이상 | BR-V2-06 |
| TP-V2-2 | `design.grep.test.ts` | 검사 | 원색 값·옛 클래스·`@fontsource/gaegu`·`prefers-color-scheme`이 없다. `color-scheme: dark`가 있다 | BR-V2-01·04·09 |
| TP-V2-3 | `format/enums.test.ts` | 예시(전수) | 모든 (kind, value)에 ko·en 라벨, 모르는 값은 원문 | BR-V2-11 |
| TP-V2-4 | `format/bands.prop.test.ts` | 속성(fast-check) | 전부·단조·경계·자르기·NaN | BR-V2-12, PBT-03 |
| TP-V2-5 | `format/dates.test.ts` | 예시 | `timeZone: "UTC"`로 고정한 ko·en 날짜, 턴 표기, 0 → "시작" | BR-V2-14 |
| TP-V2-6 | `i18n.style.test.ts` | 검사 | 새 접두어 키의 문체 끝맺음, ko·en 키 일치(지금 테스트 유지) | BR-V2-10 |
| TP-V2-7 | `errors/describe.prop.test.ts` | 속성 + 예시 | 제목이 언제나 있고 원문을 섞지 않음, code 표의 문장 | BR-V2-16 |
| TP-V2-8 | `tests/api/test_error_codes.py` (pytest) | 예시 + 매개변수화 | 예외 → (상태, code), 하위 클래스 우선, 라우터 직접 오류, 기본 code, 422 code, 없는 라우트 404·405, 500 처리기, `BodyLimitMiddleware` 413의 code, `region_in_use`·`sessions_open`의 객체 `detail` 유지 | BR-V2-15 |
| TP-V2-9 | `map/geometry.prop.test.ts` | 속성(fast-check) | `toClient` ↔ `normalizeFromMatrix` 왕복, 레터박스 밖 누름 | BR-V2-18, PBT-02 |
| TP-V2-10 | `map/labels.prop.test.ts` | 속성 + 예시 | 놓는 시점에 빈 후보가 있으면 그 후보, 입력 순서를 섞어도 같은 결과, 표식 안 가림. Emberleaf 12지역 겹침 수를 재서 기록(목표 0) | BR-V2-19, PBT-03 |
| TP-V2-11 | `map/edgeStyle.test.ts` | 예시 | 종류별 선 모양·토큰 변수, 같은 쌍 한 번 | BLM § 8.4 |
| TP-V2-12 | `ui/*.test.tsx` | 렌더 | Dialog 초점·Esc·복귀·busy, Tabs 키보드, Select·FileInput 라벨과 testid 위치, Button busy·크기, Toaster 자동 닫힘·위험 남음·같은 key 교체·key 없음 쌓임, StatusView 넷 | BR-V2-07·08·21·22·23 |
| TP-V2-13 | `hooks/*.test.tsx` | 렌더 | 늦은 답 버림, 언마운트 뒤 무시, 같은 틱에 `run()` 두 번 동기 호출 → 한 번 실행, reload 중 data 유지 | BR-V2-24 |
| TP-V2-14 | `capabilities.test.ts`(고침) | 예시(가짜 시계) | 실패 → 30초 안 마운트는 요청 없음 → 30초 뒤 마운트는 다시 요청, 성공 캐시 | BR-V2-25 |
| TP-V2-15 | `layout/*.test.tsx` | 렌더 | AppShell 메뉴 잠김(세션 없음)·LLM 띠 1개, SplitView 두 영역과 순서 | BR-V2-17·20 |
| TP-V2-16 | 기존 vitest 202 | 회귀 | 모두 GREEN. 고치는 단언은 § 8.1의 목록뿐이고, 고친 줄과 까닭을 code-summary에 적는다 | NFR-1 |

### 8.1 고쳐야 하는 기존 단언 (2026-10-07 grep, `web/src/__tests__/`)

| 단언 | 자리 | 왜 바뀌나 | 처리 |
|---|---|---|---|
| `notification-center` 존재·문구 | components.test:357, play.test:138-144·154·267, deeds.test:138 | 알림이 화면 상태가 아니라 AppShell의 Toaster로 간다 | Toaster가 같은 testid를 쓴다. 화면을 그리는 테스트는 **테스트 렌더 도우미** `renderWithShell`(`src/test/render.tsx`: MemoryRouter + Toaster + capabilities 대역)로 감싼다. 문구 단언(`play.budget`, `play.turnInProgress`, `play.runFailed`, `notif.rumors_added`)은 그대로 둔다 |
| `llm-notice` 존재·없음 | home.test:276·286, components.test:595, play.test:104·162 | 안내가 라우트 안 LlmNotice에서 AppShell 띠로 간다 | 라우트를 그리는 테스트는 라우트 자신이 AppShell을 그리므로 testid가 그대로 있다. 문구 단언 `llm.offNotice`·`play.noLlm`은 `notice.llmOff`로 바꾼다(의도된 동작 변경, BLM § 6.3) |
| `llm-notice` (GmHub 단독 렌더) | gm.test:632·648 | GmHub가 더는 띠를 그리지 않는다 | 띠 단언을 지우고, 대신 "LLM이 필요한 버튼이 꺼지고 까닭 글이 있다"를 단언한다. 띠의 1개 규칙은 TP-V2-15가 AppShell에서 본다 |
| native select `fireEvent.change` | home.test:69, play.test:299, editor.test:126·260·586 | — | 고치지 않는다. Select가 브라우저 `<select>`이고 testid가 안쪽에 붙는다 |
| 파일 입력 `fireEvent.change(files)` | components.test:523·551, editor.test:370·551·704·717·857 | — | 고치지 않는다. FileInput의 숨긴 input에 testid가 붙는다 |
| `import { AppNav }` | components.test:14·561-579 | AppNav가 지워진다 | `AppShell` 테스트로 옮긴다(메뉴 잠김, 에디터 링크). 단언의 뜻은 같다 |
| `import { autoLayout } from "../layout"`, `import { edgeStyle, toPixels } from "../viz"` | pure.test:2-3·32-38 | 파일이 `map/`으로 옮는다. `edgeStyle`의 색이 토큰 변수가 된다 | import 경로를 고친다. 색 단언(`#c0392b`)은 `var(--color-map-blocked)`로 바꾼다. 굵기 단조 단언은 그대로 |
| `import { MapOverlay }` | components.test:5·78-91, gm.test:12·168, editor.test:16·681 | MapOverlay가 WorldMap 어댑터가 된다 | 고치지 않는다. 어댑터가 지금 props를 받는다. 좌표 단언(editor.test:681 끌기)은 행렬 기반 정규화로 바뀌므로, jsdom에서 `getScreenCTM`이 없을 때 쓰는 대체 경로(컨테이너 rect)로 지금 값을 그대로 낸다 |
| 대화상자를 역할·버튼 이름으로 찾는 단언 | deeds.test:202·221, home.test:106, editor.test:376·396·719·721, components.test:331 | 대화상자가 Radix Dialog가 된다 | 고치지 않는다. ConfirmDialog도 Radix **Dialog**로 만들어 `role="dialog"`를 지킨다(alert-dialog는 `role="alertdialog"`라 쓰지 않는다). 확인·취소 버튼 이름은 지금 사전 문구(`action.confirm` 등, 화면이 넘기는 `confirmLabel`)를 그대로 쓴다. 테스트는 이미 `screen`으로 찾으므로 포털이어도 된다. 대화상자 안의 testid(`confirm-delete`, `new-session-*`)는 body 안에 그대로 있다 |

- **PBT 도구**: 프론트에 `fast-check`를 개발 의존성으로 들인다. FD가 속성 대상 함수를 넷 정했기 때문이다(단계 함수, 오류 문장, 좌표 왕복, 라벨 배치; NFR-6, PBT-09). 판 번호와 크기는 NFR light에서 확정하고, 앱 번들에는 들어가지 않는다.
- **시드 기록(PBT-08)**: vitest 실행이 fast-check 시드를 출력하도록 `setupTests.ts`에서 전역 설정한다. CI 로그에서 다시 돌릴 수 있게 한다.
- **생성기(PBT-07)**: 단계 함수는 경계 ± 1e-9를 섞은 실수다. 오류는 실제 code 집합과 모르는 문자열을 섞는다. 지도는 viewBox와 `meet` 축척(0.2~3), 이동(±500px)을 가진 행렬이다. 라벨은 한글·라틴을 섞은 1~12자 이름이다.
- **캡처(UOW-Q4=A)**: 코드가 끝나면 가짜 API로 네 화면을 1280·390px로 찍어 비공개 Artifact로 보인다. 역공학 때 쓴 스크래치 도구를 다시 쓴다.

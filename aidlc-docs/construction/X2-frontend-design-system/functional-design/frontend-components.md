# X2 Frontend Design System — Frontend Components

결정: FD-X2 Q1=A(제목=손글씨/본문=산세리프) · Q2=**C**(종이+잉크 모노) · Q3=A(은은한 스케치) · Q4=A(프리미티브 6종) · Q5=A(데스크톱 우선+최소 반응형).

> **한글 폰트 주의**: UI는 한국어(Q12=A). 손글씨 디스플레이 폰트는 **한글 글리프를 지원**하는 손글씨체(예: **Gaegu** 또는 **Nanum Pen Script**)를 로컬 번들해야 한다(라틴 전용 손글씨체는 한글 미표시). 본문은 system-ui(한글 양호).

## 디자인 토큰 (Tailwind `theme.extend` + CSS 변수)
종이+잉크 모노 팔레트:
| 토큰 | 값(제안) | 용도 |
|---|---|---|
| `--paper` | `#FAF6EC` (크림) | 앱 배경 |
| `--paper-card` | `#FFFDF7` | 카드/패널 배경 |
| `--ink` | `#201E1A` (근흑) | 본문·테두리·강조 |
| `--ink-soft` | `#5B554C` | 보조 텍스트 |
| `--line` | `#2018171A` (잉크 10%) | 옅은 구분선 |
| `--highlight` | `#EDE3C8` | 선택/hover 배경(형광펜 느낌, 저채도) |
| `--danger` | `#7A2E22` (잉크레드) | 삭제/경고 |
| `--radius` | `10px` / 불규칙(각 코너 미세 차등) | 손그림 라운드 |
| `--shadow-soft` | `2px 3px 0 var(--ink)` (오프셋 하드섀도) | 두들 카드 그림자 |
| 폰트 | `--font-display`(손글씨 한글), `--font-body`(system-ui) | 제목/본문 |

- **스케치 유틸**(Q3=A 은은): `.sketch-border`(1.5px 잉크 테두리 + 미세 비대칭 radius), `.sketch-shadow`(하드 오프셋), 밑줄 강조 `.ink-underline`(손그림 밑줄 SVG background). 과도한 hand-drawn SVG는 지양.
- 단일 **라이트** 테마(다크 없음, Q4=A/FR-UX1.4).

## 공용 프리미티브 (`web/src/ui/`)
| 컴포넌트 | props(요약) | 비고 |
|---|---|---|
| `Button` | `variant: primary\|ghost\|danger`, `size`, `disabled`, `data-testid` 통과 | 잉크 테두리 + 하드섀도, hover=highlight |
| `Panel` | `title?`, `children` | 카드형 섹션 컨테이너(제목=display 폰트) |
| `Card` | `children`, `interactive?` | 리스트 항목(소문/이벤트) |
| `Badge` | `tone: neutral\|promoted\|pruned\|event\|danger` | 상태 배지(승격/소멸/이벤트) |
| `Toast` | `tone`, `title`, `children`, `onClose` | X3 지역별 알림에 사용(본 유닛은 컴포넌트+스타일만) |
| `Modal` | `open`, `title`, `onConfirm`, `onCancel` | 확인 다이얼로그(X3 재생성 확인에 사용) |
| (보조) `Field`/`TextInput`/`Range` | 라벨+입력 스타일 통일 | 슬라이더(support/distortion) 잉크 스타일 |

- 프리미티브는 `data-testid`를 그대로 전달(FR-UX1.5 계약 보존).
- `Toast`/`Modal`은 X2에서 스타일·컴포넌트만 제공하고, 실제 사용(알림/확인 로직)은 X3.

## Tailwind 셋업(코드젠 대상)
- `web/tailwind.config.{js,ts}`: `content` = `./index.html`, `./src/**/*.{ts,tsx}`; `theme.extend` = 위 토큰(color/borderRadius/boxShadow/fontFamily).
- `web/postcss.config.js`: tailwindcss + autoprefixer.
- `web/src/index.css`: `@tailwind base/components/utilities` + `@font-face`(로컬 번들 손글씨 폰트, `web/src/assets/fonts/`) + `:root` CSS 변수 + `.sketch-*` 컴포넌트 클래스. `body { background: var(--paper); font-family: var(--font-body); }`.
- `main.tsx`에서 `import "./index.css"`.
- 외부 CDN/폰트 호출 없음(SEC-B/D) — 폰트는 저장소에 번들.

## 기존 컴포넌트 restyle 매핑 (구조 유지, 인라인 style→Tailwind/프리미티브)
| 컴포넌트 | restyle 요점 |
|---|---|
| `App` | 종이 배경, 헤더 영역, `flex` 레이아웃을 Tailwind로; error/busy/hint를 `Badge`/색 토큰으로 |
| `Toolbar` | 입력·버튼을 `Field`/`Button`로; world id 입력 잉크 스타일 |
| `SessionBar` | 세션 생성/선택/종료를 `Button` + `Panel` |
| `MapOverlay` | 지도 이미지/SVG 오버레이는 로직 유지, 컨트롤·라벨 chrome만 잉크 스타일(테두리·핀) |
| `RegionPanel` | `Panel` + `Card` 리스트, 지식 항목 카드화 |
| `SessionPanel` | GameMaster 허브를 `Panel` 섹션들 + `Button`/`Range`/`Badge`(PROMOTED 등) |
| `AugmentPanel` | Q&A를 `Panel`+`Card`, 입력 `Field` |

## 데이터/동작 불변
- 모든 이벤트 핸들러·상태·`data-testid`·API 호출 유지(FR-UX1.5). 순수 프레젠테이션 변경.
- 기존 vitest(`components.test.tsx`, `pure.test.ts`) 계약 보존; 필요한 최소 수정만.

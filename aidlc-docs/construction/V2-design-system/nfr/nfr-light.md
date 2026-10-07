# V2 디자인 시스템 — NFR (light: 요구 + 설계)

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기를 포함한다.
**지금 하는 것**: V2 NFR(가벼운 판). 새 디자인 기반이 크기 예산(JS·글꼴), 대비, 브라우저 범위, 테스트 도구 요구를 지키는지 재고 정한다.

근거:
- 요구사항 `inception/requirements/follow-up-requirements.md` NFR-1~10, 요구사항 리뷰 R-05(확인 방법)
- 유닛 `unit-of-work.md` V2의 NFR light 항목(headless 패키지와 크기, 글꼴 부분 집합과 예산, 대비 확인 방법, 브라우저·기기 범위, 옆 패널 폭 상한)
- 승인된 FD(`functional-design/*`). 리뷰 02의 R-10·R-11은 Accepted risk이고 코드 계획으로 간다.

**측정**: 2026-10-07에 스크래치에서 쟀고 저장소에는 아무것도 설치하지 않았다.
- 후보 패키지를 `npm install --ignore-scripts`로 받았다.
- vite(저장소의 판)로 react만 있는 번들과 비교해 늘어나는 gzip 크기를 쟀다.
- 글꼴은 fontsource CSS의 unicode-range와 시안 B 화면의 글자로 내려받을 조각을 셌다.

---

## 1. NFR별 적용

| NFR | V2 적용 | 방법 | 수치 · 검증 |
|---|---|---|---|
| **NFR-1 회귀 0** | ✅ | 기존 테스트는 지우지 않는다. 고치는 단언은 FD frontend-components § 8.1 목록뿐이고, 의도된 동작 변경은 § 4의 넷뿐이다 | pytest·vitest·ruff·black·tsc GREEN, mypy ≤ 11, `npm audit --omit=dev` 0. 고친 테스트 줄을 code-summary에 적는다 |
| **NFR-2 사람 화면 확인** | ✅(캡처) | 코드가 끝나면 가짜 API로 네 화면을 1280·390px로 찍어 비공개 Artifact로 보인다(UOW-Q4=A). 실제 스택 확인은 B&T에서 한다 | 캡처 8장 이상 |
| **NFR-3 대비와 읽기** | ✅ | 확인 방법은 **토큰 쌍 계산**이다(요구사항 리뷰 R-05). `tokens.contrast.test.ts`가 `index.css`의 값을 읽어 FD domain-entities § 1.6 허용 쌍 표의 모든 칸을 WCAG 상대 휘도로 계산한다. axe·브라우저 검사는 범위 밖이다(Q7=B) | 글 4.5:1, UI 경계 3:1. 지금 표의 최저: 글 4.78(faint/sunken), 경계 3.10(line-strong/surface). 본문 최소 크기는 13px(휴대폰 12px 아래 없음) |
| **NFR-4 크기** | ✅ | § 2 | JS gzip ≤ 125.6 kB(96.6 × 1.3), 첫 화면(홈) 글꼴 < 760 kB |
| **NFR-5 호환** | ✅ | 오류 응답에 `code`를 더한다(가산, `detail` 모양 유지). `/api/health` 503 모양은 그대로다. World File·번역 칸은 V2와 무관하다 | TP-V2-8 |
| **NFR-6 PBT Partial** | ✅ | 프론트에 fast-check를 들인다(§ 3). 속성 대상은 넷: 단계 함수(PBT-03), 오류 문장(PBT-03), 지도 좌표 왕복(PBT-02), 라벨 배치(PBT-03). 생성기는 FD § 8의 도메인 생성기(PBT-07)다. 시드는 실행마다 출력한다(PBT-08). 백엔드 `code` 표는 매개변수화 예시 테스트다(속성 대상 아님) | `setupTests.ts`가 `fc.configureGlobal({ seed })`를 걸고 시드를 출력한다. `FC_SEED` 환경 변수로 다시 돌린다 |
| **NFR-7 브라우저** | ✅ | § 4 | 사람 확인(B&T) |
| **NFR-8 보안 확장 꺼짐** | ✅ | 새 런타임 의존은 Radix 둘과 그 전이 의존(MIT)뿐이다. 글꼴은 자체 호스팅이다(외부 CDN 없음). `dangerouslySetInnerHTML`을 쓰지 않는다 | `npm audit` 0(스크래치 설치에서 0 확인). 소스 grep 0 |
| **NFR-9 키 없이** | ✅ | LLM 꺼짐 띠 하나와 꺼진 버튼의 까닭 글(FD BLM § 6.3). 디자인 기반은 LLM을 부르지 않는다 | TP-V2-15 |
| **NFR-10 동시성 검증** | — | V2와 무관하다(V5) | — |

## 2. 크기 예산 (NFR-4)

### 2.1 JS
| 항목 | gzip | 출처 |
|---|---|---|
| 지금 앱 번들(한 덩어리) | **96.6 kB** | 2026-10-07 `vite build`(스크래치 출력), `index-*.js` 324.7 kB → gzip 96,637 B. 요구사항 기준값과 같다 |
| react + react-dom만 | 44.9 kB | 측정용 빈 앱 |
| + Radix Dialog | +12.9 kB | |
| + Radix Tabs | +4.3 kB | Dialog와 공유 의존이 있어 따로 더한 값보다 작다 |
| + Radix Toast + Collapsible | +3.8 kB | **들이지 않는다**(§ 3) |
| 새 코드 어림(format·errors·hooks·map·layout·ui, 사전 늘어남) | +7~10 kB | 지울 코드(MapOverlay 본체, Modal, Toast, NotificationCenter) 약 −2 kB 포함 |
| **예상 합** | **≈ 119~122 kB** | 예산 125.6 kB 안 |

- **측정 방법**(BR-V2-26): 코드가 끝나면 `npx vite build --outDir <스크래치>`로 빌드하고 `assets/*.js`마다 `gzip -c | wc -c`의 합을 code-summary에 적는다. 저장소 `dist/`는 건드리지 않는다.
- **넘으면**: `routes/GmPage`·`routes/EditorPage`를 `React.lazy`로 나눠 홈·플레이가 받는 JS를 예산 안에 둔다. 합계와 첫 화면 JS를 함께 적고 사유를 남긴다(NFR-4 "넘으면 사유를 적는다"). 테스트는 페이지를 직접 그리므로 지연 적재의 영향이 없다.

### 2.2 글꼴
**결정**: 나눔명조는 **700 한 굵기**만 쓴다(제목과 내레이션 모두). FD domain-entities § 2의 800은 뺀다. 둘을 함께 쓰면 플레이 화면 글꼴이 1.2 MB가 되기 때문이다. Noto Sans KR은 400·700 두 굵기다(500은 뺀다).

| 화면(시안 B 글자 기준) | Noto 400 | Noto 700 | 나눔명조 700 | IM Fell SC | 합 |
|---|---|---|---|---|---|
| **홈(첫 화면)** | 112 kB | 114 kB | 179 kB(조각 8) | 57 kB | **462 kB** |
| 휴대폰 플레이 | 177 kB | 179 kB | 178 kB | 57 kB | 590 kB |
| 데스크톱 플레이 | 209 kB | 212 kB | 342 kB(조각 15) | 57 kB | 820 kB |

- 지금은 Gaegu 한글 두 굵기 woff2가 **762 kB**(283.7 + 478.6)로, 첫 화면에서 통째로 받는다. 새 홈은 462 kB라 예산(760 kB 미만)을 지킨다.
- 한글 글꼴은 조각(Noto 124조각, 나눔명조 92조각)으로 나뉜다. 화면에 나온 글자의 조각만 받고, 한 번 받은 조각은 다른 화면에서 다시 쓴다(브라우저 캐시).
- 데스크톱 플레이에 바로 들어오면 820 kB다. 이 값은 NFR-4의 기준(첫 화면)이 아니다. 대신 이렇게 줄인다.
  - `font-display: swap`으로 글은 시스템 글꼴로 먼저 보인다.
  - 홈을 거쳐 오면 이미 받은 조각을 다시 쓴다.
  - 이 값은 code-summary에 참고로 적는다.
- **측정 방법**: 위 표는 시안 글자로 어림한 것이다. 코드가 끝나면 캡처 도구(headless Chrome)의 네트워크 기록에서 화면별 `woff2` 바이트 합을 재서 code-summary에 적는다.
- 글꼴 라이선스는 셋 다 OFL-1.1이다. `@fontsource/*` 5.3.0을 쓴다.

## 3. 기술 스택 결정

| 결정 | 선택 | 대안과 까닭 |
|---|---|---|
| 대화상자 | `@radix-ui/react-dialog` 1.2.0(MIT, React 16.8~19) | 포커스 가두기·복귀·Esc·스크롤 잠금·`aria-*`를 직접 만들면 결함이 생기기 쉽다(설계 Q5=A). ConfirmDialog도 이것으로 만든다. alert-dialog는 `role="alertdialog"`라 지금 테스트와 맞지 않는다(FD § 8.1) |
| 탭 | `@radix-ui/react-tabs` 1.1.22(MIT) | 화살표 키·`tablist`/`tabpanel` 연결을 맡는다. +4.3 kB |
| 알림 | **직접 만든다**(`ui/toast.ts` 저장소 + `Toaster`) | Radix Toast(+약 2 kB)는 스와이프·F8 단축키처럼 이 앱에 필요 없는 것을 더한다. 필요한 것은 `aria-live` 영역 하나, `role="alert"`, 시간, key 교체(FD BR-V2-22)뿐이다. 테스트용 `clearToasts()`를 둔다(FD 리뷰 R-10) |
| 접히는 묶음(Section) | **직접 만든다**(버튼 + `aria-expanded` + `aria-controls`) | Radix Collapsible은 높이 애니메이션 말고 더하는 것이 없다 |
| select | 브라우저 `<select>` + 토큰 모양 | FD § 10 정정과 같다. JS 0 |
| 패키지 묶음 | 개별 `@radix-ui/react-*` | 통합 `radix-ui` 패키지(1.7.0)는 쓰지 않는 부품까지 의존으로 끌어온다. 개별 패키지가 audit 범위를 좁힌다 |
| 글꼴 | `@fontsource/noto-sans-kr` 400·700, `@fontsource/nanum-myeongjo` 700, `@fontsource/im-fell-english-sc` 400(5.3.0, OFL-1.1) | 지금처럼 fontsource로 자체 호스팅한다. `@fontsource/gaegu`는 지운다 |
| 속성 테스트(프론트) | `fast-check` 4.10.2(MIT, 개발 의존성만) | 사용자 생성기(arbitrary)와 자동 축소를 지원한다(PBT-09). vitest에 `@fast-check/vitest` 없이 `fc.assert`로 쓴다. 앱 번들에 들어가지 않는다 |

- 새 런타임 전이 의존: `react-remove-scroll`, `react-remove-scroll-bar`, `react-style-singleton`, `use-callback-ref`, `use-sidecar`, `aria-hidden`, `get-nonce`, `detect-node-es`, `tslib`(모두 MIT). 스크래치 `npm audit` 0이다.
- `package.json`에는 정확한 판이 아니라 지금 관례대로 `^` 범위를 쓴다. 잠금 파일(`package-lock.json`)이 판을 고정한다.

## 4. 브라우저·기기 범위 (NFR-7)

| 대상 | 범위 | 확인 |
|---|---|---|
| 데스크톱 | 최신 Chrome·Firefox·Safari | B&T에서 사람이 네 화면을 본다(1280px) |
| 휴대폰 | 최신 iOS Safari·Android Chrome, **홈·플레이만** 제대로(CQ4=A) | B&T 390px. 에디터·GM은 깨지지 않음만 본다 |
| 바닥선 | Tailwind v4가 요구하는 브라우저(Safari 16.4+, Chrome 111+, Firefox 128+) | 이보다 오래된 브라우저는 범위 밖이다 |

- 쓰는 CSS: `color-scheme`, `clamp()`, `:focus-visible`, `position: sticky`, `color-mix()`(Tailwind 투명도), cascade layers. 모두 위 바닥선에서 된다.
- jsdom(테스트)은 레이아웃·`getScreenCTM`이 없다. 지도 좌표는 대체 경로(FD BLM § 8.1)로 테스트한다.

## 5. 배치 값 (요구사항 리뷰 R-05)
FD BLM § 9에서 정한 값을 확인만 한다.
- 옆 패널은 `clamp(320px, 32vw, 420px)`이고 좁은 판은 `clamp(320px, 28vw, 380px)`다.
- 1024px 미만은 1열이다.
- 본문 최대는 1240px이고, 좌우 여백은 24px(640px 미만 16px)이다.
- 누르는 영역은 휴대폰에서 44px 이상이다.
- 판정은 사람 확인(캡처, B&T)이다. 자동 레이아웃 게이트는 없다(Q7=B, 감수한 위험 R-1).

## 6. 신뢰성
- **오류 문장이 비지 않는다**: `describeError`는 언제나 제목을 준다(BR-V2-16, 속성 테스트).
- **알림 저장소가 테스트 사이에 새지 않는다**: `setupTests.ts`의 `afterEach`가 `clearToasts()`를 부른다(FD 리뷰 R-10).
- **capabilities 재시도가 몰리지 않는다**: 실패 뒤 30초 안의 마운트는 다시 읽지 않는다(BR-V2-25).
- **500도 JSON**: 잡히지 않은 예외도 `{"detail": "internal error", "code": "error"}`다.
  - 이 응답은 Starlette의 `ServerErrorMiddleware`가 쓴다. 그래서 다른 미들웨어 바깥에서 나간다. 지금 앱에는 CORS 미들웨어가 없고(`api/main.py`는 `BodyLimitMiddleware`만 단다), 웹은 nginx가 `/api/`를 같은 출처로 넘긴다. 그래서 영향이 없다.
  - 테스트는 `TestClient(app, raise_server_exceptions=False)`로 본다.

## 7. 의도된 동작 변경 (NFR-1)
| # | 바뀌는 것 | 근거 | 테스트 영향 |
|---|---|---|---|
| C-1 | 같은 key의 알림은 쌓이지 않고 내용이 바뀐다 | FD BLM § 10, BR-V2-22 | play.test의 알림 단언(문구는 그대로) |
| C-2 | LLM 꺼짐 안내 문장이 모든 화면에서 하나(`notice.llmOff`)다. GM 허브 안의 안내는 없어진다 | BLM § 6.3, BR-V2-20 | home.test:276, components.test:595, play.test:162, gm.test:632·648 |
| C-3 | 오류 응답에 `code`가 생긴다. 잡히지 않은 500이 JSON이 된다 | BLM § 6.1, BR-V2-15 | 오류 본문 전체를 `== {"detail": …}`로 비교하는 pytest는 0건이다(2026-10-07 grep). 코드 계획에서 다시 확인한다 |
| C-4 | 화면이 B 톤(어두운 바탕)으로 바뀐다. 글꼴이 바뀌고 Gaegu가 빠진다 | Q1=B, FR-D3 | 클래스 단언 0(grep) |

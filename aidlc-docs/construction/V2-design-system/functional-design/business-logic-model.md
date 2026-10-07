# V2 디자인 시스템 — Business Logic Model

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V2 Functional Design. 네 화면이 올라설 디자인 기반의 동작을 정한다: 토큰, 글꼴, 문체, 표기 규칙, 오류 문장, 요청 도우미, 지도, 배치 틀.

**결정**(`construction/plans/V2-design-system-functional-design-plan.md`):
- **Q1 = B 등불 아래 선술집.** 시안대로 쓰고 고칠 점은 없다.
  - 시안: 비공개 캔버스 https://claude.ai/artifact/MVUpR3nDzrrez29HHg1UmK 의 둘째 줄(B · 홈 / 플레이 / 휴대폰 플레이 / 토큰과 부품). 저장소에는 두지 않는다(C-1).
  - 어두운 바탕이 **하나뿐인 테마**가 된다(CQ2=A). 요구사항 §9의 "다크 테마는 범위 밖"은 둘째 테마를 뜻했다. 이제 밝은 테마가 미뤄 둔 쪽이다.
- **Q2 = A 글의 종류마다 문체를 나눈다.** § 4에서 정한다.

**같이 보는 문서**: `business-rules.md`(BR-V2-*), `domain-entities.md`(값 목록), `frontend-components.md`(props, 파일 이동, 테스트 계획).

---

## 1. 층과 흐름

```
index.css @theme ── 토큰(원색 값은 여기에만)
      │
      ├─ ui/       프리미티브: Button·Badge·Card·Field·Select·FileInput·Textarea·Tabs·Range·
      │            CommitRange·Dialog·ConfirmDialog·Toaster·StatusView·LocalizedText·LlmNotice
      ├─ layout/   AppShell·SplitView·Section
      └─ map/      WorldMap(+ 순수 함수: 좌표·라벨 배치·연결 모양·자동 배치)
format/  enum 라벨·말 단계·숫자와 뜻·날짜  ─┐
errors/  오류 → 사용자 문장                 ├─ 화면(routes/ + features/*)이 쓴다
hooks/   useResource·useAction             ─┘
i18n/    사전(ko·en)과 표시 언어 상태
api/     http()·HttpError(+code)
```

- 화면은 위 층만 쓴다. 원색 값(`#…`), 원문 enum, `String(e)`를 화면 코드에 새로 쓰지 않는다(BR-V2-01~03).
- **V2의 화면 적용 범위**:
  - 프리미티브와 토큰은 앱 전체에서 한 번에 바뀐다. 그래서 V2가 끝나면 네 화면이 모두 B 톤으로 보이고 그대로 동작한다.
  - 화면의 **배치**(어느 패널이 어디에 있는가)와 화면 문구는 V4·V6·V8이 맡는다.
  - V2는 화면 파일에 기계적인 것만 바꾼다. 옛 토큰 클래스를 새 이름으로 바꾸고(§ 2.4), 대화상자·알림·select·파일 입력·LLM 안내를 공유 부품으로 갈아 끼운다(§ 10, § 6.3).

## 2. 토큰 체계

### 2.1 세 층
1. **원색 값**: `web/src/index.css`의 `@theme` 안에만 둔다.
2. **의미 토큰**: 쓰임새 이름이다. Tailwind v4가 `--color-<이름>`에서 `bg-<이름>`·`text-<이름>`·`border-<이름>` 유틸을 만든다. 값 목록은 `domain-entities.md` § 1에 있다.
   - 바탕: `bg`, `chrome`(머리띠), `surface`(패널), `sunken`(오목·입력 안·선택 칩)
   - 글: `fg`, `muted`, `faint`
   - 선: `line`(장식 구분선), `line-strong`(조작 경계)
   - 강조·상태: `accent`, `accent-hover`, `on-accent`, `danger`, `on-danger`, `success`, `event`, `info`, `info-fg`, `ornament`
   - 비활성: `disabled`, `disabled-fg`
   - 옅은 바탕(배지·안내): `tint-event`, `tint-danger`, `tint-success`, `tint-info`, 각자 `-line`
   - 지도: `map-sea`, `map-land`, `map-land-line`, `map-cliff`, `map-river`, `map-path`, `map-blocked`, `map-town`, `map-plate`, `map-current`, `map-player`
3. **모양 토큰**:
   - 모서리: `--radius-sm` 6px(배지 안쪽), `--radius-md` 8px(버튼·입력), `--radius-lg` 12px(패널·카드), `--radius-xl` 14px(대화상자), 배지는 999px
   - 그림자: `--shadow-panel`(안쪽 윗선 + 옅은 그림자), `--shadow-pop`(알림·대화상자)
   - 초점 고리: `--color-focus` = accent, 2px, 2px 띄움

### 2.2 어두운 하나의 테마
- `:root { color-scheme: dark }`를 둔다. 그러면 브라우저 기본 조작(스크롤바, select 펼침, 날짜 입력)도 어둡게 그려진다.
- `prefers-color-scheme`으로 테마를 바꾸지 않는다. 사용자가 밝은 모드여도 B 톤 하나로 보인다(CQ2=A). 밝은 테마는 다음 주기 후보다.

### 2.3 화면이 토큰을 쓰는 법
- 화면은 의미 토큰 유틸(`bg-surface text-fg border-line-strong`)과 프리미티브만 쓴다.
- 지도 SVG의 선·점 색은 `var(--color-map-*)`로 칠한다. `viz.ts`의 `#c0392b`·`#34495e` 하드코드는 없어진다(FR-D2).

### 2.4 옛 클래스의 기계적 변환 (V2가 화면 파일에서 하는 일)
지금 화면·프리미티브 코드에는 옛 토큰 클래스가 약 230번 쓰였다(`text-ink-soft` 88, `sketch-border` 37, `font-display` 32, `bg-paper-card` 29, `sketch-shadow` 10, `bg-highlight` 9, `bg-ink` 8 등; 2026-10-07 grep). 테마가 어두워지므로 이름만 바꿔 두면 뜻이 뒤집힌다. 그래서 아래 표로 바꾼다.

| 옛 클래스 | 새 클래스 | 메모 |
|---|---|---|
| `bg-paper` | `bg-bg` | |
| `bg-paper-card` | `bg-surface` | |
| `text-ink` | `text-fg` | |
| `text-ink-soft` | `text-muted` | |
| `bg-highlight` | `bg-sunken` | 강조 바탕이면 `bg-tint-event` |
| `bg-ink text-paper` (뒤집힌 칩·버튼) | 버튼은 `Button variant="primary"`, 칩은 `Badge tone="promoted"` | 손으로 고른다 |
| `sketch-border` | `border border-line-strong rounded-md` | 패널이면 `Card`·`Panel` |
| `sketch-shadow` | `shadow-panel` | |
| `font-display` | 제목이면 `font-heading`, 버튼·배지·본문이면 지움(본문 글꼴) | FR-D3 |
| `bg-ink/30` 같은 투명도 변형(대화상자 뒤 가림막) | `bg-scrim` | 공유 Dialog로 바뀌며 사라진다 |
| `border-ink` | `border-line-strong` | |
| `accent-ink`(슬라이더) | `accent-[var(--color-accent)]` | Range 프리미티브 안 |
| `.ink-underline`(index.css 정의) | 지운다 | 쓰는 곳 0 |
| `opacity-40`(비활성) | 프리미티브의 비활성 토큰 | NFR-3 |

- 건수(2026-10-07 재 grep, 테스트 제외, 참고값):
  - `text-ink-soft` 88, `sketch-border` 38, `font-display` 36, `bg-paper-card` 29, `sketch-shadow` 11, `bg-highlight` 9
  - `text-ink` 7, `text-paper` 6, `bg-paper` 5, `bg-ink` 4, `bg-ink/…` 4, `border-ink` 2, `accent-ink` 1
- 바꾼 뒤 옛 이름은 `@theme`에서 지운다. 남은 쓰임이 있으면 tsc는 못 잡고 화면에 색이 빠진다. 그래서 grep 검사를 테스트로 둔다(BR-V2-01 검증).
- `font-display`는 새 토큰 이름이기도 하다. 그래서 검사는 이름만 보지 않고 **파일 범위**로 본다. `layout/AppShell.tsx`(로고)와 `index.css` 밖에서는 0건이어야 한다.

## 3. 글꼴 역할과 적재

| 역할 | 글꼴 | 굵기 | 쓰는 곳 |
|---|---|---|---|
| 장식 `font-display` | IM Fell English SC | 400 | 로고 "Locus"와 라틴 문자 장식 줄. 한글 글자가 없어 한글에는 쓰지 않는다 |
| 제목 `font-heading` | 나눔명조 | 700, 800 | 화면·패널·대화상자 제목, 지역 이름, 월드 이름 |
| 본문 `font-body` | Noto Sans KR | 400, 500, 700 | 본문, 버튼, 배지, 입력, 탭, 알림 |
| 이야기 `font-story` | 나눔명조 | 700 | 선언의 결과(내레이션) 본문 |

- 셋 다 SIL OFL이다. 자체 호스팅한다(`@fontsource/*` 패키지, 외부 CDN 없음, NFR-8).
- 한글 글꼴은 unicode-range로 잘린 조각을 쓴다. 그래서 브라우저는 그 화면에 나온 글자의 조각만 받는다(NFR-4).
- 지금의 Gaegu(손글씨)는 뺀다(A-3, UX-01).
- 대체 글꼴 줄:
  - 제목: `"Nanum Myeongjo", "Noto Serif KR", serif`
  - 본문: `"Noto Sans KR", system-ui, "Apple SD Gothic Neo", "Malgun Gothic", sans-serif`
  - 글꼴을 받기 전에는 시스템 글꼴로 먼저 그린다(`font-display: swap`).
- 크기와 예산 확인은 NFR light가 한다.

## 4. 문체 (Q2 = A)

사전의 모든 문장은 네 종류 가운데 하나다. 종류는 **키의 첫 마디**로 정한다. 그래서 키만 보고도 어떤 문체로 써야 하는지 안다.

| 종류 | 키 첫 마디 | 문체 | 예 |
|---|---|---|---|
| 조작 이름 | `action.` `nav.` `tab.` | 짧은 동사형·명사형, 마침표 없음 | "기다리기", "이동", "말 걸기", "세션 닫기" |
| 안내 | `notice.` `error.` `confirm.` `empty.` `hint.` | 해요체 | "세션이 닫혔어요.", "세션을 닫을까요?" |
| 이야기 | `story.` `log.` `timeline.` | 해라체 | "솔트웨이크 항구에 닿았다." |
| 값 이름 | `enum.` `word.` `label.` `unit.` | 명사구, 마침표 없음 | "마을", "조금 부풀려짐", "4턴째" |

- 옛 키(`play.*`, `gm.*`, `editor.*` …)는 그 화면을 다시 쓰는 유닛(V4·V6·V8)에서 위 종류로 옮긴다. 옛 키를 지우는 것은 V9가 한 번에 한다(unit-of-work-dependency § 4).
- 영어 사전도 같은 종류를 따른다. 조작 이름은 동사로 시작하고(Title Case 아님), 안내는 평서문, 이야기는 과거형이다.
- 대화(NPC 말)와 서버가 만든 문장(내레이션·소문)은 LLM이 쓰므로 사전 밖이다. 다만 서술 프롬프트의 문체는 백엔드 일이라 이 유닛에서 바꾸지 않는다.

## 5. 표기 규칙 (`format/`)

### 5.1 enum 라벨
- `enumLabel(kind, value, lang)`는 사전 키 `enum.<kind>.<value>`를 찾는다.
- 모르는 값이 오면 원문을 그대로 돌려주고, 개발 빌드에서만 `console.warn`을 남긴다. 화면이 비지는 않는다.
- 테스트는 `domain-entities.md` § 4의 값 집합을 하나도 빠짐없이 돌며 ko·en 라벨이 있는지 본다(NFR-6).
- **설계 정정**: component-methods § 1.4의 `EnumKind`에 있던 `slant`는 enum이 아니다. 판정 NPC가 LLM으로 쓴 한두 낱말의 자유 문장(`DeedAppraisal.slant`)이라 빼고, 원문을 그대로 보인다.

### 5.2 수치 → 말 (플레이어 화면)
플레이어 화면은 0~1 수치를 숫자로 보이지 않고 **단계 낱말**로 보인다(FR-D8). 단계 표는 `domain-entities.md` § 3에 있다.

- `degreeWord(distortion)`: 소문이 얼마나 비틀렸는가. 예: "조금 부풀려짐".
- `decayWord(pathDecay)`: 전해 들은 이야기가 얼마나 희미한가. 예: "아주 희미하게".
- 단계 계산 규칙(모든 단계 함수에 같다, BR-V2-12):
  - 아래 경계는 넣고 위 경계는 뺀다. 마지막 단계만 1을 넣는다.
  - 0보다 작으면 0으로, 1보다 크면 1로 자른다. 개발 빌드에서는 경고를 남긴다.
  - `NaN`·`null`은 "—"를 보인다.
  - 값이 커질수록 단계는 같거나 높아지기만 한다(단조).

### 5.3 숫자와 뜻 (GM·에디터 화면)
`numberWithMeaning(kind, value, lang)`는 `"0.42 · 많이 비틀림"`처럼 숫자를 두 자리로 보이고 뒤에 단계 낱말을 붙인다.

- kind는 `distortion`, `support`, `magnitude`, `confidence`, `salience`, `weight`, `decay`, `share`다.
- 지금의 `d0.42`·`m0.40`·"감쇠"·"열의" 같은 줄임 표기를 대신한다(UX-04).

### 5.4 날짜와 턴
- `formatDate(iso, lang, timeZone?)`는 표시 언어의 로캘을 쓴다(`Intl.DateTimeFormat`). 브라우저 로캘이 아니다(UX-07).
  - **시간대**는 보는 사람의 시간대(브라우저의 시간대)다. 서버 시각은 UTC ISO 문자열이고, 사람은 자기 하루 기준으로 "언제 고쳤나"를 읽기 때문이다.
  - 테스트는 `timeZone: "UTC"`를 넘겨 결과를 고정한다.
  - ko: "2026년 10월 2일"
  - en: "Oct 2, 2026"
  - 예: `"2026-10-02T12:00:00Z"`를 UTC로 보면 위와 같다.
  - 시각이 필요한 곳은 `formatDateTime`을 쓴다(같은 규칙).
- 턴 표기: `turnLabel(n)`은 "4턴째"(지금 턴)다. `turnAt(n)`은 "4턴"(기록 줄 앞)이고, 0은 "시작"이다.

## 6. 오류 → 사용자 문장 (`errors/` + `api/errors.py`)

### 6.1 서버
- `api/errors.py`에 `ERROR_CODES`를 둔다. **순서 있는 표**로, 항목은 (예외 타입, 상태, `code`)다.
  - `http_error(exc)`는 표를 위에서부터 보고 처음 맞는 `isinstance` 줄을 쓴다.
  - 하위 클래스를 기반 클래스보다 앞에 둔다. 예: `UnsupportedWorldFile`은 `ValueError`보다 앞이다.
  - 결과는 `ApiError(HTTPException)`이고 `code`를 싣는다.
- 라우터가 직접 던지는 `HTTPException`(열린 세션 409, 업로드 413 …)도 `ApiError(..., code=…)`로 바꾼다. `detail`은 그대로라서 지금 클라이언트 동작(`openSessionsOf`)이 유지된다.
  - `RegionInUseError`는 `ERROR_CODES`에 넣지 않는다. 라우터(`world_editor.py`)가 지금처럼 잡아서 `ApiError(409, {"message", "session_ids"}, "region_in_use")`로 던진다. `http_error`로 보내면 `detail`이 문자열이 되어 `session_ids` 객체가 사라지기 때문이다.
- **오류 본문을 쓰는 자리 넷**(이 넷이 "모든 오류 응답"의 범위다, BR-V2-15):
  1. `api/main.py`의 처리기를 `starlette.exceptions.HTTPException`에 건다. FastAPI의 `HTTPException`·`ApiError`와 Starlette의 라우트 없음 404·메서드 없음 405를 함께 받는다. 본문은 `{"detail": …, "code": …}`이다.
     - `code`가 없으면 상태별 기본을 붙인다: 400 `invalid_request`, 404 `not_found`, 405 `method_not_allowed`, 409 `conflict`, 413 `too_large`, 422 `validation_failed`, 503 `service_unavailable`, 그 밖은 `error`.
     - 예외의 `headers`는 그대로 넘긴다.
  2. 검증 실패(`RequestValidationError`, 422) 처리기는 지금 본문에 `code: "validation_failed"`를 더한다.
  3. 잡히지 않은 예외(500)는 `Exception` 처리기가 `{"detail": "internal error", "code": "error"}`로 쓴다. 지금은 평문 "Internal Server Error"다. 예외는 지금처럼 로그로 남는다.
  4. `api/uploads.py`의 `BodyLimitMiddleware`는 미들웨어에서 413 `JSONResponse`를 직접 돌려준다. 처리기를 거치지 않으므로 그 본문에도 `"code": "too_large"`를 직접 싣는다.
- 범위 밖: `/api/health`의 503은 오류 본문이 아니라 상태 보고(`{"status", "boundaries"}`)다. 모양을 그대로 둔다.
- 변경은 가산이다(NFR-5). `detail`의 모양은 바뀌지 않는다.
- 코드 목록은 `domain-entities.md` § 5에 있다. V3·V5는 이 표에 줄을 더한다. 예: V5의 `gm_busy`.

### 6.2 클라이언트
- `http()`는 오류 본문의 `code`를 `HttpError.code`에 싣는다. 본문이 JSON이 아니면 `code`는 없다.
- `describeError(err, lang) → DescribedError`는 아래 순서로 고른다.
  1. `AbortError`는 오류가 아니다. 도우미가 이미 걸러 이 함수까지 오지 않는다.
  2. `HttpError`에 `code`가 있고 사전에 `error.<code>.title`이 있으면 그 문장과 `error.<code>.action`(할 일)을 쓴다.
  3. 없으면 상태 코드의 일반 문장(`error.status.<NNN>`, 없으면 `error.status.other`)을 쓴다.
  4. `fetch`가 던진 `TypeError`(서버에 닿지 못함)는 `error.network`다.
  5. 그 밖의 예외는 `error.unknown`이다.
- `raw`에는 접어 둘 원문을 담는다. 내용은 `상태 · code`와 `detail` 글(문자열이면 그대로, 객체면 `message` 칸, 없으면 JSON 한 줄, 300자에서 자름)이다.
- 지금 쓰는 `conflictKind`(문자열 매칭), `needsLlm`(문자열 매칭)은 `code`로 판단하게 바꾼다. 두 함수의 이름과 반환은 그대로 두고 안쪽만 바꾼다. 화면 코드는 고치지 않는다.

### 6.3 보이는 자리
| 상황 | 자리 | 프리미티브 |
|---|---|---|
| 첫 읽기 실패 | 그 영역 자리 | `StatusView state="error"`([다시 시도] + 자세히) |
| 쓰기 실패(버튼 하나) | 떠 있는 알림 | `toast({tone: "danger", …})` |
| 쓰기 실패(폼 안) | 폼 아래 한 줄 | `InlineError`(StatusView의 작은 꼴) |
| 대화상자 안 확인 뒤 실패 | 대화상자 안 | `ConfirmDialog error=` |

- **LLM 꺼짐 안내는 한 화면에 한 번만 보인다**(UX-08, BR-V2-20).
  - AppShell 아래 띠 하나로 보인다. 문장은 사용자 문장이고 `.env` 지시문을 쓰지 않는다. 지시문은 README와 운영 문서로 간다.
  - 띠의 문장은 모든 화면에서 하나다(`notice.llmOff`). **동작 변경**: 지금 플레이 화면은 자기 문장(`play.noLlm`)을, 다른 화면은 `llm.offNotice`를 쓴다. 이 둘이 `notice.llmOff` 하나로 바뀐다.
  - 화면 안의 버튼은 꺼지고 그 까닭을 `title`과 보조 글로 보인다. 같은 안내 띠를 다시 그리지 않는다.
  - GM 허브(`GmHub`) 안에서 그리던 안내는 없어진다. 띠는 그 위의 AppShell이 그린다.

## 7. 요청 도우미 (`hooks/`)

### 7.1 `useResource(key, load)`
```
key가 null ─────────────→ 멈춤(state "loading", 요청 없음)
key 바뀜/첫 마운트 ──→ 이전 요청 abort → state "loading"(data는 이전 값 유지)
     load(signal) 성공 ─→ 지금 key의 요청일 때만 data 반영, state "ready"
     load(signal) 실패 ─→ AbortError면 무시, 아니면 error = describeError, state "error"
reload() ──────────────→ 같은 key로 다시(이전 요청 abort)
언마운트 ───────────────→ abort, 늦은 답은 버림
```
- "지금 key의 요청인가"는 요청마다 붙인 번호로 판단한다. 늦게 도착한 옛 답이 새 답을 덮지 않는다(#14 꼴, RE-F02·F07·F14).
- 첫 읽기 동안 빈 상태를 보이지 않는다. `StatusView`가 `loading`이면 스켈레톤을 보인다(UX-10, FR-S5).
- `reload` 중에는 이전 data를 보인 채 둔다. 화면이 깜빡이지 않는다(UX-42 쪽 완화). 다시 읽는 범위를 줄이는 일은 화면 유닛이 한다.

### 7.2 `useAction(run, {onDone})`
- `busy`인 동안 다시 부르면 아무것도 하지 않고 `undefined`를 돌려준다. 같은 동작이 두 번 실행되지 않는다(#12 웹, FR-C13).
  - 가드는 **ref**(`useRef`의 진행 중 표시)로 한다. React 상태는 다음 렌더에야 바뀌므로, 같은 틱에 두 번 부르면 상태만으로는 둘 다 실행된다. 상태 `busy`는 보이기용이다.
- 끝나면 `onDone(result)`를 부른다. 화면은 여기서 필요한 읽기만 `reload()`한다.
- 실패하면 `error = describeError(e)`를 둔다. 화면은 `toast` 또는 `InlineError`로 보인다.
- 언마운트 뒤에 끝난 결과는 상태에 쓰지 않는다.

### 7.3 capabilities (RE-F09)
- 지금은 실패를 `null`로 저장하고 다시 읽지 않는다.
- 바꾼 뒤:
  - 실패하면 진행 중 표시(`pending`)를 비우고 실패 시각을 적는다. 답은 캐시하지 않는다.
  - 다음에 `useCapabilities`가 마운트될 때, 마지막 실패에서 30초가 지났으면 다시 읽는다. 30초 안이면 다시 읽지 않는다. 실패가 거듭될 때 요청이 몰리지 않게 하려는 것이다. 타이머는 두지 않는다.
  - 성공한 답은 페이지 수명 동안 쓴다.
  - "모름"은 지금처럼 아무것도 끄지 않는다(BR-U8-26 유지).

## 8. 지도 (`map/`)

### 8.1 좌표
- 저장 좌표는 지금처럼 0~1 정규화다(`Region.position`).
- SVG는 `viewBox="0 0 1000 625"`(8:5), `preserveAspectRatio="xMidYMid meet"`로 그린다. 너비는 컨테이너의 100%이고 고정 800×500이 아니다(FR-D6).
- 화면 좌표 → 정규화는 **그려진 영역 기준**으로 한다(UX 추정 §5.6).
  - `svg.getScreenCTM().inverse()`로 viewBox 좌표를 얻고 1000·625로 나눈다.
  - 순수 함수 `normalizeFromMatrix(point, inverse, viewBox)`로 떼어 둔다. jsdom에는 CTM이 없으므로 테스트는 이 순수 함수로 한다.
  - `toClient(norm, matrix, viewBox)`가 그 역이다. 둘은 왕복 속성을 가진다(PBT-02).
  - `getScreenCTM()`이 없거나 `null`이면(jsdom, 아직 그려지지 않음) svg의 `getBoundingClientRect()`와 viewBox로 `meet` 행렬을 계산한다. 축척은 `min(w/1000, h/625)`이고, 남는 쪽은 가운데 정렬 여백이다. 같은 순수 함수를 쓴다. 지금 테스트(editor.test 끌기)는 이 경로로 지금과 같은 값을 낸다.
- 빈 곳 누름(`onAddAt`)과 끌기(`onMove`)는 이 좌표를 쓴다. 지도가 줄어도 위치가 어긋나지 않는다.

### 8.2 단계 모양과 크기 (FR-D7, UX-18)
| 단계 | 표식 | 라벨 |
|---|---|---|
| 대륙 | 없음 | 큰 제목 글꼴, 자간 넓힘, `faint` |
| 지방 | 없음 | 중간 제목 글꼴, 자간 넓힘, `faint` |
| 마을 | 동그라미 r=8 | 본문 글꼴 12, 받침 위 |
| 구역 | 둥근 네모 12×12 | 본문 글꼴 11, 받침 위 |
| 지형 | 세모 14 | 본문 글꼴 11, 받침 위 |

(크기는 viewBox 단위다. 지도가 줄면 함께 준다.)

### 8.3 라벨과 표식 배치 (UX-18, UX-40)
- 라벨은 `map-plate` 받침(90% 불투명) 위에 그린다. 선이 지나가도 글이 읽힌다.
- 받침 너비는 순수 함수 `labelWidth(text, size)`로 어림한다. 한글·한자는 1.0em, 그 밖은 0.6em이다.
- 배치 후보는 아래 → 오른쪽 → 왼쪽 → 위 순서다. `placeLabels(points, labels, occupied)`는 각 라벨에 대해 이미 놓인 받침·표식과 겹치지 않는 첫 후보를 고른다. 모두 겹치면 아래에 놓는다.
- **처리 순서**는 입력 순서와 상관없이 정해진다. 그래서 같은 지도는 늘 같은 배치가 된다(속성 테스트 재현, PBT-08).
  1. 지금 위치 → 선택한 지역 → 갈 수 있는 지역 → 나머지
  2. 같은 무리 안에서는 y, x, id 순
- `occupied`에는 처음부터 모든 표식(점·말·고리)을 넣는다. 라벨은 어떤 표식도 덮지 않는다.
- 표식 자리는 고정이고 라벨 후보가 이를 피한다.
  - 지금 위치(플레이어) 말 모양은 점의 왼쪽 위(-14, -18)에 둔다.
  - 선택 고리는 점을 둘러싼다(r+6).
- 대륙·지방 라벨은 배치 대상이 아니고 자기 좌표에 그린다.

### 8.4 연결 모양 (`edgeStyle`)
| 종류 | 선 | 색 토큰 |
|---|---|---|
| 강 river | 실선, 굵게 | `map-river` |
| 길 route | 끊긴 선 7·5 | `map-path` |
| 바로 옆 adjacent | 가는 실선 | `map-path` |
| 막힘 blocked | 점선 1·5 + 가운데 × | `map-blocked` |

- 굵기는 `1.5 + weight × 3`(viewBox 단위), 불투명도는 `0.45 + weight × 0.55`다.
- 같은 두 지역 사이의 연결은 종류마다 한 번만 그린다(방향 둘을 하나로).

### 8.5 모드
- **edit**:
  - 지역 누르기는 선택이고 빈 곳 누르기는 `onAddAt`이다.
  - `draggable`일 때만 끌 수 있다. 누르고 움직이지 않고 떼면 옮기지 않는다(BR-U3-30 유지).
- **gm**:
  - 끌기가 없다(UX-36).
  - `overlay`가 지역마다 고리 색과 배지 받침("소문 2 · 사건 1")을 준다. 배지 문장과 범례는 V6가 정한다.
- **play**:
  - `focus = {id, neighbors}`가 있으면 viewBox를 그 지역과 이웃의 경계 상자 + 여백(12%)으로 좁힌다. [섬 전체 지도]가 이 줌을 끈다.
  - 갈 수 있는 곳은 강조 점선 고리를 두르고, 나머지 지역은 흐리게(45%) 그린다.

### 8.6 접근성
- `role="img"`와 `aria-label`로 지금 위치와 갈 수 있는 곳을 문장으로 알린다.
- 지역 표식은 `button` 역할 없이 둔다. 지도 키보드 조작은 범위 밖이다(§9). 대신 같은 동작이 화면의 목록(갈 수 있는 곳, 지역 목록)에 있다.

## 9. 배치 틀 (`layout/`)

- **AppShell**:
  - 머리띠(`chrome`)에 로고, 주 메뉴(월드·플레이·GM·에디터), 표시 언어 전환을 둔다.
  - 그 밑에 LLM 안내 띠가 하나 있고, 본문과 알림 자리(Toaster)가 이어진다.
  - 메뉴의 열림·잠김은 지금 `AppNav`와 같다(세션을 고르기 전 GM은 잠김, 까닭을 `title`로).
  - 640px 미만에서는 메뉴가 [메뉴] 버튼 뒤로 접히고, 언어 전환은 "한/EN" 한 버튼이 된다.
- **SplitView**(`main`, `aside`, `asideLabel`, `stackOrder`):
  - 1024px 이상에서는 2열이다. 옆 패널은 너비 320~420px(`clamp(320px, 32vw, 420px)`)이고 자체 스크롤을 가진다(높이 = 화면 높이 − 머리띠, `position: sticky`).
  - 1024px 미만에서는 1열이고 `stackOrder`로 순서를 정한다.
  - 가로 스크롤은 어느 폭에서도 생기지 않는다(BR-V2-17).
  - **폭 상한 값(요구사항 리뷰 R-05)**: 옆 패널 420px, 본문 최대 1240px, 좌우 여백은 24px(640px 미만 16px).
- **Section**: 제목·접기 버튼·행동 자리를 가진 묶음이다. 접힘 상태는 `aria-expanded`로 알린다.

## 10. 대화상자·알림·상태 하나로 (FR-D4, UX-11)

V2는 아래 셋의 **쓰는 곳을 직접 바꾼다**. 옛 컴포넌트(`Modal`, `Toast`, `NotificationCenter`)를 별칭으로 남기지 않고 V2에서 지운다. 옛 props와 새 props가 달라 별칭으로 맞출 수 없기 때문이다. 화면의 배치와 문구는 그대로 둔다.

- **대화상자**: `Dialog` 하나와 그 위의 `ConfirmDialog`로 바꾼다. 지금은 `Modal`, `MapCanvas` 안 대화상자, `BuildPanel`, `NewSessionForm`, `ConfirmDelete`, `WorldFileBar`, `DeedPanel`, `GmHub`, `DemoCard`의 아홉 곳이 제각각이다(요구사항 리뷰 R-01).
  - 포커스는 열릴 때 첫 조작으로 가고, 안에 갇혔다가, 닫히면 연 버튼으로 돌아온다.
  - Esc로 닫힌다. `aria-labelledby`로 제목을 이름으로 쓴다.
  - 확인 중(`busy`)에는 확인 버튼이 진행 표시를 보이고 다시 눌리지 않는다.
  - 옛 `Modal`의 props는 이렇게 옮긴다: `confirmTone` → `tone`("primary"는 "default"), `onConfirm`·`onCancel`·`busy`·`confirmLabel`·`cancelLabel`은 같은 이름, `children` → `body`.
- **알림**: `Toaster` 하나(AppShell에 둔다)와 `toast()` 함수로 바꾼다. 지금의 `NotificationCenter`(GmHub, PlayPage가 상태를 쥐는 제어 컴포넌트)와 `Toast` 카드를 대신한다. 두 화면은 자기 알림 목록 상태를 지우고 `toast()`를 부른다.
  - `aria-live="polite"`이고 위험 알림은 `role="alert"`이다.
  - 자동으로 6초 뒤 닫힌다. 위험 알림은 사람이 닫을 때까지 남는다.
  - **합치기(동작 변경)**: 지금은 알림마다 새 id(`n1`, `p2` …)를 받아 쌓인다. 바뀐 뒤에는 `key`가 같은 알림이 보이는 동안 다시 오면 새 알림을 쌓지 않는다. 대신 그 카드의 제목·본문을 새 것으로 **바꾸고** 6초를 다시 센다. `key`가 없으면 지금처럼 쌓인다.
    - 턴 알림의 key는 `turn:<region_id>`다. 같은 지역의 바뀜이 빠르게 이어지면 마지막 것만 보인다.
    - 지역이 아닌 알림도 종류로 key를 준다: `play:run`(턴 실패), `play:budget`(예산), `play:llm`(LLM 실패), `play:busy`(턴 진행 중). 같은 경고가 겹겹이 쌓이지 않는다.
    - 그 밖(사건 생성 등)은 key 없이 쌓인다.
  - testid는 지금 테스트가 쓰는 이름을 이어 받는다. 알림 자리는 `notification-center`, 카드는 `notif-<key 또는 id>`이고 `data-region`을 지금처럼 단다.
- **상태**: `StatusView`가 불러오는 중·비었음·오류·준비를 가른다. 스켈레톤, 빈 상태 문장, 오류 문장과 [다시 시도]와 자세히가 들어간다.
- **select**: `Select` 하나로 바꾼다. **[정정] Radix Select가 아니라 브라우저의 `<select>`에 토큰 모양을 입힌 것이다.**
  - 까닭 1: 휴대폰에서는 운영체제의 선택기가 가장 쓰기 쉽다.
  - 까닭 2: `color-scheme: dark`로 펼침 목록도 어둡게 그려진다.
  - 까닭 3: 지금 테스트 다섯 곳(`fireEvent.change`)이 그대로 동작한다.
  - 까닭 4: JS가 늘지 않는다.
  - 지금 `<select>`는 9개 파일에 13번 직접 쓰였고, 그 스타일을 복사한 곳이 18번이다(UX-11). `data-testid`는 안쪽 `<select>`로 넘긴다.
- **파일 입력**: `FileInput`으로 바꿔 브라우저 기본 문구를 숨긴다(UX-09). 숨긴 `<input type="file">`은 남고 `data-testid`는 그 input으로 넘긴다. 지금 테스트의 `fireEvent.change(…, {target: {files}})`가 그대로 동작한다.

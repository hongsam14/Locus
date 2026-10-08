# V6 GM 화면 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기에는 세 가지를 한다.
- 새 TRPG·판타지 디자인으로 화면을 다시 만든다.
- 결과가 틀리는 결함을 고친다.
- 시한이 있는 부채를 정리한다.

**지금 하는 것**: V6 Code Generation 2부 마무리. 승인된 계획(`construction/plans/V6-gm-screen-code-generation-plan.md`)대로 GM 화면을 다시 짰고, 그 결과를 적는다.

커밋(`feat/follow-up`, 푸시 안 함):

| 커밋 | 단계 | 내용 |
|---|---|---|
| `a6d82d7` | 1 | V6 FD 승인 기록, 코드 계획과 리뷰 둘 |
| `91de3fc` | 2 | 409 갈래(`conflictKind` + `isBusy`), 플레이 `gm_busy` 알림, `region_removed` 기록 줄, Select 묶음, Section 제어, 이름표 `reload`, 멈출 수 있는 `mapLimit` |
| `17818cb` | 3 | `useGmSession`, `useGmData`(자기 키 답만, `AFTER` 표, 덧씌우기), 일괄 생성의 실패 갈래와 멈춤, 세션 라벨, "새로" |
| `9ae93e6` | 4 | 새 부품: `GmHeader`·`ClosedBanner`·`MapPane`·`TurnTools`·`TurnBand`·`EventCard`·`EventForm`·`GmTabs`·`GmLayout` |
| `a4614f6` | 5 | 바꿔 끼우기: 기존 패널 새 계약, `RegionTab`, `GmSessionView`(key 경계, `gmWrite`), `GmPage` 다시 씀, `GmHub`·`ManualTurnPanel`·`useWorldState` 없앰, 옛 테스트 이전 |
| `0bf647c` | 6 | FR-D8 GM 검사와 소스 검사. 검사가 찾은 결함 하나(기록 줄의 원문 분류)를 고침 |
| `abe9135` | 7 | 캡처에서 찾음: 탭 코드가 첫 화면 JS로 들어가던 것 |
| `4723c5a` | 7 | 캡처에서 찾음: 행적 목격자 이름이 영어로 남던 것 |
| `a59d5c4` | 8 | 옛 허브만 쓰던 사전 키 27개(언어마다)를 지움 |
| `5404e3e` | 8 | code-summary, 진행 기록 |
| `7b9b616` | 리뷰 01 | 읽기와 쓰기(#2–#7, #23–#35) |
| `8f3212f` | 리뷰 01 | 초점·키보드·배치(#1, #8–#10, #13, #41–#44) |
| `75b9913` | 리뷰 01 | 문구(#11, #12, #36–#40, #45) |
| `cb9a0ef` | 리뷰 01 | 테스트 빈틈(#14–#22, #46–#50) |
| `c80dff9` | 리뷰 01 캡처 | 결과 띠의 지역 줄 문구(사건·굳음·새 소문) |

---

## 1. 기준선과 결과

| 항목 | 기준선(`a6d82d7`) | 끝 |
|---|---|---|
| vitest | 550(파일 30) | 613(파일 33), 코드 리뷰 01 뒤 **664**(파일 34) |
| tsc | 통과 | 통과 |
| pytest | 1138 | 1138(백엔드 바뀌지 않음) |
| npm audit --omit=dev | 0 | 0 |
| 첫 화면 JS gzip | 114.83 kB | 117.01 kB, 코드 리뷰 01 뒤 **117.19 kB**(+2.36, 새 사전 문구) |
| GM 청크 gzip | 6.81 kB(+ SessionBar 청크 1.21) | 15.94 kB(탭 코드 포함), 코드 리뷰 01 뒤 17.05 kB |
| GM 390px 가로 스크롤 | 있음(역공학 기록) | 없음 — 캡처 12장 모두 `scrollWidth == clientWidth`(1280·768·390) |
| GM 1280 페이지 높이 | 약 2,130px, 오른쪽 열이 지도 아래로 떨어짐 | 1,109px([지역] 탭), 지도와 패널이 나란히 |

- **캡처**: 비공개 Artifact https://claude.ai/artifact/BSMSgKWcYavigSp9jvtH1B (2판: 코드 리뷰 01 뒤, 12장 모두 가로 스크롤 없음)
  - 12장: [지역] 세 폭과 1280 한 화면, 턴 뒤 결과 띠 + 기록, 사건, 씨앗, 행적, 끝내기 확인, 끝난 세션
  - 잰 값, 찍으며 고친 것, 봐 주실 것을 함께 실었다.
- 캡처 도구는 세션 스크래치(`v6/cap/`)에 있고 저장소에는 없다. 빌드도 스크래치 출력이다.

## 2. 파일

- **새로**(`web/src/features/gm/`)
  - `useGmSession.ts`, `useGmData.ts`, `sessionLabel.ts`, `newLines.ts`
  - `GmHeader.tsx`(`ClosedBanner` 포함), `MapPane.tsx`(`badgeOf`), `TurnTools.tsx`, `TurnBand.tsx`(`outcomeOf`), `EventCard.tsx`, `EventForm.tsx`, `GmTabs.tsx`, `GmLayout.tsx`
  - `RegionTab.tsx`, `GmSessionView.tsx`
- **바뀜**
  - `routes/GmPage.tsx`(다시 씀)
  - `features/gm/{PlayerStrip,DistortionPanel,RumorPanel,RegionKnowledgePanel,EventPanel,SeedPanel,TimelinePanel,DeedPanel,WorldStateOverlay,useBulkRumors,bulk}`
  - `api/http.ts`, `hooks/{useTurnRun,useWorldNames}.ts`, `ui/{Select.tsx,index.ts}`, `layout/Section.tsx`, `i18n/{index,ko,en}.ts`
- **없앰**: `features/gm/GmHub.tsx`, `features/gm/ManualTurnPanel.tsx`, `useWorldState`와 겹침 토글 컴포넌트
- **남김**: `SessionBar.tsx` — 에디터 `WorldFileBar`의 세션 시작이 쓴다(코드 계획 리뷰 01 R-01)
- **테스트**
  - 새로: `gm.data.test.tsx`(31), `gm.parts.test.tsx`(21), `gm.layout.test.tsx`(17)
  - 고침: `components`, `deeds`, `design.grep`, `fr-d8`, `gm`, `layout`, `play.turn`, `ui.primitives`, `errors.describe.prop`, `i18n.style`

## 3. 규칙 → 확인

| 규칙 | 확인 |
|---|---|
| BR-V6-01 390·768 가로 스크롤 없음 | 캡처 12장 잰 값(§ 1) |
| BR-V6-02 넓음 2열, 그 밖 1열 | `gm.layout` TP-V6-1(실제 화면, `matchMedia` 대역), `gm.parts` GmLayout, 캡처 |
| BR-V6-03 한 폭에 한 번 | `gm.layout` TP-V6-1 |
| BR-V6-04 탭 다섯, 턴 도구는 탭 밖 | `gm.parts` GmTabs, `gm.layout` TP-V6-1 |
| BR-V6-05 지역을 고르는 세 길 | `gm.layout` TP-V6-2 |
| BR-V6-06 턴 한 번 | `gm.layout` TP-V6-3, `gm.parts` TurnTools |
| BR-V6-07 결과 띠 한 곳, 턴 알림 없음 | `gm.layout` TP-V6-3, `gm.parts` TurnBand |
| BR-V6-08 "새로" | `gm.layout` TP-V6-3, `gm.data` R-07 |
| BR-V6-09 쓰기 한 번에 하나 | `gm.layout` TP-V6-5(씨앗·승인·사건 만들기·세션 끝내기), `gm.parts` EventCard·GmHeader |
| BR-V6-10 쓴 것만 다시 읽기, 깜빡임 없음 | `gm.data` TP-V6-4(14종 매개변수), `gm.test` #13·C1 |
| BR-V6-11 슬라이더 라벨이 끄는 값을 따라감 | `gm.test` #8, `gm.layout`(공신력) |
| BR-V6-12 끝난 세션 | `gm.layout` TP-V6-10, `gm.test` U7 #11·#11(page) |
| BR-V6-13 확인이 필요한 쓰기 | `gm.parts` GmHeader·TurnTools, `deeds` |
| BR-V6-14 사건 폼 | `gm.parts` EventForm, `gm.test` LLM-off |
| BR-V6-15/16 옛 세션 답 없음 | `gm.layout` TP-V6-6(세 경우), `gm.data` TP-V6-6, `gm.test` S14 |
| BR-V6-17 세션을 바꾸면 일괄이 멈춤 | `gm.data` TP-V6-7 |
| BR-V6-18 다시 시도 | `gm.layout` TP-V6-8, `gm.data` TP-V6-8, `components` 라우팅 |
| BR-V6-19 `describeError`, `String(e)` 없음 | `design.grep`, `gm.test` 씨앗 409 |
| BR-V6-20 409 갈래, 플레이 `gm_busy` | `errors.describe.prop`, `play.turn`, `deeds`, `gm.test` #11 |
| BR-V6-21 `rumor_inactive` 뒤 다시 읽기 | `gm.layout` |
| BR-V6-22 일괄 503 | `gm.data` TP-V6-7 |
| BR-V6-23 LLM 안내 한 번 | `gm.test` LLM-off, `gm.parts` TurnTools |
| BR-V6-24/25 원문 enum·뜻 없는 숫자 없음 | `fr-d8` TP-V6-12, `design.grep` |
| BR-V6-26 세션 고르기 라벨 | `gm.data`(sessionLabel), `gm.parts` GmHeader |
| BR-V6-27 배지·범례 | `gm.parts` MapPane, 캡처 |
| BR-V6-28 "없던 일로 하기" | `deeds` |
| BR-V6-29 `region_removed` 줄 | `gm.test` V6 shared base |
| BR-V6-30 사전 키 일치 | 기존 키 일치·문체 테스트 |
| BR-V6-31 지도 끌기 없음 | `gm.parts` MapPane |
| BR-V6-32 상태는 늘 읽음 | `gm.layout` |
| BR-V6-33 상태 처리 | `gm.data`, `gm.layout`, 부품 StatusView |
| BR-V6-34 접근성 | `gm.parts`(탭 화살표 키, `role="status"`, `aria-disabled`, 라벨), `deeds`(대화상자) |
| BR-V6-35 기록 20줄 + 더 보기, 최신부터 | `gm.layout` TP-V6-3 |

- **돌연변이 확인**(넣고 돌린 뒤 복원): 28개를 넣었고 끝에는 모두 테스트가 잡았다.
  - 훅 7
  - 부품 8
  - 화면 8. 처음에는 2개를 놓쳤다. key 경계와 기록 순서다. 시험을 보강한 뒤 다시 넣어 잡았다.
  - 표기 5

- **코드 리뷰 01**(record `code/reviews/code-review-01.md`): 재현된 지적은 `gm.review.test.tsx`(42)에 고친 동작으로 단언했다. 고친 것에 돌연변이 26개를 넣었고 24개를 잡았다. 놓친 둘은 대화상자 초점 보호다(§ 6).

## 4. 고친 기존 테스트 (TP-V6-17, 의도한 변경)

| 파일 | 수 | 왜 / 어디로 |
|---|---|---|
| `components.test.tsx` | 28 → 15 | `GmHub` 묶음 13개를 `gm.layout`·`gm.parts`로 옮겼다. 단언한 동작(소문·굳음 배지·생성, 턴, 끝난 세션 끔, 사건 만들기·제안·승인·버리기·해소, 지역 왜곡, 빈 지역 일괄, 다시 만들기 확인, 원문 토글, 기록 문장)은 모두 남았다. 지역별 턴 알림은 결과 띠(Q2=A)로, `listDistortions` 읽기는 상태 읽기로 바뀌었다. 라우팅 두 개는 `session-panel` 대신 `turn-tools`를 본다. 스코프 배지는 원문 `direct` 대신 라벨이다 |
| `gm.test.tsx` | 35 → 34 → 36 | (코드 리뷰 01 #22: V6 바꿔 끼우기에서 실수로 지운 "PlayPage after U7" 두 테스트를 되살렸다. 처음 적은 "35 → 34"는 그 −2를 가리고 있었다.) GM 테스트를 실제 화면(`GmPage`) 위에서 돌린다. 겹침 토글 테스트 하나는 `MapPane`(`gm.parts`)과 BR-V6-32(`gm.layout`)로 옮겼다. 플레이어 띠는 말로 보인다. 씨앗 분류는 라벨이다. 409 줄은 `describeError` 문장이다. `llm-required` 줄 대신 AppShell 안내 하나다. 무효화 거절은 대화상자 안이다. 503은 `llm_unavailable` 코드 문장이다 |
| `deeds.test.tsx` | 10 → 12 | `DeedPanel`이 화면의 읽기·쓰기를 받는다. 거절은 안내 줄 대신 대화상자 안이다. slant는 "보는 눈: …"이다. 목격자 이름은 이름표로 찾는다 |
| `errors.describe.prop.test.ts` | 같음 | `turn_running` → `"turn_running"`(전에는 `"busy"`). 새 갈래 단언을 더했다 |
| `ui.primitives.test.tsx` | 21 → 22 | Tabs를 `../ui/Tabs`에서 가져온다(§ 5의 6). Select 묶음을 더했다 |
| `i18n.style.test.ts` | 같음 | `confirm.regen`·`confirm.regenAll` legacy 두 줄을 새 키(문체 규칙 안)로 바꿔 목록을 비웠다 |

## 5. 이탈

1. **slant는 enum이 아니다**(코드 계획 § 1.1 R-01).
   - 상위 `component-methods.md` § 1.4의 `EnumKind`에는 slant가 있다.
   - 코드(V2 결정과 `format.enums.test`)를 따랐다. 판단 줄에 "보는 눈: <원문>"으로 보인다.
2. **상태 소유**(R-02): 소유 표가 FD frontend-components § 5.2의 "`GmPage`가 `selected`와 `tab`을 가진다"를 대신한다.
   - `tab`은 세션 안(key 안)에 있다. 지역은 세션 밖에 있다.
   - 지도는 key 안에 그리되, 월드 자료는 밖에서 받는다.
3. **1열의 결과 띠 지역 이름**(R-08): 누르면 탭 영역을 화면에 보이고 [지역] 탭에 초점을 둔다. BLM § 7의 "스크롤하지 않음"을 이 경우에 한해 대신한다.
4. **FD의 틀린 전제**(코드 계획 리뷰 01 R-01)
   - BLM § 1.5와 frontend-components § 5는 "에디터에는 세션 띠가 없다"고 보고 `SessionBar`를 없앤다고 했다. 에디터의 세션 시작이 쓰고 있어 남겼다.
   - [플레이어 없는 새 세션]을 GM에 두는 결정은 그대로다. "GM이 유일한 곳"이라는 까닭만 틀렸다.
5. **사전 키 앞부분**: 계획 § 1.2는 새 GM 문구에 `gm.*`를 쓴다고 했다. 실제로는 V2 문체 규칙(BR-V2-10)의 앞부분을 썼다: `action`·`notice`·`confirm`·`empty`·`label`·`tab`·`progress`. 그래서 `i18n.style`이 새 줄의 문체를 검사한다. `session.end`는 계획대로다.
6. **공용 UI 묶음 파일에서 Tabs를 뺐다**(`ui/index.ts`).
   - 다시 내보내기 때문에 Radix 탭 코드(gzip 약 4.5 kB)가 첫 화면 JS로 들어갔다.
   - Tabs는 GM만 쓰므로 `ui/Tabs`에서 바로 가져온다. 까닭은 파일에 주석으로 적었다.
7. **다시 만들기의 거절**: BLM § 6은 확인 대화상자의 쓰기(세션 끝내기, 행적 무효화, 다시 만들기)가 거절을 대화상자 안에 보인다고 했다.
   - 이 지역·모든 지역 다시 만들기는 확인을 누르면 대화상자가 닫히고 실행된다. 일괄은 진행 막대가 있는 긴 일이다. 그래서 거절은 쓰기 오류 줄에 나온다.
   - 세션 끝내기와 행적 무효화는 대화상자 안에 나온다.
8. **플레이어 띠의 지역 이름**: `nameOf` 대신 `regionName` 함수를 받는다. 이름표가 없을 때 id가 아니라 월드의 영어 이름을 보이려는 것이다(5단계에서 테스트가 찾음).
9. **기록 줄의 분류**: GM [기록]은 사건 줄의 `category`를 라벨로 바꿔 보인다(6단계 FR-D8 검사가 찾음). 플레이 여정 기록은 이 줄을 보이지 않아 바꾸지 않았다.
10. **지역 지식 패널**: `Panel` 겉틀을 없애고 접힘 안에 들어갔다. 빈 문장은 `empty.knowledge`다.
11. **옛 사전 키를 지금 지웠다**: 계획 밖의 정리다. 옛 허브만 쓰던 키 27개는 읽는 곳도 테스트도 없어, V9로 넘기지 않고 지웠다(첫 화면 −0.58 kB).

12. **코드 리뷰 01에서 공유 바탕을 고쳤다**(V2·V4 것)
    - `ui/Dialog`: 화면이 이미 옮긴 초점은 되돌리지 않는다. 꺼진 opener에도 주지 않는다.
    - `map/WorldMap`: 바탕 그림 alt를 비웠다(장식). `ui/LocalizedText`와 `ui/FileInput` 파일 이름이 줄을 바꾼다.
    - 사전: `enum.sessionStatus.closed` "끝남", `error.session_closed` "끝났어요", `llm.required` "AI 키가 있어야 해요", `unit.turnAt` en "Turn {n}", `notif.*`(결과 띠의 지역 줄)는 사건·굳음·새 소문으로 바꿨다. 플레이 화면에도 같은 말로 보인다.
13. **수명 라벨은 V2 것을 그대로 둔다**(코드 리뷰 01 #44): FD § 4.3의 "수명 / 한 번 일어남 / 이어짐" 대신 V2 enum 라벨 "지속 방식 / 한 번 / …"이다. 다른 화면과 같은 말을 쓴다.
14. **턴 결과 문장**: 결과 띠는 "N턴째가 되었어요"다. 답의 `turn`은 진행 뒤의 지금 턴이라, FD의 "N턴이 지났어요"는 한 턴씩 어긋나 있었다(코드 리뷰 01 #45).

## 6. 알려진 제약

- 쓰기마다 `getTimeline`이 기록 전부를 읽는다. 서버가 쪽 나누기를 하지 않는다. 줄이 수천이면 느려진다.
- "새로"는 진행 직전에 없던 줄이다. 그 사이 플레이어 쪽이 쓴 줄도 들어갈 수 있다.
- 플레이어 띠는 진행 중 턴을 폴링하지 않는다. [다시 확인]으로 읽고, 겹친 쓰기는 서버 409가 막는다.
- 세션을 바꾸면 일괄 생성은 남은 지역을 보내지 않는다. 다만 이미 보낸 요청은 끊지 않는다(api가 `signal`을 받지 않음).
- 다음 세션을 읽는 동안에는 직전 월드의 지도를 보인다. 다른 월드의 세션이면 세션이 온 뒤에 바뀐다.
- 지도의 키보드 조작은 범위 밖이다(FR-S6).
- 이름표 읽기가 실패하면 알리지 않고 영어로 보인다(R-10).
- 대화상자 초점 보호 둘(Dialog가 화면이 옮긴 초점을 지킴, 화면이 대화상자가 닫힌 뒤에 초점을 옮김)은 jsdom이 Radix의 초점 가둠과 타이밍을 흉내 내지 못해 시험으로 잡히지 않는다. 화면 쪽은 초점이 실제로 옮겨졌는지 보고 나서야 멈춘다.
- [기록]의 분류 라벨 대상은 `ENUM_VALUES`에서 읽는다. 이 목록은 `format.enums.backend.test`가 백엔드와 맞춘다(코드 리뷰 01 #49).
- 캡처에서 본 것(봐 주실 것)
  - 세션 고르기 라벨이 날짜까지 길어 끝이 잘린다.
  - 390에서 탭 줄이 다섯 번째에서 줄을 바꾼다.
  - 판단의 "보는 눈"은 영어 원문이다.

## 7. 넘기는 것

- **V8(에디터)**
  - 월드 교체 경고 "session … was busy and could not be closed"의 사람 말 문장(V5 이월, `api/routers/world.py:174`). 보이는 곳은 에디터 빌드 보고서와 홈 `DemoCard`다(코드 계획 § 1.1 R-09).
  - `SessionBar`의 `variant="full"`(닫기·상태)은 이제 쓰는 곳이 없다. 에디터 세션 띠 배치와 함께 정리한다.
  - `MapOverlay` 어댑터 없애기(계획대로).
- **V9(부채·문서)**
  - `next-cycle.md`에 서버 기록 쪽 나누기를 올린다.
  - `i18n.style.test`의 주석은 "timeline.* with GM (V6)"라고 해서 GM 기록 줄을 이야기 문체(해라체)로 옮기라는 뜻을 담고 있다. V6 FD와 계획은 이것을 받지 않았다. 지금 기록 줄은 이름씨 꼴("소문 승격 · 솔트웨이크 항구")과 해라체가 섞여 있다. 옮길지 V9에서 정하거나 `next-cycle.md`에 적는다.
  - CLAUDE.md Status에 V6를 반영한다.
- **Build and Test**: 사람이 캡처를 확인한다. 실제 스택에서 GM 흐름을 한 번 돈다(턴, 사건, 세션 끝내기).

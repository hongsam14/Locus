# V4 홈·플레이 화면 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V4 코드 생성을 마쳤다(Step 1~10). 홈은 데모 카드가 데모 월드를 맡고 "내 월드"가 나머지를 보인다. 플레이는 넓음 2열, 중간 1열, 좁음 1열 + 아래 고정 행동 띠다. 턴 결과는 결과 띠 한 곳에 나오고, 대화는 넓으면 열 안, 그 밖에는 전체 시트다. 이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음 유닛에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V4-home-play-code-generation-plan.md`(10단계, 승인 2026-10-07; 〔실행 메모〕 § 1.1 R-11, § 1.2, § 1.3 R-11·R-12 포함). 단계마다의 실행 기록은 플랜의 각 Step 끝에 있다.

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2) | 결과 (Step 10, `2086092`) |
|---|---|---|
| vitest | 424 + skip 1 | **518**, skip 0. 시드 둘(무작위 두 번)로 GREEN |
| tsc | clean | clean |
| pytest | 1048 | **1048**. V4는 파이썬을 바꾸지 않았다(`git diff b7db475..HEAD -- '*.py'` 비어 있음) |
| ruff · black | clean | clean |
| mypy (`locus api`) | 11 | 11 |
| `npm audit --omit=dev` | 0 | 0 |
| JS gzip(vite 값) | 119.87 kB, 한 덩어리 | 첫 화면(홈·플레이) **113.33 kB**. 에디터 9.5 kB·GM 6.9 kB·SessionBar 1.2 kB는 열 때 받는다 |
| JS gzip(`gzip -c \| wc -c` 합, NFR-4 측정법) | — | 첫 화면 112,255 B, 전체 129,879 B(덩어리 4개) |
| 390px 가로 스크롤 | 홈 0, 플레이 대화 418(V2 캡처) | 18장 모두 `scrollWidth == clientWidth`(1280·768·390) |

- **JS 예산**: 한 덩어리로는 127.6 kB라 V2 예산 125.6 kB를 넘었다. V2 NFR-4 § 2의 처방("넘으면 `GmPage`·`EditorPage`를 `React.lazy`로 나눠 홈·플레이가 받는 JS를 예산 안에 둔다. 합계와 첫 화면 JS를 함께 적는다")대로 나눴다(`2086092`). 사유는 V4가 더한 훅·부품·사전 키(+7.8 kB)다.
- **캡처**: 비공개 Artifact https://claude.ai/artifact/2J77c8EciUacCd1Cv4FHGP (홈 5장, 플레이 13장, 잰 값, 고친 것, 봐 주실 것).

## 2. 바꾼 파일과 만든 파일

| 파일 | 상태 | 내용 | 커밋 |
|---|---|---|---|
| `web/src/hooks/useMedia.ts` | 새 | `matchMedia` 구독, `WIDE`·`NARROW` | `d7e8318` |
| `web/src/ui/Dialog.tsx` | 바뀜 | `variant: center·sheet·full`, `data-variant` | `d7e8318` |
| `web/src/ui/Button.tsx` | 바뀜 | `busy` → `aria-disabled` + 누름 무시. 호출자의 `aria-disabled`와 합친다 | `d7e8318`, `231b136` |
| `web/src/layout/AppShell.tsx` | 바뀜 | 월드 없는 "에디터"는 `Link`(활성 아님), `hint.gmLocked` | `6565326` |
| `web/src/hooks/{usePlaySession,useTurnRun,useWorldNames}.ts` | 새 | 세션·지역·기록 읽기(다른 세션 data 버림), 행동→폴링(상한·느림·다시 확인·재진입·거절 `refusal`), 이름표(월드 가드), `useHeldRereads` | `7fed45f`, `231b136` |
| `web/src/types.ts` | 바뀜 | `RegionView.gm_busy?` | `7fed45f` |
| `web/src/features/home/{HomeHero,MyWorlds,WorldRow,sessions}.ts(x)` | 새 | 머리글, 내 월드(데모 뺌, 중립 배지, 누를 때 세션 읽기), 열린 세션 최근순 | `bf77030`, `9cbc9c8` |
| `web/src/features/home/{DemoCards,DemoCard}.tsx` | 바뀜 | 카드 상태 new·loaded·resume·세션 읽기 중·실패, [데모 다시 불러오기], 409 질문 경로, `*_ko`, 지역 수·시작 지역 이름 | `bf77030` |
| `web/src/routes/HomePage.tsx` | 다시 씀 | 조립, 두 목록 `[…, lang]` 키, 빌드·불러오기 뒤 다시 읽기, `keep-all` | `bf77030`, `9cbc9c8` |
| `web/src/features/play/NewSessionForm.tsx` | 바뀜 | `worldId`가 바뀌면 지역 선택을 비운다(RE-F03) | `bf77030` |
| `web/src/features/editor/BuildPanel.tsx` | 한 줄 | 월드 id 안내(`hint.worldIdChars`) | `bf77030` |
| `web/src/features/play/{PlayHeader,ResultBand,PlayMap,ActionDock,TalkSheet,MoreList,names,PlayLayout}.ts(x)` | 새 | 머리(경로·닫힘 띠·GM 작업 중), 결과 띠, 보기 전용 지도, 휴대폰 행동 띠와 두 시트, 대화 시트, 더 보기 목록, 이름표 도우미, 폭별 배치 | `4be9a24`, `231b136` |
| `web/src/features/play/RegionScene.tsx` | 바뀜 | `SceneText`·`PeopleHere`·`KnownHere`(말 단계 배지, "당신 이야기", 휴대폰 3개). 옛 한 패널은 지움 | `4be9a24`, `231b136` |
| `web/src/features/play/{ActionBar,MovePanel,NpcList,PlayLog,DialoguePanel}.tsx` | 바뀜 | `TurnStatus`·`DeclareForm`·`lockedProps`(라벨, 초점 고리, 턴 중 `aria-disabled`), 막힌 줄 이유·강조, 이름표·[말 걸기] 꺼짐 이유, 기록 이름·턴 단어·5줄, 대화 `bare`·줄 바꿈·`describeError` | `4be9a24`, `231b136`, `9cbc9c8` |
| `web/src/features/play/NarrationCard.tsx` | 지움 | 선언 문장은 결과 띠 안 `narration-card` | `231b136` |
| `web/src/routes/PlayPage.tsx` | 다시 씀 | 조립, 세션마다 새 화면(`key`), 대화 열림(R-11), 빈 `/play`, 오류, `keep-all` | `231b136`, `9cbc9c8` |
| `web/src/map/WorldMap.tsx` | 바뀜 | play 모드의 바탕 그림은 svg 안 `<image>`(확대를 따름). edit·gm은 그대로 | `4be9a24` |
| `web/src/App.tsx` | 바뀜 | `EditorPage`·`GmPage` 지연 적재 | `2086092` |
| `web/src/i18n/{ko,en}.ts` | 바뀜 | 새 키 37개, `nav.gmLocked` → `hint.gmLocked`, `log.*` 마침표, `home.buildFromSources` 문구. 안 쓰는 키 17개 지움(`home.title`·`home.openSessions`·`npc.talk`·`play.*` 14) | 여러 커밋 |
| 테스트 | 새 5 / 바뀜 10 | § 4 | 여러 커밋 |

## 3. BR·TP 대응

| 규칙 | 확인 |
|---|---|
| BR-V4-01 390·768 가로 스크롤 없음 | 캡처 18장 잰 값(§ 1) |
| BR-V4-02 넓음 2열, 그 밖 1열 | `play.layout`(wide: 지도·이동이 `aside` 안), 캡처 |
| BR-V4-03 주 행동이 닿는 자리 | `play.layout`(narrow: 띠·시트, middle: 행동 상자), 캡처 |
| BR-V4-04 결과 한 곳 | `play.layout` TP-V4-5, `play.test` EX-7, `play.turn` |
| BR-V4-05 데모 한 번, 카드 상태 | `home.cards` TP-V4-1, `home.test` |
| BR-V4-06 열린 세션 중립 배지 | `home.cards`, `home.test`(클래스에 `danger` 없음) |
| BR-V4-07 [자료로 새 월드 만들기] 하나, 안내, 빌드 뒤 다시 읽기 | `home.test` TP-V4-3 |
| BR-V4-08 새 세션 폼 지역 비움 | `home.test` TP-V4-4 |
| BR-V4-09 홈에서 "에디터" 활성 아님 | `layout.test`(`6565326`) |
| BR-V4-10 원문 enum·소수 없음 | `fr-d8` TP-V4-14, `design.grep` TP-V4-12, `play.parts` |
| BR-V4-11 이름표와 대체 | `play.parts` TP-V4-6, `play.turn`(월드 가드) |
| BR-V4-12 홈 목록 언어 | `home.cards` TP-V4-2(fetch 대역의 `?lang=`) |
| BR-V4-13 막힌 줄 이유 | `play.parts` TP-V4-7, `play.test` EX-13 |
| BR-V4-14 지도 보기 전용 | `play.parts` TP-V4-7, `play.layout`(좁음: 이동 시트가 그 줄로 열림) |
| BR-V4-15 스켈레톤·오류 문장·`String(e)` 없음 | `home.test` TP-V4-3, `play.turn`, `design.grep` |
| BR-V4-16 다른 세션 data 없음 | `play.turn` TP-V4-10, `play.layout` TP-V4-10 |
| BR-V4-17 폴링 상한·느림·다시 확인 | `play.turn` TP-V4-9, `play.parts`(`TurnStatus`), `play.test` #15 |
| BR-V4-18 닫힌 세션·빈 `/play` | `play.layout` TP-V4-11, `play.parts` |
| BR-V4-19 `gm_busy`·다시 읽기 1초 × 5 | `play.layout`(GM 작업 중), `play.turn`(`useHeldRereads`), `play.test` S02 |
| BR-V4-20 GM은 메뉴로만 | `gm.test`(메뉴 `nav-gm`, `play-gm-btn` 없음) |
| BR-V4-21 대화 열림(폭별, 기록 칸) | `play.layout` TP-V4-8 + R-11 블록 |
| BR-V4-22 [대화 끝내기] 결과는 띠, 이동하면 닫힘 | `play.layout`, `dialogue.test` |
| BR-V4-23 라벨·초점 고리·시트 이름·`role=status` | `play.parts` TP-V4-13 |
| BR-V4-24 바쁜 버튼 `aria-disabled` | `ui.primitives`, `play.parts`(턴 중 초점 유지, `busy`와 호출자 값 합침) |
| BR-V4-25 testid 하나 | `play.layout`(`atMostOnce`, 세 폭) |
| BR-V4-26 Dialog 세 변형 | `ui.primitives`(`d7e8318`) |

## 4. 테스트 변경 (TP-V4-15)

- **더한 테스트 94개**(424 → 518)
  - 새 파일 5개에 78개: `play.turn`(11), `home.cards`(13), `play.parts`(24), `play.layout`(18), `fr-d8`(12)
  - 바뀐 파일에 7개: `home.test` TP-V4-3·4 여섯, `design.grep` 하나
  - Step 2·3에 9개: `hooks`(`useMedia`), `ui.primitives`(Dialog 변형, 바쁜 submit), `layout`(에디터 활성 아님)
- **고친 기존 단언(의도한 변경)**
  - frontend-components § 7.1 표: `home.test` 4개(EX-2, held-world, EX-13, 목록 배지)와 표 밖 2개(데모 줄 없음, 데모 목록 오류 문장), `play.test` EX-7(결과 띠).
  - § 7.1 표 밖, FD를 따른 변경
    - `play.test` 6개: EX-13(경로에 자기 지역 없음, 소문은 단어, 막힌 줄 이유와 버튼 없음), #15(`turn-error`), S02 둘·#5(b)·#7(`aria-disabled`), 계속 잡힘 7 → 6번
    - `deeds.test` 2개: 거절은 `action-error`, `KnownHere`와 "당신 이야기"
    - `dialogue.test` 1개: `people-here`
    - `gm.test` 1개: R-11, 메뉴 `nav-gm`
  - **Button busy 단언**(BR-V4-24, `d7e8318`): `gm.test` #13/C1의 `toBeDisabled` → `aria-disabled` 1곳, `ui.primitives`의 바쁜 버튼 단언 1곳.
- **대역 위생**: `home.test`·`play.test`는 매 테스트 전 api 대역을 `mockReset`한다. 실패한 테스트가 남긴 `…Once` 답이 다음 테스트로 새어 연쇄 실패하던 것을 막는다.
- **돌연변이 확인**: 단계마다 지킴 장치를 하나씩 빼 해당 테스트가 실패하는지 봤다. 모두 실패했다. 하나는 레이아웃이 실제 지킴이라 레이아웃 쪽으로 옮겨 확인했다. 단계별 목록은 플랜 실행 기록에 있다.

## 5. 이탈

| 무엇 | 왜 | 어디 |
|---|---|---|
| V4 FD 계획(`988aca9`)을 승인 전에 커밋했다 | 실수. 사람에게 알렸다 | Step 1 전 |
| Hero 머리글이 display 대신 heading 글꼴 | V2 규칙 "display는 로고만"(`design.grep`)이 FD보다 앞선다 | Step 5 |
| [데모 다시 불러오기]는 홈에 남는다. 409 [새로]·시작 지역 없음의 버튼만 불러온 뒤 플레이로 | 버튼 문구("새로 불러와 플레이")와 맞춘다 | Step 5 |
| 월드 id 안내가 권하는 말 | 서버가 데모 말고는 id 문자를 막지 않는다 | Step 5 |
| 사전 키 4개를 계획 밖에서 더함(`label.yourStory`, `action.talk`, `empty.noSession`, `hint.startFromDemo`) | GM의 `badge.deed`와 나눔, FD 문구 "말 걸기", 빈 `/play` 문장 | Step 6·7 |
| 선언 입력의 옛 `maxLength = 상한×2`를 없앰 | `Textarea`의 `maxLength`는 자체 글자 수를 보여 서버식 글자 수와 겹친다. 막음은 빨간 글자 수와 꺼지는 버튼 | Step 6 |
| `useTurnRun.refusal`을 더함 | 거절과 확인 실패가 한 칸이면 400 뒤 [다시 확인]이 지난 run을 다시 폴링할 수 있었다 | Step 7 |
| 턴 중 행동 버튼을 `aria-disabled`로(FD § 3.3), 기존 단언을 바꿈 | 초점 유지(BR-V4-24). 닫힌 세션은 native `disabled` 그대로 | Step 7 |
| 소수 검사 식을 강화 | FD의 `\b0\.\d+\b`는 "d0.42"(옛 배지)를 놓친다 | Step 8 |
| 지도 바탕 시험을 `map.worldmap` 대신 `play.parts`에 둠 | TP-V4-7 묶음에 함께 | Step 6 |
| 캡처 빌드를 저장소 `web/dist`에 한 번 함 | NFR-4 측정법은 스크래치 출력이다. `dist/`는 git이 무시하는 산출물이라 저장소 변경은 없다. 크기는 스크래치 빌드로 다시 쟀다 | Step 9 |
| JS 지연 적재(`App.tsx`) | V2 NFR-4의 "넘으면" 처방 | Step 10 |

## 6. 알려진 한계

- **작은 지도**: FD대로 "지금 위치 + 이웃"에 맞춰 확대한다. 이웃이 섬 전체에 퍼진 곳(앰버메도)은 거의 전체 지도가 되고, 360px 열에서 지명 글자가 작다. 바탕 그림은 GM·에디터에서도 로컬 파일로만 고르므로 플레이에는 아직 없다. 범례도 없다(사전 키 목록에 없었다).
- **옛 문장의 말투**: `play.hearsayHint`(합니다체), `play.declarePlaceholder`("무엇을 하시겠습니까?"), 결과 띠의 `notif.*`("1건 신규 소문", GM 말투), `dialogue.end`("대화 끝내기 (1턴)" 괄호). 계획 § 1.2대로 문장이 바뀌는 키만 옮겼다.
- **키 없을 때 [말 걸기] 꺼짐**: FD BLM § 2.5 결정이다. 예전 BR-U5-29("키 없이도 지난 대화는 열린다")와 어긋나며, 키 없이 데모를 하는 사람은 지난 대화를 볼 수 없다. 사람에게 알렸다.
- **잡힌 세션 다시 읽기**: 마운트 직후의 "낡은 표시 확인" 읽기가 1초 간격 첫 회로 합쳐졌다. 낡은 표시가 풀리는 데 최대 1초 더 걸린다.
- **넓은 홈의 데모 카드 한 장**: 두 칸 격자의 한 칸이다(FD "카드 2열", 데모 하나).
- **영어 표시**: 이름표는 번역된 칸만 실으므로 영어에서는 데모 카드의 "시작 …" 줄이 빠진다(FD R-03, 전체 내보내기를 하지 않음).
- **JS 전체 합**: 129.9 kB로 125.6 kB를 넘는다. 첫 화면은 113.3 kB로 예산 안이다.

## 7. 다음 유닛에 넘기는 것

- **V5 GM 쓰기 정확성**
  - `RegionView.gm_busy` 서버 칸을 더한다. 화면은 이미 읽고 있다(없으면 거짓, 참이면 안내·잠금·1초 × 5 다시 읽기).
  - 409 `gm_busy` 코드도 `conflictKind`가 "busy"로 읽는다.
- **V6 GM 화면**
  - 바쁜 버튼 단언은 `aria-disabled`로 한다(BR-V4-24 계약). 호출자가 `aria-disabled`를 넘겨도 `busy`가 지워지지 않는다.
  - `SessionBar.tsx:122`의 `NewSessionForm`은 `worldId`를 넘기지 않는다(V6 소유, RE-F03을 거기서도 쓰려면 넘긴다).
  - 결과 띠의 지역 변화 문장은 GM과 같은 `notif.*`를 쓴다. 말투를 고치면 두 화면이 함께 바뀐다.
  - `GmPage`는 지연 적재다. GM 화면 테스트는 페이지를 직접 그리므로 영향이 없다.
- **V8 에디터**: `BuildPanel`의 월드 id 안내 한 줄은 V4가 더했다. 지도 `<img>`의 alt는 아직 영어다. `EditorPage`도 지연 적재다.
- **V9 부채·문서**: § 6의 옛 말투 키 정리, CLAUDE.md Status 갱신, 작은 지도 초점·글자 크기 검토(사람의 판단 필요).

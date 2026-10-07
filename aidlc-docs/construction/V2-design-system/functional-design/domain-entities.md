# V2 디자인 시스템 — Domain Entities

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기를 포함한다.
**지금 하는 것**: V2 Functional Design. 디자인 기반이 쓰는 값을 목록으로 정한다: 토큰, 글꼴, 단계 표, enum 라벨, 오류 코드, 타입.

근거: 시안 B(비공개 캔버스 둘째 줄), `business-logic-model.md`. 대비 값은 WCAG 상대 휘도로 계산했다(2026-10-07, 스크래치 계산; NFR light가 같은 표를 테스트로 옮긴다).

---

## 1. 색 토큰 (B 등불 아래 선술집)

`@theme`의 `--color-<이름>`이다. 화면은 이름만 쓴다.

### 1.1 바탕·글·선
| 이름 | 값 | 쓰임 | 대비(글 토큰일 때, 그 바탕 위) |
|---|---|---|---|
| `bg` | #17120E | 페이지 바탕 | — |
| `chrome` | #1D1712 | 머리띠·바닥 행동 띠 | — |
| `surface` | #231B15 | 패널·카드·대화상자 | — |
| `sunken` | #2E241C | 오목한 곳, 선택된 칩·탭, 스켈레톤 | — |
| `fg` | #F0E6D2 | 본문 글 | bg 15.0 · surface 13.7 · sunken 12.2 · chrome 14.3 |
| `muted` | #BFAF95 | 보조 글 | bg 8.7 · surface 7.9 · sunken 7.1 |
| `faint` | #9C8F7B | 지도 지방·대륙 라벨, 흐린 지역 | bg 5.9 · surface 5.4 · sunken 4.8 · 지도 땅 5.0 · 바다 6.1 |
| `line` | #4A3B2D | 장식 구분선만(조작 경계에 쓰지 않음) | surface 1.6 |
| `line-strong` | #7A6650 | 입력·버튼·카드 경계 | bg 3.4 · surface 3.1 |
| `divider` | #3A2E23 | 목록 줄 사이 | — |

### 1.2 강조·상태
| 이름 | 값 | 쓰임 | 대비 |
|---|---|---|---|
| `accent` | #E2A54B | 주 행동, 초점 고리, 지금 위치 받침, 선택 | bg 8.6 · surface 7.8 · sunken 7.0 |
| `accent-hover` | #F2C47A | 주 행동 hover, 지금 위치 점 | on-accent 11.4 |
| `on-accent` | #1A120A | accent 위 글 | accent 8.6 |
| `danger` | #EE7A5F | 위험 행동, 오류 제목, 막힌 길 | surface 6.1 · sunken 5.5 |
| `on-danger` | #1A120A | danger 위 글 | danger 6.7 |
| `success` | #A3C77F | 해소됨, 키 없이 플레이 | tint-success 7.3 |
| `event` | #E0C46C | 사건, 턴 결과 제목 | tint-event 7.7 |
| `info` | #86B9CC | 안내 아이콘·링크, 강 | tint-info 6.7 |
| `info-fg` | #D8E8EE | 안내 띠 본문 | tint-info 11.5 |
| `ornament` | #C9933F | 장식 점·선(글에 쓰지 않음) | surface 6.2 |
| `disabled` | #2E241C | 비활성 바탕 | — |
| `disabled-fg` | #A49681 | 비활성 글 | disabled 5.2 |

### 1.3 옅은 바탕 (배지·안내 띠)
| 이름 | 값 | 짝 글 | 대비 |
|---|---|---|---|
| `tint-event` / `-line` | #3A2F14 / #6B5A26 | event | 7.7 |
| `tint-danger` / `-line` | #3D1E17 / #7A3A2B | danger | 5.4 |
| `tint-success` / `-line` | #26301A / #4B5E33 | success | 7.3 |
| `tint-info` / `-line` | #1C2C33 / #2E4650 | info · info-fg | 6.7 · 11.5 |

### 1.4 지도
| 이름 | 값 | 쓰임 |
|---|---|---|
| `map-sea` | #120E0B | 지도 바탕 |
| `map-land` | #2A2119 | 땅 |
| `map-land-line` | #7A6650 | 해안선 |
| `map-cliff` | #5C4B3A | 지형선(점선) |
| `map-river` | #86B9CC | 강 연결(땅 위 7.4) |
| `map-path` | #BFAF95 | 길·바로 옆 연결(땅 위 7.4) |
| `map-blocked` | #EE7A5F | 막힌 연결(땅 위 5.7) |
| `map-town` | #F0E6D2 | 지역 표식(땅 위 12.8) |
| `map-plate` | #17120E (90%) | 라벨 받침 |
| `map-current` | #F2C47A | 지금 위치 점(땅 위 9.7), 둘레 빛 accent 22% |
| `map-player` | #EE7A5F | 플레이어 말 |

### 1.5 모양
| 이름 | 값 |
|---|---|
| `--radius-sm` / `-md` / `-lg` / `-xl` | 6px / 8px / 12px / 14px (배지 999px) |
| `--shadow-panel` | `inset 0 1px 0 rgb(255 236 200 / 0.06)` |
| `--shadow-pop` | `0 8px 22px rgb(0 0 0 / 0.45)` |
| `--color-scrim` | `rgb(0 0 0 / 0.55)` (대화상자 뒤) |
| 초점 고리 | `outline: 2px solid var(--color-accent); outline-offset: 2px` |

### 1.6 허용 쌍 (정본, BR-V2-05·06)
글 토큰과 경계 토큰은 아래 바탕 위에서만 쓴다. 표 밖의 조합은 쓰지 않는다. 대비 테스트(TP-V2-1)는 이 표의 모든 칸을 계산한다.

| 앞(글·경계) | 허용 바탕 | 최저 대비 | 기준 |
|---|---|---|---|
| `fg` | bg, chrome, surface, sunken, map-plate | 12.2 | 4.5 |
| `muted` | bg, chrome, surface, sunken, tint-event, tint-danger, tint-success, tint-info, map-plate | 6.1 | 4.5 |
| `faint` | bg, surface, sunken, map-sea, map-land | 4.8 | 4.5 |
| `accent`(글·링크) | bg, chrome, surface, sunken | 7.0 | 4.5 |
| `danger`(글) | bg, surface, sunken, tint-danger | 5.4 | 4.5 |
| `event`·`success`·`info` | 자기 tint, bg, surface (`event`는 sunken도 — 알림 카드 제목 〔코드 리뷰 01 정정〕) | 6.7 | 4.5 |
| `info-fg` | tint-info | 11.5 | 4.5 |
| `on-accent` | accent, accent-hover | 8.6 | 4.5 |
| `on-danger` | danger | 6.7 | 4.5 |
| `disabled-fg` | disabled | 5.2 | 4.5 |
| `line-strong`(조작 경계) | bg, chrome, surface | 3.1 | 3.0 |

- `faint`는 옅은 바탕(tint) 위에 쓰지 않는다. tint-event 위에서는 4.15라 기준에 모자란다.
- 조작(입력·버튼·Select·FileInput)은 `sunken` 바탕 위에 두지 않는다. `line-strong`이 sunken 위에서 2.77이기 때문이다. sunken은 칩·스켈레톤·선택된 탭·조작이 아닌 오목한 면에만 쓴다. 선택된 탭은 글자색(accent)과 바탕으로 구별하고, 경계에 기대지 않는다.

## 2. 글꼴

| 토큰 | 글꼴(패키지) | 굵기 | 라이선스 |
|---|---|---|---|
| `--font-display` | IM Fell English SC (`@fontsource/im-fell-english-sc`) | 400 | OFL |
| `--font-heading` | 나눔명조 (`@fontsource/nanum-myeongjo`) | 700 〔Step 1.3 정정: 800 뺌, NFR light § 2.2〕 | OFL |
| `--font-body` | Noto Sans KR (`@fontsource/noto-sans-kr`) | 400, 700 〔Step 1.3 정정: 500 뺌, NFR light § 2.2〕 | OFL |
| `--font-story` | 나눔명조 | 700 | OFL |

글 크기 단계(rem, 본문 16px 기준):

| 단계 | 크기 | 쓰임 |
|---|---|---|
| `text-xs` | 12px | 배지, 범례 |
| `text-sm` | 13–14px | 보조 글, 목록 둘째 줄 |
| `text-base` | 15–16px | 본문, 버튼 |
| `text-lg` | 18px | 패널 제목 |
| `text-xl` | 20px | 섹션 제목 |
| `text-3xl` | 30px | 휴대폰 지역 이름 |
| `text-4xl` | 38px | 데스크톱 지역 이름 |
| `text-5xl` | 44px | 홈 첫 제목 |

본문 줄 간격은 1.65이고 이야기 글은 1.85다. 휴대폰에서 12px 아래 글은 쓰지 않는다.

## 3. 단계 표 (`format/`)

경계 규칙: 아래 경계를 넣고 위 경계는 뺀다. 마지막 단계만 1을 넣는다. 0~1 밖의 값은 자르고, `NaN`·`null`은 "—"다(BR-V2-12).

| 함수 / kind | 단계(ko / en) |
|---|---|
| `degreeWord` · `distortion` | [0, 0.15) 거의 그대로 / Nearly true · [0.15, 0.4) 조금 부풀려짐 / A little stretched · [0.4, 0.7) 많이 비틀림 / Badly twisted · [0.7, 1] 거의 딴 이야기 / Hardly the same story |
| `decayWord` · `decay` | [0, 0.3) 건너 들음 / Heard second-hand · [0.3, 0.6) 희미하게 / Faintly · [0.6, 1] 아주 희미하게 / Very faintly |
| `support` | [0, 0.2) 거의 안 믿음 / Hardly believed · [0.2, 0.4) 몇몇이 믿음 / A few believe it · [0.4, 0.6) 꽤 믿음 / Fairly believed · [0.6, 1] 많이 믿음 / Widely believed |
| `magnitude` | [0, 0.25) 작은 / Minor · [0.25, 0.5) 보통 / Moderate · [0.5, 0.75) 큰 / Major · [0.75, 1] 아주 큰 / Severe |
| `confidence` | [0, 0.4) 낮음 / Low · [0.4, 0.75) 보통 / Medium · [0.75, 1] 높음 / High |
| `salience` | [0, 0.34) 스쳐 봄 / Barely noticed · [0.34, 0.67) 눈여겨봄 / Noticed · [0.67, 1] 크게 주목 / Stood out |
| `weight` | [0, 0.3) 드물게 오감 / Rarely used · [0.3, 0.6) 가끔 오감 / Sometimes used · [0.6, 1] 자주 오감 / Often used |
| `share` | [0, 0.34) 조금 / A little · [0.34, 0.67) 절반쯤 / About half · [0.67, 1] 대부분 / Most |

- 소문의 **승격 상태**는 단계가 아니라 상태 배지다. 라벨은 "사실로 굳어짐 / Taken as fact"이다.
  - 시안에는 "널리 믿음"이라고 적었지만 이 이름은 support 단계 낱말과 겹친다. 승격 기준(`promotion_threshold` 0.6)은 운영자가 바꿀 수 있어 단계 경계와 묶지 않는다.
- 행적에서 생긴 소문의 배지는 "당신 이야기 / About you"다.

## 4. enum 라벨 (`enum.<kind>.<value>`)

| kind | 값 → ko / en |
|---|---|
| `regionLevel` | continent 대륙 / Continent · province 지방 / Province · town 마을 / Town · district 구역 / District · terrain 지형 / Terrain |
| `connectionKind` | adjacent 바로 옆 / Next to · route 길 / Road · river 강 / River · blocked 막힘 / Blocked |
| `travelBy` (이동 목록 문구) | adjacent 바로 옆 / Next door · route 길로 / By road · river 강을 따라 / Along the river · blocked 막혀 있음 / Blocked |
| `scopeType` | direct 이곳에서 앎 / Known here · inherited 위에서 이어받음 / From the wider land · propagated 퍼져 옴 / Spread here · global 누구나 앎 / Common knowledge · hearsay 전해 들음 / Heard second-hand |
| `eventStatus` | suggested 제안됨 / Suggested · active 진행 중 / Active · resolved 해소됨 / Resolved |
| `eventCategory` | war 전쟁 / War · plague 역병 / Plague · politics 정치 / Politics · disaster 재난 / Disaster · festival 축제 / Festival · discovery 발견 / Discovery |
| `eventLifecycle` | one_shot 한 번 / One-off · persistent 이어짐 / Lasting |
| `sessionStatus` | open 진행 중 / Open · closed 닫힘 / Closed |
| `turnRunStatus` | running 진행 중 / Running · done 끝남 / Done · failed 실패 / Failed |
| `augmentationStatus` | open 묻는 중 / Asking · converged 다 물음 / Settled · stopped 멈춤 / Stopped |
| `augmentationTarget` | knowledge 지식 / Knowledge · entity 대상 / Entity · region 지역 / Region · connection 연결 / Connection |
| `augmentationAction` | confirm 맞음 / Correct · edit 고침 / Edit · remove 지움 / Remove · add 더함 / Add · ignore 넘김 / Skip |
| `deedKind` | arrival 도착 / Arrival · statement 한 말 / Statement · declared_action 선언한 행동 / Declared action |
| `rumorOrigin` | canonical 이 땅의 이야기 / From the land · deed 당신 이야기 / About you |
| `wikiDomain` | geography 지리 / Geography · geology 지질 / Geology · climate 기후 / Climate · ecology 생태 / Ecology · economy 경제 / Economy · logistics 물자·교통 / Logistics · culture 문화 / Culture · history 역사 / History · politics 정치 / Politics · religion 종교 / Religion · military 군사 / Military · technology 기술 / Technology · other 기타 / Other |

- `slant`는 enum이 아니다. 판정 NPC가 LLM으로 쓴 자유 문장이라 원문을 보인다(설계 정정, BLM § 5.1).
- **`connectionKind`와 `travelBy`를 쓰는 곳**:
  - `connectionKind`(명사)는 연결 자체를 가리킬 때 쓴다. 지도 범례, 에디터 연결 목록·종류 선택, 지역 삭제 확인(`ConfirmDelete`), wiki 인용(`WikiPanel`), GM 화면이 여기에 든다.
  - `travelBy`(이동 방식 구절)는 플레이어 이동 목록(`MovePanel`)에서 "앰버메도 · 강을 따라 · 1턴"처럼 길을 말할 때만 쓴다.
- `augmentationTarget`은 백엔드 `TargetKind`(knowledge, entity, region, connection)를 따른다. 프론트 `QuestionTarget.kind`에는 `npc`가 있지만 백엔드는 NPC 질문을 만들지 않는다(U3 C4). 그래서 라벨을 두지 않고, 만약 오면 원문과 개발 경고로 드러낸다.
- 화면에 원문이 보이는 곳(2026-10-07 grep). V2가 라벨 함수를 만들고, 화면 쪽 교체는 각 유닛이 한다.
  - `WikiPanel.tsx:58` 도메인 배지 → `wikiDomain`(V8)
  - `ConfirmDelete.tsx:11`·`WikiPanel.tsx:39` 연결 종류 → `connectionKind`(V8)
  - `MovePanel.tsx:26` → `travelBy`(V4)
- 값 집합의 근거:
  - `locus/shared/models/enums.py`: RegionLevel, ScopeType, ConnectionKind
  - `locus/play/models.py`: SessionStatus, EventStatus, TurnRunStatus, DeedKind
  - `web/src/types.ts`: EventCategory, EventLifecycle, AugAction
  - `locus/world/augmentation/types.py`: RunStatus, TargetKind
  - `locus/shared/models/enums.py`: WikiDomain(13개)
- 백엔드에 값이 더해지면 프론트 테스트가 빠진 라벨을 잡도록, 값 목록을 `format/enums.ts` 한 곳에 둔다(BR-V2-11).

## 5. 오류 코드 (`api/errors.py` `ERROR_CODES` + 사전 `error.<code>.*`)

순서가 있다. 위에서 처음 맞는 줄을 쓴다. 표에 없는 예외는 `http_error`가 다시 던진다(지금과 같음). 그 예외는 잡히지 않은 예외로 500이 된다.

| # | 예외 | 상태 | code | ko 제목 · 할 일 | en |
|---|---|---|---|---|---|
| 1 | `SessionClosedError` | 409 | `session_closed` | 이 세션은 닫혔어요. · 새 세션을 시작하세요. | This session is closed. · Start a new session. |
| 2 | `TurnInProgressError` | 409 | `turn_running` | 다른 턴이 진행 중이에요. · 끝나면 다시 해 보세요. | A turn is still running. · Try again when it ends. |
| 3 | `SeedAlreadyRunningError` | 409 | `seed_running` | 이 씨앗은 이미 시작됐어요. · 사건 목록에서 확인하세요. | This seed has already started. · Check the event list. |
| 4 | `WorldExistsError` | 409 | `world_exists` | 같은 이름의 월드가 있어요. · 다른 이름을 쓰거나 바꾸기를 고르세요. | A world with this id exists. · Use another id or choose replace. |
| 5 | `BuildInProgressError` | 409 | `build_running` | 이 월드를 만드는 중이에요. · 끝나면 다시 해 보세요. | This world is being built. · Try again when it ends. |
| 6 | `RunFinishedError` | 409 | `run_finished` | 이 보강은 이미 끝났어요. · 새로 시작하세요. | This augmentation run has ended. · Start a new one. |
| 7 | `ChangeAlreadyRevertedError` | 409 | `change_reverted` | 이미 되돌린 변경이에요. | That change was already undone. |
| 8 | `RevertOrderError` | 409 | `revert_order` | 나중 변경부터 되돌려야 해요. · 가장 최근 것부터 되돌리세요. | Undo newer changes first. |
| 9 | `RevertConflictError` | 409 | `revert_conflict` | 그 뒤에 바뀐 것이 있어 되돌릴 수 없어요. | It changed since then and cannot be undone. |
| 10 | `AugmentationConflict`(나머지) | 409 | `augmentation_conflict` | 보강 상태가 바뀌었어요. · 다시 불러오세요. | The augmentation changed. · Reload it. |
| 11 | `ExecutorShutdownError` | 503 | `shutting_down` | 서버가 멈추는 중이에요. · 잠시 뒤 다시 해 보세요. | The server is shutting down. · Try again shortly. |
| 12 | `LlmUnavailableError` | 503 | `llm_unavailable` | AI 키가 없어 이 기능은 쉬고 있어요. | This needs an AI key, which is not set. |
| 13 | `LlmCallFailedError` | 503 | `llm_failed` | AI 응답을 받지 못했어요. · 잠시 뒤 다시 해 보세요. | The AI did not answer. · Try again shortly. |
| 14 | `UnsupportedWorldFile` | 422 | `unsupported_world_file` | 이 World File 형식은 읽을 수 없어요. | This World File format is not supported. |
| 15 | `InvalidActionError` | 400 | `invalid_action` | 지금은 할 수 없는 행동이에요. | That action is not possible now. |
| 16 | `ConversationExistsError` | 400 | `conversation_exists` | 이미 이야기 중인 상대예요. | You are already talking with them. |
| 17 | `AppraisalExistsError` | 400 | `appraisal_exists` | 이미 판정한 행적이에요. | That deed was already judged. |
| 18 | `LookupError`(나머지) | 404 | `not_found` | 찾을 수 없어요. · 목록을 다시 불러오세요. | Not found. · Reload the list. |
| 19 | `ValueError`(나머지) | 400 | `invalid_request` | 요청을 처리할 수 없어요. · 입력을 확인하세요. | The request could not be processed. · Check the input. |

라우터가 직접 던지는 것(코드를 붙이는 자리):

| 자리 | 상태 | code | ko 제목 · 할 일 |
|---|---|---|---|
| `routers/world.py` 교체 전 점검(턴 진행 중) | 409 | `sessions_busy` | 이 월드의 세션이 턴을 진행 중이에요. · 끝나면 다시 해 보세요. |
| `routers/world.py` 교체 전 점검(열린 세션) | 409 | `sessions_open` | 열린 세션이 있어요. · 닫고 바꿀지 확인해 주세요.(화면은 확인 대화상자로 이어 간다) |
| `routers/world_editor.py` 지역 삭제(`RegionInUseError`를 잡아 던짐; `ERROR_CODES`에 넣지 않음, `detail` 객체 `{message, session_ids}` 유지) | 409 | `region_in_use` | 플레이어가 이 지역에 있어요. · 그 세션을 닫거나 옮긴 뒤 지우세요. |
| `uploads.py` 크기·개수(`check_count`·`read_capped`·`read_memo`의 예외) | 413 | `too_large` | 파일이 너무 커요. · 제한: {limit} |
| `uploads.py` `BodyLimitMiddleware`의 직접 응답(처리기를 거치지 않음) | 413 | `too_large` | (위와 같음) — 미들웨어가 본문에 `code`를 직접 싣는다 |
| `uploads.py` 그림 형식 | 422 | `bad_image` | PNG, JPEG, WebP만 올릴 수 있어요. |
| `routers/world.py` 지도 JSON | 422 | `bad_map_json` | 지도 파일이 올바른 JSON이 아니에요. |
| `routers/world.py` World File 아님 | 422 | `bad_world_file` | World File(JSON)이 아니에요. |
| `deps.py` 지원하지 않는 언어 | 400 | `unsupported_lang` | 지원하지 않는 언어예요. |
| `deps.py`·라우터의 "… unavailable" | 503 | `service_unavailable` | 서버의 일부가 준비되지 않았어요. · 잠시 뒤 다시 해 보세요. |
| `world_editor.py` NPC 초안 LLM 없음 | 503 | `llm_unavailable` | (위 13과 같음) |
| `routers/world.py` 월드 빌드·업로드 빌드·데모 소스 빌드의 빌더 없음(`need_service(…, "llm_unavailable")`) 〔코드 리뷰 01 #2 정정: 처음 표는 이 셋을 위 `service_unavailable` 줄에 넣어 화면이 "LLM 키가 필요해요"를 잃었다〕 | 503 | `llm_unavailable` | (위 13과 같음) |
| 검증 실패 처리기 | 422 | `validation_failed` | 입력 값이 맞지 않아요. · 표시된 칸을 확인하세요. |
| Starlette 라우트 없음 | 404 | `not_found` | 찾을 수 없어요. |
| Starlette 메서드 없음 | 405 | `method_not_allowed` | 이 요청은 받지 않아요. |
| 잡히지 않은 예외(`Exception` 처리기) | 500 | `error` | 서버에서 문제가 생겼어요. · 잠시 뒤 다시 해 보세요. (`detail`은 "internal error") |

상태별 기본(`code`가 없을 때 서버가 붙이는 것, 클라이언트가 code를 모를 때의 문장):

| 상태 | code | ko |
|---|---|---|
| 400 | `invalid_request` | 요청을 처리할 수 없어요. |
| 404 | `not_found` | 찾을 수 없어요. |
| 405 | `method_not_allowed` | 이 요청은 받지 않아요. |
| 409 | `conflict` | 다른 작업과 겹쳤어요. · 잠시 뒤 다시 해 보세요. |
| 413 | `too_large` | 보낸 것이 너무 커요. |
| 422 | `validation_failed` | 입력 값이 맞지 않아요. |
| 500 | `error` | 서버에서 문제가 생겼어요. · 잠시 뒤 다시 해 보세요. |
| 503 | `service_unavailable` | 서버가 잠시 쉬고 있어요. · 잠시 뒤 다시 해 보세요. |
| (네트워크) | `network` | 서버에 닿지 못했어요. · 연결을 확인하고 다시 해 보세요. |
| (그 밖) | `unknown` | 알 수 없는 문제가 생겼어요. |

- V5는 `gm_busy`(409, "GM이 이 세션을 바꾸는 중이에요. · 끝나면 다시 해 보세요.")를 2번 줄 앞에 더한다. `GmBusyError`가 `TurnInProgressError`의 하위 클래스이기 때문이다(component-methods § 6).
- V3은 데모 번역 파일 경로 거절(400)이 생기면 줄을 더한다.

## 6. 타입

```ts
// api/http.ts
class HttpError extends Error {
  readonly status: number;
  readonly code?: string;        // 본문 JSON의 code (V2 가산)
  readonly detail: unknown;      // 본문 JSON의 detail (없으면 undefined)
  readonly body: string;         // 원문 본문 (지금과 같음)
}

// errors/
type DescribedError = {
  title: string;      // "이 세션은 닫혔어요."
  action?: string;    // "새 세션을 시작하세요."
  code?: string;      // "session_closed" | "network" | "unknown" …
  status?: number;    // 409
  raw?: string;       // 자세히 접힘에 보일 원문(300자까지)
};

// format/
type Lang = "ko" | "en";
type EnumKind = "regionLevel" | "connectionKind" | "travelBy" | "scopeType" | "eventStatus"
  | "eventCategory" | "eventLifecycle" | "sessionStatus" | "turnRunStatus"
  | "augmentationStatus" | "augmentationTarget" | "augmentationAction" | "deedKind" | "rumorOrigin";
type MeasureKind = "distortion" | "decay" | "support" | "magnitude" | "confidence"
  | "salience" | "weight" | "share";
type Band = { upTo: number; key: string };   // upTo는 위 경계(마지막은 1, 포함)

// map/
type Norm = { x: number; y: number };          // 0..1
type ViewBox = { x: number; y: number; w: number; h: number };
type LabelBox = { id: string; x: number; y: number; w: number; h: number; side: "below" | "right" | "left" | "above" };
```

```py
# api/errors.py
class ApiError(HTTPException):
    def __init__(self, status_code: int, detail: object, code: str) -> None: ...
ERROR_CODES: list[tuple[type[Exception], int, str]]       # 순서 있는 표(§ 5)
DEFAULT_CODES: dict[int, str]                              # 상태별 기본
def http_error(exc: Exception) -> ApiError                 # 표에 없으면 다시 던진다(지금과 같음)
```
- 설계(component-methods § 7)는 `ERROR_CODES`를 `dict[type, tuple]`로 적었다. 하위 클래스를 기반 클래스보다 먼저 맞춰야 하므로 **순서 있는 list**로 바꾼다. `isinstance`를 위에서부터 본다.

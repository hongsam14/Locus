# U8 데모·배포·문서 — Business Rules

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U8 기능 설계 중 규칙입니다. 다음 규칙을 정하고, 규칙마다 확인할 속성(TP)과 예제(EX)를 붙입니다.
- 데모 데이터
- 데모 콘텐츠
- 사건 씨앗
- 원클릭
- 키 없음
- 문서·메타
- CI
- 라이브 시나리오

번호는 `BR-U8-n`이고 안정적입니다. 근거 열의 Q는 FD-U8 답, A8은 플랜 가정, P는 플랜의 설계 원칙("데모는 데이터다")입니다.

## 1. 데모는 데이터다
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-1 | `locus/`·`api/`·`web/src/`의 코드는 데모 이름, 데모 지역 id, 시작 지역, 소스 글을 상수로 갖지 않는다. 데모는 매니페스트 항목과 그 파일로만 정해진다. 테스트는 패키지 데모 파일을 입력으로 써도 된다 | P |
| BR-U8-2 | 매니페스트 항목은 조립 때 한 번 검사하고 결과를 둔다(요청마다 다시 읽지 않는다, 〔검토 01 R-09〕). 파일이 있고 World File로 읽혀야 하고, `start_region_id`가 그 파일 지역이며 지나갈 수 있는 연결이 있어야 하고, `sources` 경로가 있고 매니페스트 폴더 안이어야 한다. 어긋난 항목은 목록에서 빠지고 경고 로그를 남긴다. 패키지 매니페스트의 잘못된 항목은 0개다 | P, A8-4 |
| BR-U8-3 | 데모 불러오기는 LLM을 0회 부른다. 기본 world id는 항목 `name`이다 | BR-U2-28 |
| BR-U8-4 | 소스 빌드는 `sources`가 있는 항목만 받는다. 없으면 404다 | P |
| BR-U8-5 | 다시 불러오기는 교체 확인 → 열린 세션 확인(409 → `confirm=true`) 순서를 거친다. 같은 world id에는 월드가 하나만 남는다 | US-1.3 |

## 2. 데모 콘텐츠 (패키지 데모 `emberleaf`)
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-6 | 지역은 10~15개이고 계층은 3단이다. 마을(잎) 지역마다 NPC가 1~3명이고, 지방·섬 지역의 NPC는 0명이다 | US-1.3, A-4 |
| BR-U8-7 | 강·길·막힌 길 연결이 각각 한 쌍 이상 있다. 모든 연결은 두 방향 쌍이다. 시작 지역에서 지나갈 수 있는 연결로 모든 마을에 닿는다. 막힌 쌍의 두 지역 사이에는 돌아가는 길이 있다 | US-1.3, A8-3 |
| BR-U8-8 | 마을마다 DIRECT 지식이 2개 이상이다. 그 마을만 아는 소문거리가 있는 마을이 3곳 이상이다. 전역 지식은 1~2개다 | US-1.3, A8-3 |
| BR-U8-9 | 씨앗은 2~3개이고, 지역과 분류가 서로 다르며, 모두 마을 지역에 있다 | US-1.3 |
| BR-U8-10 | 이름과 글은 창작이다. 원작의 고유명사를 쓰지 않는다. 매니페스트 `credits`에 영감 출처 한 줄과 무관 표시를 둔다 | Q1-2=A |
| BR-U8-11 | "지형을 따라 퍼진다"가 수치로 보인다. 〔검토 01 R-04〕 합의와 사건 번짐은 모든 연결, 행적 확산은 지나갈 수 있는 연결만 쓴다. 최대 곱 무게는 domain-entities §5.2 표와 같다. 강 무게는 1.0(1턴)이다. 강 마을 셋은 서로의 마을 지식을 그대로 안다. Ironcrag는 Saltwake·Gutterlight·Hollowdeep·Sunstrand의 마을 지식을 전해 들음으로만 안다(〔Step 1.2 정정〕 정확히는 domain-entities §5.2 표에서 0.15 이상 0.5 미만인 마을 모두). Ambermeadow에서 생긴 행적 소문은 1턴 뒤 Saltwake·Sylvarch에 있고, Ironcrag에는 3턴 전에 없다. 유물 사건은 Sunstrand에 닿지 않는다 | Q1-1=A, domain-entities §5.2 |

## 3. 사건 씨앗
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-12 | `EventSeed`는 캐노니컬이다. World File 선택 절 `event_seeds`, 그래프 노드, 스냅샷에 있고 내보내기·불러오기·교체·월드 삭제를 따른다. `format_version`은 1 그대로다. 절이 없는 파일은 `[]`로 읽는다 | Q2=A |
| BR-U8-13 | 불러올 때 `region_id`가 파일에 없는 씨앗은 빼고 error 경고를 남긴다(`ok=false`). id 재매핑은 씨앗 id와 `region_id`를 함께 바꾼다 | BR-U2-5, A2 |
| BR-U8-14 | 에디터의 지역 삭제는 그 지역의 씨앗도 지운다. 위치는 U3 삭제 순서의 ③ 뒤, ④ 앞이다. 재시도해도 남는 것이 없고, 삭제 계획과 보고에 씨앗 수가 나온다 〔U3 BLM §1.3·BR-U3-8 확장〕 | U3 Q1=A 원칙 |
| BR-U8-15 | 씨앗 시작은 GM 쓰기다. GM 리스 아래에서 열린 세션만 받는다. 닫힌 세션과 턴 중은 409이고, LLM은 0회다 | Q2=A, U7 리스 |
| BR-U8-16 | 같은 씨앗으로 시작해 해소되지 않은 사건이 그 세션에 있으면 409 `seed already running`이다. 해소된 뒤에는 다시 시작할 수 있다 | Q2=A |
| BR-U8-17 | 시작은 `SeedService`가 하고 응답은 201 `EventOut`이다. 같은 씨앗 진행 중은 `SeedAlreadyRunningError`(409)다(〔검토 01 R-06〕). 시작한 사건은 수동 생성 사건과 같다. ACTIVE이고, 지역·분류·크기·설명은 씨앗의 것이며, 수명은 씨앗 값이거나 분류 기본값이다. provenance는 `generated_by="seed"`, `refs=[seed_id]`이다. 타임라인 줄에 씨앗 제목이 나온다 | Q2=A |
| BR-U8-18 | 씨앗의 세션 상태(`running_event_id`)는 저장하지 않고 그 세션의 사건에서 읽는다. 세션 저장 스키마는 바뀌지 않는다 | domain-entities §3 |

## 4. 원클릭
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-19 | `/`는 매니페스트 항목마다 데모 카드를 월드가 있든 없든 보인다 | Q3=A, P |
| BR-U8-20 | [바로 플레이]: 월드가 없으면 불러온다. 있으면 [지금 월드로 플레이]와 [새로 불러와 플레이] 중에 고른다. 그다음 `start_region_id`에서 세션을 시작하고 `/play/:id`로 간다. 플레이어 이름은 화면 언어의 기본 이름이다 | Q3=A |
| BR-U8-21 | [에디터에서 보기]는 이미 있는 월드를 다시 불러오지 않는다 | Q3=A |
| BR-U8-22 | 단계가 실패하면 카드에 알리고 멈춘다. 이미 된 단계는 되돌리지 않는다. 〔검토 01 R-03〕 실패에는 HTTP 오류와 불러오기 `ok=false`(error 경고 앞 3개·백업 경로를 보이고 세션을 시작하지 않음)가 든다. 409 `busy_sessions`는 확인 없이 "잠시 뒤 다시"를 보인다. 있는 월드에 시작 지역이 없으면 [새로 불러와 플레이]를 권한다 | Q3=A |

## 5. 키 없음
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-23 | `GET /api/capabilities`가 `{llm, vlm, embedding}`을 준다. `/health`의 상태 규칙은 바꾸지 않는다 | Q4=A |
| BR-U8-24 | LLM이 필요한 경로(business-logic-model §4.1 표, 의존 필드와 함께)는 공급자가 없으면 503이다. LLM이 필요 없는 경로(`priors` 포함)는 키 없이 503도 500도 아니다. 500은 없다 〔검토 01 R-02〕 | US-1.4 |
| BR-U8-25 | `llm=false`이면 `/`·에디터·GM 화면 머리에 한 줄 안내를 둔다. LLM 버튼은 끄고 까닭을 붙인다. LLM이 필요 없는 기능은 켜 둔다 | Q4=A, NFR-4 |
| BR-U8-26 | `capabilities` 읽기가 실패하면 안내와 끄기를 하지 않는다 | Q4=A |
| BR-U8-27 | 503을 받은 화면의 문구는 "LLM 키가 필요합니다"(en "An LLM key is required")다 | US-1.4 |

## 6. 문서·메타
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-28 | README 첫 줄은 §0 문장이다. 절 순서는 business-logic-model §5를 따른다. README의 명령은 실제로 있는 프로필과 명령만 쓴다 | US-1.2, H1 |
| BR-U8-29 | `LICENSE`(MIT)와 `pyproject.toml` `license = { text = "MIT" }`가 같다(setuptools 하한 61에서 유효한 표 형식, 〔검토 01 R-01〕). `pyproject.toml` 설명은 §0의 영어판이다 | Q6=A, US-7.5 |
| BR-U8-30 | `requirements.txt`와 `pyproject.toml` `dependencies`는 같은 이름과 버전 조건을 갖는다 | US-7.5 |
| BR-U8-31 | 진행 중 기능 넷은 README 표와 모듈 docstring `STATUS:`로 표시한다. 화면에 닿는 것(빌드 패널의 컨셉 아트 칸)에는 "진행 중" 표시가 있다 | US-7.3, A8-7 |
| BR-U8-32 | 살아 있는 문서(README, `CLAUDE.md`, `operations.md`, `web/README.md`)의 데모 명령은 `emberleaf`를 쓴다. 지난 유닛의 code-summary는 고치지 않는다. operations.md에 옛 이름 대응 한 줄을 둔다 | A8-12 |

## 7. CI
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-33 | 워크플로는 push와 PR에서 돈다. 백엔드는 `ruff check`, `black --check`, `pytest`를 돌린다. 프런트엔드는 `npm ci`, `tsc --noEmit`, `vitest run`을 돌린다. `npm audit --omit=dev --audit-level=moderate`는 따로 된 audit 작업이다(막는다, 〔검토 01 R-11〕). `npm ci` 성공이 전제다. mypy는 넣지 않는다 | Q5=A, US-7.6 |
| BR-U8-34 | hypothesis seed는 실행마다 로그에 찍고 `--hypothesis-seed`로 넘긴다. 실패하면 재현 blob이 찍힌다 | PBT-08 |
| BR-U8-35 | `npm audit --omit=dev`는 0건이다. react-router를 고친 판으로 올린다. 〔Step 1.2 정정〕 6.x에는 고친 판이 없어 react-router-dom 7.18.x로 올린다(사람의 결정, 코드 플랜 검토 01 R-06) | Q5=A |

## 8. 라이브 시나리오
| 규칙 | 내용 | 근거 |
|---|---|---|
| BR-U8-36 | `scripts/live_scenario.py`는 business-logic-model §7의 단계를 플레이어 위치 순서대로 돌고(먼 지역은 GM 읽기, 〔검토 01 R-05〕), 단계마다 PASS·FAIL·SKIP을 찍는다. 키가 없으면 LLM 단계는 SKIP이다. FAIL이 하나라도 있으면 종료 코드는 1이다. 표준 라이브러리만 쓰고 CI에는 넣지 않는다 | A8-8 |

## 9. Testable Properties (PBT advisory, unit-of-work U8)
| 번호 | 속성 | 입력 |
|---|---|---|
| TP-U8-1 | `event_seeds`가 든 World File의 저장 → 불러오기 → 저장 결과가 같다(U2 TP-U2-1 왕복 확장) | `tests/world/strategies.py` 생성기에 씨앗 추가 |
| TP-U8-2 | id 재매핑 뒤에도 씨앗은 같은 지역(재매핑된 id)을 가리킨다 | 생성기 + 강제 재매핑 |
| TP-U8-3 | 지역 삭제 뒤 남은 씨앗 가운데 지운 지역을 가리키는 것은 0개다. n번째 쓰기에서 끊고 재시도해도 같다(TP-U3-2·2a 신탁 확장) | U3 생성기 + 씨앗 |
| TP-U8-4 | 패키지 데모가 BR-U8-6~11을 지킨다. 최대 곱 무게는 domain-entities §5.2 표의 값과 같다(소수 셋째 자리) | 패키지 파일(예제 기반) |
| TP-U8-5 | 같은 씨앗을 두 번 시작하면 두 번째는 409이고, 그 씨앗의 ACTIVE 사건은 하나다 | 인메모리 플레이 |
| TP-U8-6 | 코드에 데모 이름·지역 이름이 나오지 않는다. 검색어는 새 데모(`emberleaf`, 지역 id·이름)와 옛 데모(`aldermoor`, `riverton`, `highcrag`, `greenvale`, `frostreach`)다(〔검토 01 R-10〕) | `locus/`·`api/`·`web/src`(테스트·패키지 데이터 제외) 검색 |
| TP-U8-7 | `requirements.txt` = `pyproject.toml` `dependencies` | 두 파일 |
| TP-U8-8 | LLM 경로 표의 모든 경로가 공급자 없이 503이고, 키 없이 쓰는 대표 경로(데모 불러오기, 세션 시작, 이동 턴, 씨앗 시작, 보강 시작, `priors`)는 2xx다 | API 테스트 앱(LLM 없음) |

### 9.1 규칙별 예제 (`EX-n`)
| 번호 | 규칙 | 예제 |
|---|---|---|
| EX-1 | BR-U8-20 | 월드 없음 → [바로 플레이] → 불러오기 1회(LLM 0) → `startSession("emberleaf", {name: "여행자", start_region_id: "region-saltwake"})` → `/play/s1` |
| EX-2 | BR-U8-5·20 | `emberleaf`가 있고 열린 세션이 2개다 → [새로 불러와 플레이] → 교체 확인 → 409 → "열린 세션 2개를 닫습니다" 확인 → `confirm=true` 불러오기 → 새 세션 |
| EX-3 | BR-U8-21 | `emberleaf`가 있다 → [에디터에서 보기] → 불러오기 0회, `/editor/emberleaf` |
| EX-4 | BR-U8-15~17 | `seed-mushroom-blight` 시작 → Ambermeadow에 plague 0.5 persistent ACTIVE 사건이 생기고, 타임라인에 "씨앗 사건 시작: Blight in the mushroom fields"가 남는다. 다시 시작 → 409. 사건을 해소한 뒤 시작 → 201 |
| EX-5 | BR-U8-12 | `event_seeds`가 없는 옛 Aldermoor 파일을 불러온다 → ok이고 씨앗은 0개다. 내보내면 `"event_seeds": []`이다 |
| EX-6 | BR-U8-13 | 씨앗 `region_id`가 파일에 없다 → 그 씨앗만 빠지고 error 경고가 남으며 `ok=false`다 |
| EX-7 | BR-U8-14 | Ambermeadow 삭제 계획에 `seed_ids=[seed-mushroom-blight]`가 있다. 삭제 → `seeds_deleted=1`이고 스냅샷에 그 씨앗이 없다 |
| EX-8 | BR-U8-23~25 | 키 없음 → `capabilities.llm=false`. `/`에 안내가 있고 데모 [바로 플레이]는 켜져 있다. 에디터 NPC [초안]은 꺼져 있다. `POST …/npc-drafts` → 503 |
| EX-9 | BR-U8-11 | 합의: Saltwake의 범위에는 Sylvarch의 DIRECT 지식이 그대로 있다. Ironcrag의 범위에는 Saltwake 지식이 HEARSAY로만 있다 |
| EX-10 | BR-U8-11 | Ambermeadow에서 행적을 남긴다 → 1턴 뒤 Saltwake·Sylvarch에 그 행적 소문이 있고, 2턴 뒤까지 Ironcrag에는 없다 |
| EX-11 | BR-U8-2 | 매니페스트 항목의 `start_region_id`가 파일에 없다 → 그 항목만 목록에서 빠지고 경고가 남는다 |
| EX-12 | BR-U8-22 | [바로 플레이] → 불러오기 200 `ok=false`(commit 경고) → 카드에 경고와 백업 경로, `startSession` 호출 없음 〔검토 01 R-03〕 |
| EX-13 | BR-U8-22 | `emberleaf`에서 `region-saltwake`를 지웠다 → [지금 월드로 플레이] → 세션 시작 404 → 카드가 [새로 불러와 플레이]를 권한다 〔검토 01 R-03〕 |
| EX-14 | BR-U8-22 | 불러오기 409 `{busy_sessions: 1}` → 확인 창 없이 "잠시 뒤 다시" 〔검토 01 R-03〕 |

## 10. 스토리 추적
| 스토리 | 수용 기준 | 규칙 |
|---|---|---|
| US-1.1 | `.env` 두 값 + `--profile service up -d` → 모두 healthy, `:3000`, `/health` ok, 이미지에 `api/`, README가 없는 프로필을 부르지 않음 | BR-U8-28, Infra-light |
| US-1.2 | README 첫 줄 §0, 6단계 흐름, 스크린샷 자리, 시작 명령, 디렉터리, 진행 중 절 | BR-U8-28·31 |
| US-1.3 | 원클릭으로 10~15지역 등을 불러오고 LLM 0회, 교체 확인 | BR-U8-3·5·6~11·19~22 |
| US-1.4 | 키 없이 지도·지역 화면·에디터가 열리고, 대화·턴은 "LLM 키가 필요합니다"를 보이며 500이 없음 | BR-U8-23~27 |
| US-7.3 | 진행 중 네 기능 표시 | BR-U8-31 |
| US-7.5 | 라이선스·requirements·peer 정합 | BR-U8-29·30, Infra-light(peer) |
| US-7.6 | CI가 pytest(seed)·vitest·ruff·black·tsc를 돌리고 배지 | BR-U8-33~35 |

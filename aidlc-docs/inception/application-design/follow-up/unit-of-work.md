# Follow-up Cycle — Units of Work

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Units Generation 2부. 승인된 설계를 아홉 유닛으로 나누고, 유닛마다 범위·단계·완료 조건을 정한다.

**결정**(`inception/plans/follow-up-unit-of-work-plan.md`):
- UOW-Q1=A: 아홉 유닛.
- UOW-Q2=A: mypy 게이트는 V9.
- UOW-Q3=A: V1은 main에서 따로 작은 PR로 먼저 낸다.
- UOW-Q4=A: 화면 유닛마다 가짜 API 캡처를 비공개 Artifact로 보여 준다. 실제 스택은 B&T에서 본다.

**구조**: 모놀리스 하나(백엔드 `locus/`+`api/`, 프론트 `web/`)다. 유닛은 배포 단위가 아니라 **개발 단위(모듈 묶음)**다. 유닛마다 FD → (NFR) → 코드 계획 → 코드 → 코드 리뷰 순서로 마치고 다음으로 간다.

**공통 완료 조건**(모든 유닛):
- 게이트가 GREEN이다: pytest, vitest, ruff, black, tsc.
- mypy는 기준선 11을 넘지 않는다(V9에서 0).
- `npm audit --omit=dev`는 0이다.
- 경계 테스트(`tests/test_boundaries.py`)를 통과한다.
- 바뀐 동작의 테스트가 있다.
- 유닛 code-summary를 쓰고, 이 유닛에서 닫기로 한 리뷰 지적의 처리를 적는다.

---

## V1 — CI 시한 정리

| 항목 | 내용 |
|---|---|
| **목적** | 2026-10-19 Ubuntu 26 러너 전환 전에 CI를 안전하게 한다 |
| **범위** | FR-T1 |
| **코드** | `.github/workflows/ci.yml` |
| **단계** | FD SKIP · NFR SKIP · Code(계획 + 생성) |
| **브랜치** | PR #4 병합 뒤 main에서 `chore/ci-actions`를 따로 낸다. 작은 PR이다. 병합 뒤 `feat/follow-up`이 main을 받아 들인다. 푸시·PR·병합은 사람이 한다 |
| **완료 조건** | 네 잡(backend, frontend, audit, images)이 새 주 버전 액션에서 GREEN이다. Node 20 경고가 없다. Ubuntu 26 러너에서도 통과하는지 확인한다(러너 라벨을 명시하거나, 전환 뒤 첫 실행 결과를 본다). mypy 게이트는 넣지 않는다(V9) |
| **사람이 할 일** | 푸시, PR 생성·병합(Claude는 명령을 드린다). **시한 2026-10-19** |

## V2 — 디자인 시스템

| 항목 | 내용 |
|---|---|
| **목적** | 새 TRPG·판타지 톤의 기반을 만든다. 네 화면이 모두 그 위에 선다 |
| **범위** | FR-D1~D9 |
|  | - FR-S6(프리미티브의 접근성) |
|  | - FR-C13의 도구(`useResource`·`useAction`) |
|  | - FR-D9의 서버 쪽 오류 `code` 계약(`api/errors.py`, `api/main.py` 처리기) |
|  | - NFR-3, NFR-4, NFR-7 |
| **코드** | `web/src/{index.css, ui/, layout/, map/, format/, errors/, hooks/, i18n/, api/http.ts}`, `web/package.json`(headless 라이브러리·글꼴), `api/errors.py`, `api/main.py` |
| **단계** | **FD**: HTML 시안 2~3안을 비공개 Artifact로 만든다. 사람이 고르면 토큰·글꼴·프리미티브 API·배치 틀·지도·표기 규칙·오류 코드 목록을 정한다 |
|  | **NFR light**: headless 패키지와 크기, 글꼴 부분 집합과 크기 예산, 대비 확인 방법(토큰 쌍 계산), 브라우저·기기 범위, 옆 패널 폭 상한 — 리뷰 R-05 |
|  | **Code** |
| **화면 적용** | 공유 프리미티브는 앱 전체에서 한 번에 바꾼다. 에디터 안의 대화상자(`MapCanvas` Dialog, `BuildPanel`, `NewSessionForm`)도 공유 `Dialog`로 바꾼다(요구사항 리뷰 R-01). 화면 **배치**는 V4·V6·V8이 맡는다. V2가 끝난 뒤에도 네 화면은 새 모습으로 그대로 동작해야 한다 |
| **완료 조건** | |
|  | - 고른 시안의 토큰이 `@theme`에 있다. 화면 코드에 원색 값·원문 enum·`String(e)`가 새로 생기지 않는다. |
|  | - 본문 대비 4.5:1 이상을 계산으로 확인한다. |
|  | - JS gzip이 1.3배(≈126 kB) 이내이고, 첫 화면 글꼴 합계가 760 kB 미만이다. |
|  | - 오류 응답에 `code`가 실린다(가산). 기존 vitest는 문구 단언을 사전 키 기준으로 고친다. |
|  | - 가짜 API 캡처(1280·390px)를 Artifact로 보인다. |
| **사람이 할 일** | 시안 고르기(FD), 캡처 확인 |

## V3 — 한국어 표시 백엔드

| 항목 | 내용 |
|---|---|
| **목적** | 키 없이 연 데모가 처음부터 한국어로 보이게 하는 서버 쪽 일 |
| **범위** | FR-L2, FR-L3, FR-L4, FR-C11, Q4=A(데모 카드 문구·월드 이름) |
| **코드** | `locus/shared/models/i18n.py`(새), `locus/localization/service.py`, `locus/world/demo/__init__.py` + `demo/worlds/{manifest.json, emberleaf.ko.json}`, `locus/world/worldfile/remap.py`, `api/schemas.py`, `api/routers/{world,play,gm,world_editor}.py`(번역 칸, 시딩, purge), `locus/__main__.py`(CLI 시딩) |
| **단계** | **FD**: 데모 번역 파일 형식, 종류·필드 목록(`knowledge` 포함), 해시 규칙, 재매핑 규칙(파일 안 id만, `world` 종류 제외 — 설계 리뷰 R-07), purge 지점, CLI 시딩 조건, 매니페스트 검사 항목을 정한다 |
|  | NFR SKIP · **Code** |
| **데이터** | Emberleaf ko 번역문(지역 12, NPC 15, 지식 23, 씨앗 3, 월드 이름·설명, 카드 문구)은 코드 생성 때 만든다. 사람은 화면에서 확인한다(가정 A-1) |
| **완료 조건** | |
|  | - 키 없이 데모를 불러온 뒤 API 응답의 지역·NPC·지식·씨앗·월드·데모 카드가 ko로 나온다. |
|  | - 원문 해시가 다른 번역은 쓰이지 않는다. |
|  | - 번역 파일 읽기·쓰기 왕복 속성 테스트(PBT-02). |
|  | - 매니페스트 `name` ≠ `world.id`이면 검사가 문제로 보고한다. |
|  | - 월드 교체·삭제 때 새 종류도 지운다. |
| **사람이 할 일** | (없음 — 번역문 확인은 V4 캡처와 B&T에서) |

## V4 — 홈·플레이 화면

| 항목 | 내용 |
|---|---|
| **목적** | 데모 방문자가 실제로 보는 길(홈 → 플레이)을 새 디자인으로 다시 짠다 |
| **범위** | FR-S1, FR-S2, 이 두 화면의 FR-S5·S6·FR-L1, FR-C13 가운데 홈·플레이 쪽(RE-F03, 플레이 화면의 늦은 답), FR-C14 규칙으로 함께 고치는 RE-F08(폴링 상한). FR-C5의 플레이 화면 표시(`gm_busy` — 칸은 V5가 더하므로, V4는 없으면 false로 다룬다). UX-12~16, UX-28~33 |
| **코드** | `web/src/routes/{HomePage,PlayPage,AppNav}.tsx`, `web/src/features/{home,play}/**`, 플레이용 작은 지도(`map/` 변형), 관련 vitest |
| **단계** | **FD**: 홈·플레이 배치안을 1280·390px로, ASCII 배치도와 요소 목록으로 만든다. 승인 뒤 코드를 쓴다 |
|  | NFR SKIP · **Code** |
| **완료 조건** | |
|  | - 휴대폰 폭(390px)에서 홈·플레이가 가로 스크롤 없이 쓰인다. |
|  | - 플레이 화면에 작은 지도가 있다. 내부 수치·원문 enum이 보이지 않는다. |
|  | - 닫힌 세션과 막힌 이동에 안내가 있다. |
|  | - 데모 카드가 하나로 정리돼 있다. |
|  | - 가짜 API 캡처를 Artifact로 보인다(데모 한국어판 포함). |
| **사람이 할 일** | 배치안 승인(FD), 캡처 확인 |

## V5 — GM 쓰기 정확성 (백엔드)

| 항목 | 내용 |
|---|---|
| **목적** | GM 쓰기가 겹치거나 세션 닫기·재시작과 겹쳐도 결과가 바르게 한다 |
| **범위** | FR-C1~C5, NFR-10. #9, #12, #5(a), RE-P01~P04, RE-P06, RE-P12(일부), U8 §3 피드백 몫 |
| **코드** | `locus/play/turn/{guard,advancer}.py`, `locus/play/{session_service,distortion_service}.py`, `locus/play/{event,rumor,deeds}/*`, `locus/play/{ports,models,wiring}.py`, `locus/play/storage/{postgres_repo,memory_repo}.py`, `api/{main,errors}.py`, `api/routers/{gm,play,world}.py` |
| **단계** | **FD**: 서비스별 짧은 쓰기 구간, 타임아웃, 증분 쓰기와 상태 조건 쓰기, 닫기, 끊긴 run 복구(전 세션 `running` 조회 포트, `fail_stale_runs` 처리, `_fail`의 예외 인자 — 설계 리뷰 R-01), guard 주입(R-03), 대체되는 guard 메서드의 호출부와 월드 교체 점검의 의미, `GmBusyError` 매핑 순서(R-04), 지운 지역의 사건 처리, `gm_busy`를 정한다 |
|  | **NFR light**: 겹침 재현 테스트 방식(끼워 넣기), PostgreSQL 실제 잠금 운영자 확인 절차 |
|  | **Code** |
| **완료 조건** | |
|  | - 역공학 재현 시나리오(r1 동시 해소, r2 씨앗 경합, r3 지지도 부활, r4 닫기 중 생성, r5 끊긴 run, r9 지운 지역 사건)가 회귀 테스트로 들어가 모두 바른 결과를 낸다. |
|  | - 일괄 생성 5개 동시가 그대로 동작한다. |
|  | - 플레이어 409에 내부값이 없다. |
| **사람이 할 일** | FD 승인 |

## V6 — GM 화면

| 항목 | 내용 |
|---|---|
| **목적** | GM 모드를 새 디자인의 2열로 다시 짜고, 화면 쪽 이중 실행과 늦은 답을 막는다 |
| **범위** | FR-S3, 이 화면의 FR-S5·S6·FR-L1, FR-C13 가운데 GM 쪽(#14, #15, RE-F01, F02, F04, F05, F11, F14). UX-34~42 |
| **코드** | `web/src/routes/GmPage.tsx`, `web/src/features/gm/**`, `web/src/SessionBar.tsx`(또는 옮긴 자리), GM 지도 변형, 관련 vitest |
| **단계** | **FD**: GM 정보 구성과 배치안(가정 A-5)을 정하고 승인받는다 · NFR SKIP · **Code** |
| **완료 조건** | |
|  | - 데스크톱에서 지도 옆에 패널이 있고, 허브가 기능별로 나뉜다. |
|  | - 타임라인은 최신부터 보이고 더 보기가 있다. |
|  | - 세션 닫기는 확인을 받는다. GM 지도는 끌리지 않는다. |
|  | - [턴 진행]을 두 번 눌러도 한 번만 진행된다. |
|  | - 세션을 바꾼 뒤 옛 답이 그려지지 않는다. |
|  | - 390px에서 가로 스크롤이 없다. |
|  | - 캡처를 Artifact로 보인다. |
| **사람이 할 일** | 배치안 승인(FD), 캡처 확인 |

## V7 — 월드·지식 정확성

| 항목 | 내용 |
|---|---|
| **목적** | "지역마다 다르게 안다"를 바르게 하고, 제작자의 손작업과 월드를 지킨다 |
| **범위** | FR-C6, C7, C8, C9, C10, C12. RE-W01, W02, W03(같은 코드), W04, W18, #10, #13 |
| **코드** | `locus/knowledge/{consensus,cache}.py`, `locus/shared/storage/{base,neo4j_repo,persistence}.py`, `locus/world/{build.py, carry_over.py(새), worldfile/{import_,remap}.py, augmentation/{questions,apply}.py, editor/*}`, 테스트 대역(`tests/shared/storage/fakes.py`, `tests/world/services/test_services.py`), README 문장(빌드와 NPC) |
| **단계** | **FD**: 합의 출처 규칙과 속성(PBT-03), WorldMeta 저장 순서와 실패 경로의 `ok`(설계 리뷰 R-08), `_backup` 반환 계약(미설정은 통과, 실패만 중단)과 옛 스냅샷을 로더로 읽기(R-02), 라벨 인자 호출부 11곳(R-05), 실제 `compute_consensus` 시그니처(R-06), 이어 붙이기 규칙, 보강 `needs` 표를 정한다 |
|  | NFR SKIP · **Code** |
| **완료 조건** | |
|  | - 연결 순서를 섞어도 합의 결과가 같다(속성 테스트). |
|  | - 교체 중 다른 프로세스의 캐시가 연결 없는 스냅샷을 잡지 않는다(r08 재현 회귀). |
|  | - 백업이 실패하면 옛 월드가 남는다. |
|  | - 다시 빌드한 뒤 옛 NPC·씨앗이 남거나 경고로 보고된다. |
|  | - 중복 id World File을 거절한다. 라벨 없는 삭제가 다른 라벨을 지우지 않는다. |
|  | - 엔티티 보강 질문에 제목 칸이 없다. |
| **사람이 할 일** | FD 승인 |

## V8 — 에디터 화면 (P1)

| 항목 | 내용 |
|---|---|
| **목적** | 제작자 도구를 새 디자인의 배치로 다시 짠다 |
| **범위** | FR-S4, 이 화면의 FR-S5·S6·FR-L1, FR-C12의 카드 쪽. UX-17, UX-19~25, UX-27 |
| **코드** | `web/src/routes/EditorPage.tsx`, `web/src/features/editor/**`, 에디터 지도 변형, 관련 vitest |
| **단계** | **FD**: 에디터 배치안을 정하고 승인받는다 · NFR SKIP · **Code** |
| **넘길 때(P1)** | 시간이 모자라면 이 유닛을 `next-cycle.md`로 넘긴다. 넘겨도 V2의 공유 프리미티브·대화상자·표기 규칙·오류 문장은 에디터에 이미 적용돼 있다. 넘어가는 것은 FR-S4 목록의 **배치**와 에디터 전용 조작이다. FR-D5의 "에디터 390px 세로 쌓기"도 함께 넘어간다(요구사항 리뷰 R-01 정리) |
| **완료 조건** | |
|  | - 지도 위 띠가 하나로 정리돼 있다. 인스펙터 섹션은 접히고, 위험 버튼은 떨어져 있다. |
|  | - 추가한 지역이 선택된다. 지도를 눌러도 보강 입력이 남는다. |
|  | - 390px에서 가로 스크롤이 없다. |
|  | - 캡처를 Artifact로 보인다. |
| **사람이 할 일** | 배치안 승인(FD), 캡처 확인 |

## V9 — 부채·문서 마무리

| 항목 | 내용 |
|---|---|
| **목적** | 게이트를 강화하고 문서를 코드와 맞춘다. 남은 일을 다음 주기 목록에 적는다 |
| **범위** | FR-T2(dev audit 0), FR-T3(mypy 0 + CI 게이트), FR-T4(문서), FR-T5(env), FR-T6(테스트 위생), FR-T7(라이브 시나리오), FR-C14(`next-cycle.md` — 요구사항 리뷰 R-03의 U8 이월 묶음을 명시), FR-D10(`index.html`) |
| **코드** | `web/package*.json`, `locus/**`·`api/**`의 mypy 11건, `.github/workflows/ci.yml`(mypy 단계), `CLAUDE.md`, `README.md`, `web/README.md`, `aidlc-docs/operations/{operations,next-cycle}.md`, 낡은 docstring, `env.example`, `tests/**`(시간 초과 의존·sleep·sqlite dispose), `scripts/live_scenario.py`, `web/index.html` |
| **단계** | FD SKIP · NFR SKIP · **Code** |
| **완료 조건** | |
|  | - mypy 0이고 CI에 mypy 단계가 있다. npm audit 전체 0이다. |
|  | - pytest 경고에 sqlite ResourceWarning이 없다. 테스트 시간에서 고정 대기 11 s가 사라진다. |
|  | - CLAUDE.md Status와 Gates가 실제와 맞다. |
|  | - `next-cycle.md`에 이번에 넘긴 항목이 모두 있다. |
| **사람이 할 일** | (없음) |

---

## 그 뒤: Build and Test

- 게이트를 전부 돌린다(NFR-1).
- **사람 화면 확인 체크리스트**(NFR-2): 네 화면을 1280·390px로 본다. 대비 확인 방법과 브라우저·기기는 V2 NFR에서 정한다.
- 실제 스택은 compose로 띄운다(띄우기 전에 여쭙는다, `WEB_PORT=13000`). 키 없는 데모가 한국어로 보이는지 확인한다.
- 라이브 시나리오(운영자, 키 있음)를 돌린다. PostgreSQL 동시성 운영자 확인도 한다(NFR-10).

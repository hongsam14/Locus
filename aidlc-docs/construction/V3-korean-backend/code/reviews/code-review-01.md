# V3 한국어 표시 백엔드 — Code Review 01

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**이 리뷰가 하는 것**: 승인된 V3 코드가 승인된 설계(BR-V3-*)를 지키는지 결함 위주로 확인한다. 범위는 `git diff 580beb4..c1fc4c9`, 커밋 15개, 37파일 +2813/−67이다. 한국어 데이터의 정확성과 새 테스트의 힘도 본다. 코드는 고치지 않았다(리뷰 전용).

**방법**: V2 리뷰와 같은 방식이다.
- 네 각도를 병렬로 돌렸다.
  - localization과 CLI
  - world와 데모 데이터 계약
  - api 합성 루트와 웹 클라이언트
  - 한국어 데이터와 테스트 품질
- 재현물은 세션 scratchpad의 `v3review/{loc,world,api,data}/`에만 두었다. 저장소 파일은 바꾸지 않았다(`git status` 같음).
  - 리뷰어들의 pytest가 gitignore된 `.coverage`·`.hypothesis/`를 새로 썼다. 추적 파일에는 영향이 없다.
- 테스트 힘은 저장소를 바꾸지 않고 확인했다. 코드를 메모리에서만 바꾼 뒤 전체 테스트를 돌려 살아남는지 봤다(mutation probe).
- 이 세션이 상위 후보의 코드 자리를 다시 읽어 확인했다.
  - CLI 순서(`locus/__main__.py:285-292`)
  - 엔진 설정(`locus/shared/storage/sql.py:17`)
  - 기동 스키마(`api/main.py:76-77`)
  - 홈 효과 순서(`web/src/App.tsx:14-23`, `routes/HomePage.tsx:24-27`, `features/home/DemoCards.tsx:12-14`)
  - 지식 제목 대체값(`locus/shared/storage/graph_mapping.py:307`)
- 판정: **C** = 재현했거나 코드로 기제가 확정됨. **P** = 기제는 실재하지만 조건이 이번에 직접 돌리지 못한 환경(키 있는 서버, 화면이 `*_ko`를 읽는 V4)에 달림.

## 1. 지적 (심각도 순)

| # | 위치 | 지적 | 판정 | 심각도 | 권장 조치 |
|---|---|---|---|---|---|
| 1 | `api/routers/world.py:123-124`(`_after_replace` → `purge_world_translations`), BR-V3-13 | 어느 교체든 그 월드의 번역 행을 **전부** 지운다. 새 월드가 같은 id와 원문을 가져도 지운다. | C(재현: 123행 → 0) | **medium**(설계 수준) | 교체 뒤에는 새 월드에 **없는 id**의 행만 지운다. |
|  |  | 읽기는 이미 해시로 지켜지므로(BR-V3-01) 남겨도 틀린 글은 안 보인다. 그래서 전부 지우는 것은 깔끔함 말고 얻는 것이 없다. |  |  | 저장소 포트에 `purge_world_except(world_id, keep_ids)` 하나를 둔다. |
|  |  | 장면: 제작자가 데모를 World File로 내보냈다가 같은 월드로 다시 불러온다(`WorldFileBar` replace). |  |  | 살아 있는 id는 교체 뒤 스냅샷의 지역·NPC·씨앗·지식·월드 id다. |
|  |  | - 키 없는 서버: 데모를 다시 불러올 때까지 한국어가 사라진다. 다시 불러오면 방금 불러온 파일이 버려진다. |  |  | 남은 행은 해시가 계속 거른다. |
|  |  | - 키 있는 서버: LLM이 다시 번역해 손으로 다듬은 문장을 바꾼다. |  |  |  |
| 2 | `emberleaf.ko.json`: `k-elders-library.statement`, `npc-elowen.description`, `k-older-walls.statement` | "sealing wards"를 **봉인 결계**로 옮겼다. 결계는 막(barrier)이라 도서관에 두거나 읽을 수 없는데, 원문은 적어 두고 읽는 봉인 주문이다 | C(원문 대조) | **medium** | 세 곳 모두 "봉인 주문서"로 고친다 |
| 3 | 같은 파일: `npc-ketta.description`, `k-forge-oath.statement` vs `npc-durgan.description`, `k-forge-oath.title` | "Great Forge" → 그레이트 포지, "forge oath" → 대장간 맹세로 갈려, 같은 항목의 제목(대장간 맹세)과 문장(그레이트 포지에서)이 이어지지 않는다 | C | **medium** | 장소의 종류 낱말을 옮기는 규칙(Q1=A: 항구·발굴지)대로 "큰 대장간"으로 한다 |
| 4 | `tests/localization/test_seed.py::test_without_an_llm_there_is_a_service_that_never_warms` | "키 없으면 warm하지 않는다"(BR-V3-02)를 지키지 못하는 테스트다. 인라인 스케줄러는 `_warm`의 `finally`에서 `_in_flight`를 비우므로, 두 가드를 지워도 통과한다. 오류는 삼켜지고 기록만 된다 | C(mutation) | **medium**(테스트) | `warm_scheduler=rec.append`로 만들고 `rec == []`를 단언한다 |
| 5 | `tests/api/test_demo_seeding_api.py::test_a_replace_drops_the_worlds_rows_only_…` | BR-V3-13의 "월드 이름 행을 id로 지운다"가 검증되지 않는다. 심은 행이 재시딩과 같은 키라 덮여 버린다. `purge(kind="world", ids=[w])`를 지워도 전체 테스트가 통과한다 | C(mutation) | **medium**(테스트) | 다른 언어(`ja`) 행을 심거나, 시딩이 실패하는 저장소로 교체해 그 행이 사라졌는지 본다(#1을 고치면 그 규칙으로 다시 쓴다) |
| 6 | `web/src/App.tsx:14-23`, `routes/HomePage.tsx:24-27`, `features/home/DemoCards.tsx:12-14` | 홈의 두 목록이 첫 로드에 `?lang=`을 보내지 않고, 언어를 바꿔도 다시 읽지 않는다. 자식 효과가 App의 `getLangs()`보다 먼저 돌고 의존이 `[]`이기 때문이다. V4가 `title_ko`·`name_ko`를 쓰면, 서버 기본 ko에서 영어를 고른 사람에게 한국어 카드가 보인다 | C(코드), 영향은 P(V4부터) | low → V4에서 medium | 효과 의존에 `useRequestLang()`을 더한다. V4가 홈을 다시 쓰므로 V4 FD의 조건으로 넘겨도 된다 |
| 7 | `k-sealed-sorcerer.statement`·`title` | "Sorcerer"와 "mage"가 둘 다 마법사다. 마법사들의 마을이 있는 세계에서 "봉인된 마법사"는 모호하다. 원문이 Sorcerer를 고른 것은 원작의 이름을 피하려는 것인데(BR-U8-10), "애션 마법사"는 그 이름을 다시 떠올리게 한다 | C | medium-low | "애션 술사", "봉인된 술사"로 고친다 |
| 8 | `locus/world/demo/__init__.py` `translations()`, `locus/shared/models/i18n.py:91-99` | 실행 중 번역 파일의 항목 하나가 모델 오류면 파일 전체가 0개로 읽힌다. 빈 `text`, 모르는 키, 맞지 않는 필드가 그런 오류다. BR-V3-10과 독스트링은 "읽을 수 있는 항목은 시딩한다"고 적었다. CI가 잡으므로 출고 데모는 안전하다 | C(재현) | low | 실행 경로는 항목을 하나씩 검증해 틀린 것만 건너뛴다 |
| 9 | `locus/__main__.py:285-292` | CLI는 불러오기가 `ok`가 아니면 교체 지우기를 건너뛴다. API는 `replaced`면 `ok`와 무관하게 지운다. BR-V3-14·28과 어긋난다. 해시가 지키므로 남은 행은 고아 행일 뿐이다 | C(재현, 두 리뷰어) | low | 교체 지우기를 `ok` 검사 위로 올린다 |
| 10 | `locus/world/demo/__init__.py` `translations()` | 실행 중에는 파일의 `lang`·`world_id`가 매니페스트와 달라도 쓴다. 검사만 문제로 적는다. 장면: 매니페스트가 `"ja": "emberleaf.ko.json"`이고 ja를 지원하면, 한국어 행이 `ja`로 들어가 `?lang=ja`에 한국어가 보인다 | C(재현) | low | 다르면 `[]`과 경고를 낸다 |
| 11 | `locus/localization/wiring.py:45-48`, `locus/shared/storage/sql.py:17` | V3부터 키 없는 서버도 표시 언어 읽기마다 PostgreSQL을 읽는다. 월드 목록, 이름표(4번), 지식, 에디터 보기가 그렇다. 엔진에 `connect_timeout`·`pool_pre_ping`이 없어, DB가 응답하지 않으면 요청마다 연결 시한까지 기다린다. 키 있는 서버는 원래 그랬다 | C(코드) | low | 엔진에 연결 시한을 두거나 알려진 한계로 적는다. 배포 설정이므로 B&T·V9에서 정해도 된다 |
| 12 | `locus/world/worldfile/texts.py` vs `graph_mapping.py:307` | 지식 `title`이 빈 World File은 번역 대상에서 빠진다. 그런데 그래프에서 읽을 때는 `fallback_title(statement)`가 화면에 나온다. 그 제목은 번역할 길이 없고, 검사 (h)도 모른다. Emberleaf에는 없다 | C(재현) | low | `translatable_texts`가 지식 제목에 같은 대체값을 쓴다 |
| 13 | `locus/world/demo/__init__.py` 원문 바뀜 문장 | 양쪽을 60자에서 잘라, 60자 뒤만 바뀌면 같은 두 문자열이 찍힌다. 긴 설명의 오타 수정이 대표적인 경우다 | C(재현) | low | 처음 다른 글자 둘레를 잘라 보인다 |
| 14 | 테스트: CLI 교체 지우기, 카드 길이 300/200, 문체 검사 | 세 가지가 약하다. | C(mutation) | low | 각 사례를 더한다 |
|  |  | - CLI의 두 `purge`를 지워도 통과한다. |  |  |  |
|  |  | - 설명·크레딧 상한을 지워도 통과한다. |  |  |  |
|  |  | - 문체 검사 `endswith("다.")`는 합쇼체 "니다."도 받고, 마지막 문장만 본다. |  |  | 문체는 문장마다 "다."이고 "니다."가 아닌지 본다 |
| 15 | 번역 문장 다듬기 | 원문 대조에서 나온 작은 것들이다. | C | low | 리뷰 각도 4의 제안대로 고친다 |
|  |  | - "마흔 해 겨울 전에" → "마흔 겨울 전에" |  |  |  |
|  |  | - 배가 "내리는/댄다" → "닿는/들어온다" |  |  |  |
|  |  | - 스톤브로 → 스톤브라우(brow /braʊ/) |  |  |  |
|  |  | - 나룻배·선장 → 연락선(바다 건너 본토행) |  |  |  |
|  |  | - "세금을 매기지 않는 물건" → "세금을 피한 물건" |  |  |  |
|  |  | - "등을 돌린다" → "칼끝을 돌린다", 부하 → 간부 |  |  |  |
|  |  | - 주어 없는 "줄째로 불태워지고" |  |  |  |
|  |  | - "고리로 봉인된" → "고리 문양으로" |  |  |  |
|  |  | - 궁수대장 → 궁수 대장, 밤 시장 → 야시장 |  |  |  |
|  |  | - 카드 설명의 조각 문장 |  |  |  |

## 2. 낮은 심각도와 정리

| 위치 | 지적 | 제안 |
|---|---|---|
| `api/routers/world.py:278` + `catalog.py:27` | U2 전 월드는 `name=id`라, 키 있는 서버가 월드 id를 LLM에 번역시킨다 | meta가 없는 줄(`name == id`)은 번역하지 않는다 |
| `api/routers/world.py:446` | `model_dump(exclude={"ok"})`가 손으로 쓴 목록이라, `ImportReport`에 계산 칸이 하나 더 생기면 500이 난다 | `exclude=set(ImportReport.model_computed_fields)` |
| `locus/__main__.py:296-303` | 언어는 있지만 지원하는 언어가 없을 때 "none in this demo"라고 적는다 | "no supported language" |
| `locus/world/demo/__init__.py` `_path` | 폴더 안의 심볼릭 링크가 밖을 가리키면 지나간다. 매니페스트는 믿는 패키지 데이터다 | `resolve()` 뒤 `is_relative_to` |
| `_read_translations` | 아주 깊은 JSON은 `RecursionError`가 밖으로 나간다. 매니페스트·World File에도 같은 틈이 원래 있다 | `RecursionError`도 잡는다 |
| `DemoWorlds.card()` | 쓰는 곳이 없다. API는 `info.i18n`을 직접 읽는다 | 지우거나 API가 쓴다 |
| `test_deed_turns.py`·`test_play_api.py` 추가 단언 | `npc_id`는 있는지만, `level_path_ids`는 길이만 본다(경로 한 칸) | 실제 id와 같은지 본다 |
| `test_demo_translations.py` `FORBIDDEN_KO` | 카드 문구(`i18n.ko`)는 검사하지 않는다 | 카드 제목·설명도 검사한다. 크레딧은 유일하게 허용된 언급이다 |
| `capabilities.test.ts` | `configureLangs` 상태를 되돌리지 않는다. 지금은 해가 없다 | 테스트 끝에 기본 상태로 되돌린다 |
| `code-summary.md` § 6 "키 없는 서버의 기동" | **틀린 서술이다.** V3 전에도 `api/main.py:77`이 LLM 여부와 무관하게 `ensure_localization_schema`를 불렀다 | 그 줄을 지우고 #11로 바꾼다 |

## 3. 결함 아님

- **목록 두 곳의 400**(`/worlds?lang=fr`, `/demos?lang=fr`): 다른 모든 읽기와 같은 계약이다. 웹은 서버가 알려 준 언어만 보낸다(`requestLang`). 기본 언어는 설정 검증이 지원 언어 안에 있도록 묶는다.
- **키 있는 서버의 시딩 교착**(추측): 한 트랜잭션의 123행 upsert와 동시 warm 배치가 같은 키를 다른 순서로 넣으면 교착이 날 수 있다는 가설이다. 재현하지 못했다. warm은 키 단위로 따로 쓰고, 시딩은 데모를 불러올 때 한 번이다. 알려진 한계 R-04 쪽에 함께 적어 둔다.
- **CLI `world import/build --replace`가 번역을 지우지 않음**: V3 전부터 그렇고, 해시가 지킨다. #1을 고치면 이 경로도 같은 함수를 쓰는 편이 일관된다(선택).

## 4. 확인한 것

- **시딩**
  - 해시 규칙은 그대로라 기존 행이 맞는다. `stale`·`unknown`이 맞게 센다.
  - 한 배치 안의 같은 키는 dedupe되고 나중 것이 이긴다. Postgres(SQLite 대역)와 메모리 저장소가 같게 동작한다.
  - `world_id`를 적고, id·`created_at`을 유지한다.
- **재매핑**: `translations()`·`texts()`·`seed`가 세 경우 모두 seeded 123, stale 0, unknown 0이다.
  - 자기 id
  - `w2`로 재매핑
  - 강제 재매핑
  - `world` 항목은 대상 id다. 파일 밖 id는 unknown으로 버린다.
- **검사**
  - (a)~(h)와 메시지 산술("and N more")이 맞다.
  - 절대 경로·`..`·빈 경로·디렉터리·비UTF-8·객체 아님·`entries` 사전을 모두 문제로 적고 항목을 남긴다.
  - FR-C11은 World File 검사 실패 항목에서 번역을 읽지 않는다.
- **carry**: `description`을 먼저 보고, 해시가 맞는 행만 옮긴다. 여러 언어를 옮기고, 실패는 삼킨다. 쓰기 응답은 번역하지 않는다.
- **API**
  - 데모 불러오기의 순서(가져오기 → 교체면 지우기 → ok면 시딩)를 지킨다.
  - `replace=false`는 지우지 않는다.
  - 확인이 없으면 409 `sessions_open`이다.
  - 세션 행(`world_id` 없음)은 교체에 살아남는다. 닫힌 세션이 옮겨진 사건 번역을 그대로 읽는다.
  - 이름표는 404·400·503과 빈 맵을 맞게 낸다. `TRANSLATION_TARGET_LANG=en`이면 목록과 이름표가 비고 시딩은 ko로 된다.
- **경계와 불변**: 경계 테스트를 통과한다. 시딩은 그래프·색인에 쓰지 않는다. 내보내기에 한글이 없다.
- **데이터**
  - 숫자가 모두 맞다(마흔, 셋, 다섯, 둘, 절반, 사흘에 한 번, 동전 한 닢).
  - 문장마다 해라체이고, 이름·역할·제목에는 마침표가 없다.
  - 원작 이름의 한국어형이 없다. 카드 길이는 6·87·57이다.

## 5. 남은 결정 (사람이 고른다)

- § 1의 어느 것을 V4 전에 고칠지:
  - **#1**은 설계 규칙(BR-V3-13)을 바꾸는 일이다. 저장소 포트 메서드 하나가 는다.
  - **#2·#3·#7·#15**는 번역 문장이다. 가정 A-1에 따라 문체는 사람이 확인한다.
  - **#6**은 V4 화면 몫으로 넘길 수 있다.
  - **#11**은 배포 설정이다.

## 6. 처리 결과 (사람의 선택: 코드·테스트 전부, 번역 제안 전부)

2026-10-08. 고친 것마다 재현 테스트를 붙였다.
- 새 테스트 가운데 12개를 고치기 전 코드에 돌려 실패하는 것을 확인했다.
- 커밋은 셋이다. 커밋마다 다른 변경을 치워 둔 상태에서 게이트를 돌려 그 커밋만으로 GREEN인지 확인했다.

| # | 처리 | 커밋 |
|---|---|---|
| 1 | 교체 뒤 새 월드에 없는 id의 행만 지운다. 저장소 `purge_world_except`, 서비스 `prune_world`, api `_held_ids`가 새로 생겼다. 새 월드를 읽을 수 없으면 지금처럼 모두 지운다. BR-V3-13·BLM § 7 정정 | `132a4e8` |
| 2·3·7·15 | 번역문을 고쳤다(주문서, 큰 대장간, 술사, 연락선, 스톤브라우, 배, 세금, 간부, 겨울, 주어, 야시장, 띄어쓰기, 카드 문장·크레딧). 출고 검사는 `[]`이고, 결계·그레이트·나룻배·부하는 0곳이다 | `b4682cb` |
| 4 | 번역기가 없으면 스케줄러가 한 번도 불리지 않는지 보는 테스트 | `132a4e8` |
| 5 | 월드를 읽을 수 없을 때 표시 없는 월드 이름 행까지 지우는지 보는 테스트. 새 규칙에 맞춰 교체 테스트도 다시 썼다(없는 id만 지움) | `132a4e8` |
| 6 | V4로 넘겼다(code-summary § 7). V4가 홈을 다시 쓰며 목록 읽기를 표시 언어에 묶는다 | — |
| 8 | 실행 중에는 항목마다 검증하고, 틀린 항목만 건너뛴다 | `eab0901` |
| 9 | CLI가 교체면 `ok`와 무관하게 지운다(ok면 prune, 아니면 전부). "no supported language" 문장도 고쳤다 | `132a4e8` |
| 10 | 실행 중 다른 언어·월드용 파일은 쓰지 않는다 | `eab0901` |
| 11 | code-summary § 6의 알려진 한계로 적었다. 엔진 시한은 V9, 실제 확인은 B&T | 문서 |
| 12 | 지식 제목이 비면 그래프가 보이는 대체 제목을 번역 대상으로 쓴다 | `eab0901` |
| 13 | 원문 바뀜 문장이 처음 다른 글자 둘레를 보인다 | `eab0901` |
| 14 | 테스트 셋을 더했다: CLI 교체 지우기, 카드 300/200 상한, 문체(문장마다 "다."이고 "니다." 아님) | `132a4e8`, `eab0901` |

§ 2 처리:

| 항목 | 처리 | 커밋 |
|---|---|---|
| U2 전 월드 id 번역 | `name == id`인 줄은 번역하지 않는다 | `132a4e8` |
| `model_dump(exclude=…)` | `ImportReport.model_computed_fields`를 쓴다 | `132a4e8` |
| CLI "none in this demo" | "no supported language"와 구별한다 | `132a4e8` |
| 심볼릭 링크 | `resolve()` 뒤 폴더 안인지 본다 | `eab0901` |
| `RecursionError` | 번역 파일·World File·매니페스트 읽기에서 잡는다 | `eab0901` |
| `DemoWorlds.card()` | 지웠다 | `eab0901` |
| id 단언 | `npc_id == "n1"`, `level_path_ids == [region_id]` | `132a4e8` |
| `FORBIDDEN_KO` | "리스항구"를 더했다. 카드 제목·설명도 검사한다 | `eab0901` |
| `capabilities.test.ts`의 `configureLangs` | 고치지 않았다. 되돌릴 API가 없고, 테스트 끝 상태가 기본(ko, ko·en)과 같아 다음 테스트에 영향이 없다 | — |
| code-summary § 6 틀린 줄 | 취소선과 정정 표시. #11로 바꿨다 | 문서 |

게이트(고친 뒤):
- 백엔드: pytest 1048(+14), ruff·black 깨끗, mypy 11, 경계 테스트 통과
- 웹: 바뀐 것 없음(vitest 424 + skip 1 그대로)

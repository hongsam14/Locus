# V3 한국어 표시 백엔드 — Code Generation Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V3(실행 3/9), Code Generation 1부(계획). 승인된 V3 기능 설계를 코드로 옮긴다. 목표는 키 없이 불러온 데모가 API에서 한국어로 나오게 하는 것이다. 이 계획이 V3 코드 생성의 유일한 기준이다.

**근거**:
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-L2·L3·L4, FR-C11
  - NFR-5·6·8·9
  - 가정 A-1·A-2
- 유닛: `inception/application-design/follow-up/unit-of-work.md` V3, 맵 `unit-of-work-story-map.md`
- 설계: `inception/application-design/follow-up/{components,component-methods,services,component-dependency}.md`
- 승인된 FD: `construction/V3-korean-backend/functional-design/*`
  - BLM § 1~12, BR-V3-01~28, TP-V3-1~12, domain-entities § 1~7
  - 리뷰 01의 R-01~R-08은 Accepted risk다. 아래 실행 메모 § 1.1이 단계로 옮긴다.

**단계 표기**:
- 단계마다 체크박스를 고친다. 단계는 그 단계의 테스트가 GREEN인 상태로 끝낸다.
- 단계마다 `feat/follow-up`에 커밋한다. **이 계획의 승인이 이 커밋들의 허락이다.**
- 푸시·PR은 사람이 한다.

---

## 1. 단위 맥락

| 항목 | 내용 |
|---|---|
| 요구사항 | FR-L2(번역 범위 → 이름표, Q5=A) · FR-L3(데모 한국어판) · FR-L4(불변) · FR-C11(매니페스트 이름) · NFR-5(가산) · NFR-6(PBT-02) · NFR-8(경로) · NFR-9(키 없이) |
| shared | `locus/shared/models/i18n.py`[새], `locus/shared/models/__init__.py` |
| localization | `service.py`(번역기 없음·`seed`·`carry`), `models.py`(`SeedReport`, 독스트링), `wiring.py`(키 없는 서비스), `__init__.py` |
| world | `worldfile/texts.py`[새], `worldfile/remap.py`(`remapped_id`), `demo/__init__.py`, `demo/worlds/{manifest.json, emberleaf.ko.json[새]}` |
| knowledge·play | `knowledge/query.py`(`level_path_ids`), `play/models.py`(`RegionView.level_path_ids`), `play/player/service.py`, `play/turn/advancer.py`(`deed_seeded`의 `npc_id`) |
| api | `schemas.py`, `routers/world.py`, `routers/world_editor.py`, `routers/gm.py` |
| CLI | `locus/__main__.py`(`world demo` 시딩) |
| 웹 | `web/src/types.ts`, `web/src/api/world.ts`. 타입과 API 함수만 바꾼다. 화면은 V4·V6·V8 |
| 테스트 | `tests/shared/`, `tests/localization/`, `tests/world/`, `tests/api/`, `tests/play/`, `tests/test_cli.py`·`tests/test_demo_as_data.py`(있는 파일에 더함), `web/src/__tests__/` |
| 바꾸지 않는 것 | 화면 코드, World File v1, 그래프·색인·임베딩, 대화·서술 언어 규칙, 세션 내용 번역(소문·사건·행적)의 지금 경로 |
| 의존 | V2(오류 `code` 계약: `not_found`·`unsupported_lang`·`service_unavailable`) |
| 내는 계약 | V4·V6·V8에 셋을 낸다. |
|  | - 이름표 `GET /api/world/worlds/{w}/names?lang=` → `WorldNames` |
|  | - 목록 칸 `DemoInfo.title_ko`… · `WorldInfo.name_ko`… |
|  | - `RegionView.level_path_ids`, `deed_seeded.payload.npc_id` |

### 1.1 실행 메모 (FD 리뷰 01, 승인 때 Accepted risk)

- 〔실행 메모 R-01〕 **CLI 시딩의 DB 도달 판단**(Step 9). `locus/__main__.py`의 `world demo`는 불러오기 뒤 `assemble_localization(shared)`를 `try`로 감싼다. 결과는 넷이다.
  - 예외가 나면 `translations: skipped (database unreachable: <예외 이름>)` 한 줄을 찍는다. `ensure_schema`가 DB에 닿지 못하는 경우다.
  - `settings.translation_enabled`가 거짓이면 `translations: off` 한 줄을 찍는다.
  - `shared.sql_engine`이 `None`이면 `translations: skipped (no database configured)` 한 줄을 찍는다.
  - 셋 모두 종료 코드는 불러오기 결과대로다.
  - TP-V3-9에 "저장소가 예외를 던지면 skipped, 종료 코드 0" 사례를 더한다.
- 〔실행 메모 R-02〕 **승인된 설계와 달라지는 것**(Step 1.3). code-summary § 5에 표를 둔다. 상류 문서 해당 줄에는 〔V3 FD Q5=A 정정〕 한 줄 메모를 단다. 다음 유닛 설계가 옛 계약을 읽지 않게 하려는 것이다. 표의 줄:
  - (1) `component-dependency.md:109` V3→V4 계약과 `component-methods.md:221-225`의 `RegionViewOut.region_name_ko`·`SeedViewOut.title_ko`·`NpcOut` 칸은 만들지 않는다. 대신 이름표와 목록 칸을 쓴다. 영향 유닛: V4·V6·V8.
  - (2) `unit-of-work.md` V3의 코드 목록(`routers/{play,gm,world_editor}.py` "번역 칸")과 완료 조건 "API 응답의 지역·NPC·지식·씨앗·월드·데모 카드가 ko"는 "이름표·지식 칸·월드 목록·데모 카드가 ko"로 읽는다.
  - (3) 메서드 모양이 바뀐다.
    - `TranslationEntry`: `lang`·`source_hash` 칸 대신 `source`, 해시는 속성(Q2=A).
    - `SeedReport.missing` → `unknown`.
    - `seed`가 `lang`·`world_id`를 받는다.
    - `DemoWorlds.translations`가 `target_world_id`·`remapped`를 받는다.
    - `remapped_id`는 api가 아니라 world(`DemoWorlds`) 안에서 쓴다(`component-dependency.md:18`).
  - (4) `carry`[새](씨앗 → 사건, BR-V3-17)를 더한다.
- 〔실행 메모 R-03〕 **이름표의 두 빈틈**(Step 8).
  - `WorldContainer.cache`가 `None`이면 지금 규칙(`need_service`)대로 503 `service_unavailable`이다.
  - 큰 월드의 첫 읽기 warm에는 상한을 두지 않는다. 까닭은 셋이다.
    - 텍스트마다 한 번만 번역되고 캐시에 남는다.
    - 진행 중 키는 다시 예약되지 않는다(`_in_flight`).
    - 동시 실행 수는 `TRANSLATION_WARM_WORKERS` 풀이 묶는다.
  - 이 결정과 비용(텍스트 수만큼 LLM 호출 한 번씩, 키가 있을 때만)을 code-summary에 적는다.
- 〔실행 메모 R-04〕 **시딩과 진행 중 warm**(Step 3). `seed`는 넣은 키를 `_in_flight`에서 지운다. 그래도 이미 돌던 warm이 시딩 뒤에 끝나면 같은 키를 LLM 번역으로 덮을 수 있다. 키가 있고, 같은 텍스트를 불러오기 직전에 읽었을 때만 생긴다.
  - BR-V3-15는 "시딩은 그 시점의 행을 덮는다"로 읽는다.
  - 남는 경우는 code-summary의 알려진 한계에 적는다. 데모를 다시 불러오면 바로잡힌다.
- 〔실행 메모 R-05〕 **월드 사이 id 충돌**(Step 3, code-summary). `locus/localization/models.py`의 독스트링 "source ids are UUIDs"를 고친다. 새 문장: "id는 월드 안에서만 유일하다. 월드 사이 충돌은 해시가 틀린 글을 막고, 서로 덮는 비용만 남는다." 알려진 한계에 적는다.
- 〔실행 메모 R-06〕 **매니페스트 키 형식**(Step 5). `i18n`·`translations`의 키 형식(`^[a-z]{2}$`, `en` 아님)과 카드 문구 길이는 매니페스트 항목 모델 검증으로 둔다. 틀리면 지금처럼 그 항목이 빠진다(BR-V3-12).
  - Q3=A의 "실행은 너그러움"은 **번역 파일**의 문제(BR-V3-08 (a)~(h))에 대한 규칙이다. 매니페스트 자체의 형식 오류는 영어 `title`이 틀린 것과 같은 매니페스트 오류로 다룬다. 이 예외와 까닭을 `demo/__init__.py` 독스트링과 code-summary에 적는다.
  - `_read_manifest` 흐름은 이렇다. `_check`가 문제를 돌려주면 지금처럼 항목을 뺀다. 그렇지 않으면 항목을 넣고 `problems.extend(_check_translations(...))`를 한다.
- 〔실행 메모 R-07〕 **`carry`**(Step 3·8).
  - 시그니처: `TranslationService.carry(sources: Sequence[TranslationKey], target: TranslationKey, *, text: str, langs: Sequence[str], session_id: str | None) -> int`. 옮긴 행 수를 돌려준다.
  - api의 `carry_translation` 도우미는 예외를 기록만 하고 0을 돌려준다. 시작 응답(201)은 깨지 않는다.
  - TP-V3-10에 저장소 실패 사례를 더한다.
- 〔실행 메모 R-08〕 **테스트 계획 보강**(Step 3·8·11).
  - (a) TP-V3-12는 "**시딩 단계의** 그래프·검색 쓰기 호출이 0"으로 센다. 불러오기 자체의 쓰기는 세지 않는다.
  - (b) 시딩·purge 저장소 예외가 불러오기 응답을 깨지 않는 사례를 TP-V3-7에 더한다.
  - (c) LLM이 있을 때 이름표의 빠진 항목이 warm에 넘어가는 사례를 TP-V3-6에 더한다. 스케줄러가 한 번 불린다.
  - (d) `TranslationService.__init__(store, translator: Translator | None, …)`. `translator`가 `None`이면 `enrich`가 빠진 항목을 예약하지 않는다.

### 1.2 실행 메모 (코드 계획 리뷰 01, 승인 때 Accepted risk)
- 〔실행 메모 R-01〕 Step 5.5는 기존 `tests/world/test_demo.py`도 고친다.
  - `_workdir`/`_entry`가 항목마다 World File 사본을 둔다. 사본 이름은 `<name>.world.json`이고, 그 안의 `world.id`를 항목 `name`으로 다시 쓴다.
  - 그래서 FR-C11 검사 뒤에도 지금 단언(`list() == ["isle"]`, 문제 6개)이 그대로다.
  - FR-C11 문제는 따로 만든 항목 하나로 본다.
- 〔실행 메모 R-02〕 Step 9의 번역 한 줄은 **stderr**로 찍는다. stdout은 지금처럼 JSON 보고서 한 덩이다. 9.2에서 기존 `tests/test_cli.py`의 stdout 파싱이 그대로 통과하는지 본다.
- 〔실행 메모 R-03〕 Step 9.1에서 CLI는 api 도우미를 import하지 않는다.
  - 직접 부르는 것: `service.purge(world_id=w)` + `service.purge(kind="world", ids=[w])`, `demos.translations`/`texts`, `service.seed`.
  - 언어는 매니페스트 키 ∩ `settings.supported_langs` − {en}이다.
  - `__main__`은 `assemble_localization`을 모듈 수준에서 import한다. TP-V3-9는 `locus.__main__.assemble_localization`을 monkeypatch한다.
  - 갈래 순서는 꺼짐 → 엔진 없음 → assemble 예외 → 시딩이다.
- 〔실행 메모 R-04〕 Step 8.2의 시딩 도우미는 `loc`나 `loc.translations`가 `None`이면 `demo`의 새 메서드를 부르지 않고 빈 보고서를 돌려준다. 그래서 `tests/api/test_world_api.py`의 가짜 `_Demo`는 고치지 않는다.
  - 테스트는 커밋에 맞춰 나눈다.
    - 8단계 첫 커밋(이름표·목록 칸): 저장소에 행을 직접 넣어 확인한다.
    - 둘째 커밋(시딩·지우기·옮기기): TP-V3-7 전체, TP-V3-8, TP-V3-10.
- 〔실행 메모 R-05〕 Step 3.4는 `wiring.py`의 `if shared.llm is None: return LocalizationContainer(translations=None)`을 바꾼다. 같은 자리에서 `TranslationService(store, None, default_lang=…)`를 만들고 실행기는 `None`이다(`close`는 지금 코드로 동작).
  - 기동 때 키 없는 서버도 `translations` 테이블을 만든다. 이 행동 변경을 code-summary § 6에 적는다.
- 〔실행 메모 R-06〕 커밋 수는 14개다.

---

## 2. 단계

### Step 1 — 진행 기록, 기준선, 설계 이탈 메모
- [x] 1.1 진행 기록을 커밋한다: audit, state, V2 리뷰 기록 뒤의 문서, V3 FD 계획·산출물·리뷰, 이 계획. 커밋 메시지는 `docs(aidlc): V3 functional design approved; V3 code plan`이다.
- [x] 1.2 기준선을 잰다: `pytest -q`(974), `npx vitest run`(423 + skip 1), `ruff`, `black --check`, `npx tsc --noEmit`, `mypy locus api`(11), `npm audit --omit=dev`(0). code-summary § 1에 적는다.
- [x] 1.3 〔실행 메모 R-02〕 상류 네 문서의 해당 줄 밑에 〔V3 FD Q5=A 정정, 2026-10-07〕 한 줄 메모를 단다: `component-dependency.md:109`, `component-methods.md` § 2·4·5, `components.md:79`, `unit-of-work.md` V3 완료 조건. 메모는 "→ V3 FD BR-V3-21, 이름표 `GET …/names`"를 가리킨다. 본문은 고치지 않는다. 커밋한다(`docs(aidlc): mark the per-response *_ko contract superseded by the V3 name map`).

### Step 2 — shared 번역 모델 (domain-entities § 2, BR-V3-01·04·05)
- [x] 2.1 `locus/shared/models/i18n.py`를 만든다: `TranslationKind`, `TRANSLATABLE_FIELDS`, `source_hash`, `TranslationEntry`(`field` 검증, `key`·`source_hash` 속성), `TranslationFile`(`parse`, `to_json`). `models/__init__.py`가 다시 내보낸다.
- [x] 2.2 `locus/localization/service.py`의 `source_hash`는 shared에서 가져와 다시 내보낸다(이름 유지).
- [x] 2.3 테스트:
  - TP-V3-1: 왕복 PBT(hypothesis), 다른 `format`·`version`은 `ValueError`
  - TP-V3-2 일부: 공백만 다른 원문은 같은 해시, 고정 예(옛 값과 같음), `field` 검증
  - 커밋: `feat(shared): translation entry and file models; source_hash moves to shared (V3)`

### Step 3 — localization: 키 없는 서비스, `seed`, `carry` (BLM § 2·3·10, BR-V3-02·15·17)
- [x] 3.1 `TranslationService(store, translator: Translator | None, …)`(R-08d). `translator`가 `None`이면 `enrich`가 빠진 항목을 예약하지 않는다.
- [x] 3.2 `seed(entries, *, lang, current_text, world_id) -> SeedReport`(BLM § 3 의사코드)
  - 넣은 키를 `_in_flight`에서 지운다(R-04).
  - 저장 실패는 기록하고 `seeded=0`이다.
  - `SeedReport`는 `localization/models.py`에 둔다.
- [x] 3.3 `carry(sources, target, *, text, langs, session_id) -> int`(R-07). 언어마다 source 행을 읽고, 해시가 `text`와 맞는 첫 행을 target 키로 쓴다.
- [x] 3.4 `wiring.py`: 번역이 켜져 있고 SQL 엔진이 있으면 LLM이 없어도 `TranslationService(store, None)`을 만든다. 실행기는 없다. `models.py` 독스트링을 고친다(R-05).
- [x] 3.5 테스트:
  - TP-V3-2 나머지: 해시 불일치는 `stale`, 빈 원문은 건너뜀
  - TP-V3-6: 키 없는 assemble에서 서비스가 있다. `enrich`가 예약하지 않는다. 꺼짐·엔진 없음은 `None`이다. LLM이 있으면 예약한다(R-08c의 서비스 쪽).
  - `seed`: `unknown`·`stale`·`seeded` 수를 센다. 다시 시딩하면 행이 늘지 않는다. 저장 실패면 0이다.
  - `carry`: `description` 우선, 다음 `title`이다. 해시가 다르면 0이다.
  - 커밋: `feat(localization): a translation service without an LLM reads and seeds; seed and carry (V3)`

### Step 4 — world: 원문 목록과 id 옮기기 (BLM § 5, BR-V3-18~20)
- [x] 4.1 `locus/world/worldfile/texts.py`를 만든다: `translatable_texts(file: WorldFile) -> dict[tuple[str, str, str], str]`.
  - 대상은 `world`(`file.world`), `regions`, `npcs`, `event_seeds`, `knowledge`의 `TRANSLATABLE_FIELDS`다.
  - 빈 원문은 뺀다. 순수 함수다.
- [x] 4.2 `remap.py`: `remapped_id(target_world_id, old_id) -> str`를 공개하고, `remap_ids`의 `new()`가 이 함수를 쓰게 한다. 값은 바뀌지 않는다.
- [x] 4.3 테스트:
  - TP-V3-3: PBT. 재매핑한 파일의 id 집합이 `{remapped_id(t, i) for i in file_ids}`와 같다.
  - `translatable_texts`: Emberleaf 123개, 빈 원문은 빠짐.
  - 커밋: `feat(world): translatable texts of a World File; remapped_id is public (V3)`

### Step 5 — world demo: 매니페스트 칸, FR-C11, 번역 검사, 항목 읽기 (BLM § 5·6, BR-V3-06·08~12·18·19)
- [x] 5.1 `DemoCardText`와 `DemoInfo.i18n`·`translations`를 더한다. 키 검증은 `^[a-z]{2}$`, `en` 아님이다(R-06: 모델 검증, 독스트링에 까닭).
- [x] 5.2 `_check`에 FR-C11을 더한다: `file.world.id != info.name` → 문제, 항목 빠짐.
- [x] 5.3 `_check_translations(worlds_dir, info, file) -> list[str]`: BR-V3-08 (a)~(h)를 보고 BR-V3-09 문장을 만든다. `_read_manifest`는 항목을 넣은 뒤 문제를 `extend`한다(R-06).
- [x] 5.4 `DemoWorlds`에 세 메서드를 더한다.
  - `translations(name, lang, *, target_world_id, remapped) -> list[TranslationEntry]`. 읽지 못하면 `[]`과 경고를 낸다. id는 BR-V3-18·19대로 옮긴다.
  - `texts(name, *, target_world_id, remapped) -> dict`
  - `card(name, lang) -> DemoCardText | None`
- [x] 5.5 테스트:
  - TP-V3-4: tmp 매니페스트 폴더로 (a)~(h), FR-C11, 키 형식을 하나씩 만든다. 문장에 이름·언어·대상이 있다.
  - TP-V3-5: 실행이 너그러운지 본다. 데모가 목록에 남고, 깨진 JSON이면 `[]`다.
  - TP-V3-3 예: `w2`로 옮긴 항목이 모두 `texts(w2)`의 키다. 월드 항목은 `w2`다.
  - 커밋: `feat(world): demo card text and translation files in the manifest; the check reports name ≠ world.id (V3, FR-C11)`

### Step 6 — Emberleaf 한국어판 (domain-entities § 3·4, BR-V3-07, A-1)
- [x] 6.1 `locus/world/demo/worlds/emberleaf.ko.json`을 쓴다: 123개, World File 순서, 영어 원문은 파일 그대로.
  - 고유명사는 음역하고 지형·직함 낱말만 옮긴다(Q1=A).
  - 설명·지식·씨앗은 해라체다. 역할은 마침표 없는 값 이름이다.
  - 번역문은 이 세션이 쓴다(A-1).
  - 원문과 키는 스크래치의 작은 스크립트가 World File에서 뽑아 뼈대를 만든다. 번역문은 손으로 채운다. 스크립트는 저장소에 두지 않는다.
- [x] 6.2 `manifest.json` Emberleaf 항목에 둘을 더한다: `i18n.ko`(title·description·credits)와 `translations.ko`.
- [x] 6.3 테스트:
  - `check_packaged() == []`
  - 역할 칸에 마침표 없음
  - 영어 원문이 World File과 같음(검사가 이미 보지만 출고 패키지로 한 번 더)
  - 이름 칸에 영문자 없음(음역 확인)
  - 커밋: `feat(world): Emberleaf in Korean — translation file and card text (V3, FR-L3)`

### Step 7 — 가산 id (BLM § 11, BR-V3-24)
- [ ] 7.1 `knowledge/query.py`에 `level_path_ids(region, snapshot) -> list[str]`를 둔다. `level_path`와 같은 순서·같은 순환 방지다. `RegionView.level_path_ids: list[str] = []`를 두고, `player/service.py`가 채운다.
- [ ] 7.2 `advancer.py` `deed_seeded` payload에 `npc_id`를 더한다. `npc_name`은 그대로다.
- [ ] 7.3 테스트:
  - TP-V3-11
  - 커밋: `feat(play): level path ids on the region view; npc_id on deed_seeded (V3, additive)`

### Step 8 — api: 이름표, 목록 칸, 시딩, 지우기, 옮기기 (BLM § 3·7~10, BR-V3-13~17·21~25)
- [ ] 8.1 `api/schemas.py`에 다섯 가지를 둔다.
  - `WorldNamesOut`
  - `DemoInfoOut`에 `title_ko`·`description_ko`·`credits_ko`를 더하고, `of(info, lang)`이 카드 문구를 고른다.
  - `WorldInfo`에 `name_ko`·`description_ko`를 더한다.
  - `DemoLoadOut(ImportReport)`에 `translations_seeded`·`translations_stale`을 더한다.
  - 도우미 셋. 모두 실패를 기록만 한다.
    - `seed_demo_translations(loc, demo, name, world_id, report, langs) -> SeedReport`
    - `purge_world_translations(loc, world_id)`
    - `carry_translation(...)`
- [ ] 8.2 `routers/world.py`
  - `GET /worlds/{w}/names`: `need_service(w.cache)`(R-03), `display_lang`, BLM § 8.
  - `GET /demos`·`GET /worlds`에 `display_lang`과 칸을 더한다.
  - 데모 불러오기 순서는 "가져오기 → `_after_replace` → `ok`면 시딩"이고, 응답은 `DemoLoadOut`이다.
  - `_after_replace`의 지우기를 `purge_world_translations`로 넓힌다(BR-V3-13).
  - 시딩 언어는 매니페스트 키 ∩ `SUPPORTED_LANGS` − {en}이다.
- [ ] 8.3 `routers/world_editor.py`: 지역 삭제는 `purge(ids=deleted_ids, world_id=w)`, NPC 삭제는 `purge(kind="npc", ids=[id], world_id=w)`다. 두 라우트에 `get_localization`을 의존으로 더한다(BR-V3-16).
- [ ] 8.4 `routers/gm.py` `start_seed`: 사건을 만든 뒤 `carry_translation`을 부른다(BR-V3-17, R-07).
- [ ] 8.5 테스트:
  - TP-V3-7: 키 없는 API(메모리 번역 저장소)로 다섯 가지를 본다.
    - 이름표가 전부 ko다.
    - 지역 보기 지식 칸, 월드 목록, 데모 목록 칸이 ko다.
    - `translations_seeded == 123`이고, 다시 불러와도 같다.
    - `en`이면 빈 맵이다. 404·400·503(캐시 없음)이 맞게 난다.
    - 저장소 예외는 응답을 깨지 않는다(R-08b).
  - TP-V3-8: 교체·지역 삭제·NPC 삭제의 지우기, 순서(교체 뒤에도 시딩 행이 남음)
  - TP-V3-10: 씨앗 시작 → `GET events`의 `description_ko`. 해시 불일치·저장소 실패면 옮기지 않고 201이다.
  - R-08c: LLM이 있는 컨테이너에서 이름표의 빠진 항목이 warm 예약된다.
  - 커밋은 둘이다.
    - `feat(api): world name map, Korean card and world-list fields (V3, FR-L2)`
    - `feat(api): seed demo translations on load; purge world kinds; carry a seed's translation to its event (V3, FR-L3)`

### Step 9 — CLI `world demo` 시딩 (BLM § 4, BR-V3-28, R-01)
- [ ] 9.1 `cmd_world_demo`: 불러오기·보고 뒤에 〔실행 메모 R-01〕의 네 갈래를 따른다. 그다음 교체면 지우기, 이어서 시딩하고 한 줄을 찍는다(`translations: ko seeded 123, stale 0, unknown 0`). 종료 코드는 불러오기 결과다.
- [ ] 9.2 테스트:
  - TP-V3-9: 서비스 있음(주입), 서비스 assemble 예외(→ skipped, 종료 0), 엔진 없음, 꺼짐
  - 커밋: `feat(cli): world demo seeds the demo's translations when the database is there (V3)`

### Step 10 — 웹 타입과 API 함수 (domain-entities § 7)
- [ ] 10.1 `types.ts`: `WorldNames`, `DemoInfo`·`WorldInfo`의 `*_ko`, `RegionView.level_path_ids?`
- [ ] 10.2 `api/world.ts`
  - 새 함수 `worldNames(worldId)`, URL은 `withLang(`/api/world/worlds/{w}/names`)`.
  - `listDemos`·`listWorlds`도 `withLang`을 쓴다.
- [ ] 10.3 테스트:
  - vitest 한 개: 세 함수의 URL과 `?lang=`
  - 커밋: `feat(web): name map and Korean list field types; list calls carry the display language (V3)`

### Step 11 — 불변과 경계 (BR-V3-26·27, TP-V3-12)
- [ ] 11.1 TP-V3-12(R-08a)
  - 시딩 뒤 World File 내보내기에 한글이 없다.
  - **시딩 단계의** 그래프·검색 쓰기 호출이 0이다. 가짜 저장소로 센다.
- [ ] 11.2 `tests/test_boundaries.py`를 통과한다. world와 localization은 서로 import하지 않는다. 조사 테스트 하나를 더해, 새 파일 `models/i18n.py`가 shared 밖을 import하지 않는지 본다.
- [ ] 11.3 커밋: `test: V3 invariants — no Korean in the World File, seeding writes no graph (V3, FR-L4)`

### Step 12 — 게이트와 요약
- [ ] 12.1 게이트를 돌린다: `pytest`, `vitest`(시드 둘), `ruff`, `black --check`, `tsc`, `mypy locus api`(≤ 11), `npm audit --omit=dev`(0), `tests/test_boundaries.py`.
- [ ] 12.2 `aidlc-docs/construction/V3-korean-backend/code/code-summary.md`를 쓴다.
  - § 1 기준선과 결과
  - § 2 바꾼 파일과 만든 파일
  - § 3 BR·TP 대응
  - § 4 테스트 변경
  - § 5 승인된 설계와 달라지는 것(R-02 표)
  - § 6 알려진 한계
    - 대화 속 이름(BLM § 12)
    - 진행 중 warm(R-04)
    - 월드 사이 id(R-05)
    - 이름표 warm 비용(R-03)
  - § 7 V4·V6·V8에 넘기는 것
    - 이름표를 화면에서 한 번 받아 들고 있기(리뷰 제안)
    - 굳은 시간선 이름을 id로 찾기
- [ ] 12.3 `aidlc-docs/operations/next-cycle.md`에 한 줄을 더한다: "LLM 대사·서술에 이름표를 함께 주기".
- [ ] 12.4 커밋: `docs(aidlc): V3 code summary`

---

## 3. 이야기·요구 대응

| 요구 | 단계 |
|---|---|
| FR-L2 (이름표·목록 칸, 지우기) | 8, 10 |
| FR-L3 (데모 한국어판, 시딩, 검사) | 2, 3, 4, 5, 6, 8, 9 |
| FR-L4 (불변) | 11 |
| FR-C11 | 5 |
| NFR-5 (가산) | 7, 8, 10 |
| NFR-6 PBT-02 | 2, 4 |
| NFR-8 (경로) | 5 |
| NFR-9 (키 없이) | 3, 8 |

**규모**: 12단계, 커밋 14개. 백엔드는 새 파일 3개(+데이터 1개)와 고친 파일 약 14개다. 웹은 파일 2개다. 테스트는 pytest 약 45개, vitest 1개를 더한다.

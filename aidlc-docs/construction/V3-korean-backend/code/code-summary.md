# V3 한국어 표시 백엔드 — Code Summary

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: V3 코드 생성을 마쳤다(Step 1~12). 키 없이 불러온 Emberleaf가 API에서 한국어로 나온다. 지식은 응답 칸으로, 지역·NPC·씨앗·월드는 이름표로, 월드 목록과 데모 카드는 칸으로 나온다. 이 문서는 바뀐 것, 확인, 이탈, 알려진 한계, 다음 유닛에 넘기는 것을 모은다. 다음은 코드 승인 지점이다.

플랜: `construction/plans/V3-korean-backend-code-generation-plan.md`(12단계, 커밋 14개, 승인 2026-10-07; 〔실행 메모〕 § 1.1 R-01~R-08, § 1.2 R-01~R-06 포함).

## 1. 기준선과 결과

| 항목 | 기준선 (Step 1.2, `580beb4`) | 결과 (Step 12, `8d9a76c`) |
|---|---|---|
| pytest | 974 | **1034** (+60) |
| vitest | 423 + skip 1 | **424** + skip 1, 시드 둘(무작위·4242)로 GREEN |
| ruff · black · tsc | clean | clean |
| mypy (`locus api`) | 11 | 11, 늘지 않음 |
| 경계 테스트 | 4 passed | 4 passed |
| `npm audit --omit=dev` | 0 | 0 |
| 출고 데모 검사(`check_packaged`) | `[]` | `[]`. 이제 한국어 번역 123개의 형식·범위·원문까지 본다 |

## 2. 바꾼 파일과 만든 파일

| 파일 | 상태 | 내용 | 커밋 |
|---|---|---|---|
| `locus/shared/models/i18n.py` | 새 | `TranslationEntry`, `TranslationFile`, `TRANSLATABLE_FIELDS`, `source_hash`(localization에서 옮김, 값 같음), `SOURCE_LANG` | `45562a9`, `a1e6d6e` |
| `locus/localization/{service,models,wiring,__init__}.py` | 바뀜 | 번역기 없는 서비스, `seed`, `carry`, `SeedReport`, 키 없는 assemble, 독스트링(R-05) | `d231070` |
| `locus/world/worldfile/texts.py` | 새 | `translatable_texts(file)` | `e2336d6` |
| `locus/world/worldfile/remap.py` | 바뀜 | `remapped_id` 공개, `remap_ids`가 사용 | `e2336d6` |
| `locus/world/demo/__init__.py` | 바뀜 | 다섯 가지를 더했다. | `a1e6d6e` |
|  |  | - `DemoCardText` |  |
|  |  | - `DemoInfo.i18n`·`translations`(키 검증) |  |
|  |  | - FR-C11 검사 |  |
|  |  | - `_check_translations`(BR-V3-08 (a)~(h)) |  |
|  |  | - `translations`·`texts`·`card`·`translation_langs` |  |
| `locus/world/demo/worlds/emberleaf.ko.json` | 새(데이터) | 123개 항목 | `8994af4` |
| `locus/world/demo/worlds/manifest.json` | 바뀜 | `i18n.ko`, `translations.ko` | `8994af4` |
| `locus/knowledge/query.py` | 바뀜 | `_lineage`, `level_path_ids` | `128f5f8` |
| `locus/play/{models,player/service,turn/advancer}.py` | 바뀜 | `RegionView.level_path_ids`, `deed_seeded`의 `npc_id` | `128f5f8` |
| `api/schemas.py` | 바뀜 | 칸·응답·도우미를 더했다. | `473855d`, `b877d80` |
|  |  | - `WorldNamesOut` + `world_names` |  |
|  |  | - `WorldInfo.*_ko`, `DemoInfoOut.*_ko` + `of(info, lang)` |  |
|  |  | - `DemoLoadOut` |  |
|  |  | - 도우미 `seed_demo_translations`·`purge_world_translations`·`carry_seed_translation` |  |
|  |  | - `SOURCE_LANG`은 shared에서 가져온다 |  |
| `api/routers/world.py` | 바뀜 | 라우트와 지우기를 바꿨다. | `473855d`, `b877d80` |
|  |  | - `GET /worlds/{w}/names` |  |
|  |  | - 두 목록에 `?lang=` |  |
|  |  | - 데모 불러오기 시딩 → `DemoLoadOut` |  |
|  |  | - 교체 purge를 모든 종류로 넓힘 |  |
| `api/routers/world_editor.py` | 바뀜 | 지역·NPC 삭제 purge | `b877d80` |
| `api/routers/gm.py` | 바뀜 | 씨앗 시작 → `carry` | `b877d80` |
| `locus/__main__.py` | 바뀜 | `world demo` 시딩(stderr 한 줄) | `e96805a` |
| `web/src/{types.ts, api/world.ts}` | 바뀜 | 타입과 함수를 더했다. | `8232297` |
|  |  | - `WorldNames`, `*_ko`, `level_path_ids`, `DemoLoadReport` |  |
|  |  | - `worldNames()` |  |
|  |  | - 목록에 `withLang` |  |
| 상류 설계 문서 넷 | 바뀜 | 〔V3 FD Q5=A 정정〕 메모(R-02) | `2da094e` |

새 테스트 파일:
- `tests/shared/models/test_i18n.py`
- `tests/localization/test_seed.py`
- `tests/world/worldfile/test_texts.py`
- `tests/world/test_demo_translations.py`
- `tests/api/test_world_names_api.py`
- `tests/api/test_demo_seeding_api.py`
- `tests/api/test_v3_invariants.py`

기존 파일에 더한 것:
- `tests/test_cli.py`(4)
- `tests/knowledge/test_query.py`(1)
- `tests/play/test_deed_turns.py`(단언)
- `tests/api/test_play_api.py`(단언)
- `web/src/__tests__/capabilities.test.ts`(1)

## 3. BR·TP 대응

| 규칙 | 테스트 |
|---|---|
| BR-V3-01 해시 일치 | TP-V3-2: `test_i18n.py`, `test_seed.py::test_seed_keeps_only_entries_whose_source_is_the_text_now` |
| BR-V3-02 키 없는 서비스 | TP-V3-6: `test_seed.py` assemble 셋 |
| BR-V3-03 원문 언어 | `test_world_names_api.py::test_the_source_language_…` |
| BR-V3-04 빈 원문 | `test_texts.py::test_blank_texts_are_not_targets`, `test_seed.py` |
| BR-V3-05 파일 형식 | TP-V3-1 왕복 PBT, 다른 형식 거절 |
| BR-V3-06·08·09·10·11·12 검사 | TP-V3-4·5: `test_demo_translations.py` |
| BR-V3-07 문체 | `test_demo_translations.py::test_the_packaged_korean_follows_the_style`(마침표, 해라체, 이름 음역, 원작 이름 금지) |
| BR-V3-13·14·15·16 지우기·순서·시딩 | TP-V3-7·8: `test_demo_seeding_api.py` |
| BR-V3-17 씨앗 → 사건 | TP-V3-10: `test_demo_seeding_api.py` 둘 |
| BR-V3-18·19·20 재매핑 | TP-V3-3: `test_texts.py` PBT 둘, `test_demo_translations.py`, API의 `w2` 불러오기 |
| BR-V3-21·22·23 응답 | `test_world_names_api.py` |
| BR-V3-24 가산 id | TP-V3-11 |
| BR-V3-25 불러오기 응답 | `test_demo_seeding_api.py` |
| BR-V3-26·27 경계·불변 | TP-V3-12: `test_v3_invariants.py`, `test_boundaries.py` |
| BR-V3-28 CLI | TP-V3-9: `test_cli.py` 넷 |

## 4. 테스트 변경 (의도한 변경)

- `tests/world/test_demo.py`의 `_workdir`/`_entry`(실행 메모 R-01)
  - 항목마다 `<name>.world.json` 사본을 두고 `world.id`를 그 이름으로 쓴다. FR-C11 뒤에도 옛 단언(목록 `["isle"]`, 문제 6개)은 그대로다.
- `tests/api/test_world_api.py::test_demo_list_and_load`: 카드 응답 전체 비교에 `title_ko`·`description_ko`·`credits_ko: None`을 더했다(가산).
- `tests/api/test_error_codes.py`(V2 리뷰에서 이미 바뀜)는 그대로다.

## 5. 승인된 설계와 달라지는 것 (FD 리뷰 R-02)

| 상류 | 승인된 내용 | V3 | 근거 | 영향 |
|---|---|---|---|---|
| `component-dependency.md:109`, `component-methods.md:221-225`, `components.md:79` | 응답마다 `*_ko` 칸(`region_name_ko`, `npcs[].name_ko`, `SeedViewOut.title_ko` …) | 월드 이름표 `GET …/names` 하나, `WorldInfo`·`DemoInfoOut`의 칸, `RegionView.level_path_ids` | Q5=A. 응답 조사에서 이름을 베낀 응답이 10곳 넘고, 시간선 이름은 굳은 영어였다 | V4·V6·V8: 이름은 id로 이름표에서 찾고, 없으면 영어 |
| `unit-of-work.md` V3 완료 조건 | "API 응답의 지역·NPC·지식·씨앗·월드·데모 카드가 ko" | "지식 칸·이름표·월드 목록·데모 카드가 ko" | 같음 | 메모를 달았다(`2da094e`) |
| `component-methods.md` § 2 | `TranslationEntry(kind, id, field, lang, text, source_hash)` | `(kind, id, field, source, text)`, 해시는 속성, `lang`은 파일에 한 번 | Q2=A | 없음 |
| `component-methods.md` § 4 | `DemoWorlds.translations(name, lang)` | `translations(name, lang, *, target_world_id, remapped)`, `texts`, `translation_langs` | R-07(설계 리뷰), BLM § 5 | 없음 |
| `component-methods.md` § 5 | `seed(entries, *, current_text, world_id)`, `SeedReport(seeded, stale, missing)` | `seed(entries, *, lang, current_text, world_id)`, `SeedReport(seeded, stale, unknown)`, `carry` 새로 | BLM § 3·10 | 없음 |
| `component-dependency.md:18` | api가 `remapped_id`를 쓴다 | world(`DemoWorlds`) 안에서 쓴다. api는 옮겨진 항목을 받기만 한다 | world가 id를 소유 | 없음 |

- 상류 표 칸의 옛 내용은 지우지 않았다. 취소선과 메모를 달았다. 플랜 1.3의 "본문은 고치지 않는다"보다 조금 더 손댄 것이다. 옛 계약을 읽는 사람이 바로 알아보게 하려는 것이다.

## 6. 알려진 한계

- **대화 속 이름**(BLM § 12): LLM이 쓰는 대사·서술·소문은 이름표를 모른다. 그래서 한국어 대사 안에 "Saltwake Harbor"나 LLM이 고른 음역이 나올 수 있다. 다음 주기 목록에 적었다.
- **진행 중 warm**(실행 메모 R-04): 키가 있고 같은 텍스트를 불러오기 직전에 읽었다면, 그 warm이 시딩 뒤에 끝나 손으로 다듬은 행을 LLM 번역으로 덮을 수 있다. 데모를 다시 불러오면 바로잡힌다.
- **월드 사이 id**(실행 메모 R-05): 캐시 키에 월드가 없다. 같은 비UUID id를 쓰는 두 월드는 서로의 행을 덮는다. 해시가 틀린 글은 막으므로 화면은 영어로 떨어질 뿐이다.
- **이름표의 warm 비용**(실행 메모 R-03): 키가 있으면 직접 만든 큰 월드의 첫 이름표 읽기가 텍스트 수만큼 LLM 번역을 예약한다. 텍스트마다 한 번이고, `TRANSLATION_WARM_WORKERS`가 동시 실행을 묶는다.
- ~~키 없는 서버의 기동~~ 〔코드 리뷰 01 § 2 정정〕 이 줄은 틀렸다. V3 전에도 `api/main.py:77`이 LLM 여부와 무관하게 `translations` 테이블을 만들었다.
- **키 없는 서버의 DB 읽기**(코드 리뷰 01 #11): V3부터 키 없는 서버도 표시 언어 읽기마다 PostgreSQL을 읽는다. 월드 목록, 이름표, 지식, 에디터 보기가 그렇다. 엔진(`locus/shared/storage/sql.py:17`)에 `connect_timeout`·`pool_pre_ping`이 없어, DB가 응답하지 않으면 요청마다 연결 시한까지 기다린다. 키 있는 서버는 원래 그랬다. B&T에서 실제 스택으로 보고, 엔진 설정은 V9에서 정한다.
- **쓰기 응답**: 씨앗 시작 응답의 `description_ko`는 지금 규칙(쓰기는 번역하지 않음)대로 비어 있다. 다음 사건 읽기가 옮겨진 행을 찾는다.

## 7. 다음 유닛에 넘기는 것

- **V4(홈·플레이), V6(GM), V8(에디터)**
  - 지역·NPC·씨앗·월드 이름은 `api.worldNames(worldId)`로 받아 id로 찾는다. 응답에 베껴진 영어 이름은 대체값으로만 쓴다.
  - 이름표는 화면에서 한 번 받아 세션·언어가 바뀔 때까지 들고 있는다(FD 리뷰 제안).
- **시간선·플레이 기록 줄**: `payload`의 굳은 이름 대신 옆의 id(`region_id`, `from_/to_region_id`, `npc_id`, `seed_id`)로 이름표를 찾는다.
- **지역 경로**는 `level_path_ids`로 찾는다.
- **홈 데모 카드**는 `title_ko`·`description_ko`·`credits_ko`를, **월드 목록**은 `name_ko`를 쓴다. 칸이 비면 영어를 쓴다.
- **홈 목록의 언어**(코드 리뷰 01 #6): 지금 홈의 두 목록(`HomePage` 월드 목록, `DemoCards`)은 첫 로드에 `?lang=`을 보내지 않고, 언어를 바꿔도 다시 읽지 않는다. 효과 의존이 `[]`라서다. V4는 홈을 다시 쓸 때 목록 읽기가 `useRequestLang()`(또는 `useResource`의 키)을 따르게 한다. 그러지 않으면 `title_ko`·`name_ko`가 표시 언어와 어긋난다.
- **사람 확인**: 번역문 품질(음역·문체)은 V4 캡처와 B&T에서 본다(가정 A-1). 코드 리뷰 01이 원문 대조로 고친 뒤의 문장이다(`b4682cb`).

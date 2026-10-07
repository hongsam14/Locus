# V3 한국어 표시 백엔드 — Functional Design Plan

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것. 이번 주기는 새 TRPG·판타지 디자인으로 화면 다시 만들기, 결과가 틀리는 결함 고치기, 시한 있는 부채 정리다.
**지금 하는 것**: Construction V3(실행 3/9), Functional Design. 키 없이 연 데모가 처음부터 한국어로 보이게 하는 서버 쪽 규칙을 정한다. 정하는 것은 일곱 가지다: 데모 번역 파일 형식, 번역 종류·필드, 해시 규칙, 재매핑 규칙, purge 지점, CLI 시딩 조건, 매니페스트 검사 항목.

**입력**:
- 요구사항 `inception/requirements/follow-up-requirements.md`
  - FR-L2(서버 번역 범위), FR-L3(데모 한국어판), FR-L4(불변), FR-C11(매니페스트 이름)
  - NFR-5(가산 호환), NFR-6(PBT-02 왕복), NFR-8(경로 검사), NFR-9(키 없이)
  - 가정 A-1(번역문은 코드 생성 때 만든다), A-2(`*_ko` 칸 이름 유지)
- 설계 `inception/application-design/follow-up/`
  - `services.md` S3(데모 불러오기 + 시딩)
  - `components.md`: `TranslationEntry`, `TranslationService`, `DemoWorlds`, `remap.py`, `schemas.py`, `world.py`, CLI
  - `component-methods.md` § 2·4·5
  - `component-dependency.md`(shared에 둔 까닭)
- 유닛 `unit-of-work.md` V3, 맵 `unit-of-work-story-map.md`
- 이 단계에서 닫을 리뷰 지적: 설계 리뷰 R-07
  - 재매핑은 파일 안 id만 한다. `world` 종류는 제외한다.
  - 번역 종류 목록에 `knowledge`를 함께 적는다.

**산출물 위치**: `aidlc-docs/construction/V3-korean-backend/functional-design/`
- `business-logic-model.md`
- `business-rules.md`
- `domain-entities.md`
- 화면 코드는 바꾸지 않으므로 `frontend-components.md`는 없다. 웹 타입에 칸을 더하는 일만 `domain-entities.md`에 적는다.

---

## 계획 (checkbox)

- [x] 1. 질문(아래)의 답을 받고, 모호함이 있으면 다시 묻는다 — Q1~Q5 = A, 모호한 답 없음(2026-10-07)
- [x] 2. `domain-entities.md`를 쓴다
  - `TranslationEntry`
  - 데모 번역 파일 형식
  - 번역 종류·필드 표
  - 매니페스트 항목의 새 칸(`i18n`, `translations`)
  - 응답 DTO에 더하는 `*_ko` 칸
  - `SeedReport`
- [x] 3. `business-logic-model.md`를 쓴다
  - 데모 불러오기 → purge → 시딩 흐름(API·CLI)
  - 키 없는 번역 서비스(캐시 읽기·시딩만)
  - 재매핑
  - 응답에 칸을 채우는 자리
  - purge 지점
  - 검사(`_check`)의 흐름
- [x] 4. `business-rules.md`를 쓴다(BR-V3-*)
  - 해시 일치 규칙
  - 재매핑 규칙(R-07)
  - purge 규칙
  - 검사 항목과 등급
  - FR-C11
  - 경로 검사(NFR-8)
  - 불변(FR-L4)
  - play가 localization을 import하지 않는 규칙
- [x] 5. 테스트 계획(TP-V3-*)을 적는다
  - 번역 파일 왕복 PBT(PBT-02)
  - 해시 불일치
  - 재매핑
  - purge
  - 키 없는 데모가 ko로 나오는 API 테스트
  - 검사
- [x] 6. 설계 검토자 리뷰(adversarial, 최대 2회) 뒤 승인 (iter 1, 승인 2026-10-07; 지적 8건은 코드 계획으로)

---

## 이 계획이 스스로 정한 것 (질문하지 않음)

- **키 없는 번역 서비스**: 지금 `assemble_localization`은 LLM이 없으면 번역 서비스를 만들지 않는다(`locus/localization/wiring.py:42`, `translations=None`).
  - 그대로 두면 시딩한 번역도 읽히지 않는다. "키 없이 한국어 데모"(FR-L3, NFR-9)가 될 수 없다.
  - 그래서 번역이 켜져 있고 PostgreSQL이 있으면, LLM이 없어도 서비스를 만든다. 이 서비스는 캐시 읽기와 시딩만 한다.
  - 캐시에 없는 항목을 백그라운드로 채우는 warm은 하지 않는다.
  - 키가 있으면 지금처럼 warm한다.
  - 설계(S3)가 빠뜨린 전제다. 목적에 따라 정해지는 것이라 묻지 않는다.
- **해시 함수의 자리**: 지금의 `source_hash`(앞뒤 공백을 뗀 sha256, `locus/localization/service.py:40`)를 `locus/shared/models/i18n.py`로 옮긴다.
  - world(검사)와 localization(시딩·읽기)이 같은 함수를 쓴다.
  - localization은 이전 이름을 다시 내보내므로 기존 import가 깨지지 않는다.
  - 값은 바뀌지 않는다. 이미 캐시에 있는 행도 그대로 맞는다.
- **순서**: 데모를 불러온 뒤의 순서는 "가져오기 → 월드 범위 purge(지금의 `_after_replace`) → 시딩"이다. purge가 시딩한 행을 지우지 않게 하려는 것이다.
- **번역 행의 월드 표시**: 새 종류(지역·NPC·씨앗·월드)와 시딩한 지식 행에는 `world_id`를 적는다. 그래야 월드 교체 때 월드 범위 purge가 이 행들을 지운다. 지금 지식 행은 이미 `world_id`를 적는다.
- **월드 교체 purge 범위**: 지금은 `kind="knowledge", world_id=w`만 지운다(`api/routers/world.py:104`). 이를 그 월드의 모든 종류로 넓힌다. 세션 내용(소문·사건·행적)은 `world_id`를 적지 않으므로 이 purge에 걸리지 않는다. 그것은 지금처럼 세션 닫기 쪽 규칙을 따른다.
- **CLI 시딩**: `locus world demo --name … --world …`는 번역이 켜져 있고 PostgreSQL에 닿으면 불러온 뒤 같은 시딩을 한다. 닿지 않으면 건너뛰고 한 줄로 알린다(설계 그대로).
- **데모 카드 문구**: 매니페스트의 언어별 문구(`i18n.ko`)를 `DemoInfoOut`의 `title_ko`·`description_ko`·`credits_ko`로 보낸다. 번역 캐시와 무관하다(설계 그대로).
- **편집 purge 지점**: 지금 에디터는 지식 삭제 때만 번역을 지운다(`api/routers/world_editor.py:235`).
  - 지역 삭제 보고의 `deleted_ids`(지역·NPC·씨앗, `locus/world/editor/models.py:44`)로 그 종류들을 지운다.
  - NPC 삭제는 그 NPC를 지운다.
  - 이름·설명을 고친 경우에는 지우지 않는다. 해시가 어긋나 저절로 쓰이지 않는다(지금 지식과 같은 규칙).
- **번역 대상에서 빼는 것**: 엔티티 이름·설명, NPC 특성(`traits`)이다. 둘은 에디터에만 보이고(`web/src/features/editor/NpcEditorList.tsx:48`), 에디터는 영어 원문을 고치는 자리다. 플레이·GM 화면에는 나오지 않는다.

---

## 질문

답은 `[Answer]:` 뒤에 적거나 대화창에서 주세요. 고정 선택지 `X. Other (please specify)`는 그대로 둡니다.

### Q1. 고유명사를 한국어로 어떻게 옮길까

**배경**:
- Emberleaf에는 지역 12, NPC 15, 씨앗 3이 있고, 이름이 대부분 지어낸 영어 낱말이다. Saltwake Harbor, Ironcrag, Hollowdeep, Captain Brisa 같은 것들이다(`locus/world/demo/worlds/emberleaf.world.json`).
- V2 시안은 임시로 음역("솔트웨이크 항구")을 썼다. 그때 실제 방식은 V3에서 정하기로 했다.
- 이 답에 따라 번역 파일의 이름 칸 수십 개가 달라진다. 플레이·GM 화면이 내는 분위기도 함께 달라진다.
- 설명문과 지식 문장은 어느 쪽을 골라도 뜻으로 옮긴다.

A. 음역에 지형 낱말만 옮김 — "솔트웨이크 항구", "아이언크래그", "할로우딥", "브리사 대장". 원문을 아는 사람이 대응을 찾기 쉽고 판타지 고유명사 느낌이 남는다. 대신 이름만 보고 뜻은 알 수 없다. 나중에 바꾸려면 번역 파일의 이름 칸만 고치면 된다. (권장: 원작 판타지 번역의 관례이고, 영어 화면과 오가도 같은 곳임을 알아보기 쉽다)
B. 뜻으로 옮김 — "소금바람 항구", "무쇠벼랑", "깊은골", "브리사 대장". 이름에서 장소의 성격이 바로 읽혀 한국어 TRPG 느낌이 강하다. 대신 영어 화면이나 영어로 생성되는 대화와 같은 곳인지 바로 알아보기 어렵다. 되돌리기 쉬운 정도는 A와 같다.
C. 섞음 — 뜻이 분명한 지형·마을 이름은 뜻으로, 사람 이름은 음역으로. 읽기 쉬움과 원문 대응을 반씩 얻는다. 대신 기준이 이름마다 판단이라 일관성을 지키기 어렵다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-07) — 음역 + 지형 낱말만 옮김

### Q2. 데모 번역 파일에 영어 원문을 함께 적을까

**배경**:
- 설계는 번역 항목마다 영어 원문의 해시를 적기로 했다(`components.md` `TranslationEntry(…, source_hash)`). 해시가 지금 원문과 맞을 때만 번역을 쓴다(FR-L3).
- 이 답이 정하는 것은 두 가지다. 하나는 번역 파일 `emberleaf.ko.json`의 모양이고, 다른 하나는 사람이 그 파일을 읽고 고칠 수 있는지다.
- 번역을 쓸지 말지 판단하는 규칙은 어느 쪽이든 같다. 원문이 바뀌면 낡은 번역은 쓰이지 않는다.

A. 원문을 적고 해시는 읽을 때 계산함 — 항목 하나가 `{kind, id, field, source, text}` 꼴이다. 사람이 파일만 열어도 무엇을 옮겼는지 보이고, 검사가 "원문이 바뀐 항목"을 원문과 함께 보여 줄 수 있다. 원문이 바뀌면 검사가 실패하므로 같이 고치게 된다. 파일은 두 배쯤 커진다(Emberleaf 기준 수십 kB). (권장: 사람이 손으로 고칠 수 있고, 해시를 따로 만들어 줄 도구가 필요 없다)
B. 해시만 적음 — 항목이 `{kind, id, field, source_hash, text}`다. 파일이 작다. 대신 무엇을 옮겼는지 보려면 World File을 함께 열어야 한다. 원문이 바뀌면 해시를 다시 계산해 줄 작은 도구가 필요하다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-07) — 영어 원문을 함께 적고 해시는 읽을 때 계산

### Q3. 번역 파일의 검사는 얼마나 엄격할까

**배경**:
- 지금 데모 검사(`_check`, `locus/world/demo/__init__.py:150`)는 문제가 있는 매니페스트 항목을 목록에서 빼고 `problems`에 적는다. CI 이미지 잡이 `check_packaged()`로 같은 검사를 돌린다.
- 번역 파일에서 생길 수 있는 문제는 다섯 가지다.
  - 형식 오류
  - 매니페스트 폴더 밖 경로
  - World File에 없는 id
  - 원문이 바뀐 항목
  - 덮지 않은 이름·설명
- 이 답이 정하는 것은 둘이다. 어느 문제가 CI를 실패시키는지, 그리고 그때 데모를 여전히 플레이할 수 있는지다.

A. CI는 엄격, 실행은 너그러움 — 다섯 가지 모두 `problems`에 적혀 CI가 실패한다. 그래서 출고하는 데모는 늘 전부 한국어다. 실행 중에는 번역 파일이 깨져 있어도 데모를 목록에서 빼지 않는다. 번역 없이 영어로 불러오고, 쓸 수 있는 항목만 시딩한다. (권장: 출고물의 품질은 CI가 지키고, 방문자는 번역 문제로 데모를 잃지 않는다)
B. 둘 다 엄격 — 번역 파일에 문제가 있으면 그 데모를 목록에서 뺀다. 규칙이 단순하다. 대신 번역 한 줄의 실수로 데모 전체가 사라질 수 있다.
C. 덮는 범위는 경고만 — 형식·경로·없는 id만 CI를 실패시킨다. 덮지 않은 이름과 원문이 바뀐 항목은 경고로만 남는다. 데모를 고칠 때 번역을 미뤄도 CI가 막지 않는다. 대신 출고 데모에 영어가 섞여 나갈 수 있다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-07) — CI는 엄격, 실행은 너그러움

### Q4. 매니페스트 `name`과 파일 `world.id`가 다르면 (FR-C11)

**배경**:
- 홈의 [바로 플레이]는 데모를 `name`이라는 월드 id로 불러오고, 매니페스트의 `start_region_id`로 세션을 연다(`web/src/features/home/DemoCard.tsx:23·77`).
- 그런데 파일의 `world.id`가 `name`과 다르면 가져오기가 id를 재매핑한다(`locus/world/worldfile/import_.py:56`). 그러면 시작 지역 id가 바뀌어 세션 시작이 조용히 실패한다(#11).
- 지금 Emberleaf는 둘이 같다.
- 이 답에 따라 검사 규칙(`_check`)과 데모 불러오기 경로 가운데 어느 쪽이 바뀌는지가 정해진다.

A. 검사가 문제로 보고함 — 둘이 다르면 그 항목을 목록에서 빼고 `problems`에 적는다. CI가 실패하므로 데이터를 고쳐야 출고된다. 코드가 가장 작고 숨은 경로가 없다. (권장: 데모는 데이터이고, 틀린 데이터는 출고 전에 잡는 것이 지금 규칙(BR-U8-2)과 같다)
B. 불러올 때 시작 지역도 함께 재매핑 — 둘이 달라도 동작한다. `DemoInfoOut`이 재매핑된 시작 지역 id를 보내야 한다. 그 id는 불러오기 전에는 알 수 없으므로 웹이 불러오기 보고서에서 받아 써야 한다. 데이터 실수를 감추는 대신 경로가 하나 는다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-07) — 검사가 문제로 보고

### Q5. 화면이 번역된 지역·NPC·씨앗 이름을 어디서 받을까

**배경**:
- 응답 목록을 조사했다(2026-10-07). 지역·NPC·씨앗·월드 이름에 `*_ko` 칸은 아직 하나도 없다.
- 이름이 들어 있는 곳은 둘로 나뉜다.
  - **서버가 이름을 베껴 넣은 응답**이 10곳이 넘는다.
    - 플레이: 지역 보기 `region_name`·`description`, 이동 `moves[].region_name`, 턴 결과 `region_changes[].region_name`
    - GM: 씨앗 `region_name`, 행적 `region_name`·`witness_names`·`npc_name`, 상태 `region_name`
    - 에디터: 에디터 보기의 `other_region_name`·`children`, 삭제 계획
  - **이름을 id로 찾는 화면**도 있다. GM과 에디터는 월드 내보내기(`/export`)의 `regions`로 id → 이름을 직접 찾는다(`web/src/routes/GmPage.tsx:36-38`).
- 거의 모든 이름 옆에 id가 함께 있다.
- 시간선·플레이 기록 줄은 이름을 **쓸 때의 영어로 굳혀** `payload`에 담는다(`locus/play/**` 여러 곳). 응답 칸으로는 옮길 수 없고, id로 찾아야만 한국어가 된다.
- 설계(`component-dependency.md` V3→V4)는 응답마다 칸(`region_name_ko`, `npcs[].name_ko`…)을 더하기로 적었다. 이 조사 전의 판단이다.
- 이 답에 따라 V3가 바꾸는 서버 응답의 수와, V4·V6·V8 화면이 이름을 찾는 방법이 정해진다.

A. 월드 이름표 하나 — 새 읽기 하나(`GET /api/world/worlds/{w}/names?lang=ko`)가 그 월드의 지역·NPC·씨앗·월드 번역을 `{id: 이름}` 꼴로 한 번에 준다. 화면은 id로 찾고, 없으면 영어 원문을 쓴다.
   - 시간선의 굳은 이름도 옆의 id로 한국어가 된다.
   - 서버 응답 여럿을 고치지 않으므로 V3가 작다.
   - 월드 목록과 데모 카드는 응답 칸(`name_ko`, `title_ko`)으로 둔다.
   - 대신 화면이 읽기를 하나 더 하고, FR-L2의 "응답에 번역 칸을 채운다"를 "이름표로 채운다"로 바꾼다.
   - 이름만 있고 id가 없는 곳 둘(`level_path`, `deed_seeded`의 NPC)에는 id를 더한다(가산).
   - (권장: 한 가지 방식으로 굳은 이름까지 덮고, 화면들이 이미 id 옆에 이름을 두는 구조와 맞는다)
B. 응답마다 `*_ko` 칸 — 설계 그대로다. 위 10여 곳의 DTO에 칸을 더하므로 화면은 받은 칸을 그대로 쓴다.
   - 대신 V3의 서버 변경과 테스트가 그만큼 늘어난다.
   - 시간선의 굳은 이름은 여전히 영어로 남는다. 따로 id 찾기를 더해야 한다.
C. 둘 다 — 플레이 주 경로(지역 보기·이동·NPC)는 응답 칸으로, GM·에디터·시간선은 이름표로 받는다.
   - 화면마다 가장 자연스러운 쪽을 쓴다.
   - 대신 같은 번역이 두 길로 나가서, 규칙과 테스트가 두 벌이다.
X. Other (please specify)

[Answer]: A (대화창, 2026-10-07) — 월드 이름표 하나

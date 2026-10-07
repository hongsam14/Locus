# Follow-up Cycle — Components

> Application Design(Standard). 근거: `inception/requirements/follow-up-requirements.md`(승인), 설계 질문 답 Q1~Q6(모두 A, `inception/plans/follow-up-application-design-plan.md`).
> 이 문서는 **이번 주기에 새로 생기거나 책임이 바뀌는** 구성 요소만 적는다. 그대로인 것은 `inception/reverse-engineering/architecture.md`가 설명한다.
> 표기: **[새]** 새 구성 요소, **[바뀜]** 책임이나 계약이 바뀜, **[유지]** 이름은 그대로이고 안쪽만 고침.

---

## 1. 웹 (`web/src`) — 디자인 시스템과 화면 기반 (V2, 화면 유닛 V4·V6·V8이 씀)

| 구성 요소 | 표기 | 책임 | 인터페이스(밖으로 내는 것) | 요구사항 |
|---|---|---|---|---|
| **디자인 토큰** `index.css` `@theme` | [바뀜] | TRPG·판타지 톤 하나의 의미 토큰. 색(바탕·면·글·약한 글·선·강조·위험·성공·정보·지도 단계·연결 종류), 글꼴 역할(장식 제목·세리프 제목·본문), 간격, 모서리, 그림자, 비활성 상태. 원색 값은 이 파일에만 둔다 | Tailwind 유틸 이름(`bg-surface`, `text-muted`…), CSS 변수 | FR-D2, NFR-3 |
| **글꼴 묶음** | [바뀜] | 공개 라이선스 한글 글꼴을 자체 호스팅한다. 첫 화면은 부분 집합이나 unicode-range로 내려받는다. Gaegu는 새 톤에 맞지 않으면 뺀다 | `font-display` / `font-heading` / `font-body` | FR-D3, NFR-4, A-3 |
| **프리미티브** `ui/` | [바뀜] | Button, Card/Panel, Badge, Field, Textarea, **Select**[새], **FileInput**[새], **Tabs**[새], Range/CommitRange, **Dialog**(Modal 대체), **Toaster**(알림 하나), **StatusView**[새](로딩·빈 상태·오류), **ConfirmDialog**[새](확인 대화상자). 접근성 동작은 headless 라이브러리(Radix UI 계열)가 맡고, 모양은 토큰으로 입힌다(Q5=A) | 컴포넌트 props(§ component-methods 1) | FR-D4, FR-S5, FR-S6 |
| **배치 틀** `layout/` | [새] | `AppShell`(내비·언어 토글·알림 자리), `SplitView`(데스크톱 2열: 주 영역 + 옆 패널, 옆 패널 폭 상한·자체 스크롤, 좁은 화면 1열), `Section`(접을 수 있는 묶음). 브레이크포인트는 이 층에만 둔다 | `<AppShell>`, `<SplitView main aside>`, `<Section>` | FR-D5, UX-02, UX-03 |
| **지도** `map/` | [새] (`MapOverlay.tsx` 대체) | 컨테이너 폭에 맞춰 줄어드는 SVG 지도. 클릭·끌기 좌표는 그려진 영역 기준(SVG 좌표 변환)으로 정규화한다. 지역 단계마다 모양과 크기가 다르고, 라벨 받침으로 겹침을 줄인다. 선택·플레이어 표식을 라벨과 겹치지 않게 놓는다. 끌기는 명시적으로 켤 때만 된다. 배치 변형은 셋: 에디터(그리기·끌기), GM(상태 겹쳐 보기), 플레이(작은 지도: 지금 위치·이웃·갈 수 있는 곳) | `<WorldMap mode=… regions connections …/>` | FR-D6, FR-D7, FR-S2, UX-18, UX-36 |
| **표기 규칙** `format/` | [새] | 서버 값을 사람 말로 바꾸는 규칙 하나를 둔다. 모든 enum의 ko/en 라벨, 수치를 말과 단계로(플레이어용) 또는 숫자와 뜻으로(GM·에디터용) 바꾸는 것, 표시 언어 로캘 날짜가 여기 있다 | 순수 함수(`enumLabel`, `degreeWord`, `formatDate`…) | FR-D8, FR-L1, UX-04, UX-07 |
| **오류 문장** `errors/` | [새] | 오류 응답의 `code`(Q6=A)와 상태 코드로 사용자 문장(제목·할 일)을 고른다. 원문 detail은 접어서 보이게 한다. `conflictKind` 같은 문자열 매칭을 걷어 낸다 | `describeError(err, lang)` | FR-D9, UX-06 |
| **요청 도우미** `hooks/` | [새] | (1) 읽기: AbortController로 늦은 답을 버리고, 언마운트·키가 바뀌면 취소한다. 지금 섞여 있는 세 패턴과 #14 꼴을 대체한다. (2) 쓰기: 진행 중이면 다시 누를 수 없게 막고, 끝난 뒤 지정한 읽기만 다시 한다. 오류는 `describeError`로 바꾼다 | `useResource`, `useAction` | FR-C13, RE-F01·F02·F07·F11·F14, UX-42 |
| **i18n 사전** `i18n/` | [바뀜] | ko/en 사전을 늘린다(enum 라벨, 오류 문장, 화면 문구). 키 일치 테스트는 유지한다. 지금의 `i18n.ts` 하나를 언어별 파일과 상태 모듈로 나눈다 | `t(key)`, `useLang`, `useRequestLang` | FR-L1 |
| **API 클라이언트** `api/` | [바뀜] | `HttpError`에 `code`를 싣는다. 번역 칸(지역·NPC·씨앗·월드·데모 카드)을 타입에 더한다. 업로드도 같은 오류 처리를 쓴다 | `http<T>()`, 경계별 함수 | FR-D9, FR-L2 |
| **화면** `routes/` + `features/{home,play,gm,editor}` | [바뀜] | 위 기반 위에서 다시 배치한다. 화면별 배치안은 각 유닛의 FD에서 정한다 | 라우트 넷 | FR-S1~S4 |

## 2. `locus/shared` (경계 바닥)

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **번역 항목 모델** `models/i18n.py` | [새] | `TranslationEntry(kind, id, field, lang, text, source_hash)`. 데모 번역 파일 한 줄의 형태다. world(파일을 읽음)와 localization(캐시에 넣음)이 둘 다 이 모델을 쓴다. 두 경계는 서로 import하지 않으므로 공통 모델을 shared에 둔다 | FR-L3, C-2 |
| **그래프 포트** `storage/base.py` | [바뀜] | `get_node`와 `delete_node`에 선택 인자 `label`을 더한다. 라벨이 주어지면 그 라벨만 찾고 지운다. 에디터와 삭제 경로는 늘 라벨을 넘긴다 | FR-C10 |
| **Neo4j 어댑터** | [유지] | 라벨 인자를 따른다. 라벨이 있는 질의는 라벨별 인덱스를 쓴다 | FR-C10 |
| **저장 순서** `storage/persistence.py` | [바뀜] | `WorldMeta`를 **마지막에**(엣지와 색인 뒤) 쓴다. 그래서 버전 표식이 연결·스코프보다 먼저 확정되지 않는다 | FR-C7 |

## 3. `locus/knowledge`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **합의 계산** `consensus.py` | [유지] | 지식 하나가 여러 출처 지역에서 닿으면, **경로 가중이 가장 큰 출처**를 고른다(같으면 지역 id 순). 결과와 `unknown_count`가 엣지·출처 순서와 무관하다 | FR-C6, NFR-6 |
| **WorldCache** `cache.py` | [유지] | 버전을 모르는(WorldMeta가 없는) 스냅샷은 캐시하지 않는다. hit 경로의 버전 읽기 실패는 miss 경로와 같이 다룬다(RE-W03, 같은 코드라 함께 고침) | FR-C7 |

## 4. `locus/world`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **WorldBuilder** `build.py` | [바뀜] | (1) 백업이 실패하면 교체하지 않는다. 옛 월드를 남기고 `ok=false`, stage `backup`, error로 끝낸다. (2) 교체할 때 옛 월드의 NPC·씨앗을 읽어 두었다가 새 월드에 **이어 붙인다**(Q3=A). 못 붙인 것은 경고로 남긴다. 빌드 자체는 NPC를 만들지 않는다 | FR-C8, FR-C9 |
| **이어 붙이기 규칙** `carry_over.py` | [새] | 순수 함수. 옛 NPC·씨앗의 집 지역·씨앗 지역을 옛 월드의 (이름, 단계)로 새 월드 지역에 맞춘다. 결과는 (붙인 NPC, 붙인 씨앗, 경고)다 | FR-C9 |
| **WorldFileImporter** `worldfile/import_.py` | [바뀜] | 백업이 실패하면 교체하지 않는다. **절 사이·절 안 중복 id**가 있으면 아무것도 쓰기 전에 거절한다(`ok=false`) | FR-C8, FR-C10 |
| **id 재매핑** `worldfile/remap.py` | [바뀜] | 한 id의 새 값을 계산하는 순수 함수 `remapped_id(target, old)`를 공개한다. 데모 번역 항목의 id를 같은 규칙으로 옮기는 데 쓴다. 중복 id를 찾는 `duplicate_ids(file)`도 둔다 | FR-L3, FR-C10 |
| **DemoWorlds** `demo/__init__.py` | [바뀜] | 매니페스트 항목에 두 가지가 생긴다: 언어별 카드 문구(`i18n: {lang: {title, description, credits}}`, Q4=A)와 선택적 번역 파일 경로(`translations: {lang: file}`). 검사(`_check`)가 보는 것도 늘어난다: (a) `name`과 파일 `world.id`가 같은가(FR-C11), (b) 번역 파일 형식, (c) 번역이 덮는 범위, (d) 매니페스트 폴더 밖 경로 거절. 번역 항목은 `TranslationEntry` 목록으로 읽어 준다 | FR-L3, FR-C11, NFR-8 |
| **Emberleaf 번역 파일** `demo/worlds/emberleaf.ko.json` | [새] (데이터) | 지역 12·NPC 15·지식 23·씨앗 3·월드 이름과 설명의 ko 번역. 각 항목은 영어 원문 해시를 함께 적는다. 매니페스트 카드 문구 ko도 함께 쓴다 | FR-L3, A-1 |
| **보강 질문** `augmentation/questions.py` | [유지] | `NEEDS`를 (이슈 종류, **대상 종류**)로 찾는다. 엔티티 대상에는 제목 칸이 없다. 아무것도 바꾸지 않은 답은 변경 기록을 남기지 않는다 | FR-C12 |
| **에디터 쓰기** `editor/*` | [유지] | 삭제와 읽기에 라벨을 넘긴다(FR-C10) | FR-C10 |

## 5. `locus/localization`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **TranslationService** | [바뀜] | (1) 번역 종류가 는다: `region`(name, description), `npc`(name, role, description), `event_seed`(title, description), `world`(name, description). 읽기는 그대로 캐시 전용이고 warm도 같다. (2) **시딩**[새]: `TranslationEntry` 목록과 지금 영어 원문을 받아, 해시가 맞는 항목만 캐시에 upsert한다. 원문이 바뀐 낡은 번역은 버린다. (3) purge가 새 종류도 지운다 | FR-L2, FR-L3 |

## 6. `locus/play`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **TurnGuard** `turn/guard.py` | [바뀜] | 세 가지를 한 곳에서 다룬다. | FR-C1, C2, C5 |
|  |  | (1) 지금처럼 턴과 GM 리스는 서로 배타이고, GM 리스는 함께 쥔다. |  |
|  |  | (2) **세션별 짧은 쓰기 잠금**[새](Q1=A): 읽고-쓰는 구간을 세션마다 하나씩 줄 세운다. 짧게 기다리고, 타임아웃이 지나면 409(`gm_busy`)를 준다. |  |
|  |  | (3) 상태를 따로 묻는 길: `turn_running(session)`과 `gm_busy(session)`. |  |
|  |  | 턴과 GM 리스가 겹칠 때의 오류도 둘로 나눈다: `TurnInProgressError`(턴)와 `GmBusyError`[새](GM). |  |
| **GM 쓰기 서비스들** `event/service.py`, `event/seeds.py`, `rumor/service.py`, `deeds/service.py`, `distortion_service.py` | [바뀜] | 읽고-쓰는 구간을 짧은 쓰기 잠금 안으로 옮긴다. 대상은 해소, 승인, 폐기, 씨앗 시작, 지지도 조정, 행적 취소, 왜곡도 설정, 소문 생성·재생성의 저장 단계다. 잠금 안에서 **세션이 열려 있는지 다시 확인**한다. LLM 호출은 잠금 밖에 남긴다. 세부 규칙(절대값 대신 증분 쓰기, 상태 조건 쓰기)은 V5 FD에서 정한다 | FR-C1, FR-C2 |
| **SessionService** `session_service.py` | [바뀜] | 닫기는 짧은 쓰기 잠금을 쥐고 상태를 바꾼다. 그 뒤 진행 중이던 GM 쓰기는 잠금 안의 열림 확인에서 멈춘다. 월드 교체의 닫기도 같은 길을 쓴다 | FR-C2 |
| **TurnAdvancer** `turn/advancer.py` | [바뀜] | (1) **끊긴 run 복구**[새]: 재시작 때 `running` run마다 실패 보상(`_fail`과 같은 규칙)을 적용한다. (2) 월드에서 지운 지역의 활성 사건은 적용하지 않는다. 처리 방식(해소 또는 건너뜀)은 V5 FD에서 정한다 | FR-C3, FR-C4 |
| **PlayService / RegionView** | [바뀜] | `RegionView`에 `gm_busy`를 더한다. `turn_running`은 턴 run만 뜻한다(Q2=A) | FR-C5 |

## 7. `api/`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| **오류 계약** `errors.py` + `main.py` 처리기 | [바뀜] | 오류마다 **`code`**를 정해 응답에 `{"detail": …, "code": …}`로 싣는다(Q6=A). `detail`은 그대로라 가산 변경이다. 객체 detail(열린 세션 409)에도 `code`를 더한다. 413·422·503(경계 없음) 같은 프레임워크 오류도 코드를 갖는다 | FR-D9 |
| **번역 칸** `schemas.py` | [바뀜] | 지역 보기, NPC 목록, GM 상태·씨앗, 에디터 보기, 월드 목록, 데모 목록에 번역 칸(`*_ko`, A-2)을 채운다. 데모 카드는 매니페스트의 언어별 문구에서 고른다 | FR-L2, FR-L3 |
| **데모 라우트** `routers/world.py` | [바뀜] | 데모를 불러온 뒤 번역 항목을 시딩한다(재매핑했으면 id를 옮긴다). 월드 교체·편집·삭제 때 새 번역 종류도 purge한다 | FR-L2, FR-L3 |
| **lifespan** `main.py` | [바뀜] | 시작할 때 `fail_stale_runs` 대신 끊긴 run 복구를 부른다 | FR-C3 |
| **GM 라우터** `routers/gm.py` | [유지] | `_idle` 리스는 그대로 둔다. 짧은 쓰기 잠금은 서비스 안에서 쥔다. 저장소를 직접 읽던 곳(왜곡도 응답)은 서비스를 거친다 | FR-C1 |

## 8. CLI `locus/__main__.py`

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| `world demo` | [바뀜] | PostgreSQL에 닿을 수 있고 번역이 켜져 있으면, 불러온 뒤 데모 번역도 시딩한다. 닿을 수 없으면 건너뛰고 한 줄로 알린다 | FR-L3 |

## 9. CI·문서·테스트 (V1·V9)

| 구성 요소 | 표기 | 책임 | 요구사항 |
|---|---|---|---|
| `.github/workflows/ci.yml` | [바뀜] | 액션을 새 주 버전으로 올린다. 러너가 Ubuntu 26으로 바뀌어도 통과하게 한다. backend 잡에 `mypy locus api`를 더한다 | FR-T1, FR-T3 |
| 문서 묶음 | [바뀜] | CLAUDE.md, README, `operations.md`, `web/README.md`, `next-cycle.md`, 낡은 docstring | FR-T4, FR-C14 |
| 테스트 위생 | [바뀜] | 계약 테스트의 시간 초과 의존을 없애고, retry 테스트가 실제로 자지 않게 하며, sqlite 엔진을 dispose한다. 라이브 시나리오 10a를 강화한다 | FR-T6, FR-T7 |

## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Units Generation — Follow-up cycle
**Reviewed artifact:** `aidlc-docs/inception/application-design/follow-up/unit-of-work.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-07T09:03:41Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/inception/application-design/follow-up/unit-of-work.md > V2 코드 | V2가 `web/src/{layout,map,format,errors,hooks,i18n}/`를 코드 자리로 적었으나 새 폴더라는 표시가 없다. 실제로는 이 중 `ui/`만 폴더로 있다. 더 중요하게 `web/src/layout.ts`와 `web/src/i18n.ts`가 파일로 이미 있어 `./layout`, `./i18n` import가 폴더와 겹친다(`App.tsx:4`가 `./i18n`을 import). 지도는 `web/src/MapOverlay.tsx`와 `viz.ts`에 있는데 V2 코드 목록에 이름이 없고, 설계(components.md)는 `i18n.ts`를 나눈다고만 적었다. 구현자는 무엇이 새로 생기고 무엇이 옮겨지는지 추측해야 한다. | V2에 새 경로(새로 만듦)와 옮기거나 지울 기존 파일(`layout.ts`, `i18n.ts`, `MapOverlay.tsx`, `viz.ts`, `types.ts`, `capabilities.ts`)을 구분해 적는다. `layout.ts`·`i18n.ts`와 폴더 이름이 겹치는 문제는 V2 FD에서 정하도록 항목을 둔다. | New |
| R-02 | Major | aidlc-docs/inception/application-design/follow-up/unit-of-work.md > V5 코드·완료 조건; unit-of-work-dependency.md > 1 (V4 → V5 ◦), 3 (V5 → V4·V6 계약) | `gm_busy`는 `RegionView`(`locus/play/models.py:381`)에 칸이 생기고 `locus/play/player/service.py:78`(`turn_running=self._guard.is_running(...)`)에서 채워지며 `api/schemas.py:117` `RegionViewOut`으로 나간다. 그런데 V5 코드 목록에는 `locus/play/player/`와 `api/schemas.py`가 없다(`api/schemas.py`는 의존 문서 § 4가 V5가 고친다고 적는다). `is_running` 호출부 4곳 가운데 `player/service.py:78`이 빠진 셈이다. 또 의존 문서는 "V5의 완료 조건에 '플레이 화면이 실제 gm_busy로 바뀐다'를 넣는다"고 하는데 `unit-of-work.md` V5 완료 조건에는 없고, V5 코드 목록에는 웹 파일도 없다. V4가 가짜 응답으로 만든 표시를 실제 값에 연결하는 책임이 어느 유닛에도 걸려 있지 않다. | V5 코드에 `locus/play/player/service.py`, `locus/play/errors.py`(새 오류가 거기 있다면), `api/schemas.py`를 더하고, V5 완료 조건에 "플레이 화면의 `gm_busy` 표시가 실제 칸으로 바뀐다(필요한 웹 수정은 `features/play/` 최소 범위)"를 넣는다. 의존 문서와 일치시킨다. | New |
| R-03 | Minor | aidlc-docs/inception/application-design/follow-up/unit-of-work-dependency.md > 4 같은 파일을 여러 유닛이 고치는 곳 | 표가 `unit-of-work.md`의 코드 목록과 맞지 않는다. 빠진 겹침: (a) `api/routers/{play,gm}.py` — V3(번역 칸)와 V5가 둘 다 고친다. 표는 `world.py`만 적었다. (b) `locus/world/worldfile/remap.py` — V3(재매핑 규칙)와 V7(중복 id 거절, RE-W13/#10)이 둘 다 고친다. (c) `web/package.json` — V2(headless·글꼴)와 V9(audit). (d) `features/play/NewSessionForm`·`features/editor/MapCanvas·BuildPanel` — V2가 대화상자를 바꾸고 V4·V8이 화면을 다시 짠다. (e) `locus/play/turn/advancer.py` 등 V5와 `__main__.py` 등은 겹치지 않아 문제없다. | 표에 (a)~(d) 줄을 더하고 조정 규칙(순서, 무엇을 누가 고치는지)을 적는다. 특히 `remap.py`는 V3가 먼저이므로 V7 FD가 V3의 결과를 읽도록 한다. | New |
| R-04 | Minor | aidlc-docs/inception/application-design/follow-up/unit-of-work-dependency.md > 1 의존 행렬, 2 mermaid | "모든 화살표가 앞 순서를 가리킨다"는 문장이 V4 행의 ◦ V5(V5는 V4보다 뒤)와 맞지 않는다. ◦는 선택 의존이라 순환은 아니지만 문장은 틀리다. 또 mermaid의 실선 사슬 V1→V2→V3→…→V9는 행렬(V2는 V1에, V3는 V2에 필수로 기대지 않음, V7은 독립)보다 강한 순서 의존을 그린다. 행렬은 V1과 V7이 독립이고 V3는 V2에 ◦만이다. 순환은 없다(검사함). | 문장을 "필수(✓) 의존은 앞 순서만 가리킨다"로 고치고, mermaid에서 실선(실행 순서)과 점선(의존)을 범례로 구분한다. | New |
| R-05 | Minor | aidlc-docs/inception/application-design/follow-up/unit-of-work-story-map.md > 4 결함 ID → 유닛; unit-of-work.md > V2, V6, V8 범위 | 결함 배정이 두 문서 사이에서 어긋난다. (a) RE-F13(object URL 해제)은 `EditorPage.tsx:157`과 `GmPage.tsx:167` 두 곳인데 story map은 V8에만 둔다. GmPage쪽이 V6에 안 걸린다. (b) RE-F07·F12·F13·F06은 story map에는 V8이지만 `unit-of-work.md` V8 범위에는 적히지 않았다. RE-F10(V6)도 V6 범위에 없다. (c) RE-F09는 V2로 배정됐는데 V2 코드 목록에 `web/src/capabilities.ts`가 없다. FR-C14 규칙("같은 코드를 만지면 함께")은 story map에만 있어 유닛 문서만 읽는 구현자는 놓친다. | `unit-of-work.md` V6·V8 범위에 해당 RE-F 번호를 적고, RE-F13을 V6(GmPage)과 V8(EditorPage)에 나눠 건다. RE-F09의 `capabilities.ts`를 V2 코드에 더하거나 next-cycle로 확정한다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 유닛 코드 경로 존재(`ls`) | 기존 경로 모두 존재. 새로 만들기로 표시된 `models/i18n.py`, `carry_over.py`, `emberleaf.ko.json`은 없음(정상). `web/src/{layout,map,format,errors,hooks,i18n}/`는 없는데 새 경로 표시도 없음 | R-01 |
| `layout.ts`, `i18n.ts`, `MapOverlay.tsx`, `viz.ts` 대 V2 폴더 | 파일로 존재하고 V2 목록에 없음. `App.tsx:4` `./i18n` import | R-01 |
| `is_running`/`assert_idle`/`fail_stale_runs` 호출부 grep | production 4곳(`player/service.py:78`, `session_service.py:115`, `routers/world.py:64`, `main.py:120` + postgres_repo) 중 `player/service.py`가 V5 목록에 없음 | R-02 |
| `get_node`/`delete_node` 호출부 grep | `world/augmentation/apply.py`, `world/editor/{bundle,writes,regions}.py` 11곳 — 모두 V7 코드 목록(`editor/*`, `augmentation/apply.py`)에 포함 | OK |
| 중복 파일 조정 표 대 코드 목록 대조 | `api/routers/{play,gm}.py`, `remap.py`, `package.json` 누락 | R-03 |
| FR 41개 배정 | FR-D10, S6, L4, C14, T7 모두 한 유닛 이상에 배정, 고아 0 | OK |
| UX-01~42 배정 | UX-26만 범위 밖(요구사항 § 9), 나머지 배정됨. V4·V6·V8 구간 겹침 없음 | OK |
| NFR-1~10 배정 | 모두 배정 | OK |
| 설계 리뷰 R-01~R-09, 요구사항 R-01~R-06 → 유닛 | story map § 5가 전부 닫는 유닛을 가짐. R-01/03/04→V5, R-02/05/06/08→V7, R-07→V3, R-09→V9가 설계 리뷰 본문과 일치 | OK |
| 의존 그래프 순환 | 필수 의존은 모두 앞 번호를 가리킴, ◦ V4→V5만 뒤를 가리키나 선택이고 가짜 응답으로 끊김 | 순환 없음 (R-04는 문장 정정만) |
| Mermaid 구문 | `flowchart LR`, 노드 라벨 따옴표, 점선 라벨 구문 정상 | OK |
| 각 유닛 독립 빌드·테스트 | V1·V7·V9는 독립, V4는 V5 없이 가짜 응답으로 테스트, V6은 V5 의존 | OK, 단 R-02 |

### Summary

유닛 분해는 전반적으로 건전하다. FR·NFR·UX는 빠짐없이 배정되고 의존은 순환이 없으며 설계 리뷰 지적의 배치도 맞다. 구현자가 막힐 곳은 V2의 코드 경로(기존 `layout.ts`·`i18n.ts`·`MapOverlay.tsx`와의 관계가 적히지 않음)와 V5의 `gm_busy`를 플레이어 서비스·스키마·플레이 화면에 연결하는 책임이 비어 있는 점, 이 둘(Major)이다. 나머지는 겹침 표와 결함 배정 정리다.

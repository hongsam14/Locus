## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Functional Design — V2 디자인 시스템
**Reviewed artifact:** `aidlc-docs/construction/V2-design-system/functional-design/business-logic-model.md`
**Class:** adversarial
**Iteration:** 2
**Date:** 2026-10-07T12:13:29Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V2-design-system/functional-design/frontend-components.md > § 6 / § 8.1 / TP-V2-16 · business-logic-model.md > § 6.3, § 10 | § 8.1이 깨지는 기존 단언을 자리와 처리 방식으로 적는다. grep 대조 결과 `notification-center`(components.test:357, play.test:138-154·267, deeds.test:138)와 `llm-notice`(home.test:276·286, components.test:595, gm.test:632·648, play.test:104·162)가 모두 목록에 있다. Select는 브라우저 `<select>`로 정해 native `fireEvent.change` 5곳이 유지되고, GmHub 단독 렌더는 `renderWithShell` 도우미로 처리한다. AppNav·`../layout`·`../viz`·MapOverlay import도 처리가 적혔다. 남은 틈은 R-10(toast 전역 저장소의 테스트 간 격리)뿐이라 새 ID로 옮긴다. | 없음 | Resolved |
| R-02 | Major | frontend-components.md > § 1.2, § 2 · business-logic-model.md > § 10 | § 10이 별칭 대신 직접 교체로 정했고(Modal·Toast·NotificationCenter 삭제, 사용처를 `ConfirmDialog`·`Dialog`·`toast()`로), § 1.2·§ 6과 모순이 없다. 같은 key 교체·key 없음 누적·`turn:<region_id>`·`play:run\|budget\|llm\|busy`가 "동작 변경"으로 적혔고 TP-V2-12가 단언한다. | 없음 | Resolved |
| R-03 | Major | business-logic-model.md > § 6.1 · domain-entities.md > § 5 · business-rules.md > BR-V2-15 | § 6.1이 오류 본문을 쓰는 네 자리를 정했다. Starlette `HTTPException` 처리기(404·405 기본 code 포함), 검증 422, `Exception` 500, `BodyLimitMiddleware` 직접 413(`api/uploads.py:100`의 `JSONResponse`가 `code`를 직접 싣는다고 적음). `RegionInUseError`는 `ERROR_CODES`에서 빼고 라우터가 `ApiError(409, 객체 detail, "region_in_use")`로 던진다고 정했다(world_editor.py:132 현행과 일치). TP-V2-8이 미들웨어 413과 객체 `detail` 유지를 단언한다. | 없음 | Resolved |
| R-04 | Minor | frontend-components.md > § 1.2 (`routes/AppNav.tsx`), § 1.3 | AppNav는 V2가 지운다고 정했고, components.test:14·561-579는 AppShell 테스트로 옮기며, § 1.3이 라우트 4개와 AppNav를 V2의 기계적 변경으로 기록했다(승인된 상위 표를 고치지 않고 FD에서 조정). | 없음 | Resolved |
| R-05 | Minor | domain-entities.md > § 1.6 · business-rules.md > BR-V2-05·06 | § 1.6 허용 쌍 표를 정본으로 못 박고, faint는 tint 위 금지, 조작은 sunken 위 금지로 적었다. 스크래치 재계산: muted/tint 6.13~7.0, faint/land 4.98·sea 6.06, danger/tint-danger 5.43, line-strong/chrome 3.25·bg 3.40·surface 3.10, fg/plate 15.0 로 표의 최저값과 일치한다. | 없음 | Resolved |
| R-06 | Minor | domain-entities.md > § 4 · business-rules.md > BR-V2-02·11 | `wikiDomain`(13개, enums.py의 WikiDomain과 일치)이 표에 들어왔고, 원문 노출 자리와 소유 유닛이 적혔다. `npc`는 라벨 없이 원문 + 개발 경고로 처리한다고 근거를 적었다. `connectionKind`와 `travelBy`의 사용처도 구분됐다. | 없음 | Resolved |
| R-07 | Minor | business-logic-model.md > § 7.2, § 7.3 · BR-V2-24, TP-V2-13·14 | useAction 가드를 ref로 정하고 TP-V2-13이 동기 두 호출을 단언한다. capabilities는 "다음 마운트에서 마지막 실패 30초 후면 재조회, 타이머 없음"으로 한 문장이 됐다. | 없음 | Resolved |
| R-08 | Minor | business-logic-model.md > § 2.4 · BR-V2-01 | 변환표에 `border-ink`·`bg-ink/…`·`accent-ink`·`.ink-underline`이 들어왔고(실제 사용 위치 MapCanvas·WorldFileBar·NewSessionForm·Range·AppNav·Modal·BuildPanel·index.css:57과 부합), `font-display` 검사는 `layout/AppShell.tsx`·`index.css` 밖 0건으로 파일 범위가 됐다. | 없음 | Resolved |
| R-09 | Minor | business-logic-model.md > § 5.4, § 8.3 · BR-V2-19 · TP-V2-10 | 시간대(보는 사람의 시간대, 테스트는 UTC 고정), `placeLabels` 처리 순서(지금 위치 → 선택 → 갈 수 있음 → 나머지, 무리 안 y·x·id), "놓는 시점에" 속성, Emberleaf 겹침은 측정해 기록(목표 0)으로 정리됐다. 단 `formatDate` 시그니처가 두 문서에서 다르다 → R-11. | 없음 | Resolved |
| R-10 | Minor | frontend-components.md > § 2 (`toast()`·`Toaster`) · § 8.1 (`renderWithShell`) · TP-V2-12 | `toast()`는 모듈 전역 저장소라(상태가 화면에서 Toaster로 이동) 한 테스트 파일 안에서 앞 테스트의 알림이 다음 테스트에 남는다. 위험 알림은 사람이 닫을 때까지 안 사라지고, `play.test`는 같은 파일에서 `notification-center`의 `toHaveTextContent`를 여러 번 단언한다(138-154·267). 앞 테스트의 `play.budget` 등이 남아 `not` 단언이나 문구 단언을 오염시킬 수 있다. 설계는 저장소 초기화를 말하지 않는다. | `toast` 저장소에 `clearToasts()`(테스트용)를 두고 `setupTests.ts`의 `afterEach` 또는 `renderWithShell`이 부른다고 한 줄 적는다. | New |
| R-11 | Minor | frontend-components.md > § 5 (`formatDate(iso, lang?)`, `formatDateTime(iso, lang?)`) vs business-logic-model.md > § 5.4 (`formatDate(iso, lang, timeZone?)`) · TP-V2-5 | 같은 함수가 두 문서에서 다른 시그니처다. 구현자가 `frontend-components.md`를 따르면 테스트(TP-V2-5)가 시간대를 고정할 길이 없다. | `frontend-components.md` § 5의 두 함수에 `timeZone?: string`을 더해 BLM § 5.4와 맞춘다. | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| § 8.1 표 대 `web/src/__tests__` grep (`notification-center`, `notif-`, `llm-notice`) | testid 단언 줄 번호가 표와 일치(components 357·595, deeds 138, gm 632·648, home 276·286, play 104·138-154·162·267). `notif-` 단언 0건 | R-01 닫힘. 목록 누락 없음 |
| `components.test:357`·`gm.test` 렌더 방식 | GmHub를 AppShell 없이 단독 `render`함 | `renderWithShell` 도우미 필요성이 맞다. 도우미 파일은 아직 없음(`web/src/test/` 없음, 코드 단계에서 만든다고 적힘) |
| `api/uploads.py:100`, `api/main.py` 핸들러, `world_editor.py:132` | 미들웨어 직접 `JSONResponse`, `RequestValidationError` 처리기만 있음, `RegionInUseError` 객체 detail | BLM § 6.1의 네 자리와 `RegionInUseError` 처리가 현행 코드와 맞는다 |
| 옛 클래스 잔여 사용처 grep | `bg-ink/30`(MapCanvas·NewSessionForm·Modal·BuildPanel), `border-ink`(WorldFileBar·AppNav), `accent-ink`(Range), `.ink-underline`(index.css:57) | 변환표가 이를 덮는다 |
| 대비 재계산(WCAG 상대 휘도, 스크래치) | § 1.6 허용 쌍의 최저값과 일치(±0.05) | R-05 닫힘 |
| WikiDomain 값 수 | enums.py 13개(`other` 포함 여부는 표에 13개 모두 있음) | R-06 닫힘 |
| `web/package.json`·`vite.config.ts` | `setupFiles: ./src/setupTests.ts` 존재. `fast-check`는 아직 없음(FD가 개발 의존성 추가를 명시) | 일관됨 |

### Summary

Critical 0, Major 0이라 READY다. 1차의 Major 셋(R-01~R-03)은 문서 안에서 직접 닫혔다. 깨지는 기존 단언 목록과 테스트 도우미, 별칭 대신 직접 교체와 합치기 규칙, 오류 `code` 계약의 네 자리가 현행 코드와 맞는다. 새로 찾은 Minor 둘(R-10 toast 전역 저장소의 테스트 간 격리, R-11 `formatDate` 시그니처 불일치)은 코드 단계 전 한 줄씩 고치면 되고 차단하지 않는다. 제안(지적 아님): 500용 `Exception` 처리기는 Starlette에서 `ServerErrorMiddleware`가 돌려서 응답을 보낸 뒤 예외를 다시 던지므로, TP-V2-8의 500 테스트는 `TestClient(raise_server_exceptions=False)`로 써야 한다. 이 경로의 응답은 CORS 미들웨어 바깥이라 개발 서버를 직접 가리킬 때는 `code`를 브라우저가 못 읽을 수 있다(프록시 사용 시 무관).

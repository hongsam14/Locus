# X3 Frontend UX Features — Code Summary

**결과**: 프론트 **24 vitest GREEN**(19→24, +5), tsc clean, `vite build` OK · 백엔드 **281 pytest GREEN**(+1 regen), ruff/black clean. 회귀 0. 외부 CDN 없음.

## 코드 리뷰(high, 멀티에이전트) 반영 — 7건 전부 수정
- **#1(backend, correctness)**: regen이 보존된 승격 소문을 시드로 재사용해 소문이 증식 → `_collect_sources(include_existing=False)` 추가, `regenerate_region`은 **캐노니컬만 시드**. 테스트에 count==4(무증식) 단언 추가.
- **#2(bulk 중복)**: generateAll `if(progress!=null) return` + pre-scan 전 progress 세팅, 지역 generate/regen 버튼도 progress 중 비활성화(추가 append 방지).
- **#3(타임라인 이벤트 구분 소실)**: `event_created` 템플릿 제거 → create/suggest/approve는 각자 summary로 폴백(구분 보존). `timelineText`에 summary 폴백 인자.
- **#4(무제한 pre-scan)**: `mapLimit`(상한 5)로 빈지역 판정 병렬 제한.
- **#5(토스트 타이머 리셋)**: `addNotif`/`dismissNotif` `useCallback` 메모이즈 → 자동 소멸 정상.
- **#6(testid 충돌)**: 토스트 testid를 `notif-{id}`(고유)로, region은 `data-region`. 알림 테스트를 notification-center+텍스트 기준으로 갱신.
- **#7(0/0 알림)**: 빈 지역 없으면 "생성할 빈 지역이 없습니다" 안내, runBulk는 caller가 progress 가드.
- (refuted 2건: region_changes 배열 optional·직렬화 가정 — 타입상 필수, 무효.)

## 백엔드 (Q6/Q7=A)
- `locus/session/rumor_service.py::regenerate_region`: **승격 소문 보존** — 승격은 삭제하지 않고 비승격만 삭제·재생성, 반환=`kept + fresh`. 타임라인 payload `+kept`. (기존 "drop all"에서 변경, BR-X3-9.)
- 테스트 `tests/session/test_game_master.py::test_regenerate_preserves_promoted_rumors` 추가. 기존 `test_regenerate_deletes_then_recreates`는 승격 없어 그대로 통과.

## 프론트 신규
- `web/src/i18n.ts` (C10): 한국어 UI 라벨 + `t(key,params)` + 타임라인 kind 템플릿 `timelineText()`(F2a) + 알림 세그먼트.
- `web/src/ui/LocalizedText.tsx` (C11): ko 기본 + 항목별 "원문" 토글.
- `web/src/ui/NotificationCenter.tsx` (C14): 우상단 fixed 토스트 스택, 자동 소멸 + 닫기.
- `web/src/ui/index.ts`: export 추가.

## 프론트 수정
- `web/src/types.ts` (C15): `SessionRumor.statement_ko?` · `SessionEvent.description_ko?` · `KnowledgeView.title?/statement_ko?/title_ko?` · 신규 `RegionTurnChange` · `TurnResult.region_changes?`(+pruned/feedback).
- `web/src/SessionPanel.tsx` (C12/C13/C14): **전체 생성**(빈 지역만, distortions+listRumors 판정, 병렬 청크 상한 + progress-bar + N/M) · **전체 재생성**(Modal 확인, 병렬) · **지역 재생성** Modal 확인(승격 보존 안내) · **advance-turn 알림**(region_changes→지역별 토스트) · 소문/이벤트 `LocalizedText` · 타임라인 `timelineText` · 라벨 `t()` 한국어화.
- `web/src/RegionPanel.tsx` (C11): 지식 항목 `LocalizedText`.
- 테스트: 라벨 한국어화로 `distortion`→`왜곡` 1건 갱신 + 신규 5건(전체생성 빈지역·전체재생성 확인·지역별 알림·원문 토글·타임라인 i18n).

## 결정 반영
- Q1=A(우상단 지역별 토스트) · Q2=A+progress-bar · Q3=A(별도 버튼+Modal) · Q4=A(타임라인 i18n) · Q5=A(원문 토글) · Q6/Q7=A(승격 보존). FR-UX2.1~2.6·3.1·3.4. SEC-E(병렬 청크 상한 BULK_LIMIT=5).

## 신규 testid
- `generate-all-btn`/`regen-all-btn`/`generate-progress`/`notif-{rid}`(+`notif-bulk`)/`rumor-text-{id}`(+`-toggle`)/`event-desc-{id}`/`knowledge-text-{id}`.

## 비고
- ko는 X1 read-lazy라 첫 조회는 원문일 수 있음 — 재조회 시 반영(BR-X3-4). X3는 응답 필드가 오면 표시.
- **모든 유닛(X1·X2·X3) 코드 완료.** 다음: Build & Test → Operations.

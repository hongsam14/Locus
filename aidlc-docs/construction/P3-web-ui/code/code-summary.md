# P3 Web UI — Code Summary

> additive — 기존 백엔드/프론트 회귀 0. 오프라인 GREEN.

## 수정/생성 파일
### 백엔드 (additive)
- `locus/session/game_master.py` — `list_distortions(session_id)`(읽기, 닫힌 세션 허용; RegionDistortion import 추가).
- `api/routers/session.py` — `GET /sessions/{sid}/distortions` → list[RegionDistortion](404).
- `tests/session/test_session_api.py` — distortions 조회(seeded 기본/set 후/404) 테스트.

### 프론트엔드 (`web/src/`)
- `types.ts` — `EventCategory`/`EventLifecycle`/`EventStatus` union, `SessionEvent`, `EventDraft`; `TurnResult` +applied/resolved ids.
- `api.ts` — `listEvents`/`createEvent`/`suggestEvents`/`approveEvent`/`resolveEvent`/`discardEvent`/`listDistortions`.
- `SessionPanel.tsx` — events/distortions state; refresh에 listEvents+listDistortions; Suggest events 버튼; 세션 전역 Event 목록(status badge·region 라벨·approve/discard/resolve); 선택 리전 Event 생성 폼(category/description/magnitude/lifecycle); distortion 슬라이더 실제값(distortions[regionId]) 반영; 닫힌 세션 disabled; data-testid.
- `__tests__/components.test.tsx` — api mock에 신규 메서드 추가; create/suggest/approve/resolve·실제 distortion·닫힌 세션 disabled 테스트.

## 검증 결과 (오프라인)
- **Backend: 219 pytest GREEN** (218 + distortions). ruff/black/compileall 클린. 세션 라우트 +1(distortions).
- **Frontend: 17 vitest GREEN** (14 + 3). `tsc --noEmit` 클린, `vite build` 클린.
- **총 236 offline (219 backend + 17 frontend).** 기존 SessionPanel 동작(generate/regen/advance/support/promoted badge/timeline) 보존.

## 스토리 커버리지
- FR-P8.1 ✅(Event 생성 폼) · FR-P8.2 ✅(Suggest + approve/discard) · FR-P8.3 ✅(Event 목록 + resolve) · FR-P8.4 ✅(Timeline event 항목 자동) · FR-P8.5 ✅(실제 distortion 표시) · NFR-P5 ✅(회귀 0).

# Phase 2 — Unit Dependency

## 의존성 매트릭스
| 단위 | 의존 | 이유 |
|---|---|---|
| P1 Event Foundation | (없음 — 기존 세션 레이어/Phase 1 기반) | SessionEvent 모델·Event CRUD·status enum 신설 |
| P2 Dynamic Engine | **P1** | SessionEvent/Event CRUD/status·lifecycle enum 사용; resolve 복원 완성 |
| P3 Web UI | **P2** | advance-turn 확장 결과·event API(suggest/approve/resolve/create)·TS 계약 사용 |

- **빌드 순서**: P1 → P2 → P3 (순차, 병렬 불가 — 선형 의존).
- **순환 없음**. 캐노니컬→세션 단방향(읽기 참조), 세션 쓰기는 캐노니컬 불변.

## 조정 지점 (Coordination Points)
- **SessionRepository 포트**(P1 정의) → P2가 dynamics/advance_turn에서 사용. 시그니처는 P1에서 확정.
- **SessionEvent.status/contributions 필드**(P1) → P2 resolve 복원·advance_turn 누적이 사용.
- **advance-turn API + event API**(P2) → P3 UI가 호출. TurnResult/SessionEvent TS 타입은 P2 산출 기준으로 P3 작성.
- **EventSuggester 주입**(P2): main.py 와이어링에 LLMProvider 연결.

## 테스트 체크포인트
- P1: Event CRUD/상태전이(in-memory) + postgres 어댑터 오프라인 스모크.
- P2: dynamics 순수 PBT(delta/전파/support/복원) + advance_turn 시퀀스 통합(mock LLM, in-memory repo) + Phase 1 회귀(소문/승격/NPC 쿼리 불변).
- P3: vitest + tsc + vite build; 기존 14 vitest 회귀.
- 전체(Build&Test): 177 backend + 14 frontend 회귀 GREEN + 신규 테스트; ruff/black/tsc 클린.

## 롤백 전략
- 세션 레이어 격리 — 단위별로 신규 모듈/라우트/테이블 제거로 복구. 캐노니컬 영향 0. P3→P2→P1 역순 롤백 가능.

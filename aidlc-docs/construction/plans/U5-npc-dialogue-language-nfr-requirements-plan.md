# U5 NPC 대화·언어 — NFR Requirements + Design (light) 플랜

**원하시는 것**: 세계관 자료로 월드를 만들고, 그 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG.
**지금 하는 것**: U5의 비기능 요구(대화 응답성·LLM 비용·프롬프트 주입·회귀·PBT·문서)를 한 장으로 확정 — 코드 생성 플랜이 지킬 수치와 방법을 정하는 단계.

실행 계획(`inception/plans/purpose-restructure-execution-plan.md` §NFR): 플레이·에디터 유닛은 **light** — 유닛별 `nfr/nfr-light.md` 한 장에 요구와 설계를 함께 적는다. 새 기술 스택 선택은 없다(C-3, C-4). Plan Review는 light 규칙대로 **advisory 한 번**(architecture-reviewer), 기록은 `construction/U5-npc-dialogue-language/nfr/reviews/nfr-light-review-01.md`.

## 플랜
- [x] 승인된 FD 산출물 분석(`construction/U5-npc-dialogue-language/functional-design/*`, 검토 02의 R-04·R-12·R-13 disposition)
- [x] NFR-1~9와 U5의 접점 정리; 질문 필요 여부 판단
- [x] `construction/U5-npc-dialogue-language/nfr/nfr-light.md` 작성(요구 + 설계 + 수치 + 검증 방법 + 코드 플랜 입력)
- [x] Plan Review(architecture-reviewer, **advisory** 1회) → `construction/U5-npc-dialogue-language/nfr/reviews/nfr-light-review-01.md`
- [x] 완료 메시지 + 승인 게이트 → 다음: U5 Code Generation Part 1(플랜)

## 질문
없음. U5에 걸리는 값은 이미 정해져 있다. 컨텍스트 한도는 FD-U5 Q3=A(전언 제외로 facts 12 · rumors 8 · 메시지 10), 표시 언어는 Q1=A(서버 기본 + 요청별), 대화 한 번 = LLM 1회는 가정 A-1·FR-C4, 정리 시점은 Q4=A다. 아래 가정은 값이 비어 있던 곳을 채운 것이고 코드 생성 플랜의 질문에서 바꿀 수 있다.

## 가정 (nfr-light.md에 반영)
| # | 가정 | 근거 |
|---|---|---|
| N5-1 | 메시지 길이 상한 500자(`NPC_MAX_MESSAGE_CHARS`), NPC 답 1~3문장 지시 | FD domain-entities §2, 프롬프트 |
| N5-2 | 응답 목표(로컬): `start`·`history`·`npcs` p95 ≤ 100ms(LLM 없음), `say`는 LLM 왕복에 지배되므로 목표를 두지 않고 **프롬프트 상한**으로만 관리(컨텍스트 한도 → 대략 1.2k 토큰 이하) | NFR-3, Q3=A |
| N5-3 | 대화 LLM 실패의 최악 시간 = 호출당 약 97초(`retry.py` `CALL_TIMEOUT_SECONDS=30` × `MAX_ATTEMPTS=3` + 백오프 1+2초). 대화는 턴 예산 밖이고 한 요청 = 한 호출이므로 요청 하나가 그 시간을 넘지 않는다 | NFR-5, 코드 확인 |
| N5-4 | 플레이어 입력은 프롬프트에 그대로 들어간다(자유 텍스트). 가드는 시스템 프롬프트의 컨텍스트 경계 선언 + 길이 상한이고, 완전한 주입 방어는 하지 않는다(로컬 1인 데모, 인증 없음 전제) | NFR-6, A-4 |
| N5-5 | 대화 이력에는 보관 정책을 두지 않는다(세션 삭제 시 함께). 프롬프트에 들어가는 것은 최근 10개뿐이므로 길어져도 비용이 늘지 않는다 | Q3=A |
| N5-6 | 사라진 NPC의 대화 행은 남는다. `history`는 읽히고 `say`는 404다(NPC가 월드에 없다) | NFR-9, FD BR-U5-28 |

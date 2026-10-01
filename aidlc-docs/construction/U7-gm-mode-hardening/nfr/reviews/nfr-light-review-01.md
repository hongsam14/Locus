## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements (light) — U7 GM 모드·안정화
**Reviewed artifact:** aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-01T02:04:13Z

### Findings
| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §1 NFR-5, 플랜 N7-4 | 제안 프롬프트 "≤ 8,000자"는 이 설계에서 도출되지 않는다. 묶인 것은 지역 수(30)·설명(160자)·지식 개수(2)·사건·행적 개수뿐이다. 이름·경로·지식 항목의 글자 수 상한은 없다. 30 × (이름+경로+160+지식 2개)는 항목당 약 270자만 넘어도 8,000자를 넘기고, 사건 5×160과 행적 5줄이 더해진다. 40개 지역 월드 단언은 30개 상한이 먼저 걸려 통과 여부가 월드 자료의 글자 수에 달린다. | 지식 항목·경로·이름의 글자 상한을 N7-3/N7-4에 더해 합계를 계산으로 보이거나, 8,000자를 실제 합계가 넘지 않는 값으로 바꾼다. 단언은 가장 긴 자료로 만든 월드로 한다. | New |
| R-02 | Major | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §1 NFR-3 (`npcs` 한 번에 `get_conversation` 0회), §3 | `npcs` 메시지 수 질의 1회는 새 저장소 포트 메서드(개수 일괄 조회)를 전제한다. 지금 `locus/play/npc/dialogue.py:92`는 NPC마다 `get_conversation`을 부르고, `locus/play/ports.py:113`에는 개수 메서드가 없다. §3 "신규 없음"과 §4 변경 목록 어디에도 포트 확장(PlayRepository, 구현 2곳, 계약 테스트)이 없다. 구현자가 추측해야 한다. | 필요한 포트 메서드와 시그니처, 구현 대상(SQLAlchemy·인메모리), 계약 테스트 추가를 §3 또는 §5에 명시한다. `PlayRepository`를 흉내 내는 테스트 더블이 있으면 함께 적는다. | New |
| R-03 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §1 NFR-6, N7-3 | 주입 방어가 `\n`(줄바꿈)만 다룬다. `\r`, U+2028/2029, `\x85` 등 다른 줄 구분자와, 사용자 글이 "material, not instructions" 머리말 구간을 닫는 형태는 검증 칸에 없다. 검증 사례도 `\n` 하나다. | 정규화 대상을 "모든 유니코드 줄 구분자와 제어문자"로 넓히고 `\r\n`, U+2028 사례를 검증 칸에 더한다. | New |
| R-04 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §3 "조정값 표 env" | env JSON 문자열을 pydantic-settings가 읽는다는 근거만 있고, 깨진 JSON이나 알 수 없는 키·범위 밖 값일 때의 동작(시작 실패인지 기본값 복귀인지)이 없다. `locus/shared/config/settings.py:99-101`은 같은 이유로 tuple을 쉼표 문자열로 바꾼 전례가 있다. NFR-4(`.env` 두 값만으로 데모)에 따라 새 env는 모두 기본값을 가져야 한다는 점도 적혀 있지 않다. | 새 env는 전부 기본값이 있고 `.env` 두 값만으로 부팅된다고 적고, 잘못된 JSON·범위 밖 값의 처리를 한 줄로 정한다. | New |
| R-05 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §1 NFR-3 vs 플랜 N7-1, N7-5 | `/log`(요청마다 타임라인 전체 순회)와 `/distortions`에는 구조 단언이 없고 p95 ≤ 100ms는 운영자 확인이다. 수천 줄 세션 조건의 줄 수·지역 수 전제가 수치로 적혀 있지 않아 재현 조건이 모호하다(U6 NFR 검토 R-05와 같은 종류). | p95 조건에 줄 수(예: 3,000)와 지역 수(예: 15)를 붙이고, `/log`가 저장소 읽기 1회임을 구조 단언에 더한다. | New |
| R-06 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > 근거, §1 NFR-7 | 기준선(pytest 636, vitest 74)은 CLAUDE.md와 일치한다. mypy 기준선 11은 이 검토에서 확인할 수 없다(실행 금지). `SessionPanel.tsx` 518줄은 확인했으나 위치는 `web/src/SessionPanel.tsx`이고 §1이 말하는 `features/gm/` 패널 디렉터리는 신설이다. | 코드 플랜 첫 단계에서 mypy 수를 실측해 적고, `SessionPanel.tsx` 이동 경로와 새 디렉터리를 신규로 선언한다. | New |
| R-07 | Minor | aidlc-docs/construction/U7-gm-mode-hardening/nfr/nfr-light.md > §1 NFR-2 | 요구 NFR-2의 PBT 대상에 맞춰 TP-U7-1~7만 나열하고 TP-U7-8(`Settings`→tuning, 예제 기반)은 빠졌다. NFR-6의 "의존성 취약점 0(npm audit)"도 U7 적용 여부가 적혀 있지 않다. | TP-U7-8을 NFR-2에 한 줄로 받고, `npm audit`은 적용 또는 비적용을 한 줄로 정한다. | New |

### Checks Run
| Check | Result |
|---|---|
| §4 테스트 파일:줄 참조 | 확인: test_rumor_dynamics.py:39, test_repository_contract.py:82, test_postgres_repo.py:97, test_models.py:225, test_deed_turns.py:312, test_player_mode.py:940/768, test_play_services.py 존재, tests/api/test_play_api.py:88(`/log`), tests/api/test_play_gm_api.py:194(`test_list_distortions`). 표는 파일명만 적어 디렉터리(tests/play, tests/api)는 불명확 |
| `ADDED_COLUMNS` 확장 방식 | `locus/play/storage/schema.py:214-248`: 열 추가와 재호출 무해 로직 존재, `feedback_share` 추가는 같은 패턴. `region_distortions` 항목은 아직 없음(신규로 맞음) |
| 테스트 기준선 636+74=710 | CLAUDE.md와 일치 |
| mypy 기준선 11 | 검증 불가(R-06) |
| `SessionPanel.tsx` 518줄, `data-testid` 28곳 | 확인: web/src/SessionPanel.tsx |
| `GM_ONLY_KINDS` | web/src/features/play/PlayLog.tsx:8 존재(클라이언트 필터) |
| hypothesis 프로필 `locus` | tests/conftest.py:12 존재 |
| NFR-1~9 요구 ID | purpose-restructure-requirements.md에 모두 존재, 표의 항목과 일치 |
| `get_conversation` N+1 | locus/play/npc/dialogue.py:92 확인; 개수 메서드는 ports.py에 없음(R-02) |

### Summary
수치와 방법이 대체로 측정 가능하고 요구 NFR-1~9와 FD의 규칙에 맞게 정리되어 있다. 새 기술 스택이 없다는 판단, 구조 단언을 오프라인 게이트로 삼는 방식, 스키마 보존(ADDED_COLUMNS)은 현재 코드와 맞는다. Major 2건(R-01, R-02)은 숫자와 포트 변경이 설계에서 도출되지 않는 곳이며, 둘 다 코드 플랜에서 한 줄 보강하면 풀려 advisory로 READY(Major 2건은 허용 범위)로 본다. 사람이 게이트에서 weigh할 점은 R-01(8,000자 목표)과 R-02(숨은 포트 확장)다. 나머지는 코드 플랜에서 받으면 된다.

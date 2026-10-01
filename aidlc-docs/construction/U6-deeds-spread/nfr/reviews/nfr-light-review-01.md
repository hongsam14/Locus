## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements + Design (light) — U6 행적·전파
**Reviewed artifact:** aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md
**Class:** advisory
**Iteration:** 1
**Date:** 2026-09-30T23:42:41Z

### Findings
| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md > §1 NFR-5, §2 실패 격리 | 호출당 106초는 `retry.py`와 일치한다. 그러나 선언·대화 마침 한 실행의 최악 시간이 수치로 없다("준비 106초 + 턴"). operations.md의 기존 상한(≈ 비용 턴 × 106초)은 회로 차단이 호출 실패 뒤의 나머지를 끊는다는 전제다. 준비 단계 LLM 실패는 "대체 서술, 판단 없음"으로 계속 진행하는데, 이 실패가 그 턴의 전파·캐노니컬 차단기를 세우는지 적혀 있지 않다(BR-U6-22는 전파 호출 실패만 말한다). 안 세우면 LLM 장애 시 준비 106초 뒤에 전파 호출이 또 106초를 쓰고, 차단기 없이 세면 예산 8 × 106 = 848초까지 간다. 배경 실행기는 FIFO 단일 워커라 그 시간 동안 다른 세션의 실행도 밀린다. | 행동 종류별(선언·대화 마침·이동) 최악 시간을 수치로 적는다. 준비 실패가 턴의 회로 차단을 세우는지 정하고(권장: 세운다), 그 결과로 operations.md에 쓸 경계를 명시한다. 해당 경로(준비 실패 → 전파 호출 생략)를 테스트 단계에 넣는다. | New |
| R-02 | Major | aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md > §1 NFR-8·NFR-9, plans/U6-deeds-spread-nfr-requirements-plan.md > N6-3, N6-6 (business-rules.md > BR-U6-34) | 스키마 추가 범위가 문서마다 다르다. N6-3은 "추가만 하는 열 셋", NFR-8은 "열 셋과 turn_runs 보강", BR-U6-34·domain-entities §7(18)은 session_rumors 4열(origin_kind, origin_deed_id, origin_appraisal_id, spread_from_region_id) + turn_runs 3열이다. `deeds`는 새 테이블이라 `create_all`이 만들므로 `deeds.run_id`는 ALTER 대상이 아닌데 BR-U6-34가 같이 적는다. 또 현재 `ensure_play_schema`는 비-SQLite에서만 `ADD COLUMN IF NOT EXISTS`를 쓰고 SQLite는 건너뛴다(schema.py 158-). `turn_runs.lang`은 NOT NULL이 자연스러워 기존 행에 server default가 필요하다. N6-6이 `session_rumors.origin_deed_id` 색인을 요구하지만, 기존 테이블에 `create_all`은 색인을 더하지 않는다. "코드 약 40줄"은 이 범위에서 과소 추정일 수 있다. | 열 목록을 한 표로 고정한다(테이블·열·타입·nullable·default·색인, 7열). 기존 테이블 색인은 별도 `CREATE INDEX IF NOT EXISTS`로 할지 정한다. 새 테이블의 `run_id`는 제외한다. 비용 추정을 고친다. | New |
| R-03 | Minor | aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md > §1 NFR-9, §2 실패 격리 | 실패 보상이 행적을 지우는 경로(BR-U6-36)는 `advanced == 0`인 실패 실행만 덮는다. 재시작 때의 `fail_stale_runs(reason="interrupted")`(api/main.py 101-105)는 보상을 하지 않는다. 준비 단계가 행적을 커밋한 뒤 프로세스가 죽으면 턴은 안 쓰였는데 행적이 남는다. NFR-9 "저장소 무결성"이 이 경우를 말하지 않는다. | 중단 실행의 행적을 지울지 남기고 감수할지 한 줄로 정한다. 남긴다면 NFR-9에 감수한 위험으로 적는다. | New |
| R-04 | Minor | aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md > §1 NFR-5 | `LLM_MAX_CALLS_PER_TURN`은 `ge=0`(settings.py 74)이다. 예산 0이면 "준비 호출 예약"이 불가능하다. 그 경우 NFR-4의 대체 동작(고정 문구, 판단 없음)을 타는지 적혀 있지 않다. EX-8은 예산 2만 덮는다. | 예산 0(및 1)에서의 준비 동작을 한 줄로 적고 예제를 더한다. | New |
| R-05 | Minor | aidlc-docs/construction/U6-deeds-spread/nfr/nfr-light.md > §1 NFR-1, NFR-7, NFR-3 | 기준선 621(557+64)과 mypy ≤ 11은 이 검토에서 검증할 수 없다(CLAUDE.md는 601, 545+56이며 U5 코드 리뷰 뒤 값이라는 근거가 아티팩트에 없다). `GET deeds` p95 ≤ 100ms는 행적 개수(N6-6은 세션당 수백) 전제가 없어 운영자가 같은 조건으로 재현하기 어렵다. | 코드 플랜 첫 단계에서 기준선과 mypy 수를 실측해 적는다. p95 목표에 행적 수(예: 300)와 소문 수 조건을 붙인다. | New |

### Checks Run
| Check | Result |
|---|---|
| `locus/shared/llm/retry.py`: 30×3+8+8 = 106초, 3회, 캡 8초, `max_retries=0` | 일치 |
| `settings.py`: `LLM_MAX_CALLS_PER_TURN` 기본 8, ge=0 | 일치(R-04) |
| 조정값 여섯 env 이름이 domain-entities §5와 같은가 | 일치 |
| BR-U6-15·21·22·28·29·34~37, TP-U6-1~8, EX-2·8·15·19, 이탈 13·18·19 해소 | 모두 존재 |
| `tests/conftest.py` hypothesis 프로파일 `locus`, `print_blob=True` | 존재 |
| `ensure_play_schema` 현재 동작(SQLite는 ALTER 생략, PG만) | R-02 |
| `fail_stale_runs` 경로의 보상 여부 | 보상 없음(R-03) |
| `best_path_weights(start_id, connections)` 존재 | 존재 |
| 테스트 기준선 621, mypy 11 | 검증 불가(R-05) |

### Summary
NFR 아홉 개가 모두 U6에 매핑되어 있고, 구조 단언(UoW 열린 동안 LLM 0회, 호출 횟수 정확히 1회)과 TP 대응은 오프라인에서 검증 가능한 형태다. FD 이월 네 건(R-10, R-15, R-16, R-17)과 제안 셋(N6-2~4)은 §4와 가정으로 빠짐없이 받았다. 위 Major 둘은 코드 플랜 입력이 모호한 곳이며(최악 시간의 경계, 스키마 열 목록), 게이트에서 한 줄씩 정하면 해결된다. 제안: N6-5의 주입 예제는 선언 경로만 덮으므로, 발언 → 판단 `summary` → NPC 프롬프트 경로에도 길이 상한·프레이밍 문장이 프롬프트에 들어 있는지 확인하는 단언 하나를 더하면 좋다.

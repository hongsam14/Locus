# 요구사항 — 루머 동역학 & Phase 2 하드닝 (코드리뷰 후속)

> **네이밍 주의**: 이 사이클은 "Phase 2 하드닝"으로 시작했으나, 명확화1=A 결정으로
> **[2]가 Phase 3 "루머 동역학(Rumor Dynamics)" 설계로 승격**되었습니다. 파일명은
> 안정성을 위해 `rumor-phase2-hardening-*`로 유지하되, 내용상 **Phase 3(부분) + 하드닝**입니다.

## 1. 개요 / 배경
Phase 2(P1+P2+P3) 완료 후 고강도 코드리뷰가 턴 엔진의 findings를 도출했다. 명확한
정합성/효율 3건([1] 포화 후 resolve 복원, [3] 빈 턴 support 감쇠, [9] 중복 read)은
이미 수정·커밋(`81be437`)되어 **범위 밖**이다. 이 문서는 나머지를 다룬다.

핵심 통찰(사용자): **support(공신력)** 는 루머가 얼마나 "살아있는지"를 나타내는 값으로,
세계를 다이나믹하게 만드는 핵심 변수다. [2]의 지수적 루머 증가는 "루머가 태어나기만 하고
소멸하지 않는" 구조적 결함이며, support를 **생존·증식의 지렛대**로 삼아 근본 해결한다.

## 2. 결정 요약 (검증/명확화 답변)
| 항목 | 결정 |
|------|------|
| 사이클 범위 (Q1) | **C** — [2]+[8]+프론트 워터폴+ [4]/[5] 조사 |
| [2] 프레이밍 (명확화1) | **A** — 루머 동역학/생명주기 전용 설계로 승격 (Phase 3 루머-피드백 포함, 자체 FD) |
| support 역할 (명확화2) | **C** — 생존(prune) + 증식 자격(threshold) 둘 다 |
| [8] upsert (Q3) | **A** — `SessionRepository`에 배치 `upsert_rumors` 추가 |
| 프론트 (Q4) | **A** — `SessionPanel.refresh` `Promise.all` 병렬화 |
| [4]/[5] (Q5) | **A** — 조사 후 실제 결함이면 수정 |
| 프로세스 (Q6+명확화3) | **B+A** — 풀 AI-DLC 단계, 스코프는 findings 목록 그대로 |
| 확장 (Q7) | **A** — Security off, PBT Partial on |

## 3. 기능 요구사항 (Functional Requirements)

### 테마 A — 루머 동역학 / 생명주기 (승격된 [2]; Phase 3 루머 피드백)
- **FR-H1 (support 감쇠 & 정리/prune)**: `advance_turn`에서 강화되지 않은 루머의 support는
  감쇠하고, support가 **바닥(floor) 임계값 미만**인 루머는 세션 집합에서 **정리(삭제)** 된다.
  → 자연 선택으로 루머 집합이 유한하게 유지된다. (승격된 루머의 예외 여부는 FD에서 확정.)
- **FR-H2 (support 기반 증식 자격)**: 매 턴 자동 append(루머 소스 수집)에서 **support ≥ 증식
  임계값**인 루머만 새 왜곡의 소스로 재사용된다. 임계 미만 루머는 새 루머를 낳지 않는다.
  수동 `generate_rumors`/`regenerate_region`의 소스 규칙은 영향받지 않는다.
- **FR-H3 (루머→지역 피드백 루프)**: 지역의 루머 상태 집계(예: 고-support/승격 루머의 밀도)가
  매 턴 그 지역의 distortion 진화에 **되먹임**된다(미뤄둔 Phase 3 루프). 이벤트가 없어도 강한
  루머가 지역을 계속 다이나믹하게 만든다. (되먹임 공식·가중치는 FD에서 확정.)
- **FR-H4 (결정성 & 튜닝 가능)**: 신규 파라미터(감쇠율·바닥 임계·증식 임계·피드백 가중)는
  상수/설정으로 노출되고 **결정적(LLM 비의존)** 이며, 가능한 한 순수 함수로 구현한다(PBT 대상).

### 테마 B — 효율 ([8], 프론트)
- **FR-H5 (배치 루머 영속화)**: `SessionRepository` 포트에 `upsert_rumors(list)` 배치 메서드를
  추가한다. `advance_turn`의 support 진화/정리는 이를 사용해 **턴당 트랜잭션 1회**로 쓴다.
  인메모리 + Postgres(+ SQLite 테스트) 어댑터 구현.
- **FR-H6 (프론트 refresh 병렬화)**: `SessionPanel.refresh()`의 독립적인 read(timeline/events/
  distortions/rumors)를 `Promise.all`로 병렬 로드한다(왕복 깊이 1회). 동작·표시는 불변.

### 테마 C — 캐노니컬 빌드 조사 ([4], [5])
- **FR-H7 ([4] set_wiki 순서 조사)**: `orchestrator.build_world`에서 `topology.build`가 wiki 주입
  **전에** 실행되어 토폴로지 가중/rationale에 common-sense prior가 반영되지 않는지 확인하고,
  실제 결함이면 wiki 주입을 build 전으로 옮기거나 동등하게 수정한다.
- **FR-H8 ([5] barrier terrain 드롭 조사)**: `map_image_ingestor`에서 연결 지역이 2개가 아닌
  barrier terrain이 조용히 버려지는 엣지케이스를 확인하고, 실제 결함이면 최소한 orphan/경고로
  드러내거나(또는 처리 규칙 보강) 수정한다. FD-B Q1=B 설계 의도와 정합성 유지.

## 4. 비기능 요구사항 (Non-Functional Requirements)
- **NFR-H1 (결정성)**: 루머 동역학 엔진(감쇠·정리·증식자격·피드백)은 결정적이어야 하며 LLM에
  의존하지 않는다. 루머 텍스트 생성만 LLM을 쓰고 graceful하다(실패 시 스킵, 턴 진행).
- **NFR-H2 (하위 호환/가산성)**: 모든 변경은 additive. 캐노니컬 레이어(Neo4j/OpenSearch) 불변.
  NPC 세션 쿼리 규칙은 유지한다(피드백은 distortion을 바꿔 생성에 영향, 쿼리 규칙 자체는 불변).
- **NFR-H3 (테스트)**: 오프라인 테스트 GREEN 유지, 회귀 0. 순수 동역학에 PBT(Partial) 추가.
  배치 어댑터는 오프라인(SQLite)로 검증. 프론트 vitest 유지.
- **NFR-H4 (인프라 무변경)**: 신규 인프라 없음. 스키마 변경이 필요하면 `init-schema` idempotent
  가산 컬럼/테이블로 한정.
- **NFR-H5 (확장)**: Security Baseline off, Property-Based Testing on(Partial).

## 5. 범위 밖 (Out of Scope)
- 이미 수정된 [1]/[3]/[9].
- **이벤트-이벤트 상호작용**(Phase 3 나머지 절반) — 이번 사이클엔 미포함(여전히 defer).
- 프로젝트 전체 아키텍처 감사(명확화3=A로 배제) — 스코프는 findings 목록으로 한정.
- 루머 텍스트 의미 기반 병합(명확화2에서 E 미선택) — support 기반 생존/증식이 1차 메커니즘.

## 6. 추적성 (Traceability)
| 코드리뷰 finding | 요구사항 |
|---|---|
| [2] 루머 지수 증가 (승격) | FR-H1, FR-H2, FR-H3, FR-H4 |
| [8] 루머 단건 upsert | FR-H5 |
| 프론트 refresh 워터폴 | FR-H6 |
| [4] orchestrator set_wiki | FR-H7 |
| [5] barrier terrain 드롭 | FR-H8 |

## 7. FD에서 확정할 열린 설계 파라미터
- 감쇠율/바닥 임계/증식 임계/피드백 가중의 구체 값과 공식.
- 승격(promoted) 루머가 정리(prune)에서 예외인지.
- 피드백 집계 방식(고-support 밀도 vs 승격 수 vs 가중 평균).
- [4]/[5]가 실제 결함인지의 조사 결론(수정 여부 분기).

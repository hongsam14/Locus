# UX Improvement — Requirements

## Intent Analysis
- **User Request**: 세 갈래 UX 개선 — (1) 프론트엔드 디자인/UX 개편, (2) 루머 생성 방식 개선(전체 생성 + 지역 상세 재생성), (3) 한국어 로컬라이징.
- **Request Type**: Enhancement (brownfield).
- **Scope Estimate**: Multiple Components — `web/` 프론트엔드 전반 + `locus/session/` · `api/routers/session.py` 백엔드(번역 저장·조회) + LLM 번역 유틸.
- **Complexity Estimate**: Moderate. 프론트 개편은 넓지만 위험 낮음; 로컬라이징은 저장 스키마/생성 파이프라인에 번역 필드가 추가되어 중간 복잡도.
- **Workspace Finding**: 프론트엔드는 이미 React+Vite+TS이며 인라인 스타일만 존재(디자인 시스템 없음). 따라서 항목 1은 **HTML→React 이관이 아니라 기존 React 앱의 디자인 시스템 도입/재스타일**이다 (Q1=A 확정).

## Verified Decisions (verification-questions 답변)
| Q | 답 | 결정 |
|---|---|---|
| Q1 | A | 기존 React 앱 유지, 디자인 시스템·스타일 입혀 UX 개편 |
| Q2 | A | **Tailwind CSS** 도입 |
| Q3 | A | 앱 전체 일관 디자인 시스템 |
| Q4 | A(+note) | 단일 라이트 테마. 시각 스타일 = **"Doodly"(손그림/스케치풍, 장난기 있는)** |
| Q5 | C | "전체 생성"은 빈 지역만 채움; 덮어쓰기(전체 재생성)는 별도 확인 |
| Q6 | B | 프론트 병렬 호출(Promise.all) + 진행률 표시 |
| Q7 | B(+note) | 재생성 동작 개선(승격 소문 보존·확인) + **변동 알림** — 승격 알림을 이벤트·루머 변동 전반 알림으로 확장(사용자 후속 요청) |
| Q8 | B | 콘텐츠 + UI 라벨 모두 한국어화 |
| Q9 | A | 백엔드가 **생성 시점에 원문+번역 함께 저장** |
| Q10 | A | 기존 **OpenAI LLMProvider 재사용** (포트 추상화 유지) |
| Q11 | B | 번역 표시 + **원문(영어) 토글/툴팁** |
| Q12 | A | **한국어만** (en→ko 고정, 언어 선택기 없음) |
| Security | **B (No)** + 지정 | 확장은 비활성. 단 SEC-A~E(입력검증·보안헤더·에러처리·의존성관리·엔드포인트 남용방지)만 일반 NFR로 적용 (사용자 후속 지정) |
| PBT | B (Partial) | 순수 함수·직렬화 왕복에만 PBT |

---

## Functional Requirements

### A. Frontend 디자인 / UX (FR-UX1)
- **FR-UX1.1** 기존 React 컴포넌트를 유지한 채 **Tailwind CSS** 기반 디자인 시스템을 도입한다 (인라인 `style={{}}` → Tailwind 유틸/클래스로 이전).
- **FR-UX1.2** 앱 전체(`MapOverlay`, `RegionPanel`, `SessionBar`, `SessionPanel`, `Toolbar`, `AugmentPanel`, `App`)에 **일관된 디자인 토큰**(색·간격·타이포·라운드·그림자)을 적용한다.
- **FR-UX1.3** 시각 컨셉은 **"Doodly"** — 손으로 그린 듯한 스케치 테두리, 장난기 있는/손글씨 느낌의 디스플레이 폰트, 부드러운 라운드·플레이풀한 강조. 정보 가독성은 유지한다.
- **FR-UX1.4** 단일 **라이트 테마**만 지원한다(다크 모드 제외).
- **FR-UX1.5** 개편 과정에서 기존 기능/상호작용과 `data-testid` 기반 프론트 테스트 계약을 보존한다(회귀 0 목표).

### B. Rumor 생성 UX (FR-UX2)
- **FR-UX2.1** SessionPanel에 **"전체 루머 생성"** 버튼을 추가한다. 클릭 시 세션의 **모든 지역 중 세션 소문이 없는 지역에만** 생성한다(이미 있는 지역은 건너뜀).
- **FR-UX2.2** **전체 재생성(덮어쓰기)** 은 첫 클릭에서 실행하지 않고 **별도의 명시적 확인** 후에만 수행한다.
- **FR-UX2.3** 전체 생성은 프론트엔드가 지역별 기존 엔드포인트를 **병렬 호출(Promise.all)** 하여 처리하며 **진행률 피드백**(예: N개 중 M개 완료, 스피너)을 제공한다. 부분 실패는 개별 표시하고 나머지를 중단하지 않는다.
- **FR-UX2.4** 재설계된 **지역 상세 뷰**에 **지역별 재생성 버튼**을 눈에 띄게 배치한다.
- **FR-UX2.5** 재생성 동작을 개선한다: **승격된 소문은 보존**하고, 파괴적 재생성 전 **확인 다이얼로그**를 노출한다.
- **FR-UX2.6** **변동 알림 (승격 → 이벤트·루머 변동 전반으로 확장)** — advance-turn 등 세션 진행에서 발생하는 상태 변동을 GameMaster가 놓치지 않도록 **가시적 알림**(토스트/배너 + 요약 목록)으로 노출한다. 조용한 변동 금지. 알림 대상은 기존 `TurnResult` 필드로 이미 제공되는 다음을 포함한다:
  - **루머 변동**: 승격(`promoted_ids`), 강등(`demoted_ids`), 프루닝/소멸(`pruned_rumor_ids`), 피드백으로 왜곡이 이동한 지역(`feedback_regions`), 이번 턴 새로 생성된 소문.
  - **이벤트 변동**: 이번 턴 적용된 이벤트(`applied_event_ids`), 자동/수동 해소된 이벤트(`resolved_event_ids`), 새로 제안된(suggested) 이벤트.
  - **지역 단위 알림 (턴당 지역별 1건)**: 한 턴에서 변동이 발생한 **지역마다 알림 1건**을 발생시킨다. 즉 병합 단위는 "턴 전체"가 아니라 **각 지역**이다 — 한 지역의 여러 변동(승격·소멸·이벤트 해소 등)은 그 지역의 알림 하나로 병합하고, 변동이 있는 지역이 N개면 알림도 N건 발생한다. 예(턴 5):
    - `[턴5] 지역 A — 2건 승격, 1건 소멸`
    - `[턴5] 지역 B — 이벤트 1개 해소, 소문 1건 생성`
  - 개별 변동 항목은 종류·대상(소문/이벤트 id·요약)을 담고, 지역 귀속은 소문/이벤트의 `region_id`와 `feedback_regions`로 결정한다. 변동이 없는 지역은 알림을 만들지 않는다. (알림의 표시 형태·지속/닫기·다건 스택 정책은 Functional Design에서 확정.)

### C. 로컬라이징 (FR-UX3)
- **FR-UX3.1** **UI 라벨/정적 텍스트**(버튼·헤더·상태 문구 등)를 한국어로 제공한다. 언어는 한국어 고정(Q12=A).
- **FR-UX3.2** **LLM 생성 콘텐츠**(소문 텍스트, 이벤트 설명, 타임라인 메시지, NPC 지식 등)에 대해 **생성 시점에 원문(en)과 번역(ko)을 함께 저장**한다.
- **FR-UX3.3** 번역은 **기존 `LLMProvider` 포트**를 통해 수행한다(별도 번역 서비스/키 없이 OpenAI 재사용). 번역 로직은 포트 뒤에 추상화되어 목킹 가능해야 한다.
- **FR-UX3.4** 프론트엔드는 **한국어 번역을 기본 표시**하고, **원문(영어) 토글/툴팁**을 제공한다.
- **FR-UX3.5** 저장된 번역은 재사용하여 **중복 번역을 피한다**(콘텐츠 변경 시에만 재번역).
- **FR-UX3.6 (설계 경계 — Functional Design에서 확정)** 캐노니컬 `Knowledge`(Neo4j, `build-world` 시 영어 생성)의 한국어 표시 방식: (a) `build-world` 시 번역 저장 vs (b) 세션 조회 시 번역 vs (c) 이번 범위는 세션 콘텐츠 위주. 세션 NPC 뷰가 캐노니컬 지식+소문을 함께 보여주므로 이 경계를 FD에서 결정한다.

---

## Non-Functional Requirements
- **NFR-UX1 (Usability)** 전체 생성·재생성·번역 등 지연 있는 작업은 진행 상태/완료 피드백을 제공하고 UI를 블로킹하지 않는다.
- **NFR-UX2 (Performance/Cost)** 번역은 저장·재사용으로 LLM 호출 비용을 최소화한다. 배치 번역 시 지역/항목 병렬성은 합리적 상한 내에서 처리한다.
- **NFR-UX3 (Maintainability)** 모든 외부 I/O(번역 포함)는 기존 포트(`LLMProvider`) 뒤에 유지한다. 오프라인 테스트는 목으로 동작한다.
- **NFR-UX4 (Testability)** 백엔드 오프라인 pytest + 프론트 vitest 스위트를 GREEN으로 유지하고 신규 동작에 테스트를 추가한다.
- **NFR-UX5 (Compatibility)** 캐노니컬(Neo4j/OpenSearch) 및 세션(PostgreSQL) 계약은 가산적으로만 변경한다(번역 필드 추가 = 후방호환 마이그레이션).
- **NFR-UX6 (Accessibility)** "Doodly" 스타일이라도 대비/폰트 크기 등 기본 가독성을 유지한다.

---

## Security Posture (Extension = **No**; 지정 실무 항목만 일반 NFR로 적용)
보안 확장(Security Baseline)은 이전 사이클과 동일하게 **비활성(No)** 이다 — blocking 게이트/컴플라이언스 요약 없음. 다만 사용자가 지정한 아래 **5개 실무 항목만** 일반 요구사항으로 적용한다(확장 규칙이 아니라 프로젝트 NFR로 취급).

- **SEC-A 입력 검증** — 신규/변경 API(전체 생성·번역·이벤트) 파라미터의 타입·길이·범위를 검증한다(FastAPI/Pydantic 스키마). DB 접근은 파라미터라이즈드 쿼리(SQLAlchemy) 유지.
- **SEC-B 보안 헤더** — HTML/정적 자산 서빙 경로에 기본 보안 응답 헤더(예: CSP `default-src 'self'`, `X-Content-Type-Options: nosniff`, `X-Frame-Options`)를 설정한다(필요 예외는 문서화).
- **SEC-C 에러 처리** — 번역/LLM/DB 등 외부 호출에 명시적 에러 처리(fail-closed, 리소스 정리)를 적용하고, 사용자 대상 응답은 일반화된 메시지로 스택/내부 경로를 노출하지 않는다.
- **SEC-D 의존성 관리** — 락파일(`package-lock.json`/`pyproject`) 유지·버전 핀 고정, 신규 의존성(Tailwind 등)은 공식 레지스트리·미사용 제거, Docker 이미지 `latest` 태그 지양.
- **SEC-E 엔드포인트 남용 방지** — LLM 비용이 드는 엔드포인트(번역·전체 생성)의 남용/비용 폭주를 방지한다(입력 상한·배치 크기 제한·합리적 병렬 상한 등; 필요 시 간단한 레이트리밋).

> 위 5개는 blocking 확장 규칙이 아니라 NFR로 다룬다. 인증·암호화·IAM·네트워크·세션 등 나머지 보안 영역은 본 로컬 no-auth MVP 범위 밖(불적용).

## Extension Configuration (this cycle)
| Extension | Enabled |
|---|---|
| Security Baseline | **No** (단, SEC-A~E 실무 항목은 일반 NFR로 적용) |
| Property-Based Testing | **Partial** (순수 함수·직렬화 왕복) |

## Out of Scope
- 다국어 선택기/추가 언어(한국어만) · 다크 모드 · 인증 시스템 도입 · 캐노니컬 그래프 스키마의 비가산적 변경 · 이미 별도인 Phase 3(rumor→region 피드백, event-to-event) 신규 기능.

## Key Requirements Summary
1. **Tailwind 기반 "Doodly" 라이트 테마**로 앱 전체 재스타일(컴포넌트 재사용, 회귀 0).
2. **전체 루머 생성(빈 지역만) + 확인형 전체 재생성 + 병렬 진행률**, 지역 상세 재생성 개선(승격 보존·확인), **턴 변동 알림**(승격/강등/소멸/피드백 + 이벤트 적용/해소/제안).
3. **한국어 로컬라이징** — UI 라벨 + LLM 콘텐츠(생성시 en/ko 동시 저장, OpenAI 포트 재사용, 원문 토글).
4. **Security 확장=No**, 단 SEC-A~E(입력검증·보안헤더·에러처리·의존성관리·엔드포인트 남용방지)만 NFR로 적용. **PBT=Partial**, 오프라인 테스트 GREEN 유지.

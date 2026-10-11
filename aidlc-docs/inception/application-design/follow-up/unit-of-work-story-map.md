# Follow-up Cycle — Requirements → Units Map

> 이번 주기는 User Stories를 건너뛰었다(같은 페르소나·여정, 승인 2026-10-07). 그래서 이 문서는 **스토리 대신 요구사항(FR/NFR)·UX 항목·결함 ID**를 유닛에 맞춘다. 근거: `inception/requirements/follow-up-requirements.md`, `inception/reverse-engineering/{screen-inventory,code-quality-assessment}.md`.

## 1. 기능 요구사항 → 유닛

| FR | 내용(요약) | 유닛 |
|---|---|---|
| FR-D1 | HTML 시안 2~3안, 사람이 고름 | V2 |
| FR-D2 | 의미 토큰, 테마 하나 | V2 |
| FR-D3 | 글꼴 역할 분리 | V2 |
| FR-D4 | 프리미티브 다시 만들기 | V2 |
| FR-D5 | 배치 틀·브레이크포인트 | V2(틀) + V4·V6·V8(적용) |
| FR-D6 | 지도가 컨테이너에 맞춰 줄어듦, 좌표 정규화 | V2 |
| FR-D7 | 지도 시각(단계 구별, 라벨 겹침) | V2(바탕) + V6(상태 배지·범례) |
| FR-D8 | 표기 규칙 | V2 |
| FR-D9 | 오류·안내 문장(+서버 `code`) | V2 |
| FR-D10 | `index.html` 머리 | V9 |
| FR-S1 | 홈 | V4 |
| FR-S2 | 플레이 | V4 |
| FR-S3 | GM | V6 |
| FR-S4 | 에디터(P1) | V8 |
| FR-S5 | 공통 상태 처리 | V2(StatusView) + V4·V6·V8 |
| FR-S6 | 접근성 기본 | V2(프리미티브) + V4·V6·V8(라벨·이름) |
| FR-L1 | 화면 문구 전부 | V2(사전·표기) + V4·V6·V8(화면 문구) |
| FR-L2 | 서버 번역 범위 확대 | V3 |
| FR-L3 | 데모 한국어판(+카드 문구·월드 이름) | V3 |
| FR-L4 | 불변 | V3(확인) |
| FR-C1 | 겹친 GM 쓰기 | V5 |
| FR-C2 | 닫기 ∥ GM 쓰기 | V5 |
| FR-C3 | 끊긴 run 보상 | V5 |
| FR-C4 | 지운 지역의 사건 | V5 |
| FR-C5 | 턴 / GM 구별 표시 | V5(서버) + V4·V6(화면) |
| FR-C6 | 합의 출처 순서 무관 | V7 |
| FR-C7 | 캐시 버전 순서 | V7 |
| FR-C8 | 백업 실패 시 교체 안 함 | V7 |
| FR-C9 | 다시 빌드 때 NPC·씨앗 이어 붙이기 | V7 |
| FR-C10 | 중복 id 거절·라벨 있는 삭제 | V7 |
| FR-C11 | 매니페스트 name = world.id 검사 | **V3**(설계에서 옮김) |
| FR-C12 | 보강 `needs` 대상 종류 | V7(서버) + V8(카드) |
| FR-C13 | 늦은 답·이중 실행 | V2(도구) + V4·V6·V8(적용) |
| FR-C14 | 남은 항목 기록 | V9 |
| FR-T1 | CI 액션·러너 | V1 |
| FR-T2 | dev npm audit 0 | V9 |
| FR-T3 | mypy 0 + CI 게이트 | V9 |
| FR-T4 | 문서 어긋남 | V9(+V7의 README 빌드 문장) |
| FR-T5 | env.example | V9 |
| FR-T6 | 테스트 위생 | V9 |
| FR-T7 | 라이브 시나리오 | V9 |

**빠진 FR: 0** (FR-D 10, FR-S 6, FR-L 4, FR-C 14, FR-T 7 = 41).

## 2. 비기능 요구사항 → 유닛

| NFR | 유닛 |
|---|---|
| NFR-1 회귀 0 | 모든 유닛(공통 완료 조건) + V9(mypy 0, audit 0) + B&T |
| NFR-2 사람 화면 확인 | V2·V4·V6·V8(캡처) + B&T(체크리스트) |
| NFR-3 대비·읽기 | V2(NFR light, 토큰 쌍 계산) |
| NFR-4 크기 | V2(NFR light, 예산) + B&T(확인) |
| NFR-5 호환 | V2(오류 `code` 가산), V3(번역 칸 가산), V5(`gm_busy` 가산) |
| NFR-6 PBT Partial | V3(번역 파일 왕복, PBT-02), V7(합의 순서 무관, PBT-03), V5(필요하면 순수 규칙) |
| NFR-7 브라우저 | V2(NFR light 범위) + B&T |
| NFR-8 보안 확장 꺼짐(기존 검사 유지) | V3(번역 파일 경로 검사) |
| NFR-9 키 없이 | V3(한국어 데모) + B&T |
| NFR-10 동시성 검증 | V5(NFR light, 끼워 넣기 재현) + B&T(운영자 PG 확인) |

## 3. UX 항목 → 유닛

| UX | 유닛 |
|---|---|
| UX-01 손글씨 버튼 | V2 |
| UX-02·03 가로 스크롤·옆 열이 떨어짐 | V2(틀·지도) + V4·V6·V8 |
| UX-04 원문 enum·내부 수치 | V2(표기) + V4·V6·V8 |
| UX-05 영어 본문 | V3 |
| UX-06 오류 원문 | V2 |
| UX-07 날짜 로캘 | V2 |
| UX-08 개발자 지시문 | V2(문장) + V4·V6·V8(한 번만 보임) |
| UX-09 파일 input | V2(FileInput) |
| UX-10 로딩·빈 상태 | V2(StatusView) + V4·V6·V8 |
| UX-11 대화상자·알림·select 복사 | V2 |
| UX-12~16 홈 | V4 |
| UX-17, UX-19~25, UX-27 에디터 | V8 |
| UX-18 지도 단계 구별·라벨 | V2 |
| UX-26 지도 배경 저장 | 범위 밖(next-cycle) |
| UX-28~33 플레이 | V4 |
| UX-34~42 GM | V6(UX-40 지도 쪽은 V2 + V6) |

**빠진 UX: 0** (UX-26은 요구사항 § 9에서 범위 밖으로 정함).

## 4. 결함 ID → 유닛

| 결함 | 유닛 |
|---|---|
| #9, #12(서버), RE-P01, RE-P06, U8 §3 피드백 몫 | V5 |
| #12(웹 이중 클릭), #14, #15, RE-F01, F02, F04, F05, F11, F14 | V6 |
| RE-F03 | V4 |
| RE-F08 (턴 폴링 상한) | V4 — FR-C14 규칙: 플레이 화면을 다시 짜며 같은 코드를 만지므로 함께 고친다 |
| RE-F07, RE-F12, RE-F13 | V8 — FR-C14 규칙: 에디터를 다시 짜며 같은 코드를 만지므로 함께 고친다 |
| RE-F06 (스코프 없음 링크) = UX-22 | V8 |
| RE-F10 (DeedPanel 빈 상태) = UX-10 | V6 |
| RE-F09 (capabilities 다시 읽기) | V2 — FR-C14 규칙: 요청 도우미를 만들며 같은 코드를 만지면 함께, 아니면 next-cycle |
| RE-F15 (ESLint 없음) | 범위 밖(next-cycle). 훅 도구(V2)가 같은 결함 꼴을 줄인다 |
| #5(a), RE-P02, RE-P03, RE-P04, RE-P12(일부) | V5 |
| RE-W01, W02, W03, W04, W18, #10, #13 | V7 |
| #11 | V3 |
| RE-T01, RE-T02, RE-T12 | V9 |
| 나머지 RE-W/P/F/T low·정리, U8 리뷰 §3 22건·§2 11건·설계 메모 3·4·6~10 | V9가 `next-cycle.md`에 기록(FR-C14, 요구사항 리뷰 R-03) |

## 5. 리뷰 지적(Accepted risk) → 닫을 유닛

| 지적 | 유닛 |
|---|---|
| 요구사항 R-01 (에디터 P1 경계) | V2(공유 대화상자 교체) + V8(넘길 때 문장) — `unit-of-work.md` V8 |
| 요구사항 R-02 (데모 카드) | V3 (설계 Q4=A로 범위에 들어옴) |
| 요구사항 R-03 (U8 이월 묶음) | V9 |
| 요구사항 R-04 (다시 빌드 동작) | V7 (설계 Q3=A) |
| 요구사항 R-05 (확인 방법) | V2 NFR light + B&T |
| 요구사항 R-06 (브랜치) | 정함(PR #4 병합 → `feat/follow-up`, V1은 `chore/ci-actions`) |
| 설계 R-01, R-03, R-04 | V5 FD |
| 설계 R-02, R-05, R-06, R-08 | V7 FD |
| 설계 R-07 | V3 FD |
| 설계 R-09 | 정함(UOW-Q2=A, V9) |

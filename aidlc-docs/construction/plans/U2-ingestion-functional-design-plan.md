# U2 Ingestion — Functional Design Plan

U2는 멀티모달 입력(텍스트 메모 / 지도 이미지(VLM) / 구조화 맵 / 컨셉아트)을 정규화된 `IngestionResult`로 변환합니다(FR-A, US-1.1~1.4). U1 모델·provider 추상화를 사용합니다. 아래 질문에 답해 주시면 FD 산출물을 생성합니다.

각 `[Answer]:` 뒤 보기 문자, 끝나면 "완료". 권장(Recommended) 표시.

---

## Questions

## Question FD2-Q1 — 텍스트/이미지 추출 방식
LLM/VLM로부터 엔티티·관계·지역을 어떻게 뽑을까요?

A) 모달리티별 **단일 구조화 출력 호출**(`llm.structured`/`vlm`)로 한 번에 추출 — 정의된 스키마로 엔티티/관계/지역힌트/지형 반환 (Recommended — 단순·결정적, MVP)
B) 다단계 체인(엔티티 추출 → 관계 추출 → 검증) — 정교하나 호출↑·복잡
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD2-Q2 — 단일 입력 내 중복 처리
한 번의 ingestion 내에서 같은 이름의 엔티티가 여러 번 나오면?

A) 정규화 이름 기준 병합(대소문자/공백 정규화), confidence는 최댓값 (Recommended)
B) 병합하지 않고 그대로(후속 단계/온톨로지에서 병합)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD2-Q3 — 구조화 맵 입력 포맷
어떤 구조화 포맷을 지원할까요?

A) **Locus 맵 JSON**(regions[], connections[]) + **GeoJSON**(FeatureCollection) 둘 다 (Recommended — 간단 포맷 + 표준)
B) Locus 맵 JSON만
C) GeoJSON만
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD2-Q4 — confidence 산정
추출 항목의 confidence는?

A) LLM/VLM 구조화 출력이 self-report한 값 사용 + 모달리티 기본값(구조화 맵=1.0, 텍스트=모델값, 컨셉아트=낮음 예:0.4); 임계 미만은 저신뢰 플래그 (Recommended)
B) 모두 고정 기본값(1.0), 저신뢰 개념 없음
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD2-Q5 — U2의 산출 경계 (지역/지형)
지도/텍스트에서 지역·지형을 얼마나 만들까요? (토폴로지 그래프는 U3 담당)

A) U2는 **region_hints + terrain 단서**(엔티티)만 산출, 계층/연결 그래프 구성은 U3에 위임 (Recommended — 단위 경계 명확)
B) U2가 기본 계층/연결까지 일부 구성
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question FD2-Q6 — 컨셉아트(US-1.4, P1) MVP 범위
컨셉아트 처리는?

A) 기본 포함 — VLM로 장소·분위기 보조 단서를 낮은 confidence로 추출 (Recommended)
B) 인터페이스만(stub) — 차순 구현, 지금은 빈 결과 반환
X) Other (please describe after [Answer]: tag below)

[Answer]: A

---

## Mandatory Artifacts (답변 후 생성)
- [ ] `domain-entities.md` — U2 입출력 모델·추출 스키마(LLM 구조화 출력용)
- [ ] `business-logic-model.md` — Ingestor별 흐름(text/map-image/structured/concept-art), 병합, 저신뢰 플래그
- [ ] `business-rules.md` — 검증·제약(포맷 스키마, confidence 기본값/임계, 병합 규칙)

## Execution Checklist
- [x] 1. FD2-Q1~6 반영 (all A)
- [x] 2. domain-entities.md / business-logic-model.md / business-rules.md 작성

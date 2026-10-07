## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** NFR Requirements + NFR Design (light) — V2 디자인 시스템
**Reviewed artifact:** `aidlc-docs/construction/V2-design-system/nfr/nfr-light.md`
**Class:** advisory
**Iteration:** 1
**Date:** 2026-10-07T12:27:54Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | aidlc-docs/construction/V2-design-system/nfr/nfr-light.md > § 2.2 결정 · aidlc-docs/construction/V2-design-system/functional-design/domain-entities.md > § 2 (101-102행), business-logic-model.md > 94-95행 | NFR 노트가 승인된 FD의 글꼴 굵기를 바꾼다(나눔명조 700·800 → 700만, Noto Sans KR 400·500·700 → 400·700). FD 두 곳은 여전히 800과 500을 적고 있다. NFR 노트는 이를 FD 변경으로 선언하지 않았고, 이 굵기를 쓰는 곳(제목, 버튼 등)도 확인하지 않았다. 코드 계획 작성자가 FD 표를 따르면 없는 굵기를 요청해 브라우저가 가짜 굵기를 합성하거나 예산이 깨진다. | 이 결정이 승인된 FD 값을 바꾼다고 노트에 명시하고, FD § 2와 BLM 94-95행을 700 / 400·700으로 맞추는 일(또는 코드 계획 첫 단계로 넣는 일)을 적는다. 토큰·프리미티브에서 `font-medium`·800을 쓰는 곳이 없음을 확인하거나 매핑(500→400 또는 700)을 정한다. | New |
| R-02 | Minor | nfr-light.md > § 2.2 표와 \"측정 방법\" | 글꼴 크기는 시안 B 화면의 글자로 어림한 값이다. 내레이션·NPC 대사·월드 이름은 LLM 출력과 사용자 입력이라 한글 조각 수에 상한이 없다. 홈 462 kB는 NFR-4(첫 화면 < 760 kB)와 가깝지 않지만, 플레이 화면은 데이터에 따라 Noto 124조각·나눔 92조각 전체(수 MB)까지 늘 수 있다. 노트는 \"시안 기준 어림\"만 적고 상한 수치를 주지 않았다. | code-summary의 실측 옆에 데이터 의존 최악값(전체 조각 합)을 참고로 적고, 첫 화면 기준이 홈의 데모 카드 글자임을 명시한다. 새 월드의 홈 실측도 1건 더한다. | New |
| R-03 | Minor | nfr-light.md > § 2.1 \"넘으면\" | 예산은 JS gzip **합계** ≤ 125.6 kB인데(요구사항 NFR-4), 초과 시 대응이 `React.lazy`로 GM·에디터를 나누는 것이다. 지연 적재는 첫 화면 JS를 줄일 뿐 합계는 그대로다. 예상 합 119~122 kB는 여유가 3~6 kB이고 새 코드 +7~10 kB는 측정 아닌 어림이다. | 초과 시 대응이 합계 예산을 만족시키는 것이 아니라 \"사유를 적고 첫 화면 JS를 기준으로 판정\"임을 분명히 한다(요구사항의 \"넘으면 사유를 적는다\"와 일치시킨다). | New |
| R-04 | Minor | nfr-light.md > § 1 NFR-3 · domain-entities.md > § 1.6 | 대비 테스트는 허용 쌍 표의 칸만 계산한다. (a) 표에 투명도 값(`map-plate` 90%, 호버·accent 22% 둘레)이 있는데 투명 색을 바탕과 합성해 계산하는 규칙이 없다. (b) 가장 얇은 여유는 line-strong/surface 3.10(기준 3.0)과 faint/sunken 4.78이며, \"조작은 sunken 위에 두지 않는다\" 같은 금지 쌍은 계산이 아니라 규율에 의존한다. 표 밖 조합이 컴포넌트에 쓰이면 어떤 테스트도 잡지 않는다. | 테스트가 알파 색을 불투명 바탕 위에 합성해 계산한다고 적는다. 표 밖 조합을 막는 수단(예: 토큰 사용 grep 또는 프리미티브 안에서만 쌍을 고정)을 한 줄로 정하거나 감수하는 위험으로 적는다. | New |
| R-05 | Minor | nfr-light.md > § 2.2 \"한 번 받은 조각은 … 브라우저 캐시\" · web/nginx.conf | 글꼴 조각 재사용(홈→플레이 820 kB 완화)이 브라우저 캐시에 기댄다. 확인한 `web/nginx.conf`에는 `/assets` 해시 파일의 `Cache-Control`·`expires`가 없다. 기본 ETag·Last-Modified 재검증으로 304가 나가 동작은 하나, 조각 수십 개의 재검증 왕복이 생긴다. | 코드 계획에 nginx `/assets/` 불변 캐시 헤더 추가를 넣거나, 이 점을 범위 밖으로 적는다(NFR-4는 첫 방문 기준). | New |

### Checks Run

| Check | Result | Interpretation |
|---|---|---|
| 현재 JS 기준값 96.6 kB | web-dist-baseline/assets/index-BkQEzvK4.js 324,668 B, `gzip -c \| wc -c` = 96,637 B | 노트와 일치. 예산 96.6 × 1.3 = 125.6 OK |
| Gaegu 한글 woff2 762 kB | 스크래치·index.css가 korean-400/700 + latin을 import, 노트의 283.7+478.6 | 기준(요구사항 NFR-4 약 760 kB)과 일치 |
| 후보 패키지 판 | @fontsource 3종 5.3.0, radix dialog 1.2.0·tabs 1.1.22, fast-check 설치됨, React 16.8~19 peer | 노트와 일치. React 18 호환 |
| 나눔명조 700 단일 굵기 가능 | 5.3.0에 400·700·800 조각 존재 | 700만 쓰는 선택은 가능, R-01 참조 |
| 노트가 요구사항·유닛 NFR 항목을 모두 덮음 | NFR-1~10 전부 행 있음(NFR-10 V2 무관), 유닛 NFR light 5개(headless·글꼴·대비 방법·브라우저·폭 상한) § 2~5에 있음 | OK |
| PBT Partial(02/03/07/08/09) | § 1 NFR-6이 대상 4개, 생성기, 시드 출력·재현(FC_SEED), 프레임워크 선정을 적음 | OK |
| FD 일관성(글꼴, 대비 수치, 폭 값) | 대비 표 최저값(3.1, 4.8) 일치. 글꼴 굵기만 불일치 | R-01 |
| FD 리뷰 R-10·R-11 | clearToasts + afterEach는 § 3·§ 6에 반영. R-11(formatDate 시그니처)은 NFR 범위 밖이라 코드 계획에서 닫을 것 | 노트 쪽 문제 없음 |
| 500 JSON 주장 | api/main.py는 BodyLimitMiddleware만 사용, CORS 없음(노트 서술과 일치, 확인한 범위에서) | OK |

### Summary

수치(JS 96.6 kB 기준, 글꼴 762 kB 기준, 패키지 판)는 스크래치 산출물로 재현되고 NFR-1~10과 유닛의 NFR light 항목, PBT Partial을 빠짐없이 덮는다. 사람이 볼 것은 R-01(승인된 FD의 글꼴 굵기를 NFR 노트가 바꾸는데 FD 두 곳이 그대로임)이고, 나머지는 글꼴 크기가 어림이라는 점과 지연 적재·대비 테스트·캐시 헤더의 보완 한 줄씩이다. Major 1건이라 READY이며 코드 계획에서 닫을 수 있다.

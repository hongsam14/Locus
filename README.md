**Locus는 세계관 자료로 월드를 만들고, 그 월드 안에서 소문과 사건이 지형을 따라 퍼지며 지역마다 NPC가 다르게 아는 것을 직접 겪는 솔로 TRPG다.**

[![CI](https://github.com/hongsam14/Locus/actions/workflows/ci.yml/badge.svg)](https://github.com/hongsam14/Locus/actions/workflows/ci.yml)

## 무엇을 하나
1. **자료 넣기**: 세계관 메모, 지도(JSON·그림), 컨셉 아트를 올립니다.
2. **월드 자동 구성**: 지역과 그 사이 연결(길·강·막힌 고개), 지역마다 알려진 지식, NPC가 만들어집니다.
3. **에디터에서 다듬기**: 지도에서 지역을 옮기고 잇습니다. 지식의 범위를 고치고, 빈틈을 묻는 보강 질문에 답합니다.
4. **세션·이동·대화**: 캐릭터로 지역을 오가며 NPC와 이야기합니다. NPC는 자기 지역에서 알 수 있는 것만 압니다.
5. **선언·사건**: 하고 싶은 일을 선언하면 GM이 서술합니다. 사건 씨앗을 터뜨리면 그 지역부터 세계가 흔들립니다.
6. **소문이 지형을 따라 퍼짐**: 턴이 흐르면 행적과 사건이 소문이 되어 연결을 따라 한 칸씩 퍼집니다. 지역마다 다르게 일그러져 들립니다.

## 스크린샷
(준비 중입니다. 홈의 데모 카드, 플레이 화면, GM 화면을 둘 자리입니다.)

## 시작하기
Docker와 Docker Compose가 있으면 됩니다.

```bash
./scripts/setup-volumes.sh                      # 처음 한 번: ./data 폴더를 만든다(다시 돌려도 해가 없다)
cp env.example .env                             # NEO4J_PASSWORD, SESSION_DB_PASSWORD 두 값을 채운다
docker compose --profile service up -d --build  # neo4j·opensearch·postgres + app(:8000) + web(:3000)
```

http://localhost:3000 을 열고 데모 카드의 **[바로 플레이]** 를 누릅니다. 데모 월드를 불러오고, 시작 지역에 캐릭터를 세운 뒤, 플레이 화면으로 갑니다. LLM은 부르지 않습니다.

- **포트가 이미 쓰이고 있으면**: `.env`에 바꿀 번호를 적습니다. 컨테이너끼리는 compose 네트워크로 닿으므로 앱 설정은 그대로입니다.
  ```bash
  NEO4J_HTTP_PORT=17474
  NEO4J_BOLT_PORT=17687
  # OPENSEARCH_PORT, SESSION_DB_PORT, DASHBOARD_PORT, API_PORT, WEB_PORT도 같다
  ```
- 인프라 포트(neo4j·opensearch·postgres·dashboard)는 `127.0.0.1`에만 열립니다. app(:8000)과 web(:3000)은 모든 주소에 열려서, 같은 망의 다른 기기에서도 데모를 볼 수 있습니다.
- OpenSearch Dashboards: `docker compose --profile tools up -d dashboard` (http://localhost:5601)
- 멈추기: `docker compose --profile service --profile tools down`
- 상태 보기: `docker compose ps`, `curl localhost:8000/health`, `curl localhost:8000/api/capabilities`

## 키 없이 둘러보기
`OPENAI_API_KEY`가 없어도 앱은 뜹니다.

- **됩니다**: 데모 불러오기와 [바로 플레이], 지도와 이동, 턴, 에디터 편집, World File 저장·불러오기, 보강 질문(템플릿), 사건 씨앗 시작, GM의 수동 사건·왜곡도·지지도
- **꺼집니다**: 자료로 월드 만들기, NPC 대화, NPC 초안, 소문 생성·재생성, 사건 제안
- 화면은 머리에 한 줄로 알리고, 꺼진 버튼에 "LLM 키가 필요합니다"를 붙입니다(`GET /api/capabilities`).
- `.env`에 `OPENAI_API_KEY`를 넣고 `docker compose --profile service up -d`로 다시 띄우면 켜집니다.

## 데모 월드: Emberleaf Isle
- 절벽과 강으로 나뉜 섬입니다. 세 고장(Greenreach, Stonebrow, Saltmarch)에 마을 여덟이 있습니다. 시작은 항구 Saltwake Harbor입니다.
- 사건 씨앗 셋이 기다립니다(Ambermeadow의 버섯 들판 역병, Ashen Dig의 봉인된 유물, Gutterlight의 등불 조합 분열). GM 화면의 [시작]으로 터뜨립니다.
- 데모는 코드가 아니라 데이터입니다. `locus/world/demo/worlds/`의 매니페스트와 World File을 더하면 홈에 카드가 하나 늘어납니다.

## 진행 중인 기능
| 기능 | 상태 | 한 줄 |
|---|---|---|
| 교차 월드 prior 검색 | 진행 중 | 다른 월드의 상식 prior를 도메인 태그로 찾는 길이 있으나, 도메인 필터가 저장된 값과 아직 맞지 않습니다 |
| 컨셉 아트 수집 | 진행 중 | 올린 그림은 빌드에 들어가지만, 낮은 신뢰도의 엔티티 단서로만 남고 지식이 되지 않습니다. 빌드 패널의 그 칸에 "진행 중" 표시가 있습니다 |
| LangGraph 래퍼 | 진행 중 | 보강 루프(탐지 → 질문 → 적용)를 LangGraph로 본 것이 있으나, 어떤 서비스에도 연결되지 않았습니다 |
| wiki 순환 구조 | 진행 중 | prior는 빌드마다 한 번 증류되어 빌드·보강이 읽습니다. 쓰인 결과가 prior를 다듬는 길은 다음 사이클입니다 |

모듈마다 docstring 첫 줄에 `STATUS: in-progress`가 있습니다.

## 개발
호스트에서 백엔드와 프런트엔드를 따로 돌립니다.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
docker compose up -d                       # 인프라만 (neo4j + opensearch + postgres)
locus init-schema                          # 제약·인덱스·세션 테이블 (여러 번 돌려도 된다)
locus world demo --name emberleaf --world emberleaf   # LLM 없이 데모 월드 불러오기
uvicorn api.main:app --port 8000 --workers 1
cd web && npm ci && npm run dev            # http://localhost:5173 (/api → :8000)
```

- 호스트에서 돌릴 때는 `.env`의 `NEO4J_URI`, `OPENSEARCH_URL`, `SESSION_DB_URL`을 `localhost`와 쓰는 포트 번호로 맞춥니다.
- API는 워커 하나로 돌립니다(프로세스 안의 `WorldCache`).

검사는 CI(`.github/workflows/ci.yml`)와 같습니다.

```bash
ruff check locus api tests && black --check locus api tests
pytest                                      # 오프라인: 외부 I/O는 모두 포트 뒤의 가짜
mypy locus api                              # 기준선 11건 (CI에는 없다)
cd web && npx tsc --noEmit && npx vitest run
cd web && npm audit --omit=dev              # 0건이어야 한다
```

이 저장소는 AWS AI-DLC 방법론으로 개발합니다. 설계·계획 산출물은 `aidlc-docs/`에 있습니다(상태: `aidlc-docs/aidlc-state.md`, 운영: `aidlc-docs/operations/operations.md`).

## 디렉터리
```
locus/                 코어 패키지, 다섯 경계
  shared/              모델, 설정(tuning), LLM 공급자, 저장소 포트·어댑터
  knowledge/           합의(지역마다 아는 것), 전파, 로더, 질의
  world/               수집, 토폴로지, 온톨로지, wiki, 보강, 빌드, 에디터, World File, 데모
    demo/worlds/       데모 매니페스트와 World File (데이터)
  play/                세션, 턴, 플레이어, NPC 대화, 행적·전파, 소문, 사건, GM
  localization/        번역 캐시
api/                   FastAPI 조립 루트 (/api/world, /api/knowledge, /api/play, /api/gm)
web/                   React + Vite + TypeScript (홈, 에디터, GM, 플레이 화면)
tests/                 경계별 오프라인 테스트
scripts/               setup-volumes.sh
aidlc-docs/            AI-DLC 설계·계획 문서 (코드 아님)
docker-compose.yml     다섯 서비스, 세 프로필(기본·service·tools)
```

## 라이선스와 크레딧
- 코드: [MIT](LICENSE)
- 데모 월드 Emberleaf Isle은 메이플스토리 빅토리아 아일랜드의 구조와 분위기를 참고해 새로 지은 월드입니다. 이름과 글은 새로 썼고, Nexon과 관계가 없습니다. 참고한 자료: [인벤 메이플스토리 스토리 게시판](https://www.inven.co.kr/board/maple/2304/24374)

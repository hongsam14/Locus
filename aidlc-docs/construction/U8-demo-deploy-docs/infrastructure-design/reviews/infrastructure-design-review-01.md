## Review

**Verdict:** READY
**Reviewer:** architecture-reviewer
**Stage:** Infrastructure Design (light) — U8
**Reviewed artifact:** aidlc-docs/construction/U8-demo-deploy-docs/infrastructure-design/infrastructure-design.md (+ deployment-architecture.md)
**Class:** adversarial
**Iteration:** 1
**Date:** 2026-10-01T13:55:22Z

### Findings

| ID | Severity | Location | Finding | Required action | Status |
|---|---|---|---|---|---|
| R-01 | Major | infrastructure-design.md > §2 데이터 (Q1=B); docker-compose.yml volumes (`device: ./data/...`) | 설계는 bind mount를 "그대로" 두고 그 위에 "다섯 서비스 healthy"를 세운다. 그런데 compose 볼륨의 `driver_opts.device`는 compose가 프로젝트 경로로 풀어 주지 않는 값이고, local 드라이버가 데몬 쪽에서 mount(2)에 넘기므로 상대 경로(`./data/neo4j/data`)는 통하지 않는 것으로 알려져 있다(절대 경로 필요). 설계에 이 조합이 실제로 떴다는 증거가 없다(이 호스트는 7474 충돌로 compose를 못 띄웠고 확인은 운영자 몫). | 상대 `device`가 되는지 근거를 대거나, 절대 경로(`${PWD}/data/...` 등 .env/셸로 풀리는 값 또는 짧은 bind 문법 + setup-volumes.sh의 chmod)로 바꾸는 것을 설계에 넣는다. 못 정하면 라이브 시나리오 1단계의 첫 확인 항목으로 명시하고 실패 시 대안을 적는다. | New |
| R-02 | Major | infrastructure-design.md > §1 표 web healthcheck, §3.2 | `wget -q --spider http://localhost/`: nginx:alpine의 busybox wget은 `localhost`를 ::1로 먼저 풀 수 있는데 web/nginx.conf는 `listen 80;`(IPv4만)이라 healthcheck가 실패하는 사례가 흔하다. web이 unhealthy가 되면 US-1.1의 "다섯 서비스 healthy"가 깨진다. busybox wget 존재 자체는 맞다. | 주소를 `127.0.0.1`로 쓰거나(`wget -q --spider http://127.0.0.1/`) nginx에 `listen [::]:80`을 더하는 쪽으로 정한다. | New |
| R-03 | Minor | infrastructure-design.md > §3.2 nginx 요청 크기; api/uploads.py (REQUEST_MAX=48 MiB, JSON 오류 본문) | nginx와 앱 상한이 같은 48 MiB라 경계를 넘는 요청은 nginx가 먼저 받아 HTML 413을 주고, 앱의 고정 문구 JSON 413(필드·파일명·상한)은 나오지 않는다. 프런트가 413의 JSON 모양을 기대하면 이 경우만 다르게 보인다. | nginx를 앱보다 약간 크게(예 49m) 두어 앱이 상한을 판정하게 하거나, `error_page 413`으로 같은 모양을 주거나, 프런트가 비 JSON 413을 다룬다는 근거를 적는다. | New |
| R-04 | Minor | infrastructure-design.md > §3.1, §5 이미지의 데모 확인; pyproject.toml; locus/world/demo/__init__.py | (a) §3.1은 app 이미지가 "지금 그대로"라 하나 현재 pyproject의 package-data는 `world/demo/worlds/*.json`뿐이라 `worlds/*/*` 글롭은 코드 생성 단계에서 바꿔야 한다(변경 항목으로 적을 것). (b) CI의 `<데모 확인>`은 스크립트가 없고, `DemoWorlds`는 importer를 필수 인자로 받으며 현재 `DemoInfo`에는 sources 필드가 없다(FD가 더함). 서비스 없이 도는 확인이 어떤 객체로 무엇을 읽는지 열려 있다. | 확인 스크립트(importer 자리에 무엇을 넣는지, manifest·소스 파일 경로 검사 방식)를 한 단락으로 정하고, pyproject 글롭 변경을 코드 생성 대상으로 적는다. `python -c "import api.main"`은 조립이 lifespan에서 일어나 서비스 없이 안전함을 확인했다. | New |
| R-05 | Minor | infrastructure-design.md > §5 backend·frontend 작업 | 첫 실행에서 `ruff check`/`black --check`/`tsc --noEmit`/`npm ci`가 현재 트리에서 통과한다는 확인이 없다(pytest의 addopts `--cov`는 dev extras의 pytest-cov로 충족, `--hypothesis-seed`는 hypothesis 플러그인이 제공함은 확인). npm 캐시는 `cache-dependency-path: web/package-lock.json`이 필요하다. web/.dockerignore가 `tsconfig.tsbuildinfo`를 빼지 않아 `tsc -b`가 낡은 빌드 정보를 쓸 수 있다. | 코드 생성 단계에서 네 명령을 로컬로 먼저 돌려 기준선을 확인하는 단계를 두고, cache 경로와 tsbuildinfo 제외를 적는다. | New |
| R-06 | Minor | infrastructure-design.md > §1, §8; env.example | 새 포트 변수(NEO4J_HTTP_PORT 등)를 operations.md에만 적는다. env.example과 compose 머리 주석에도 없으면 찾기 어렵다. 또 `--profile tools`로 띄운 dashboard는 `--profile service down`으로 내려가지 않는다. | env.example에 주석 처리된 포트 변수를, 문서에 `down`에 `--profile tools`도 붙이는 줄을 더한다. | New |

### Checks Run

| Check | Result |
|---|---|
| tools 프로필의 dashboard가 프로필 없는 opensearch에 depends_on | 문제 없음(기본 서비스는 항상 포함) |
| 기본+`service` 프로필 = neo4j·opensearch·postgres·app·web 다섯 | 맞음(dashboard 이동 후) |
| `127.0.0.1:${VAR:-n}:n` 포트 문법 | 유효 |
| 상대 경로 bind `device` | 근거 없음 → R-01 |
| web healthcheck (busybox wget, localhost) | → R-02 |
| node:22 + Vite 8 engines (lock: ^20.19.0 \|\| >=22.12.0), lockfileVersion 3 | 충족; npm ci 성공 자체는 미실행 |
| nginx 48m vs api/uploads.py (48 MiB, World File 20 MiB) | 수치 일치, 413 모양 차이 → R-03 |
| pytest-cov·hypothesis·ruff·black가 dev extras에 있음, conftest 프로필 | 확인 |
| `import api.main` 부작용 | 조립은 lifespan, 안전 |
| root .dockerignore에 web·scripts 추가 | app 빌드 안전(COPY 대상 아님); web 이미지는 web/.dockerignore를 쓰며 존재 |
| package-data 글롭 / DemoInfo sources | 현재 미반영 → R-04 |
| US-1.1·US-7.5·US-7.6 매핑 | deployment-architecture §5에서 모두 매핑됨 |

### Summary

두 Major(R-01, R-02)는 둘 다 "다섯 서비스 healthy"라는 수용 기준을 직접 위협하지만 작은 수정으로 닫힌다. READY는 Major 2건 이하 기준에 따른 것이며, 두 건 모두 승인 전에 고치거나 라이브 시나리오 첫 확인 항목으로 못박기를 권한다. Q1=B는 다시 따지지 않았고, 그 구현(준비 명령 + 기동 명령 두 줄)은 올바르다. 그 밖의 설계(프로필, 포트 바인딩, 이미지, CI 구성)는 대체로 읽은 파일과 맞는다.

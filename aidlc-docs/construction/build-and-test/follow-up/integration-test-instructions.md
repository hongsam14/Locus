# Integration Test Instructions — Follow-up 주기 (V1~V9)

**원하시는 것**: Purpose Restructure 주기에서 넘긴 일을 처리해 솔로 TRPG를 다듬는 것.
**지금 하는 것**: 이 주기의 Build and Test다. 이 문서는 실제 스택(Neo4j·OpenSearch·PostgreSQL·nginx·OpenAI)에 대고 확인하는 방법을 적는다. 오프라인 시험이 닿지 못하는 것만 여기서 본다: 실제 행 잠금, 재시작, 실제 Neo4j 라벨, 프록시 머리, 실제 LLM, 브라우저에서의 한 바퀴.

## 준비
```bash
WEB_PORT=13000 docker compose --profile service up -d --build
curl -s localhost:8000/health && curl -s localhost:8000/api/capabilities
```

## 1. 라이브 시나리오 (U8, V9에서 강화)
```bash
python scripts/live_scenario.py --base http://localhost:8000 --world emberleaf   # 대상 월드를 교체한다
```
- 단계표는 지난 주기 문서(`../purpose-restructure/integration-test-instructions.md`)와 같다.
- V9에서 바뀐 것:
  - **10a**는 네 가지를 함께 본다.
    - 씨앗 지역의 활성 사건이 항구에 Ironcrag보다 크게 닿는다(`contributions`).
    - 항구의 왜곡도가 Ironcrag보다 크다.
    - 항구 왜곡도에서 피드백 몫을 뺀 값이 0.3 + 사건 기여 이상이다.
  - JSON이 아닌 답이나 깨진 응답은 traceback 없이 FAIL이다.
  - `--timeout`은 0보다 큰 유한한 수만 받고, `--poll`은 1초보다 작으면 1초로 올린다.

## 2. PostgreSQL 스모크 (V5 nfr-light § 3, P1~P6과 잠금)
확인 스크립트는 저장소에 두지 않는다(V5 결정). 아래 순서를 curl이나 작은 스크립트로 돌린다. 이번에는 세션 scratchpad의 `v9/bt/pg_smoke.py`로 돌렸다. 겹침은 스레드 장벽으로 같은 순간에 보냈다.

| # | 하는 법 | 바른 결과 |
|---|---|---|
| P1 | GM 세션(`POST /api/play/worlds/emberleaf/sessions`, 본문 없음). Ambermeadow에 지속 사건 둘(`POST …/events`, war 0.5·0.4), 턴 둘(`POST /api/gm/sessions/{s}/advance`), 두 해소(`POST …/events/{e}/resolve`)를 동시에 | 둘 다 200, 왜곡도가 사건 전 값(0.3) |
| P2 | 사건 하나, 턴 둘, 해소와 `PUT …/regions/{r}/distortion {"degree":0.8}`를 동시에 | 둘 다 200, 왜곡도 0.8, 그 지역의 사건 기여 없음 |
| P3 | 같은 씨앗 시작(`POST …/seeds/{id}/start`) 둘을 동시에 | 201 하나, 409 `seed_running` 하나 |
| 잠금 | 사건 하나, 턴 하나. `psql`에서 `BEGIN; SELECT id FROM session_events WHERE id='…' FOR UPDATE; SELECT pg_sleep(5); COMMIT;`을 띄우고 1초 뒤 해소 | 해소가 잠금이 풀릴 때까지 기다린다(약 4초), 200 |
| P4 (키) | 항구 소문 생성(`POST …/regions/{r}/rumors`) 0.4초 뒤 세션 닫기(`POST /api/play/sessions/{s}/close`) | 닫기 200, 생성 409 `session_closed`, 소문 0 |
| P5 | 플레이어 세션에서 선언(`act` declare) 직후 app을 **죽이고**(`docker compose kill app`) 다시 띄움(`start app`) | run `failed`/`interrupted`, 턴 그대로, 지역 그대로, 타임라인 `turn_run_failed` |
| P6 (키) | 플레이어 세션에서 GM 소문 생성 0.4초 뒤 플레이어 [기다리기] | 409 `gm_busy`, 문장에 세션·run id 없음 |

- P5에서 `docker compose restart app`을 쓰면 안 된다. 그것은 정상 종료라서, API가 진행 중인 run을 `TURN_SHUTDOWN_TIMEOUT_S`(30초)까지 기다려 마친다(operations.md "Background executor"). 끊긴 run의 복구를 보려면 죽여야 한다.

## 3. V7 실제 Neo4j 확인
- **라벨 있는 삭제**
  1. 지역 B(Sylvarch)와 같은 id를 가진 씨앗을 지역 A(Gutterlight)에 `cypher-shell`로 만든다(`CREATE (:EventSeed {id:'region-sylvarch', world_id:'emberleaf', region_id:'region-gutterlight', …})`).
  2. app을 다시 띄워 캐시를 비운다.
  3. `GET …/regions/region-gutterlight/delete-plan`의 `seed_ids`에 그 씨앗이 있는지 본다.
  4. `DELETE …/regions/region-gutterlight`를 보낸다.
  5. `MATCH (n {id:'region-sylvarch'})`에 `Region`만 남아야 한다.
- **백업 실패**
  1. app 안에서 `mv /app/data/backups /app/data/backups.bt && touch /app/data/backups`를 한다.
  2. 데모를 다시 불러온다(`POST …/demo/emberleaf?replace=true&confirm=true`). `ok:false`, `replaced:false`, stage `backup`이어야 하고 옛 월드가 그대로여야 한다.
  3. 폴더를 되돌린다.
  - app은 root로 돈다(RE-T06). 그래서 `chmod`로는 막히지 않는다. 경로에 파일을 둔다.

## 4. nginx 머리 (V2 § 6)
```bash
curl -sI localhost:13000/ | grep -i cache-control                         # no-cache
curl -sI localhost:13000/assets/index-*.js | grep -i cache-control         # public, max-age=31536000, immutable
curl -sI localhost:13000/favicon.svg | grep -i content-type                # image/svg+xml
```

## 5. 브라우저 한 바퀴 (V6 § 7, V8 § 8)
헤드리스 Chrome(CDP)으로 `:13000`을 돈다. 이번에는 scratchpad의 `v9/bt/walk.mjs`를 썼다.
- 에디터
  - [지역 추가]로 지도의 빈 곳을 누르고 이름을 넣어 저장하면, 그 지역이 인스펙터에 골라진다.
  - [선택·이동]으로 바꾼 뒤 마커를 끌면 위치가 저장된다. [지역 추가] 도구는 지역을 만든 뒤에도 켜져 있다.
  - [파일 ▾]에서 World File을 고르면 먼저 묻고, 확인하면 "불러왔어요." 알림이 뜬다.
- GM
  - [턴 진행]을 누르면 결과 띠에 "조용히 1턴째가 되었어요"가 뜬다.
  - 씨앗 탭에서 [시작]을 누르면 "진행 중"이 된다.
  - [세션 끝내기]를 확인하면 닫힘 띠가 뜨고 세션이 `closed`가 된다.
- 빌드 경고의 단계 이름: 서버의 `stage` 값 15개가 모두 `web/src/features/editor/buildStages.ts`의 목록에 있다(정적 대조).

## 정리
`emberleaf`를 데모로 다시 불러와 처음 상태(지역 12)로 돌린 뒤 `docker compose --profile service --profile tools down`.

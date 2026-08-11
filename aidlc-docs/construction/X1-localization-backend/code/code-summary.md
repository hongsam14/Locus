# X1 Localization Backend — Code Summary

**결과**: 오프라인 **280 pytest GREEN** (249→280, +31), ruff/black/compileall clean. 회귀 0. 캐노니컬(Neo4j/OpenSearch) 불변, 세션 계층은 가산 변경.

## 코드 리뷰(high, 멀티에이전트) 반영 — 10건 수정
읽기 경로 재설계 + 캐시/설정 정리:
- **#3(읽기 LLM 블로킹)**: 읽기는 **캐시 전용**(LLM 무호출), 미스는 **백그라운드 워밍**(prod=ThreadPoolExecutor, 테스트=inline). `TranslationService.enrich`(캐시 조회 후 setattr, 미스는 `warm_scheduler`로 스케줄).
- **#1(무-failsafe 500)**: `enrich`/`_cached`가 repo 오류를 삼켜 원문으로 degrade.
- **#2(lang 무시)**: 서비스가 `default_lang` 보유, 라우터·쿼리 공용 `enrich`가 설정 lang 사용.
- **#4(self-identical 미캐시)**: `Translator.try_translate`가 성공(원문과 동일 포함)=str / 실패·공백=None → 성공분은 항상 캐시, 실패만 재시도.
- **#5(TRANSLATION_MODEL 무효)**: 설정·파라미터 제거(LLMProvider.complete에 model 인자 없음).
- **#6(upsert 경쟁)**: SAVEPOINT + `IntegrityError`→update 폴백.
- **#7(무제한 IN)**: `get_translations_many` id 청킹(500).
- **#8(miss마다 트랜잭션)**: `upsert_translations` 배치(단일 트랜잭션).
- **#9(무의미 batch_size)**: 배칭 제거(설정·파라미터 삭제).
- **#10(중복 enrichment)**: 라우터 `_attach_ko`·쿼리 `_localize` 모두 `TranslationService.enrich` 사용(단일 지점).
- (refuted 1건: `zip(strict=False)` 드롭 위험 — translate 항목별이라 길이 동일, 무효.)

**동작 변화**: 첫 조회는 원문(캐시 미스)→백그라운드 워밍→이후 조회는 번역 표시(결과적 일관성). X3 프론트는 refetch/폴링으로 번역을 반영.

## 신규 파일
- `locus/translation/__init__.py` · `translator.py`(C1 Translator, LLMProvider 재사용·fail-safe) · `service.py`(C3 TranslationService, 캐시우선·`source_hash` 무효화·배치 상한).
- `locus/session/turn_changes.py`(C6 순수 `shape_region_changes`, P-F4).
- 테스트: `tests/translation/test_translator.py` · `test_translation_service.py`(+PBT hash) · `tests/session/test_turn_changes.py`(+PBT) · `tests/session/test_localization_api.py` · `tests/storage/test_translation_repo.py`.

## 수정 파일
- `locus/config/settings.py`: `translation_enabled/target_lang/model/batch_size`(워밍 설정 없음 — P-F1).
- `locus/session/models.py`: `Translation` 엔티티 + `RegionTurnChange` + 응답 전용 `SessionRumor.statement_ko`/`SessionEvent.description_ko`(비영속, BR-X1-27).
- `locus/session/turn.py`: `TurnResult.region_changes`(가산); advance_turn이 `append_for_region` 반환 수집(F1) + `shape_region_changes` 호출; `_EventApplication.event_regions`.
- `locus/session/repository.py`(port) + `memory_repo.py`: `get_translation`/`get_translations_many`/`upsert_translation`.
- `locus/storage/postgres_session_repo.py`: `translations` 테이블(유니크 키, ensure_schema create_all) + 3 메서드 + row 매핑.
- `locus/models/io.py`: `KnowledgeView.statement_ko`/`title_ko`(응답 전용).
- `locus/session/query.py`: `SessionQueryEngine`에 `translation` DI + `_localize`(rumor 세션스코프·캐노니컬 world스코프 지연, Q4=B).
- `api/routers/session.py`: `_attach_ko` 헬퍼(read-path 단일 지점, P-F3) — `list_rumors`/`list_events`만 ko 부착; generate/regen은 ko=null(P-F2/Q2=A).
- `api/main.py`: Translator→TranslationService 배선(`translation_enabled=False`면 미주입, graceful); SessionQueryEngine에 주입.
- `locus/session/__init__.py`, `env.example`(TRANSLATION_*).

## 결정 반영
- Q1=A(신규 `locus/translation/`) · Q2=C(별도 `translations` 캐시) · Q3=A(생성시 저장 — 단, P-F1로 워밍 미구현·조회 지연으로 캐시 채움) · Q4=B(캐노니컬 조회시 world 캐시) · Q5=A(region_changes) · Q6=A best-effort · Q7=A(배치 20).
- 리뷰 findings: **F1**(append 수집) · **F2a**(타임라인 LLM 번역 제외 — X3 i18n) · **F3**(ko 응답 전용) · **F4**(워밍 드롭) · **P-F3/P-F4/P-F5**(라우터 헬퍼·순수 모듈·비영속 가드) 모두 반영.

## 알려진 한계 (설계 내)
- `RegionTurnChange`는 6개 리스트(rumor/event 상태 변동)만 보유. rumor→region **피드백만** 발생한 지역(다른 변동 없음)은 별도 알림을 만들지 않음(BR-X1-19/21의 6-list 모델 결과). 피드백은 보통 event 지역의 rumors_added/support 변동과 동반되어 표면화됨.
- 캐노니컬 `KnowledgeView.title`이 consensus 경로에서 채워질 때만 `title_ko`가 생성됨(없으면 statement만 번역).

## Build & Test 이관
- 라이브 시나리오(실 OpenAI 번역 품질, PostgreSQL `translations` 마이그레이션, ko 표시 E2E)는 X3 이후 Build & Test에서 operator-run.

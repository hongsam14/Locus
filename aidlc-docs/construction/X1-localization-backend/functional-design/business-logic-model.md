# X1 Localization Backend — Business Logic Model

## 1. Translator (C1)
```
translate(text, target_lang="ko") -> str
  if text.strip() == "": return text                     # 무번역 통과
  try: return llm.complete(prompt(text, target_lang), system=_SYS).strip()
  except Exception: log.warning(...); return text        # SEC-C fail-safe → 원문
translate_many(texts, ...) -> list[str]                   # 소배치 순차(Q7), 각 항목 독립 폴백
```
- 프롬프트: "Translate to {lang}. Keep meaning/tone/length. Return only the translation." (SEC-A: API 키 미로깅)

## 2. TranslationService (C3) — cache-first
```
localize(kind, id, field, source_text, *, world_id=None, session_id=None, lang="ko") -> str:
  h = hash(source_text)
  cached = repo.get_translation(kind, id, field, lang)
  if cached and cached.source_hash == h: return cached.text        # 캐시 히트(Q1)
  ko = translator.translate(source_text, lang)
  if ko != source_text:                                            # 성공한 번역만 저장(Q4)
      repo.upsert_translation(Translation(kind,id,field,lang,text=ko,
                                          source_hash=h, world_id, session_id))
  return ko                                                        # 실패 시 원문 반환(조용한 폴백)

localize_many(items, ...) -> dict[(id,field), str]:
  미스만 모아 translator.translate_many (배치 상한 Q7); 히트는 캐시 재사용 → N+1 방지
```
- **무효화(Q1=A)**: 캐시의 `source_hash` ≠ 현재 원문 해시면 재번역·덮어쓰기(FR-UX3.5).
- **폴백(Q4=A)**: 번역=원문(실패)이면 저장 생략 → 다음 조회에 재시도.

## 3. 생성 시점 워밍 (C4, Q3=A / Q6=A best-effort)
```
소문 생성 후:   translation.localize("rumor", r.id, "statement", r.statement, session_id=sid)
이벤트 생성 후: translation.localize("event", e.id, "description", e.description, session_id=sid)
# 타임라인: LLM 번역 대상 아님(F2(a)) — X3 UI i18n(kind+payload)로 현지화
```
- **격리(Q6=A)**: 워밍은 try/except로 감싸 실패해도 콘텐츠 생성/커밋에 영향 없음. `translation` 미주입 시 워밍 스킵(조회 때 지연 생성).
- **지연 고려(F4, NFR-UX1)**: 워밍은 **선택적 최적화**다. `advance_turn`이 다수 지역에 소문을 append하는 경로에서는 동기 워밍이 턴 임계경로를 늘릴 수 있으므로, **턴 중 워밍은 생략**하고 조회 경로(§4)의 지연 번역을 안전망으로 삼는 것을 기본으로 한다(수동 단건 생성 등 저빈도 경로만 워밍). 워밍 on/off는 `translation_warm_on_generate`(기본 False)로 제어.

## 4. 조회 로컬라이제이션 (C5)
```
세션 knowledge/list 응답 조립 시:
  소문/이벤트/타임라인: localize_many(캐시 히트 위주) → DTO에 *_ko 동봉
  캐노니컬 Knowledge(Q4=B, Q2=A title+statement, Q3=A world 캐시):
    title_ko  = localize("knowledge", k.id, "title",     k.title,     world_id=wid)
    stmt_ko   = localize("knowledge", k.id, "statement", k.statement, world_id=wid)
    (miss면 지연 번역·world 캐시 저장 → 이후 세션에서 재사용)
```

## 5. TurnAdvancer 변동 셰이핑 (C6, Q5=A)
```
advance_turn(...) -> TurnResult:
  (기존 로직 그대로: promoted_ids/demoted_ids/pruned_rumor_ids/applied/resolved/feedback_regions)
  # F1: 2단계에서 append 반환을 수집
  added_by_region: dict[str, list[str]] = {}
  for region_id in events.target_regions:
      new_rumors = self._rumors.append_for_region(session, region_id, ...)   # 반환 포획(기존엔 버림)
      added_by_region[region_id] = [r.id for r in new_rumors]
  ...
  region_changes = shape_region_changes(rumors_by_id, events_by_id, feedback_regions, added_by_region)
  return TurnResult(... , region_changes=region_changes)

shape_region_changes:
  각 소문 id → 소속 region_id로 그룹핑(promoted/demoted/pruned)
  각 이벤트 id → region_id로 그룹핑(events_applied/events_resolved)
  added_by_region[region_id] → rumors_added (F1, Q5=A)
  feedback_regions는 해당 지역 버킷 보장(피드백 표기)
  6개 리스트 전부 빈 지역은 제외(무변동 무알림)
```

## 6. Wiring/Config (C8)
```
settings: translation_enabled(bool, 기본 True), translation_target_lang("ko"),
          translation_model(None→openai_model_name), translation_batch_size(기본 20, Q7),
          translation_warm_on_generate(bool, 기본 False — F4: 턴 임계경로 보호)
main.py: Translator(llm, model) → TranslationService(repo, translator)
         → RumorService/EventService/TurnAdvancer(translation=...) DI, SessionQuery(translation=...)
graceful: translation_enabled=False → 전 경로 원문(영어) 그대로(폴백)
```

## 데이터 흐름
```
생성: content → (옵션)localize warm → translations 캐시     # 기본 off, 조회 지연이 안전망(F4)
조회: content → localize_many/lazy(knowledge) → en+ko 응답  # 주 경로
턴:   advance_turn → (append 반환 수집) → region_changes 셰이핑 → 응답  # F1
타임라인: X3 UI i18n(kind+payload) — LLM 번역 무관(F2a)
```

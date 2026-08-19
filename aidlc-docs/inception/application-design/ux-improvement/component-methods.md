# UX Improvement — Component Methods (interface-level)

> 시그니처 수준만 정의. 상세 비즈니스 룰(해시 무효화 규칙, 빈지역 판정 경계, 알림 병합 규칙 등)은 per-unit Functional Design에서 확정.

## Backend

### C1 Translator (`locus/translation/translator.py`)
```python
class Translator:  # LLMProvider 재사용
    def __init__(self, llm: LLMProvider, *, model: str | None = None) -> None: ...
    def translate(self, text: str, target_lang: str = "ko") -> str: ...
    def translate_many(self, texts: list[str], target_lang: str = "ko") -> list[str]: ...
```
- 빈/공백 → 그대로 반환. LLM 오류 → 원문 반환 + 경고 로그(SEC-C fail-safe).

### C2 Translation 엔티티 + Repo
```python
class Translation(LocusModel):
    id: str
    source_kind: str      # rumor | event | timeline | knowledge
    source_id: str
    target_lang: str = "ko"
    text: str             # 번역문
    source_hash: str      # 원문 해시(무효화)
    world_id: str | None = None
    session_id: str | None = None
    created_at: datetime | None = None

# SessionRepository (port) 확장 — 가산
def get_translation(kind: str, source_id: str, lang: str) -> Translation | None: ...
def get_translations_many(keys: list[tuple[str, str]], lang: str) -> dict[str, Translation]: ...
def upsert_translation(t: Translation) -> Translation: ...
```

### C3 TranslationService (`locus/translation/service.py`)
```python
class TranslationService:
    def __init__(self, repo: SessionRepository, translator: Translator) -> None: ...
    def localize(self, kind: str, source_id: str, source_text: str, *,
                 world_id: str | None = None, session_id: str | None = None,
                 lang: str = "ko") -> str: ...            # cache-first, hash-invalidate
    def localize_many(self, items: list[tuple[str, str, str]], *,
                      world_id: str | None = None, session_id: str | None = None,
                      lang: str = "ko") -> dict[str, str]: ...  # {source_id: ko}
```

### C4 Generation hooks (기존 서비스에 주입)
```python
# RumorGenerator/RumorService: 소문 생성 후
translation.localize("rumor", r.id, r.statement, session_id=sid)   # 캐시 워밍
# EventService.create: 이벤트 생성 후 description
# turn/timeline: summary 기록 후
```

### C5 Read enrichment (`session/query.py` + `api/routers/session.py` DTO)
```python
# 세션 쿼리/목록 응답 조립 시:
def _attach_ko(items, kind, *, world_id=None, session_id=None): ...  # en+ko 동봉
# 캐노니컬 Knowledge: localize("knowledge", k.id, k.content, world_id=wid) (Q4=B 지연 캐시)
```

### C6 RegionTurnChange (`session/models.py`, `turn.py`)
```python
class RegionTurnChange(LocusModel):
    region_id: str
    promoted: list[str] = []
    demoted: list[str] = []
    pruned: list[str] = []
    events_applied: list[str] = []
    events_resolved: list[str] = []
    rumors_added: list[str] = []

# TurnResult 가산
region_changes: list[RegionTurnChange] = []

# TurnAdvancer.advance_turn(): 기존 id 리스트 + region 귀속으로 region_changes 조립
```

### C7 API (`api/routers/session.py`)
- 응답 모델에 `*_ko`(또는 `translation`) 필드 동봉(C5).
- `POST …/advance-turn` 응답에 `region_changes`(C6).
- 전체 생성 신규 라우트 없음(Q6=B). 입력 검증 유지(SEC-A).

### C8 Wiring/Config
```python
# settings.py: translation_enabled: bool, translation_target_lang: str = "ko", translation_model: str | None
# main.py: Translator(llm) → TranslationService(repo, translator) → 세션 서비스/쿼리에 DI
```

## Frontend

### C9 Design System
```ts
// tailwind.config.{ts} — 토큰(colors, borderRadius, fontFamily: doodle), content globs
// src/index.css — @tailwind base/components/utilities + @font-face(로컬 번들) + sketch utilities
// src/ui/{Button,Panel,Card,Badge,Toast,Modal}.tsx — 공용 프리미티브
```

### C10 i18n (`src/i18n.ts`)
```ts
export const messages = { ko: { 'session.generateAll': '전체 소문 생성', /* ... */ } };
export function t(key: string): string;
```

### C11 LocalizedText (`src/ui/LocalizedText.tsx`)
```ts
function LocalizedText(props: { ko?: string; original: string }): JSX.Element  // ko 기본 + "원문" 토글
```

### C12 전체 생성 (`SessionPanel.tsx`, `api.ts`)
```ts
async function generateAll(sid: string): Promise<void>  // empty regions → Promise.all + progress
// empty 판정: api.listDistortions(sid) + api.listRumors(sid, rid) (Q6=B)
// overwrite(전체 재생성)은 confirm 모달 후
```

### C13 지역 재생성 (`RegionPanel.tsx`/`SessionPanel.tsx`)
```ts
async function regenRegion(sid, rid): Promise<void>  // confirm 모달 + 승격 보존 표시
```

### C14 NotificationCenter (`src/ui/NotificationCenter.tsx`)
```ts
function notifyTurn(result: TurnResult): void  // region_changes → 지역별 1건 알림
```

### C15 api.ts/types.ts
```ts
// types.ts: SessionRumor += statement_ko?; SessionEvent += description_ko?; TimelineEntry += summary_ko?;
//           QueryResult knowledge += *_ko?; TurnResult += region_changes: RegionTurnChange[]
```

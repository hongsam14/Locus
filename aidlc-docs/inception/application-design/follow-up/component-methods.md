# Follow-up Cycle — Component Methods

> 새로 생기거나 바뀌는 메서드의 시그니처와 입출력이다. **세부 규칙**(타임아웃 값, 증분 쓰기 공식, 문장, 배치)은 유닛별 Functional Design에서 정한다.
> Python은 타입 힌트, TypeScript는 함수·props 시그니처로 적는다. "→"는 반환 값이다.

---

## 1. 웹 (`web/src`)

### 1.1 프리미티브 `ui/` (V2)
```ts
Button(props: { variant?: "primary" | "secondary" | "ghost" | "danger"; size?: "sm" | "md";
               busy?: boolean } & ButtonHTMLAttributes)            // busy이면 비활성 + 진행 표시
Dialog(props: { open: boolean; onOpenChange(open: boolean): void; title: ReactNode;
               description?: ReactNode; children: ReactNode; footer?: ReactNode })
ConfirmDialog(props: { open: boolean; title: ReactNode; body?: ReactNode;
               confirmLabel: string; tone?: "default" | "danger"; busy?: boolean;
               onConfirm(): void | Promise<void>; onCancel(): void })
Select<T extends string>(props: { label: string; value: T | ""; options: { value: T; label: string }[];
               onChange(v: T): void; placeholder?: string; disabled?: boolean })
FileInput(props: { label: string; accept?: string; multiple?: boolean;
               onFiles(files: File[]): void; hint?: string })
Tabs(props: { value: string; onValueChange(v: string): void;
               tabs: { value: string; label: ReactNode; content: ReactNode }[] })
StatusView(props: { state: "loading" | "empty" | "error" | "ready"; error?: DescribedError;
               emptyText?: string; onRetry?(): void; children?: ReactNode })
Toaster(): JSX.Element                               // AppShell에 하나, aria-live
toast(n: { tone: "info" | "event" | "danger"; title: string; body?: string }): void
Field, Textarea, Badge, Card, Range, CommitRange    // 지금 props를 유지하고 모양만 토큰으로 바꾼다
```

### 1.2 배치 틀 `layout/` (V2)
```ts
AppShell(props: { children: ReactNode })                       // 내비 + 언어 토글 + Toaster
SplitView(props: { main: ReactNode; aside: ReactNode; asideLabel: string;
                   stackOrder?: "main-first" | "aside-first" })  // 좁은 화면에서 쌓는 순서
Section(props: { title: ReactNode; collapsible?: boolean; defaultOpen?: boolean;
                 actions?: ReactNode; children: ReactNode })
```

### 1.3 지도 `map/` (V2, 변형은 화면 유닛)
```ts
WorldMap(props: {
  regions: MapRegion[]; connections: MapConnection[];
  mode: "edit" | "gm" | "play";
  selectedId?: string; playerRegionId?: string;
  reachableIds?: string[];                      // play: 갈 수 있는 곳
  overlay?: Record<string, RegionOverlay>;      // gm: 상태 색·배지
  draggable?: boolean;                          // 기본 false (UX-36)
  onSelect?(id: string): void;
  onMove?(id: string, pos: { x: number; y: number }): void;   // 0..1, 그려진 영역 기준
  onAddAt?(pos: { x: number; y: number }): void;              // edit 전용
  background?: string;
})
toNormalized(svg: SVGSVGElement, clientX: number, clientY: number): { x: number; y: number }  // 순수(테스트 대상)
```

### 1.4 표기 규칙 `format/` (V2)
```ts
type EnumKind = "regionLevel" | "connectionKind" | "scopeType" | "eventStatus" | "eventCategory"
              | "eventLifecycle" | "sessionStatus" | "augmentationStatus" | "deedKind" | "slant";
enumLabel(kind: EnumKind, value: string, lang: Lang): string        // 모르는 값은 원문 + 개발 경고
degreeWord(value: number, lang: Lang): string                       // 플레이어용 말(왜곡 정도)
decayWord(pathDecay: number, lang: Lang): string                    // 플레이어용 말(전해 들음의 희미함)
numberWithMeaning(kind: "distortion" | "support" | "magnitude" | "confidence",
                  value: number, lang: Lang): string                // GM·에디터용
formatDate(iso: string, lang: Lang): string
```

### 1.5 오류 문장 `errors/` (V2)
```ts
type DescribedError = { title: string; action?: string; code?: string; status?: number; raw?: string };
describeError(err: unknown, lang: Lang): DescribedError     // code → 사전 문장, 없으면 상태 코드 일반 문장
```

### 1.6 요청 도우미 `hooks/` (V2)
```ts
useResource<T>(key: unknown[] | null, load: (signal: AbortSignal) => Promise<T>):
    { data: T | undefined; state: "loading" | "ready" | "error"; error?: DescribedError; reload(): void }
    // key가 바뀌거나 언마운트되면 이전 요청을 abort하고, 늦은 답은 버린다
useAction<A extends unknown[], R>(run: (...a: A) => Promise<R>, opts?: { onDone?(r: R): void }):
    { run(...a: A): Promise<R | undefined>; busy: boolean; error?: DescribedError }
    // busy 동안 다시 부르면 아무것도 하지 않는다(이중 실행 방지)
```

### 1.7 API 클라이언트 `api/` (V2·V3·V5)
```ts
class HttpError extends Error { status: number; code?: string; detail: unknown; body: string }
// 타입 추가: RegionViewOut.gm_busy, *_ko 칸(region/npc/event_seed/world), DemoInfoOut.title_ko 등
```

## 2. `locus/shared`

```python
# models/i18n.py [새]
class TranslationEntry(LocusModel):
    kind: Literal["region", "npc", "event_seed", "world", "knowledge"]
    id: str
    field: str
    lang: str
    text: str
    source_hash: str              # 영어 원문 해시(localization.service.source_hash와 같은 규칙)

# storage/base.py — GraphRepository [바뀜]
def get_node(self, world_id: str, node_id: str, *, label: str | None = None) -> Node | None: ...
def delete_node(self, world_id: str, node_id: str, *, label: str | None = None) -> None: ...

# storage/persistence.py [바뀜: 순서만]
def persist_graph(graph_repo, search_repo, embedding, world_id, *, ..., meta: WorldMeta | None) -> list[BuildWarning]
    # 노드(WorldMeta 제외) → 엣지 → 임베딩·색인 → WorldMeta 순서
```

## 3. `locus/knowledge`

```python
# consensus.py [유지: 규칙 수정]
def compute_consensus(region_id: str, snapshot_parts..., params: KnowledgeTuning) -> ConsensusView
def best_origins(pw: dict[str, float], region_direct: dict[str, list[tuple[str, float]]],
                 exclude: str) -> dict[str, tuple[str, float]]     # [새, 순수] knowledge_id → (출처 지역, 최대 가중)

# cache.py [유지]
WorldCache.get(world_id: str) -> WorldSnapshot     # 버전 None이면 캐시하지 않음, hit 경로 버전 실패는 miss처럼
```

## 4. `locus/world`

```python
# carry_over.py [새, 순수]
@dataclass(frozen=True)
class CarryOver:
    npcs: list[NPC]
    seeds: list[EventSeed]
    warnings: list[BuildWarning]
def carry_over(old: WorldSnapshot, new_regions: list[Region], world_id: str) -> CarryOver

# build.py [바뀜]
class BackupFailedError(RuntimeError): ...
WorldBuilder.build(world_id: str, inputs: WorldInputs, *, replace: bool = True) -> BuildReport
    # 커밋 단계: 옛 스냅샷 읽기 → 백업(실패 → BackupFailedError → ok=false, 교체 안 함)
    #  → delete → 새 월드 저장 → carry_over 저장 → 리포트(carried_npcs, carried_seeds, 경고)

# worldfile/remap.py [바뀜]
def remapped_id(target_world_id: str, old_id: str) -> str          # uuid5(NAMESPACE_LOCUS, f"{target}:{old}")
def duplicate_ids(wf: WorldFile) -> list[str]                      # 절 사이·절 안에서 두 번 이상 나온 id

# worldfile/import_.py [바뀜]
WorldFileImporter.import_(wf: WorldFile, world_id: str, *, replace: bool, remap: bool | None) -> ImportReport
    # 중복 id → ok=false(쓰기 전), 백업 실패 → ok=false(교체 안 함)

# demo/__init__.py [바뀜]
class DemoInfo(BaseModel):
    ...                                                   # 지금 칸
    i18n: dict[str, DemoCardText] = {}                    # lang → {title, description?, credits?}
    translations: dict[str, str] = {}                     # lang → 매니페스트 기준 상대 경로
DemoWorlds.translations(name: str, lang: str) -> list[TranslationEntry]    # 없으면 []
DemoWorlds.card(name: str, lang: str) -> DemoCardText                      # 없으면 영어 원문
# _check: name == world.id, 번역 파일 파싱·범위·경로

# augmentation/questions.py [유지]
NEEDS: dict[tuple[IssueType, TargetKind], dict[Action, list[str]]]
```

## 5. `locus/localization`

```python
# service.py [바뀜]
TranslationService.seed(entries: Sequence[TranslationEntry], *, current_text: Mapping[tuple[str, str, str], str],
                        world_id: str) -> SeedReport
    # (kind, id, field) → 지금 영어 원문. 해시가 맞는 항목만 upsert. SeedReport(seeded, stale, missing)
TranslationService.enrich(...)       # 그대로. 새 kind 값을 받는다
TranslationService.purge(...)        # 그대로. 새 kind 값을 받는다
```

## 6. `locus/play`

```python
# turn/guard.py [바뀜]
class GmBusyError(TurnInProgressError): ...        # 409, code "gm_busy"
TurnGuard.acquire(session_id: str, run_id: str) -> None        # 턴: GM 리스가 있으면 GmBusyError, 턴이 있으면 TurnInProgressError
TurnGuard.hold(session_id: str, *, label: str = "gm") -> ContextManager[str]   # 그대로(GM 리스 공유)
TurnGuard.short_write(session_id: str, *, timeout_s: float) -> ContextManager[None]   # [새] 세션별 줄 세우기
TurnGuard.turn_running(session_id: str) -> bool                # [새] 턴 run만
TurnGuard.gm_busy(session_id: str) -> bool                     # [새] GM 리스
# is_running / running_run_id / assert_idle은 위 둘로 대체(호출부 정리는 V5)

# session_service.py [바뀜]
SessionService.close_session(session_id: str) -> GameSession   # short_write 안에서 닫는다. 턴이 돌고 있으면 409(그대로)

# 각 GM 쓰기 서비스 [바뀜: 시그니처는 그대로, 안쪽 구간을 short_write로 감쌈]
EventService.resolve_event(session_id, event_id) -> SessionEvent
EventService.approve_event(session_id, event_id) -> SessionEvent
EventService.discard_event(session_id, event_id) -> None
SeedService.start(session_id, seed_id) -> SessionEvent
RumorService.adjust_support(session_id, rumor_id, support) -> SessionRumor
RumorService.generate_rumors(session_id, region_id) -> list[SessionRumor]       # LLM은 잠금 밖, 저장만 안
RumorService.regenerate_region(session_id, region_id) -> RegenerateResult
DeedService.void(session_id, deed_id) -> VoidResult
DistortionService.set_region_distortion(session_id, region_id, degree) -> RegionDistortion   # [바뀜] 지금은 None, 라우터가 저장소를 직접 읽음
EventService.create_event / suggest_events(...)                                   # 저장 구간만 안

# turn/advancer.py [바뀜]
TurnAdvancer.recover_interrupted() -> list[str]     # [새] running run id마다 실패 보상, 처리한 run id 목록

# models.py [바뀜]
class RegionView(LocusModel):
    ...
    turn_running: bool = False      # 턴 run만
    gm_busy: bool = False           # [새] GM 리스
```

## 7. `api/`

```python
# errors.py [바뀜]
ERROR_CODES: dict[type[Exception], tuple[int, str]]      # 예외 → (상태, code)
def http_error(exc: Exception) -> ApiError               # ApiError(HTTPException) + code
# main.py: ApiError·HTTPException·RequestValidationError 처리기 → {"detail": ..., "code": ...}

# schemas.py [바뀜]
class RegionViewOut(RegionView):
    region_name_ko: str | None; description_ko: str | None
    npcs: list[NpcOut]                                    # name_ko, role_ko, description_ko
class SeedViewOut(SeedView): title_ko: str | None; description_ko: str | None
class WorldInfo(WorldSummary): ...; name_ko: str | None; description_ko: str | None   # [바뀜] 칸 추가
class DemoInfoOut(BaseModel): ... title_ko, description_ko, credits_ko: str | None
def localize_region_view(view, loc, *, lang) -> RegionViewOut          # 지역·NPC 종류 더함
def purge_translations(loc, *, kind, ids=None, world_id=None, session_id=None) -> None   # 새 종류

# routers/world.py [바뀜]
POST /api/world/worlds/{w}/demo/{name}       # import → (번역 켜짐이면) seed → ImportReport(+translations_seeded)
GET  /api/world/demos?lang=                   # 카드 문구 언어별
```

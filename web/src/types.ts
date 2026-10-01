export interface Coord {
  x: number;
  y: number;
}

export interface Provenance {
  source: string;
  generated_by?: string | null;
  refs?: string[];
  note?: string | null;
}

export interface Region {
  id: string;
  world_id?: string;
  name: string;
  level: string;
  parent_id?: string | null;
  description?: string | null;
  attributes?: Record<string, unknown>;
  position?: Coord | null;
  provenance?: Provenance;
}

export type ConnectionKind = "adjacent" | "route" | "river" | "blocked";

export interface ConnectionEdge {
  world_id?: string;
  source_region_id: string;
  target_region_id: string;
  kind: string;
  weight: number;
  rationale?: string | null;
  wiki_prior_ref?: string | null;
  provenance?: Provenance;
}

// --- U3 world editor (domain-entities §2·§3·§5) ------------------------------- //
export interface Knowledge {
  id: string;
  world_id: string;
  statement: string;
  title: string;
  topic?: string | null;
  confidence: number;
  is_global?: boolean;
  about_entity_ids?: string[];
  derived_from_prior_ids?: string[];
  provenance: Provenance;
  statement_ko?: string | null; // response-only (editor reads)
  title_ko?: string | null;
}

export interface ScopeLink {
  world_id: string;
  knowledge_id: string;
  region_id: string;
  scope_type?: string;
  confidence?: number;
}

export interface NameRef {
  id: string;
  name: string;
}

export interface ConnectionKey {
  world_id: string;
  a_region_id: string;
  b_region_id: string;
  kind: string;
}

export interface PriorRefView {
  prior_id: string;
  condition?: string | null;
  effect?: string | null;
  broken: boolean;
}

export interface ConnectionView {
  key: ConnectionKey;
  other_region_id: string;
  other_region_name: string;
  weight: number;
  rationale?: string | null;
  prior?: PriorRefView | null;
}

export interface ScopedKnowledge {
  knowledge: Knowledge;
  scope_region_ids: string[];
}

export interface EditorRegionView {
  region: Region;
  children: NameRef[];
  connections: ConnectionView[];
  knowledge: ScopedKnowledge[];
  npcs: NPC[];
}

export interface RegionDeletePlan {
  region_id: string;
  region_name: string;
  new_parent_id?: string | null;
  children: NameRef[];
  connections: ConnectionKey[];
  npcs: NameRef[];
  knowledge_to_unscope: NameRef[];
  knowledge_scope_removed: NameRef[];
  entities_unlocated: NameRef[];
  blocked_by_sessions: string[];
}

export interface RegionDeleteReport extends RegionDeletePlan {
  deleted_ids: string[];
}

export interface NpcDraft {
  name: string;
  role: string;
  description: string;
  traits: string[];
}

export interface NpcDraftResult {
  region_id: string;
  drafts: NpcDraft[];
  llm_calls: number;
  failed: boolean;
}

export interface WikiPrior {
  id: string;
  world_id: string;
  prior_type: string;
  condition: string;
  effect: string;
  domains: string[];
  description?: string | null;
  confidence: number;
}

export interface PriorUsage {
  prior: WikiPrior;
  connections: ConnectionKey[];
  knowledge: NameRef[];
}

export interface BrokenRef {
  ref_id: string;
  connections: ConnectionKey[];
  knowledge: NameRef[];
}

export interface PriorRefsOut {
  usages: PriorUsage[];
  broken: BrokenRef[];
}

export interface WorldExport {
  world_id: string;
  world?: WorldFileMeta;
  regions: Region[];
  connections: ConnectionEdge[];
  entities: unknown[];
  knowledge: Knowledge[];
  scopes: ScopeLink[];
  npcs?: NPC[];
  priors?: WikiPrior[];
}

// --- World File v1 (U2 FR-B8): the save format; a superset of WorldExport ---- //
export interface WorldFileMeta {
  id: string;
  name: string;
  description?: string | null;
}

export interface WorldFile {
  format_version: number;
  world: WorldFileMeta;
  exported_at?: string | null;
  regions: Region[];
  connections: ConnectionEdge[];
  entities: unknown[];
  relations: unknown[];
  knowledge: unknown[];
  scopes: unknown[];
  priors: unknown[];
  prior_links: unknown[];
  npcs: NPC[];
}

export interface NPC {
  id: string;
  world_id: string;
  name: string;
  role: string;
  description: string;
  home_region_id: string;
  traits: string[];
  provenance: { source: string; generated_by?: string | null; refs?: string[]; note?: string | null };
}

/** Display language (FD-U5 Q1=A): UI labels + the `?lang=` of translated reads. */
export type Lang = "ko" | "en";

/** One line of a conversation, stored in the language it was written in (A-1). */
export interface Message {
  id: string;
  conversation_id: string;
  role: "player" | "npc";
  text: string;
  lang: string;
  turn: number;
  created_at?: string | null;
}

/** The one conversation a session has with one NPC (BR-U5-1). */
export interface Conversation {
  id: string;
  session_id: string;
  npc_id: string;
  started_turn: number;
  messages: Message[];
  created_at?: string | null;
}

/** The NPC's answer to one `say` (exactly one LLM call). */
export interface NpcReply {
  message: Message;
  lang: string;
  llm_calls: number;
  context_ids: string[];
}

/** An NPC of the player's region and how far the player has talked with them. */
export interface NpcSummary {
  npc: NPC;
  has_conversation: boolean;
  message_count: number;
}

export interface BuildWarning {
  stage: string;
  item_id?: string | null;
  message: string;
  severity: "warning" | "error";
}

export interface BuildReport {
  world_id: string;
  regions_created: number;
  connections_created: number;
  entities_created: number;
  knowledge_created: number;
  corroborations_created: number;
  warnings: BuildWarning[];
  unscoped_knowledge_ids: string[];
  llm_calls: number;
  embedding_calls: number;
  replaced: boolean;
  closed_session_ids: string[];
  backup_path?: string | null;
  priors_created?: number;
  ok: boolean;
}

export interface ImportReport {
  world_id: string;
  format_version: number;
  source_world_id: string;
  remapped: boolean;
  forced: boolean;
  replaced: boolean;
  backup_path?: string | null;
  closed_session_ids: string[];
  counts: Record<string, number>;
  warnings: BuildWarning[];
  ok: boolean;
}

export interface WorldInfo {
  id: string;
  name: string;
  description?: string | null;
  region_count: number;
  updated_at?: string | null;
  last_writer?: string | null;
  open_sessions?: number | null;
}

export interface DemoInfo {
  name: string;
  title: string;
  description?: string | null;
  file: string;
}

export interface RegionBrief {
  region_id: string;
  name: string;
  level: string;
  level_path: string[];
  description?: string | null;
  top_knowledge: string[];
}

export interface KnowledgeView {
  knowledge_id: string;
  statement: string;
  title?: string | null;
  scope_type: string; // direct | inherited | hearsay
  is_hearsay: boolean; // canonical distance-decayed knowledge (legacy: is_rumor)
  confidence: number;
  path_decay?: number | null; // hearsay: decay along the topology path
  distortion?: number | null; // session rumor views: LLM distortion degree
  source?: string | null; // provenance source, or "rumor" / "rumor:promoted" in a session view
  region_id?: string | null;
  // X1 localization (response-only): ko translation, null when unresolved
  statement_ko?: string | null;
  title_ko?: string | null;
}

export interface QueryResult {
  world_id: string;
  region_id: string;
  items: KnowledgeView[];
  shared_ids: string[];
  unique_ids: string[];
}

// --- Augmentation Q&A (U3 BLM §4, domain-entities §4 〔Step 1.3 정정〕) ------- //
export type AugAction = "confirm" | "edit" | "remove" | "add" | "ignore";

export interface QuestionTarget {
  kind: "knowledge" | "entity" | "region" | "npc" | "connection";
  id: string;
  name: string;
  region_id?: string | null;
  region_name?: string | null;
  field?: string | null;
  broken_id?: string | null;
}

export interface AugQuestion {
  id: string;
  issue_id: string;
  issue_key: string;
  text: string;
  target?: QuestionTarget | null;
  actions: AugAction[];
}

export interface ChangeSet {
  id: string;
  description: string;
  added_ids: string[];
  reverted: boolean;
}

// AugmentationRun — one designer Q&A run over a world, kept by the screen (B2).
export interface AugRun {
  id: string;
  world_id: string;
  status: "open" | "converged" | "stopped";
  answers: number;
  open_questions: AugQuestion[];
  ignored_keys: string[];
  history: ChangeSet[];
  llm_calls: number;
  llm_budget_exhausted: boolean;
}

export interface AugAnswer {
  question_id: string;
  action: AugAction;
  statement?: string;
  title?: string;
  confidence?: number;
  region_id?: string;
  ref_id?: string;
}

export interface AnswerResult {
  change: ChangeSet | null;
  run: AugRun;
  changed: QuestionTarget[];
}

// --- Session layer (S3) ---------------------------------------------------- //
export interface GameSession {
  id: string;
  world_id: string;
  status: "open" | "closed";
  turn: number;
  created_at?: string | null;
  closed_at?: string | null;
}

export interface SessionRumor {
  id: string;
  session_id: string;
  region_id: string;
  distorted_from_id: string;
  distorted_from_kind: string;
  statement: string;
  distortion_degree: number;
  support: number;
  confidence: number;
  promoted: boolean;
  statement_ko?: string | null; // X1 localization (response-only)
  active?: boolean; // false once pruned or voided (the GM deed view lists those too)
  // U6: where the rumor came from ("deed" = a player's deed, spread along the map)
  origin_kind?: "canonical" | "deed";
  origin_deed_id?: string | null;
  origin_appraisal_id?: string | null;
  spread_from_region_id?: string | null;
}

export interface RegionDistortion {
  session_id: string;
  region_id: string;
  distortion_degree: number;
  feedback_share?: number; // U7: the part feedback put there (capped, given back)
}

// U7 GM overlay (FR-D4): one row per world region, built on read
export interface RegionState {
  region_id: string;
  region_name: string;
  distortion: number;
  feedback_share: number;
  active_rumors: number;
  promoted_rumors: number;
  deed_rumors: number;
  active_events: number;
}

export interface WorldState {
  session_id: string;
  turn: number;
  player_region_id: string | null;
  regions: RegionState[];
  max_event_suggestions?: number; // the server's suggestion cap (U3, U7 review #15)
}

export interface TimelineEntry {
  id: string;
  session_id: string;
  turn: number;
  kind: string;
  summary: string;
  payload: Record<string, unknown>;
  created_at?: string | null;
}

export interface RegionTurnChange {
  region_id: string;
  region_name?: string; // U4 (FR-D3): filled by the backend from the snapshot
  promoted: string[];
  demoted: string[];
  pruned: string[];
  events_applied: string[];
  events_resolved: string[];
  rumors_added: string[];
}

export interface TurnResult {
  session_id: string;
  turn: number;
  promoted_ids: string[];
  demoted_ids: string[];
  applied_event_ids: string[];
  resolved_event_ids: string[];
  pruned_rumor_ids?: string[];
  feedback_regions?: string[];
  region_changes?: RegionTurnChange[]; // X1 per-region turn-change summary (FR-UX2.6)
  // U4 (additive): LLM budget accounting
  llm_calls?: number;
  budget_exhausted?: boolean;
  llm_failed?: boolean;
  rumors_skipped_regions?: string[];
  rumors_capped_regions?: string[];
}

// --- Player mode (U4) --------------------------------------------------------- //
export interface Player {
  id: string;
  session_id: string;
  name: string;
  region_id: string;
  turns_spent: number;
  created_at?: string | null;
}

export interface PlayerCreate {
  name: string;
  start_region_id: string;
}

export type PlayerAction =
  | { type: "move"; to_region_id: string }
  | { type: "wait" }
  | { type: "end_talk"; npc_id: string }
  | { type: "declare"; text: string };

export interface MoveOption {
  region_id: string;
  region_name: string;
  kind: string;
  weight: number;
  cost_turns: number;
  passable: boolean;
  reason?: string | null;
}

export interface RegionView {
  session_id: string;
  turn: number;
  player: Player;
  region_id: string;
  region_name: string;
  level: string;
  description: string;
  level_path: string[];
  npcs: NPC[];
  facts: KnowledgeView[];
  hearsay: KnowledgeView[];
  rumors: SessionRumor[];
  moves: MoveOption[];
  turn_running: boolean;
  llm_available: boolean;
  declare_max_chars?: number; // U6: the server's declaration limit
}

export type TurnRunStatus = "running" | "done" | "failed";

export interface ActionResult {
  session: GameSession;
  player: Player | null;
  turns: TurnResult[];
  changes: RegionTurnChange[];
  narration: string[];
  llm_calls: number;
  budget_exhausted: boolean;
  llm_failed: boolean;
  llm_available: boolean;
  declaration?: Narration | null; // U6: a declare action's narration
}

export interface TurnRun {
  id: string;
  session_id: string;
  action: PlayerAction | null;
  cost_turns: number;
  status: TurnRunStatus;
  started_turn: number;
  started_at?: string | null;
  finished_at?: string | null;
  result?: ActionResult | null;
  error?: string | null;
}

export interface SessionStartOut {
  session: GameSession;
  player: Player;
}

// --- Session events (Phase 2) --------------------------------------------- //
export type EventCategory =
  | "war"
  | "plague"
  | "politics"
  | "disaster"
  | "festival"
  | "discovery";
export type EventLifecycle = "one_shot" | "persistent";
export type EventStatus = "suggested" | "active" | "resolved";

export interface SessionEvent {
  id: string;
  session_id: string;
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
  lifecycle: EventLifecycle;
  status: EventStatus;
  created_turn: number;
  resolved_turn?: number | null;
  contributions: Record<string, number>;
  description_ko?: string | null; // X1 localization (response-only)
}

export interface EventDraft {
  region_id: string;
  category: EventCategory;
  description: string;
  magnitude: number;
}

// --- U6 deeds & spread -------------------------------------------------------- //
/** A declaration's outcome: `text` in the display language, `record` in English. */
export interface Narration {
  text: string;
  record: string;
  lang: string;
  llm_calls: number;
}

export type DeedKind = "arrival" | "statement" | "declared_action";

export interface Deed {
  id: string;
  session_id: string;
  player_id: string;
  region_id: string;
  turn: number;
  kind: DeedKind;
  text: string;
  declaration?: string | null;
  witnessed_npc_ids: string[];
  voided: boolean;
  voided_turn?: number | null;
  created_at?: string | null;
  // GM view (DeedViewOut)
  text_ko?: string | null;
  region_name?: string;
  witness_names?: string[];
}

export interface DeedAppraisal {
  id: string;
  deed_id: string;
  npc_id: string;
  noteworthy: boolean;
  salience: number;
  slant: string;
  retelling: string;
  turn: number;
  seeded_rumor_id?: string | null;
  retelling_ko?: string | null;
  npc_name?: string;
}

export interface DeedViewOut {
  deed: Deed;
  appraisals: DeedAppraisal[];
  rumors: SessionRumor[];
  reached_region_ids: string[];
  reached_region_names: string[];
}

export interface VoidResult {
  deed_id: string;
  deactivated_rumor_ids: string[];
}

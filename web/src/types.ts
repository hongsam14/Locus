export interface Coord {
  x: number;
  y: number;
}

export interface Region {
  id: string;
  name: string;
  level: string;
  parent_id?: string | null;
  attributes?: Record<string, unknown>;
  position?: Coord | null;
}

export interface ConnectionEdge {
  source_region_id: string;
  target_region_id: string;
  kind: string;
  weight: number;
}

export interface WorldExport {
  world_id: string;
  regions: Region[];
  connections: ConnectionEdge[];
  knowledge: unknown[];
  scopes: unknown[];
}

export interface KnowledgeView {
  knowledge_id: string;
  statement: string;
  title?: string | null;
  scope_type: string;
  is_rumor: boolean;
  confidence: number;
  distortion_degree?: number | null;
  source?: string | null;
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

export interface AugQuestion {
  id: string;
  issue_id: string;
  text: string;
  options: string[];
  kind: string;
}

export interface AugSession {
  id: string;
  world_id: string;
  round: number;
  status: string;
  open_questions: AugQuestion[];
  history: { id: string; description: string }[];
}

export interface AugAnswer {
  question_id: string;
  action: string;
  target_id?: string;
  statement?: string;
  confidence?: number;
  region_id?: string;
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
}

export interface RegionDistortion {
  session_id: string;
  region_id: string;
  distortion_degree: number;
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

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
  scope_type: string;
  is_rumor: boolean;
  confidence: number;
  distortion_degree?: number | null;
  source?: string | null;
  region_id?: string | null;
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

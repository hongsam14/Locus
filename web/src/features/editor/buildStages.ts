import { t } from "../../i18n";
import type { BuildWarning } from "../../types";

/** The stages a build or import report names (V8 code plan § 1.2). Not a closed enum: the
 * server's `BuildWarning.stage` is a free string, so an unknown stage reads "기타" instead of
 * failing a check against a server enum. */
const KNOWN = new Set([
  "ingestion",
  "topology",
  "wiki",
  "ontology",
  "persist-graph",
  "persist-search",
  "persist-meta",
  "embed",
  "import",
  "load",
  "backup",
  "carry-over",
  "duplicate-ids",
  "commit",
  "sessions",
]);

export function stageLabel(stage: string): string {
  return t(`label.stage.${KNOWN.has(stage) ? stage : "other"}`);
}

export interface StageGroup {
  stage: string; // the server's stage, or "other"
  label: string;
  severity: "warning" | "error";
  warnings: BuildWarning[];
}

/** The warnings by stage, errors first, in the order each stage first came (BR-V8-30). */
export function groupByStage(warnings: BuildWarning[]): StageGroup[] {
  const groups = new Map<string, StageGroup>();
  for (const w of warnings) {
    const stage = KNOWN.has(w.stage) ? w.stage : "other";
    const severity = w.severity === "error" ? "error" : "warning";
    const key = `${severity}:${stage}`;
    const g = groups.get(key) ?? { stage, label: stageLabel(stage), severity, warnings: [] };
    g.warnings.push(w);
    groups.set(key, g);
  }
  const all = [...groups.values()];
  return [...all.filter((g) => g.severity === "error"), ...all.filter((g) => g.severity === "warning")];
}

/** How many open sessions a replace could not close (the server's "sessions" stage, V6). */
export function sessionsNotClosed(warnings: BuildWarning[]): number {
  return warnings.filter((w) => w.stage === "sessions").length;
}

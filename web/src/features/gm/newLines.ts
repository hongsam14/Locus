// The timeline's "new" marks (V6 BLM § 5.6, BR-V6-08, code plan § 1.1 R-07): the lines that
// were not there just before [advance turn] was pressed. A timeline not read yet at that
// moment gives no snapshot, and then nothing is marked.
import type { TimelineEntry } from "../../types";

export function snapshotIds(timeline: TimelineEntry[] | undefined, ready: boolean): Set<string> | null {
  return ready && timeline ? new Set(timeline.map((e) => e.id)) : null;
}

export function newLineIds(before: Set<string> | null, timeline: TimelineEntry[] | undefined): Set<string> {
  if (!before || !timeline) return new Set();
  return new Set(timeline.filter((e) => !before.has(e.id)).map((e) => e.id));
}

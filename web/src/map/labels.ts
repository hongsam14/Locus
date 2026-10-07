// Region labels on plates that keep out of each other and of every marker (V2 FR-D7,
// BLM § 8.3, BR-V2-19). Greedy and deterministic: labels are placed in a fixed order —
// the player's region, the selected one, the reachable ones, then the rest, each group by
// y, x and id — so the same map always gets the same layout whatever the input order.

export type Box = { x: number; y: number; w: number; h: number };
export type Side = "below" | "right" | "left" | "above";
export type LabelBox = Box & { id: string; side: Side };
export type LabelAnchor = { id: string; x: number; y: number; r: number; group?: number };
export type LabelText = { id: string; text: string; size: number };

const SIDES: Side[] = ["below", "right", "left", "above"];
const GAP = 4;

/** How wide a label plate is: Hangul, Han and other wide letters 1 em, the rest 0.6 em,
 * plus a little padding. An estimate — the plate only needs to cover the text. */
export function labelWidth(text: string, size: number): number {
  let w = 0;
  for (const ch of text) {
    const cp = ch.codePointAt(0) ?? 0;
    const wide = (cp >= 0x1100 && cp <= 0x11ff) || (cp >= 0x2e80 && cp <= 0xa4cf) || (cp >= 0xac00 && cp <= 0xd7a3) || (cp >= 0xf900 && cp <= 0xfaff) || (cp >= 0xff00 && cp <= 0xff60);
    w += wide ? size : size * 0.6;
  }
  return w + size * 0.8;
}

export function overlaps(a: Box, b: Box): boolean {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

function candidate(side: Side, a: LabelAnchor, w: number, h: number): Box {
  switch (side) {
    case "below":
      return { x: a.x - w / 2, y: a.y + a.r + GAP, w, h };
    case "right":
      return { x: a.x + a.r + GAP, y: a.y - h / 2, w, h };
    case "left":
      return { x: a.x - a.r - GAP - w, y: a.y - h / 2, w, h };
    case "above":
      return { x: a.x - w / 2, y: a.y - a.r - GAP - h, w, h };
  }
}

/** The four places a label may take, in the order they are tried. */
export function candidateBoxes(anchor: LabelAnchor, text: string, size: number): (Box & { side: Side })[] {
  const w = labelWidth(text, size);
  const h = size * 1.4;
  return SIDES.map((side) => ({ ...candidate(side, anchor, w, h), side }));
}

/** The plate of each label, next to its anchor. `occupied` are the markers and rings
 * already drawn; a label never covers one when any side is free. */
export function placeLabels(anchors: LabelAnchor[], labels: LabelText[], occupied: Box[]): LabelBox[] {
  const byId = new Map(anchors.map((a) => [a.id, a]));
  const order = labels
    .filter((l) => byId.has(l.id))
    .sort((p, q) => {
      const a = byId.get(p.id)!;
      const b = byId.get(q.id)!;
      return (a.group ?? 9) - (b.group ?? 9) || a.y - b.y || a.x - b.x || (p.id < q.id ? -1 : p.id > q.id ? 1 : 0);
    });
  const placed: LabelBox[] = [];
  for (const l of order) {
    const a = byId.get(l.id)!;
    const taken = [...occupied, ...placed];
    const options = candidateBoxes(a, l.text, l.size);
    const free = options.find((box) => !taken.some((t) => overlaps(box, t)));
    placed.push({ ...(free ?? options[0]), id: l.id });
  }
  return placed;
}

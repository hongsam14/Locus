// Labels keep out of each other and of every marker when they can, stay on the map, never
// cover their own marker, and the same map gets the same layout whatever order it comes in
// (V2 BR-V2-19, TP-V2-10, PBT-03). Anchors carry their own marker room: a selected or
// reachable marker takes more (its ring), as on the real map (V2 review #5).
import { readFileSync } from "node:fs";
import fc from "fast-check";
import {
  MAP_EXTENT,
  candidateBoxes,
  markerBox,
  overlaps,
  placeLabels,
  within,
  type LabelAnchor,
  type LabelText,
} from "../map";

const name = fc.oneof(
  fc.string({ minLength: 1, maxLength: 12 }),
  fc.array(fc.integer({ min: 0xac00, max: 0xd7a3 }), { minLength: 1, maxLength: 8 }).map((cs) => String.fromCodePoint(...cs)),
);
const map = fc
  .uniqueArray(
    fc.record({
      id: fc.string({ minLength: 1, maxLength: 6 }),
      x: fc.double({ min: 0, max: MAP_EXTENT.w, noNaN: true }),
      y: fc.double({ min: 0, max: MAP_EXTENT.h, noNaN: true }),
      group: fc.integer({ min: 0, max: 3 }),
      room: fc.constantFrom(9, 10, 15, 16, 18), // plain, ringed, selected/reachable, the player
      below: fc.constantFrom(0, 0, 16), // some carry a badge
      text: name,
    }),
    { minLength: 2, maxLength: 30, selector: (r) => r.id },
  )
  .map((rows) => ({
    anchors: rows.map(({ id, x, y, group, room }) => ({ id, x, y, r: room, group })) as LabelAnchor[],
    labels: rows.map(({ id, text, below }) => ({ id, text, size: 16, below })) as LabelText[],
  }));

describe("label placement (properties)", () => {
  it("a label takes the first free side on the map; else the first side on the map; else below", () => {
    fc.assert(
      fc.property(map, ({ anchors, labels }) => {
        const placed = placeLabels(anchors, labels, [], MAP_EXTENT);
        const byId = new Map(anchors.map((a) => [a.id, a]));
        const labelOf = new Map(labels.map((l) => [l.id, l]));
        const markers = anchors.map(markerBox);
        return placed.every((b, i) => {
          const before = [...markers, ...placed.slice(0, i)];
          const l = labelOf.get(b.id)!;
          const options = candidateBoxes(byId.get(b.id)!, l.text, 16, l.below);
          const onMap = options.filter((o) => within(o, MAP_EXTENT));
          const firstFree = onMap.find((o) => !before.some((t) => overlaps(o, t)));
          return b.side === (firstFree ?? onMap[0])?.side || (onMap.length === 0 && b.side === "below");
        });
      }),
    );
  });

  it("a label never covers its own marker, whatever room its rings take", () => {
    fc.assert(
      fc.property(map, ({ anchors, labels }) => {
        const own = new Map(anchors.map((a) => [a.id, markerBox(a)]));
        return placeLabels(anchors, labels, [], MAP_EXTENT).every((b) => !overlaps(b, own.get(b.id)!));
      }),
    );
  });

  it("the layout does not depend on the input order", () => {
    fc.assert(
      fc.property(map, fc.integer({ min: 1, max: 1000 }), ({ anchors, labels }, salt) => {
        const shuffled = [...labels].sort((a, b) => ((a.id.charCodeAt(0) * salt) % 7) - ((b.id.charCodeAt(0) * salt) % 7));
        const one = placeLabels(anchors, labels, [], MAP_EXTENT);
        const two = placeLabels([...anchors].reverse(), shuffled, [], MAP_EXTENT);
        return JSON.stringify(one) === JSON.stringify(two);
      }),
    );
  });
});

describe("label placement (the Emberleaf demo)", () => {
  it("records how many plates still touch on the demo map (target 0)", () => {
    // the demo is data: its World File in the package (vitest runs from web/)
    const world = JSON.parse(readFileSync("../locus/world/demo/worlds/emberleaf.world.json", "utf8")) as {
      regions: { id: string; name: string; level: string; position: { x: number; y: number } | null }[];
    };
    const towns = world.regions.filter((r) => r.position && !["continent", "province"].includes(r.level));
    expect(towns.length).toBeGreaterThan(3); // the demo still has towns to place
    const at = (r: (typeof towns)[number]) => ({ x: r.position!.x * MAP_EXTENT.w, y: r.position!.y * MAP_EXTENT.h });
    // as drawn: plain markers, then each town selected in turn (its ring takes more room)
    for (const selected of [null, ...towns.map((r) => r.id)]) {
      const anchors = towns.map((r) => ({ id: r.id, ...at(r), r: r.id === selected ? 16 : 10, group: r.id === selected ? 1 : 3 }));
      const markers = anchors.map(markerBox);
      const placed = placeLabels(anchors, towns.map((r) => ({ id: r.id, text: r.name, size: 16 })), [], MAP_EXTENT);
      let touching = 0;
      for (let i = 0; i < placed.length; i++)
        for (const other of [...markers, ...placed.slice(i + 1)]) if (overlaps(placed[i], other)) touching++;
      if (selected == null) console.log(`emberleaf label overlaps: ${touching} (${placed.length} labels)`);
      expect(placed).toHaveLength(towns.length);
      expect({ selected, touching }).toEqual({ selected, touching: 0 });
      expect(placed.every((b) => within(b, MAP_EXTENT))).toBe(true);
    }
  });
});

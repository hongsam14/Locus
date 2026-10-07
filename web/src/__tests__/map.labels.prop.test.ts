// Labels keep out of each other and of every marker when they can, and the same map gets
// the same layout whatever order it comes in (V2 BR-V2-19, TP-V2-10, PBT-03).
import { readFileSync } from "node:fs";
import fc from "fast-check";
import { MAP_EXTENT, candidateBoxes, overlaps, placeLabels, type Box, type LabelAnchor, type LabelText } from "../map";

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
      text: name,
    }),
    { minLength: 2, maxLength: 30, selector: (r) => r.id },
  )
  .map((rows) => ({
    anchors: rows.map(({ id, x, y, group }) => ({ id, x, y, r: 8, group })) as LabelAnchor[],
    labels: rows.map(({ id, text }) => ({ id, text, size: 16 })) as LabelText[],
    markers: rows.map(({ x, y }) => ({ x: x - 10, y: y - 10, w: 20, h: 20 })) as Box[],
  }));

describe("label placement (properties)", () => {
  it("a label takes the first free side, and a covered place only when no side was free", () => {
    fc.assert(
      fc.property(map, ({ anchors, labels, markers }) => {
        const placed = placeLabels(anchors, labels, markers);
        const byId = new Map(anchors.map((a) => [a.id, a]));
        const textOf = new Map(labels.map((l) => [l.id, l.text]));
        return placed.every((b, i) => {
          const before = [...markers, ...placed.slice(0, i)];
          const options = candidateBoxes(byId.get(b.id)!, textOf.get(b.id)!, 16);
          const firstFree = options.find((o) => !before.some((t) => overlaps(o, t)));
          return firstFree ? firstFree.side === b.side : b.side === "below";
        });
      }),
    );
  });

  it("the layout does not depend on the input order", () => {
    fc.assert(
      fc.property(map, fc.integer({ min: 1, max: 1000 }), ({ anchors, labels, markers }, salt) => {
        const shuffled = [...labels].sort((a, b) => ((a.id.charCodeAt(0) * salt) % 7) - ((b.id.charCodeAt(0) * salt) % 7));
        const one = placeLabels(anchors, labels, markers);
        const two = placeLabels([...anchors].reverse(), shuffled, markers);
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
    const anchors = towns.map((r) => ({ id: r.id, x: r.position!.x * MAP_EXTENT.w, y: r.position!.y * MAP_EXTENT.h, r: 8 }));
    const markers = anchors.map((a) => ({ x: a.x - 10, y: a.y - 10, w: 20, h: 20 }));
    const placed = placeLabels(anchors, towns.map((r) => ({ id: r.id, text: r.name, size: 16 })), markers);
    let touching = 0;
    for (let i = 0; i < placed.length; i++)
      for (const other of [...markers, ...placed.slice(i + 1)]) if (overlaps(placed[i], other)) touching++;
    console.log(`emberleaf label overlaps: ${touching} (${placed.length} labels)`);
    expect(placed).toHaveLength(towns.length);
    expect(touching).toBe(0);
  });
});

// Pointer ↔ map coordinates round-trip under any meet scale and offset (V2 BR-V2-18,
// TP-V2-9, PBT-02).
import fc from "fast-check";
import { MAP_EXTENT, inside, invert, meetMatrix, normalizeFromMatrix, toClient, type ViewBox } from "../map";

const norm = fc.record({ x: fc.double({ min: 0, max: 1, noNaN: true }), y: fc.double({ min: 0, max: 1, noNaN: true }) });
// a container somewhere on the page, of any size and shape the map could be drawn into
const rect = fc.record({
  left: fc.double({ min: -500, max: 500, noNaN: true }),
  top: fc.double({ min: -500, max: 500, noNaN: true }),
  width: fc.double({ min: 40, max: 3000, noNaN: true }),
  height: fc.double({ min: 40, max: 3000, noNaN: true }),
});
// the full map or a close-up inside it
const viewBox: fc.Arbitrary<ViewBox> = fc.oneof(
  fc.constant(MAP_EXTENT),
  fc
    .record({ x: fc.double({ min: 0, max: 800, noNaN: true }), y: fc.double({ min: 0, max: 500, noNaN: true }), w: fc.double({ min: 100, max: 1000, noNaN: true }) })
    .map(({ x, y, w }) => ({ x, y, w, h: (w * 5) / 8 })),
);

describe("map coordinates (properties)", () => {
  it("toClient and normalizeFromMatrix undo each other", () => {
    fc.assert(
      fc.property(norm, rect, viewBox, (p, r, vb) => {
        const m = meetMatrix(r, vb);
        const back = normalizeFromMatrix(toClient(p, m), invert(m));
        return Math.abs(back.x - p.x) < 1e-9 && Math.abs(back.y - p.y) < 1e-9;
      }),
    );
  });

  it("a point on the letterbox beside the drawing is outside 0..1", () => {
    fc.assert(
      fc.property(rect, (r) => {
        const m = meetMatrix(r, MAP_EXTENT);
        const left = toClient({ x: 0, y: 0.5 }, m);
        const right = toClient({ x: 1, y: 0.5 }, m);
        const top = toClient({ x: 0.5, y: 0 }, m);
        // one pixel beyond the drawn map on the side that has room
        const beyond = r.width / r.height > 1.6 ? { x: left.x - 1, y: left.y } : { x: top.x, y: top.y - 1 };
        return !inside(normalizeFromMatrix(beyond, invert(m))) && right.x <= r.left + r.width + 1e-6;
      }),
    );
  });
});

describe("map coordinates (examples)", () => {
  it("a 800 × 500 box maps its corners to 0 and 1", () => {
    const m = meetMatrix({ left: 10, top: 20, width: 800, height: 500 }, MAP_EXTENT);
    expect(normalizeFromMatrix({ x: 10, y: 20 }, invert(m))).toEqual({ x: 0, y: 0 });
    const far = normalizeFromMatrix({ x: 810, y: 520 }, invert(m));
    expect(far.x).toBeCloseTo(1, 12);
    expect(far.y).toBeCloseTo(1, 12);
  });
});

// How connections are drawn (V2 BLM § 8.4, TP-V2-11).
import { edgeStyle, focusBox, MAP_EXTENT, uniqueEdges } from "../map";
import type { ConnectionEdge } from "../types";

const edge = (a: string, b: string, kind: string, weight = 0.5) =>
  ({ source_region_id: a, target_region_id: b, kind, weight }) as ConnectionEdge;

describe("edge style", () => {
  it("draws each kind its own way, in token colours", () => {
    expect(edgeStyle("river", 1)).toMatchObject({ stroke: "var(--color-map-river)", dashed: false });
    expect(edgeStyle("route", 1)).toMatchObject({ stroke: "var(--color-map-path)", dash: "7 5" });
    expect(edgeStyle("adjacent", 1)).toMatchObject({ stroke: "var(--color-map-path)", dashed: false });
    expect(edgeStyle("blocked", 1)).toMatchObject({ stroke: "var(--color-map-blocked)", cross: true });
    for (const kind of ["river", "route", "adjacent", "blocked", "new"]) expect(edgeStyle(kind, 0.5).stroke).toMatch(/^var\(--color-/);
  });

  it("draws the two directions of a connection once, with the stronger weight", () => {
    const one = uniqueEdges([edge("a", "b", "route", 0.2), edge("b", "a", "route", 0.7), edge("a", "b", "river")]);
    expect(one).toHaveLength(2);
    expect(one.find((c) => c.kind === "route")?.weight).toBe(0.7);
  });
});

describe("play close-up", () => {
  it("frames the player and neighbours at 8:5 inside the map", () => {
    const box = focusBox({ a: { x: 0.4, y: 0.9 }, b: { x: 0.6, y: 0.65 }, c: { x: 0.65, y: 0.92 } }, { id: "a", neighbors: ["b", "c"] });
    expect(box.w / box.h).toBeCloseTo(1.6, 6);
    expect(box.x).toBeGreaterThanOrEqual(0);
    expect(box.y + box.h).toBeLessThanOrEqual(MAP_EXTENT.h + 1e-9);
    expect(focusBox({}, { id: "x", neighbors: [] })).toEqual(MAP_EXTENT);
  });
});

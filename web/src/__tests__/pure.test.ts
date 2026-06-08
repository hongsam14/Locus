import { describe, expect, it } from "vitest";
import { autoLayout } from "../layout";
import { edgeStyle, toPixels } from "../viz";
import type { Region } from "../types";

const region = (id: string, position?: { x: number; y: number }): Region => ({
  id,
  name: id,
  level: "town",
  position: position ?? null,
});

describe("autoLayout", () => {
  it("uses region.position when present", () => {
    const out = autoLayout([region("a", { x: 0.2, y: 0.8 })]);
    expect(out.a).toEqual({ x: 0.2, y: 0.8 });
  });

  it("places missing regions on a circle within [0,1]", () => {
    const out = autoLayout([region("a"), region("b"), region("c")]);
    for (const id of ["a", "b", "c"]) {
      expect(out[id].x).toBeGreaterThanOrEqual(0);
      expect(out[id].x).toBeLessThanOrEqual(1);
      expect(out[id].y).toBeGreaterThanOrEqual(0);
      expect(out[id].y).toBeLessThanOrEqual(1);
    }
  });
});

describe("viz", () => {
  it("blocked edges are red + dashed", () => {
    const s = edgeStyle("blocked", 0.2);
    expect(s.dashed).toBe(true);
    expect(s.color).toBe("#c0392b");
  });

  it("weight scales width/opacity", () => {
    expect(edgeStyle("route", 1).width).toBeGreaterThan(edgeStyle("route", 0).width);
  });

  it("toPixels scales by canvas size", () => {
    expect(toPixels({ x: 0.5, y: 0.5 }, 800, 500)).toEqual({ px: 400, py: 250 });
  });
});

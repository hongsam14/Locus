// Every allowed text/ground and line/ground pair of the V2 tokens meets WCAG
// (V2 FD domain-entities § 1.6, BR-V2-05/06, TP-V2-1). Values are read from index.css,
// so a token change that breaks a pair fails here. Colours with alpha (the map label
// plate) are composited onto their opaque ground first (NFR light review R-04).
import { readFileSync } from "node:fs";
import { colorTokens, composite, contrast, parseColor, type Rgba } from "../test/contrast";
import { webPath } from "../test/paths";

// vitest runs from web/ (the CI job and npm test both do)
const css = readFileSync(webPath("src/index.css"), "utf8");
const tokens = colorTokens(css);

function color(name: string): Rgba {
  const value = tokens[name];
  if (value == null) throw new Error(`no token --color-${name}`);
  return parseColor(value);
}

/** A ground: an opaque token, or "top@base" for a translucent token over an opaque one. */
function ground(name: string): Rgba {
  const [top, base] = name.split("@");
  return base ? composite(color(top), color(base)) : color(top);
}

const TEXT = 4.5;
const UI = 3.0;

// [front, grounds, minimum] — the canonical table
const PAIRS: [string, string[], number][] = [
  ["fg", ["bg", "chrome", "surface", "sunken", "map-plate@map-land"], TEXT],
  [
    "muted",
    ["bg", "chrome", "surface", "sunken", "tint-event", "tint-danger", "tint-success", "tint-info", "map-plate@map-land"],
    TEXT,
  ],
  ["faint", ["bg", "surface", "sunken", "map-sea", "map-land"], TEXT],
  ["accent", ["bg", "chrome", "surface", "sunken"], TEXT],
  ["danger", ["bg", "surface", "sunken", "tint-danger"], TEXT],
  ["event", ["tint-event", "bg", "surface", "sunken"], TEXT], // sunken: a toast title (V2 review § 2)
  ["success", ["tint-success", "bg", "surface"], TEXT],
  ["info", ["tint-info", "bg", "surface"], TEXT],
  ["info-fg", ["tint-info"], TEXT],
  ["on-accent", ["accent", "accent-hover"], TEXT],
  ["on-danger", ["danger"], TEXT],
  ["disabled-fg", ["disabled"], TEXT],
  ["line-strong", ["bg", "chrome", "surface"], UI],
  ["map-river", ["map-land"], UI],
  ["map-path", ["map-land"], UI],
  ["map-blocked", ["map-land"], UI],
  ["map-town", ["map-land"], UI],
  ["map-current", ["map-land"], UI],
];

describe("token contrast (allowed pairs)", () => {
  for (const [front, grounds, min] of PAIRS) {
    for (const g of grounds) {
      it(`${front} on ${g} ≥ ${min}`, () => {
        expect(contrast(color(front), ground(g))).toBeGreaterThanOrEqual(min);
      });
    }
  }

  it("composites a translucent colour before measuring", () => {
    const plate = parseColor("rgb(23 18 14 / 0.9)");
    const over = composite(plate, parseColor("#2a2119"));
    expect(over.a).toBe(1);
    expect(over.r).toBe(Math.round(23 * 0.9 + 42 * 0.1));
  });

  it("known values match the FD table", () => {
    expect(contrast(color("fg"), color("bg"))).toBeCloseTo(15.01, 1);
    expect(contrast(color("line-strong"), color("surface"))).toBeCloseTo(3.1, 1);
  });
});

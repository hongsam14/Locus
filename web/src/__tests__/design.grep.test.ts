// The design system stays the only source of colour and type (V2 BR-V2-01/03/04/09,
// TP-V2-2). Reads the source files as text, from web/ (src/test/paths).
import { readdirSync, readFileSync } from "node:fs";
import { webPath } from "../test/paths";

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(webPath(dir), { withFileTypes: true })) {
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__" && entry.name !== "test") out.push(...sources(path));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) out.push(path);
  }
  return out;
}

const FILES = sources("src").map((path) => ({ path, text: readFileSync(webPath(path), "utf8") }));

// a raw colour: #rgb, #rgba, #rrggbb, #rrggbbaa, or a colour function (review § 2)
const RAW_COLOUR = /#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b(?![0-9a-fA-F])|\b(rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\(/;
// a CSS colour keyword written into a style or an svg attribute
const NAMED_COLOUR = /\b(fill|stroke|color|background|backgroundColor|borderColor|stopColor)\s*[:=]\s*\{?\s*["'](white|black|red|green|blue|yellow|orange|purple|gray|grey|pink|brown|gold|silver)["']/;
// a class from Tailwind's default palette (index.css turns that palette off too)
const PALETTE_CLASS = /\b(bg|text|border|ring|fill|stroke|from|to|via|outline|divide|accent|caret|decoration|shadow|placeholder)-(slate|gray|zinc|neutral|stone|red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|black|white)(-\d{2,3})?\b/;

function offenders(pattern: RegExp, allow: (path: string) => boolean = () => false): string[] {
  return FILES.filter((f) => !allow(f.path) && pattern.test(f.text)).map((f) => f.path);
}

describe("design rules in the source", () => {
  it("has no raw colour value outside index.css", () => {
    expect(offenders(RAW_COLOUR)).toEqual([]);
    expect(offenders(NAMED_COLOUR)).toEqual([]);
    expect(offenders(PALETTE_CLASS)).toEqual([]);
  });

  it("the checks catch what they look for", () => {
    for (const bad of ["#17120e80", "#fff8", "#f0e6d2", "#abc", "rgb(0 0 0)", "oklch(70% 0.1 80)"]) expect(bad).toMatch(RAW_COLOUR);
    for (const ok of ["review #14", "var(--color-bg)", "distortionColor(0.3)"]) expect(ok).not.toMatch(RAW_COLOUR);
    expect('style={{ fill: "white" }}').toMatch(NAMED_COLOUR);
    expect('fill="black"').toMatch(NAMED_COLOUR);
    expect("text-red-600 bg-white").toMatch(PALETTE_CLASS);
    expect("text-danger bg-surface border-tint-danger-line").not.toMatch(PALETTE_CLASS);
  });

  it("buttons, badges and tabs use the body face (BR-V2-09)", () => {
    for (const f of FILES.filter((f) => /^src\/ui\/(Button|Badge|Tabs)\.tsx$/.test(f.path))) {
      expect(f.text, f.path).not.toMatch(/font-(heading|display|story)/);
    }
    expect(FILES.filter((f) => /^src\/ui\/(Button|Badge|Tabs)\.tsx$/.test(f.path))).toHaveLength(3);
  });

  it("has none of the old Doodly classes", () => {
    const old = /(?<![\w-])(text-ink|text-ink-soft|bg-paper|bg-paper-card|bg-highlight|sketch-border|sketch-shadow|border-ink|bg-ink|text-paper|accent-ink|ink-underline)(?![\w-])/;
    expect(offenders(old)).toEqual([]);
  });

  // V4 (BR-V4-10/15/23, TP-V4-12): the home and play screens show words, described errors
  // and the focus ring — no fixed-point number, no raw error text, no hidden outline
  it("home and play have no toFixed, String(e) or outline-none", () => {
    const scope = FILES.filter(
      (f) => /^src\/features\/(home|play)\//.test(f.path) || /^src\/routes\/(HomePage|PlayPage)\.tsx$/.test(f.path),
    );
    expect(scope.length).toBeGreaterThan(15); // the check checks something
    for (const rule of [/\.toFixed\(/, /String\((e|err|error)\)/, /outline-none/]) {
      expect(scope.filter((f) => rule.test(f.text)).map((f) => f.path), String(rule)).toEqual([]);
    }
  });

  it("uses the display face for the logo only", () => {
    expect(offenders(/font-display/, (p) => p.endsWith("layout/AppShell.tsx"))).toEqual([]);
  });

  it("has no String(e) in the design system's own code (BR-V2-03)", () => {
    const own = /^src\/(format|errors|hooks|ui|layout|map)\//;
    // describeError is the one place that turns an error into text: its String(err) is the
    // folded original (`raw`), never the sentence people read
    const exempt = (p: string) => p.endsWith("errors/describe.ts");
    expect(
      FILES.filter((f) => own.test(f.path) && !exempt(f.path) && /String\((e|err|error)\)/.test(f.text)).map((f) => f.path),
    ).toEqual([]);
  });

  it("one dark theme, no handwriting font", () => {
    const css = readFileSync(webPath("src/index.css"), "utf8");
    expect(css).toMatch(/color-scheme:\s*dark/);
    expect(css).not.toMatch(/prefers-color-scheme/);
    expect(css).not.toMatch(/gaegu/i);
    expect(readFileSync(webPath("package.json"), "utf8")).not.toMatch(/gaegu/i);
    expect(css).toMatch(/--color-\*:\s*initial/); // no default palette
  });
});

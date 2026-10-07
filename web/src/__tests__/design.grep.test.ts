// The design system stays the only source of colour and type (V2 BR-V2-01/03/04/09,
// TP-V2-2). Reads the source files as text; vitest runs from web/.
import { readdirSync, readFileSync } from "node:fs";

function sources(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__" && entry.name !== "test") out.push(...sources(path));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) out.push(path);
  }
  return out;
}

const FILES = sources("src").map((path) => ({ path, text: readFileSync(path, "utf8") }));

function offenders(pattern: RegExp, allow: (path: string) => boolean = () => false): string[] {
  return FILES.filter((f) => !allow(f.path) && pattern.test(f.text)).map((f) => f.path);
}

describe("design rules in the source", () => {
  it("has no raw colour value outside index.css", () => {
    expect(offenders(/#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3}\b(?![0-9a-fA-F])|\brgba?\(|\bhsla?\(/)).toEqual([]);
  });

  it("has none of the old Doodly classes", () => {
    const old = /(?<![\w-])(text-ink|text-ink-soft|bg-paper|bg-paper-card|bg-highlight|sketch-border|sketch-shadow|border-ink|bg-ink|text-paper|accent-ink|ink-underline)(?![\w-])/;
    expect(offenders(old)).toEqual([]);
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
    const css = readFileSync("src/index.css", "utf8");
    expect(css).toMatch(/color-scheme:\s*dark/);
    expect(css).not.toMatch(/prefers-color-scheme/);
    expect(css).not.toMatch(/gaegu/i);
    expect(readFileSync("package.json", "utf8")).not.toMatch(/gaegu/i);
  });
});

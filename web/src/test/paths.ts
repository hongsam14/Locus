// A path under web/, whatever folder vitest was started from (src/test/globalSetup.ts sets
// WEB_ROOT). `webPath("src/index.css")`, `webPath("../locus/…")`.
import { readdirSync } from "node:fs";

const env = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env;

export function webPath(path: string): string {
  return `${env.WEB_ROOT ?? "."}/${path}`;
}

// The app's .ts/.tsx files under `dir` (a web/ path), tests and test helpers left out.
export function sourceFiles(dir: string): string[] {
  const out: string[] = [];
  for (const entry of readdirSync(webPath(dir), { withFileTypes: true })) {
    const path = `${dir}/${entry.name}`;
    if (entry.isDirectory()) {
      if (entry.name !== "__tests__" && entry.name !== "test") out.push(...sourceFiles(path));
    } else if (/\.(ts|tsx)$/.test(entry.name) && !entry.name.endsWith(".d.ts")) out.push(path);
  }
  return out;
}

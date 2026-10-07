// A path under web/, whatever folder vitest was started from (src/test/globalSetup.ts sets
// WEB_ROOT). `webPath("src/index.css")`, `webPath("../locus/…")`.
const env = (globalThis as unknown as { process: { env: Record<string, string | undefined> } }).process.env;

export function webPath(path: string): string {
  return `${env.WEB_ROOT ?? "."}/${path}`;
}

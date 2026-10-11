// One fast-check seed per vitest run, printed once and shared by every test file
// (V2 NFR-6, PBT-08). Re-run a failure with FC_SEED=<seed> npx vitest run. Also the web/
// folder, for tests that read files.
type Env = Record<string, string | undefined>;

export default function setup(): void {
  const env = (globalThis as unknown as { process: { env: Env } }).process.env;
  // tests that read files (index.css, the sources, the demo world, the backend enums) read
  // them from web/ wherever vitest was started (V2 review § 2)
  env.WEB_ROOT = decodeURIComponent(new URL("../../", import.meta.url).pathname).replace(/\/$/, "");
  if (!env.FC_SEED) env.FC_SEED = String(Math.floor(Math.random() * 2 ** 31));
  console.log(`fast-check seed: ${env.FC_SEED} (re-run: FC_SEED=${env.FC_SEED} npx vitest run)`);
}

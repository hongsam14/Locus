// One fast-check seed per vitest run, printed once and shared by every test file
// (V2 NFR-6, PBT-08). Re-run a failure with FC_SEED=<seed> npx vitest run.
type Env = Record<string, string | undefined>;

export default function setup(): void {
  const env = (globalThis as unknown as { process: { env: Env } }).process.env;
  if (!env.FC_SEED) env.FC_SEED = String(Math.floor(Math.random() * 2 ** 31));
  console.log(`fast-check seed: ${env.FC_SEED} (re-run: FC_SEED=${env.FC_SEED} npx vitest run)`);
}

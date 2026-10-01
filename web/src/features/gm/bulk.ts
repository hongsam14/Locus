export const BULK_LIMIT = 5; // max concurrent region ops (SEC-E)

/** Run fn over items with bounded concurrency (SEC-E; review #4). */
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (x: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length) {
      const idx = next++;
      out[idx] = await fn(items[idx]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

export const BULK_LIMIT = 5; // max concurrent region ops (SEC-E)

/** A bulk run's progress line (moved here from ManualTurnPanel, V6). */
export interface BulkProgress {
  done: number;
  total: number;
  failed: number;
}

/** Run fn over items with bounded concurrency (SEC-E; review #4). A worker asks
 * `shouldStop` before it takes the next item: a stopped run sends no more (V6 R-06). The
 * slots of items never sent stay undefined. */
export async function mapLimit<T, R>(
  items: T[],
  limit: number,
  fn: (x: T) => Promise<R>,
  shouldStop: () => boolean = () => false,
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  async function worker() {
    while (next < items.length && !shouldStop()) {
      const idx = next++;
      out[idx] = await fn(items[idx]);
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker));
  return out;
}

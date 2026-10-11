import type { Norm } from "../../map/geometry";

/** Saves of dragged regions (V8 code plan § 1.1 R-16, BLM § 4). One save at a time per region:
 * a drag that ends while that region's save is out waits, and only the last spot waiting is
 * sent once the save comes back — parallel saves could land out of order and leave the
 * server on the older spot. Different regions never wait for each other. A failed save drops
 * that region's waiting spot and reports it. */
export interface DragSaves {
  move(regionId: string, pos: Norm): void;
  /** The spot last sent for a region, or undefined. */
  lastSent(regionId: string): Norm | undefined;
  /** A save of this region is out, or one is waiting. */
  busy(regionId: string): boolean;
  /** Forget everything (a world replaced or another world opened). */
  clear(): void;
}

export function createDragSaves(opts: {
  save(regionId: string, pos: Norm): Promise<unknown>;
  onSaved?(regionId: string, pos: Norm): void;
  onFailed(regionId: string, err: unknown): void;
}): DragSaves {
  const out = new Set<string>();
  const waiting = new Map<string, Norm>();
  const sent = new Map<string, Norm>();
  let epoch = 0; // a clear() drops the answers of saves sent before it

  function send(regionId: string, pos: Norm) {
    out.add(regionId);
    sent.set(regionId, pos);
    const mine = epoch;
    opts.save(regionId, pos).then(
      () => {
        if (mine !== epoch) return;
        out.delete(regionId);
        const next = waiting.get(regionId);
        if (next) {
          waiting.delete(regionId);
          send(regionId, next);
        } else {
          opts.onSaved?.(regionId, pos);
        }
      },
      (err) => {
        if (mine !== epoch) return;
        out.delete(regionId);
        waiting.delete(regionId);
        opts.onFailed(regionId, err);
      },
    );
  }

  return {
    move(regionId, pos) {
      if (out.has(regionId)) waiting.set(regionId, pos);
      else send(regionId, pos);
    },
    lastSent: (regionId) => sent.get(regionId),
    busy: (regionId) => out.has(regionId) || waiting.has(regionId),
    clear() {
      epoch += 1;
      out.clear();
      waiting.clear();
      sent.clear();
    },
  };
}

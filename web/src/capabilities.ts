// What the server can do (U8, BR-U8-23/26): read once per page load and shared. A failed
// read is not kept (RE-F09, V2 BR-V2-25): the next mount reads again once 30 s have passed
// since the failure, so a server that was down is asked again without a request storm.
import { useEffect, useState } from "react";
import { api } from "./api";
import type { Capabilities } from "./types";

let cached: Capabilities | null = null;
let pending: Promise<Capabilities | null> | null = null;
let failedAt: number | null = null;
export const RETRY_AFTER_MS = 30_000;
const listeners = new Set<(c: Capabilities | null) => void>();

function load(): Promise<Capabilities | null> {
  if (pending) return pending;
  if (failedAt != null && Date.now() - failedAt < RETRY_AFTER_MS) return Promise.resolve(null);
  pending = Promise.resolve()
    .then(() => api.capabilities())
    .then((c) => {
      cached = c;
      failedAt = null;
      return c;
    })
    .catch(() => {
      failedAt = Date.now(); // unknown: no notice and nothing switched off (BR-U8-26)
      pending = null;
      return null;
    })
    .then((c) => {
      for (const l of listeners) l(c);
      return c;
    });
  return pending;
}

/** The server's providers, or `null` while unknown (or when the read failed). */
export function useCapabilities(): Capabilities | null {
  const [caps, setCaps] = useState<Capabilities | null>(cached);
  useEffect(() => {
    listeners.add(setCaps);
    if (cached) setCaps(cached);
    else void load();
    return () => {
      listeners.delete(setCaps);
    };
  }, []);
  return caps;
}

/** True only when the server said it has no LLM: an unknown answer switches nothing off. */
export const llmOff = (caps: Capabilities | null): boolean => caps?.llm === false;

/** Tests: forget the cached answer. */
export function resetCapabilities(): void {
  cached = null;
  pending = null;
  failedAt = null;
}

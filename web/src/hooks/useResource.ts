// A read that is safe against late answers (V2 FR-C13, BLM § 7.1, BR-V2-24). When the key
// changes or the component goes away, the running request is aborted and its answer, if
// it still comes, is dropped: an old answer never overwrites a newer one (#14, RE-F02/F07/F14).
import { useCallback, useEffect, useRef, useState } from "react";
import { describeError, type DescribedError } from "../errors";

export type ResourceState = "loading" | "ready" | "error";

export interface Resource<T> {
  data: T | undefined;
  state: ResourceState;
  error?: DescribedError;
  /** Read again with the same key; the data on screen stays until the new answer comes. */
  reload(): void;
}

function isAbort(err: unknown): boolean {
  return (err as { name?: unknown } | null)?.name === "AbortError";
}

/** `key` null = not ready to read (no request; state "loading"). The key is compared by
 * value (JSON), so an inline array literal does not read again on every render. */
export function useResource<T>(
  key: readonly unknown[] | null,
  load: (signal: AbortSignal) => Promise<T>,
): Resource<T> {
  const [value, setValue] = useState<{ data?: T; state: ResourceState; error?: DescribedError }>({
    state: "loading",
  });
  const [tick, setTick] = useState(0);
  const loadRef = useRef(load);
  loadRef.current = load;
  const seq = useRef(0);
  const lastKey = useRef<string | null>(null);
  const keyText = key === null ? null : JSON.stringify(key);

  useEffect(() => {
    if (keyText === null) return;
    const id = ++seq.current;
    const controller = new AbortController();
    const newKey = keyText !== lastKey.current;
    lastKey.current = keyText;
    // a new key shows "loading" (its old data stays for the layout); a reload keeps the screen
    if (newKey) setValue((v) => ({ data: v.data, state: "loading" }));
    let request: Promise<T>;
    try {
      request = Promise.resolve(loadRef.current(controller.signal));
    } catch (err) {
      request = Promise.reject(err);
    }
    request.then(
      (data) => {
        if (seq.current === id && !controller.signal.aborted) setValue({ data, state: "ready" });
      },
      (err) => {
        if (seq.current !== id || controller.signal.aborted || isAbort(err)) return;
        setValue((v) => ({ data: v.data, state: "error", error: describeError(err) }));
      },
    );
    return () => controller.abort();
  }, [keyText, tick]);

  const reload = useCallback(() => setTick((n) => n + 1), []);
  return { data: value.data, state: value.state, error: value.error, reload };
}

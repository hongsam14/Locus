// A write that runs once at a time (V2 FR-C13, BLM § 7.2, BR-V2-24). The guard is a ref:
// React state changes only on the next render, so two calls in the same tick would both
// pass a state check (#12 web). `busy` is for the screen.
import { useCallback, useEffect, useRef, useState } from "react";
import { describeError, type DescribedError } from "../errors";

export interface Action<A extends unknown[], R> {
  /** Runs the action; `undefined` when it was already running or it failed. */
  run(...args: A): Promise<R | undefined>;
  busy: boolean;
  error?: DescribedError;
  clearError(): void;
}

export function useAction<A extends unknown[], R>(
  run: (...args: A) => Promise<R>,
  opts?: { onDone?(result: R): void },
): Action<A, R> {
  const running = useRef(false);
  const mounted = useRef(true);
  const runRef = useRef(run);
  runRef.current = run;
  const optsRef = useRef(opts);
  optsRef.current = opts;
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<DescribedError>();

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const call = useCallback(async (...args: A): Promise<R | undefined> => {
    if (running.current) return undefined;
    running.current = true;
    setBusy(true);
    setError(undefined);
    try {
      const result = await runRef.current(...args);
      if (mounted.current) optsRef.current?.onDone?.(result);
      return result;
    } catch (err) {
      if (mounted.current) setError(describeError(err));
      return undefined;
    } finally {
      running.current = false;
      if (mounted.current) setBusy(false);
    }
  }, []);

  const clearError = useCallback(() => setError(undefined), []);
  return { run: call, busy, error, clearError };
}

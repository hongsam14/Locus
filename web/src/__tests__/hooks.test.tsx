// Request helpers drop late answers and run a write once at a time (V2 BR-V2-24, TP-V2-13).
import { act, renderHook, waitFor } from "@testing-library/react";
import { useAction, useResource } from "../hooks";

type Deferred<T> = { promise: Promise<T>; resolve(v: T): void; reject(e: unknown): void };
function deferred<T>(): Deferred<T> {
  let resolve!: (v: T) => void;
  let reject!: (e: unknown) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

describe("useResource", () => {
  it("is loading, not empty, before the first answer", () => {
    const { result } = renderHook(() => useResource(["a"], () => new Promise<string>(() => {})));
    expect(result.current.state).toBe("loading");
    expect(result.current.data).toBeUndefined();
  });

  it("drops a late answer for an old key", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const signals: AbortSignal[] = [];
    const { result, rerender } = renderHook(({ k }) =>
      useResource([k], (signal) => {
        signals.push(signal);
        return k === "a" ? first.promise : second.promise;
      }), { initialProps: { k: "a" } });
    rerender({ k: "b" });
    expect(signals[0].aborted).toBe(true); // the old request was told to stop
    await act(async () => second.resolve("B"));
    expect(result.current).toMatchObject({ data: "B", state: "ready" });
    await act(async () => first.resolve("A")); // arrives late
    expect(result.current.data).toBe("B");
  });

  it("ignores an answer after unmount and aborts the request", async () => {
    const d = deferred<string>();
    let signal: AbortSignal | undefined;
    const { result, unmount } = renderHook(() =>
      useResource(["a"], (s) => {
        signal = s;
        return d.promise;
      }));
    unmount();
    expect(signal?.aborted).toBe(true);
    await act(async () => d.resolve("late"));
    expect(result.current.data).toBeUndefined();
  });

  it("keeps the data on screen while it reads again, and reports an error in words", async () => {
    let n = 0;
    const next = deferred<number>();
    const { result } = renderHook(() =>
      useResource(["x"], () => (++n === 1 ? Promise.resolve(1) : next.promise)));
    await waitFor(() => expect(result.current.data).toBe(1));
    act(() => result.current.reload());
    expect(result.current).toMatchObject({ data: 1, state: "ready" });
    await act(async () => next.reject(new TypeError("Failed to fetch")));
    expect(result.current.state).toBe("error");
    expect(result.current.data).toBe(1);
    expect(result.current.error?.code).toBe("network");
  });

  it("does not read while the key is null", () => {
    const load = vi.fn(() => Promise.resolve(1));
    renderHook(() => useResource(null, load));
    expect(load).not.toHaveBeenCalled();
  });
});

describe("useAction", () => {
  it("runs once when called twice in the same tick", async () => {
    const d = deferred<string>();
    const run = vi.fn(() => d.promise);
    const { result } = renderHook(() => useAction(run));
    let a: Promise<string | undefined> | undefined;
    let b: Promise<string | undefined> | undefined;
    act(() => {
      a = result.current.run();
      b = result.current.run(); // same tick: the state is not updated yet
    });
    expect(run).toHaveBeenCalledTimes(1);
    expect(result.current.busy).toBe(true);
    await act(async () => d.resolve("ok"));
    await expect(a).resolves.toBe("ok");
    await expect(b).resolves.toBeUndefined();
    expect(result.current.busy).toBe(false);
  });

  it("reports a failure in words and calls onDone only on success", async () => {
    const onDone = vi.fn();
    const { result } = renderHook(() =>
      useAction(async (ok: boolean) => {
        if (!ok) throw new TypeError("Failed to fetch");
        return 7;
      }, { onDone }));
    await act(async () => {
      await result.current.run(false);
    });
    expect(result.current.error?.code).toBe("network");
    expect(onDone).not.toHaveBeenCalled();
    await act(async () => {
      await result.current.run(true);
    });
    expect(onDone).toHaveBeenCalledWith(7);
    expect(result.current.error).toBeUndefined();
  });

  it("does not touch state after unmount", async () => {
    const d = deferred<number>();
    const onDone = vi.fn();
    const { result, unmount } = renderHook(() => useAction(() => d.promise, { onDone }));
    act(() => {
      void result.current.run();
    });
    unmount();
    await act(async () => d.resolve(1));
    expect(onDone).not.toHaveBeenCalled();
  });
});

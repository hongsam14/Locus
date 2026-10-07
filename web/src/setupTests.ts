import "@testing-library/jest-dom";
import { afterEach } from "vitest";
import fc from "fast-check";
import { clearToasts } from "./ui/toast";

// Property tests use the run's seed (src/test/globalSetup.ts; V2 NFR-6, PBT-08).
const seedEnv = (globalThis as unknown as { process?: { env?: Record<string, string | undefined> } })
  .process?.env?.FC_SEED;
if (seedEnv) fc.configureGlobal({ seed: Number(seedEnv) });

// jsdom has no PointerEvent: without it testing-library fires a bare Event and pointer
// coordinates (clientX/Y) are lost. A MouseEvent subclass carries them (U3 map drag).
if (typeof window !== "undefined" && typeof window.PointerEvent === "undefined") {
  class PointerEventShim extends MouseEvent {
    constructor(type: string, init?: MouseEventInit) {
      super(type, init);
    }
  }
  (window as unknown as { PointerEvent: typeof MouseEvent }).PointerEvent = PointerEventShim;
}

// The notification store is module state: no card leaks into the next test (FD review R-10).
afterEach(() => clearToasts());

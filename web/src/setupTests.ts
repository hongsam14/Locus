import "@testing-library/jest-dom";

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

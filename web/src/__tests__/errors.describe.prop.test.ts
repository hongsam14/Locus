// describeError always gives people a sentence, never the raw text (V2 BR-V2-16, TP-V2-7).
import fc from "fast-check";
import { HttpError, conflictKind, needsLlm } from "../api/http";
import { describeError } from "../errors";
import { dicts } from "../i18n";

const CODES = Object.keys(dicts.ko)
  .filter((k) => k.startsWith("error.") && k.endsWith(".title"))
  .map((k) => k.slice("error.".length, -".title".length));

// a server error: status 400..599, a known code / an unknown string / none, and a body
// that is JSON with a string or object detail, not JSON at all, or empty
const serverError = fc
  .record({
    status: fc.integer({ min: 400, max: 599 }),
    code: fc.oneof(fc.constantFrom(...CODES), fc.string({ minLength: 1, maxLength: 12 }), fc.constant(undefined)),
    detail: fc.oneof(
      fc.string({ minLength: 12, maxLength: 60 }).map((s) => `raw:${s}`),
      fc.record({ message: fc.string({ minLength: 12, maxLength: 40 }).map((s) => `raw:${s}`) }),
    ),
    shape: fc.constantFrom("json", "text", "empty"),
  })
  .map(({ status, code, detail, shape }) => {
    const body =
      shape === "json" ? JSON.stringify(code ? { detail, code } : { detail }) : shape === "text" ? `raw:${status} broke` : "";
    return new HttpError(status, "Status", body);
  });

describe("describeError (properties)", () => {
  for (const lang of ["ko", "en"] as const) {
    it(`always has a title in ${lang} and keeps the original out of it`, () => {
      fc.assert(
        fc.property(serverError, (err) => {
          const d = describeError(err, lang);
          return d.title.trim().length > 0 && !d.title.includes("raw:") && d.status === err.status;
        }),
      );
    });
  }

  it("a known code picks its own sentence, whatever the status", () => {
    fc.assert(
      fc.property(fc.constantFrom(...CODES), fc.integer({ min: 400, max: 599 }), (code, status) => {
        const d = describeError(new HttpError(status, "S", JSON.stringify({ detail: "x", code })), "ko");
        return d.title === dicts.ko[`error.${code}.title`] && d.code === code;
      }),
    );
  });
});

describe("describeError (examples)", () => {
  it("falls back to the status when the code is unknown or missing", () => {
    const d = describeError(new HttpError(409, "Conflict", '{"detail":"x","code":"brand_new"}'), "ko");
    expect(d.title).toBe(dicts.ko["error.conflict.title"]);
    expect(d.code).toBe("brand_new"); // the server's code is still reported
    expect(describeError(new HttpError(404, "Not Found", "nope"), "en").title).toBe("Not found.");
    expect(describeError(new HttpError(418, "Teapot", ""), "ko").title).toBe(dicts.ko["error.error.title"]);
  });

  it("keeps the original, clipped, for the folded detail", () => {
    const d = describeError(
      new HttpError(409, "Conflict", JSON.stringify({ detail: { message: "3 open sessions", session_ids: ["a"] }, code: "sessions_open" })),
      "ko",
    );
    expect(d.raw).toBe("409 · sessions_open · 3 open sessions");
    expect(d.action).toBe(dicts.ko["error.sessions_open.action"]);
    const long = describeError(new HttpError(500, "E", "y".repeat(500)), "ko");
    expect(long.raw!.length).toBeLessThanOrEqual(301);
  });

  it("tells a network failure from a bug", () => {
    expect(describeError(new TypeError("Failed to fetch"), "ko").code).toBe("network");
    expect(describeError(new TypeError("x is undefined"), "ko").code).toBe("unknown");
    expect(describeError("Error: 503 Service Unavailable: down", "ko").status).toBe(503);
  });

  it("reads code before the old message text", () => {
    const closed = new HttpError(409, "Conflict", '{"detail":"anything","code":"session_closed"}');
    expect(conflictKind(closed)).toBe("closed");
    expect(conflictKind(new HttpError(409, "Conflict", '{"detail":"a turn","code":"turn_running"}'))).toBe("busy");
    expect(needsLlm(new HttpError(503, "S", '{"detail":"no key","code":"llm_unavailable"}'))).toBe(true);
    expect(needsLlm(new HttpError(503, "S", '{"detail":"needs an LLM provider","code":"llm_failed"}'))).toBe(false);
  });
});

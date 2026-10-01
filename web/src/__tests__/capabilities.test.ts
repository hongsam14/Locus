// U8 (frontend-components §2.1, §3, §4): the capabilities read, the 409/503 helpers, the
// demo load's argument order against the real URL, and the seed-start timeline line.
import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { api } from "../api";
import { HttpError, needsLlm, openSessionsOf, useReplaceConfirm } from "../api/http";
import { llmOff, resetCapabilities, useCapabilities } from "../capabilities";
import { dicts, setLang, t, timelineText } from "../i18n";

beforeEach(() => {
  resetCapabilities();
  setLang("ko");
});
afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  resetCapabilities();
});

describe("useCapabilities (BR-U8-23/26)", () => {
  it("reads the server once and shares the answer", async () => {
    const read = vi.spyOn(api, "capabilities").mockResolvedValue({ llm: false, vlm: false, embedding: false });
    const a = renderHook(() => useCapabilities());
    const b = renderHook(() => useCapabilities());
    await waitFor(() => expect(a.result.current).toEqual({ llm: false, vlm: false, embedding: false }));
    await waitFor(() => expect(b.result.current?.llm).toBe(false));
    const c = renderHook(() => useCapabilities()); // mounted later: the cached answer
    expect(c.result.current?.llm).toBe(false);
    expect(read).toHaveBeenCalledTimes(1);
    expect(llmOff(c.result.current)).toBe(true);
  });

  it("a failed read is unknown: nothing is switched off", async () => {
    const read = vi.spyOn(api, "capabilities").mockRejectedValue(new Error("network"));
    const { result } = renderHook(() => useCapabilities());
    await act(async () => {});
    expect(read).toHaveBeenCalledTimes(1);
    expect(result.current).toBeNull();
    expect(llmOff(result.current)).toBe(false);
    expect(llmOff({ llm: true, vlm: false, embedding: false })).toBe(false);
  });

  it("a read that throws before it returns a promise is unknown too", async () => {
    vi.spyOn(api, "capabilities").mockImplementation(() => {
      throw new TypeError("not a function");
    });
    const { result } = renderHook(() => useCapabilities());
    await act(async () => {});
    expect(result.current).toBeNull();
  });
});

describe("the 409 and 503 helpers", () => {
  it("openSessionsOf reads the open and busy counts from the JSON detail", () => {
    const open = new HttpError(409, "Conflict", JSON.stringify({ detail: { open_sessions: 2, session_ids: ["s1", "s2"] } }));
    expect(openSessionsOf(open)).toEqual({ open: 2, busy: undefined, sessionIds: ["s1", "s2"] });
    const busy = new HttpError(409, "Conflict", JSON.stringify({ detail: { busy_sessions: 1, session_ids: ["s1"] } }));
    expect(openSessionsOf(busy)?.busy).toBe(1);
    expect(openSessionsOf(new HttpError(409, "Conflict", '{"detail":"world exists"}'))).toBeNull();
    expect(openSessionsOf(new HttpError(409, "Conflict", "not json"))).toBeNull();
    expect(openSessionsOf(new HttpError(400, "Bad Request", '{"detail":{"open_sessions":1}}'))).toBeNull();
  });

  it("needsLlm is a 503 for a missing provider, not a failed call", () => {
    const missing = new HttpError(503, "Service Unavailable",
      '{"detail":"npc dialogue needs an LLM provider (set OPENAI_API_KEY)"}');
    expect(needsLlm(missing)).toBe(true);
    const failed = new HttpError(503, "Service Unavailable",
      '{"detail":"the NPC could not answer right now; try again"}');
    expect(needsLlm(failed)).toBe(false);
    expect(needsLlm(new HttpError(503, "Service Unavailable", '{"detail":"world editor unavailable"}'))).toBe(false);
    expect(needsLlm(new HttpError(400, "Bad Request", "llm"))).toBe(false);
  });
});

describe("useReplaceConfirm (U3 review C8)", () => {
  const conflict = (detail: object) => new HttpError(409, "Conflict", JSON.stringify({ detail }));

  it("asks replace, then the sessions question; only the second answer carries confirm", () => {
    const { result } = renderHook(() => useReplaceConfirm());
    expect(result.current.open).toBe(false);
    act(() => result.current.askReplace());
    expect(result.current.ask).toBe("replace");
    let confirm = true;
    act(() => {
      confirm = result.current.answer();
    });
    expect(confirm).toBe(false);
    expect(result.current.open).toBe(false);
    let asked = false;
    act(() => {
      asked = result.current.sessionsAsked(conflict({ open_sessions: 2, session_ids: ["a", "b"] }), false);
    });
    expect(asked).toBe(true);
    expect(result.current.sessions).toBe(2);
    act(() => {
      confirm = result.current.answer();
    });
    expect(confirm).toBe(true);
  });

  it("a confirmed send, a mid-turn 409 or another error is not a question", () => {
    const { result } = renderHook(() => useReplaceConfirm());
    const open = conflict({ open_sessions: 1, session_ids: ["a"] });
    for (const [err, confirmed] of [
      [open, true],
      [conflict({ busy_sessions: 1, session_ids: ["a"] }), false],
      [new HttpError(409, "Conflict", '{"detail":"world already exists: w"}'), false],
      [new HttpError(500, "Server Error", "boom"), false],
    ] as const) {
      let asked = true;
      act(() => {
        asked = result.current.sessionsAsked(err, confirmed);
      });
      expect(asked).toBe(false);
    }
    expect(result.current.open).toBe(false);
  });
});

describe("api.loadDemo (worldId, name, options) — FD review 01 R-08", () => {
  it("puts the world id in the path and the demo name after /demo/", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => ({ ok: true }) });
    vi.stubGlobal("fetch", fetchMock);
    await api.loadDemo("my-copy", "emberleaf", { replace: true, confirm: true });
    const url = String(fetchMock.mock.calls[0][0]);
    expect(url).toContain("/api/world/worlds/my-copy/demo/emberleaf?");
    expect(url).toContain("replace=true");
    expect(url).toContain("confirm=true");
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ method: "POST" });
  });

  it("listSeeds and startSeed call the GM seed routes", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    await api.listSeeds("s1");
    await api.startSeed("s1", "seed-a");
    expect(String(fetchMock.mock.calls[0][0])).toMatch(/\/api\/gm\/sessions\/s1\/seeds$/);
    expect(String(fetchMock.mock.calls[1][0])).toMatch(/\/api\/gm\/sessions\/s1\/seeds\/seed-a\/start$/);
    expect(fetchMock.mock.calls[1][1]).toMatchObject({ method: "POST" });
  });
});

describe("i18n after U8", () => {
  it("a seed's event_created line reads as a seed start (BR-U8-18)", () => {
    const payload = { category: "plague", region_name: "Ambermeadow", seed_id: "seed-a", seed_title: "Blight in the mushroom fields" };
    expect(timelineText("event_created", payload, 2)).toBe("씨앗 사건 시작: Blight in the mushroom fields");
    setLang("en");
    expect(timelineText("event_created", payload, 2)).toBe("Seed event started: Blight in the mushroom fields");
    // a GM's own event keeps its wording
    expect(timelineText("event_created", { category: "war", region_name: "A" }, 2)).toBe("war event created · A");
  });

  it("the new keys exist in both dictionaries and the dead ones are gone (C14)", () => {
    for (const key of ["demo.play", "demo.playerName", "llm.offNotice", "llm.required", "seed.none",
      "timeline.seedStarted", "build.conceptArtsWip", "wip.badge"]) {
      expect(dicts.ko[key]).toBeTruthy();
      expect(dicts.en[key]).toBeTruthy();
    }
    for (const key of ["toolbar.loadDemo", "editor.noWorld", "home.loadDemo", "home.newWorldId",
      "deed.appraisals", "augment.start", "wiki.domains"]) {
      expect(dicts.ko[key]).toBeUndefined();
      expect(dicts.en[key]).toBeUndefined();
    }
    expect(t("llm.required")).toBe("LLM 키가 필요합니다");
    setLang("en");
    expect(t("llm.required")).toBe("An LLM key is required");
    expect(t("demo.playerName")).toBe("Traveler");
  });
});

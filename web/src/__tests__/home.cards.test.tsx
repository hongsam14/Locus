// V4 home (FD BR-V4-05/06/12, TP-V4-1/2): a demo card's state comes from the world list, the
// card's own session read and the world name map; both lists follow the display language.
// The api is real here: a fetch stand-in answers by path, so `?lang=` is seen on the wire.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { resetCapabilities } from "../capabilities";
import { configureLangs, setLang, t } from "../i18n";
import { HomePage } from "../routes/HomePage";
import type { DemoInfo, GameSession, WorldInfo } from "../types";

const EMBER: DemoInfo = {
  name: "emberleaf",
  title: "Emberleaf Isle",
  title_ko: "엠버리프 섬",
  description: "An island of three provinces.",
  start_region_id: "region-saltwake",
  has_sources: true,
};
const HELD: WorldInfo = { id: "emberleaf", name: "Emberleaf Isle", region_count: 12, open_sessions: 2 };
const MINE: WorldInfo = { id: "harrow", name: "Harrow", region_count: 4, open_sessions: 1 };
const sess = (id: string, status: "open" | "closed", created_at: string): GameSession =>
  ({ id, world_id: "emberleaf", status, turn: 0, created_at });

type Answer = unknown | { status: number; body: string };
let routes: Record<string, Answer | (() => Answer)>;
let calls: { method: string; url: string }[];

function reply(a: Answer) {
  const failed = a && typeof a === "object" && "status" in a && "body" in a ? (a as { status: number; body: string }) : null;
  if (failed) return { ok: false, status: failed.status, statusText: "Error", text: async () => failed.body };
  return { ok: true, status: 200, json: async () => a, text: async () => JSON.stringify(a) };
}

beforeEach(() => {
  calls = [];
  routes = {
    "GET /api/capabilities": { llm: true, vlm: true, embedding: true },
    "GET /api/world/demos": [EMBER],
    "GET /api/world/worlds": [HELD, MINE],
    "GET /api/play/worlds/emberleaf/sessions": [],
    "GET /api/world/worlds/emberleaf/names": { world_id: "emberleaf", lang: "ko", world: {}, regions: {}, npcs: {}, event_seeds: {} },
    "POST /api/play/worlds/emberleaf/sessions": { session: { id: "s-new" }, player: {} },
  };
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    calls.push({ method, url });
    const route = routes[`${method} ${url.split("?")[0]}`];
    if (route === undefined) return reply({ status: 404, body: '{"detail":"no route"}' });
    return reply(typeof route === "function" ? (route as () => Answer)() : route);
  }));
  resetCapabilities();
  act(() => configureLangs("ko", ["ko", "en"]));
  act(() => setLang("ko"));
});

afterEach(() => {
  vi.unstubAllGlobals();
  resetCapabilities();
  act(() => setLang("ko"));
  localStorage.clear();
});

function Where() {
  return <div data-testid="where">{useLocation().pathname}</div>;
}

function renderHome() {
  render(
    <MemoryRouter initialEntries={["/"]}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="*" element={<Where />} />
      </Routes>
    </MemoryRouter>,
  );
}

const card = () => screen.getByTestId("demo-card-emberleaf");
const primaries = (el: HTMLElement) =>
  within(el).getAllByRole("button").filter((b) => b.className.includes("bg-accent "));

describe("TP-V4-1: demo card states, no duplicate row", () => {
  it("new: not loaded — [play now] and [view in editor], no session read, no reload", async () => {
    routes["GET /api/world/worlds"] = [MINE];
    renderHome();
    await screen.findByTestId("world-row-harrow");
    expect(within(card()).getByTestId("demo-play-emberleaf")).toBeEnabled();
    expect(within(card()).getByTestId("demo-edit-emberleaf")).toBeInTheDocument();
    expect(screen.queryByTestId("demo-fresh-emberleaf")).not.toBeInTheDocument();
    expect(screen.queryByTestId("demo-meta-emberleaf")).not.toBeInTheDocument();
    expect(calls.some((c) => c.url.includes("/sessions"))).toBe(false);
    expect(primaries(card())).toHaveLength(1);
  });

  it("resume: the latest open session; [new session] starts at the start region", async () => {
    routes["GET /api/play/worlds/emberleaf/sessions"] = [
      sess("older", "open", "2026-10-01T09:00:00Z"),
      sess("closed", "closed", "2026-10-03T09:00:00Z"),
      sess("newer", "open", "2026-10-02T09:00:00Z"),
    ];
    renderHome();
    const go = await screen.findByTestId("demo-continue-emberleaf");
    expect(card()).toHaveTextContent("엠버리프 섬"); // *_ko first
    expect(screen.queryByTestId("world-row-emberleaf")).not.toBeInTheDocument(); // BR-V4-05
    expect(screen.getByTestId("world-row-harrow")).toBeInTheDocument();
    expect(within(card()).getByTestId("demo-new-session-emberleaf")).toBeInTheDocument();
    expect(within(card()).getByTestId("demo-fresh-emberleaf")).toBeInTheDocument();
    expect(screen.queryByTestId("demo-play-emberleaf")).not.toBeInTheDocument();
    expect(primaries(card())).toEqual([go]);
    fireEvent.click(go);
    expect(screen.getByTestId("where")).toHaveTextContent("/play/newer");
  });

  it("resume: [new session] asks nothing and opens play", async () => {
    routes["GET /api/play/worlds/emberleaf/sessions"] = [sess("a", "open", "2026-10-01T09:00:00Z")];
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-new-session-emberleaf"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s-new"));
    const start = calls.find((c) => c.method === "POST");
    expect(start?.url).toBe("/api/play/worlds/emberleaf/sessions");
    expect(calls.some((c) => c.url.includes("/demo/"))).toBe(false); // no load
  });

  it("loaded: only closed sessions — [play now] is the new session, and [reload the demo] is there", async () => {
    routes["GET /api/play/worlds/emberleaf/sessions"] = [sess("x", "closed", "2026-10-01T09:00:00Z")];
    renderHome();
    const play = await screen.findByTestId("demo-play-emberleaf");
    await waitFor(() => expect(play).toBeEnabled());
    expect(screen.queryByTestId("demo-continue-emberleaf")).not.toBeInTheDocument();
    expect(within(card()).getByTestId("demo-fresh-emberleaf")).toBeInTheDocument();
    expect(primaries(card())).toEqual([play]);
  });

  it("sessions unread: one line with [retry], no [continue]; a retry reads again", async () => {
    let n = 0;
    routes["GET /api/play/worlds/emberleaf/sessions"] = () =>
      ++n === 1 ? { status: 500, body: "down" } : [sess("a", "open", "2026-10-01T09:00:00Z")];
    renderHome();
    const line = await screen.findByTestId("demo-sessions-error-emberleaf");
    expect(line).toHaveTextContent(t("notice.sessionsUnreadable"));
    expect(screen.queryByTestId("demo-continue-emberleaf")).not.toBeInTheDocument();
    expect(within(card()).getByTestId("demo-play-emberleaf")).toBeEnabled();
    fireEvent.click(within(line).getByRole("button", { name: t("action.retry") }));
    expect(await screen.findByTestId("demo-continue-emberleaf")).toBeInTheDocument();
  });

  it("reading sessions: the loaded buttons are off until the answer", async () => {
    let answer: (v: unknown) => void = () => {};
    routes["GET /api/play/worlds/emberleaf/sessions"] = () => new Promise((r) => (answer = r));
    // the stand-in answers whatever the route returns; a promise resolves to the body
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      const route = routes[`${init?.method ?? "GET"} ${url.split("?")[0]}`];
      const a = typeof route === "function" ? await (route as () => Answer)() : route;
      return reply(a === undefined ? { status: 404, body: "" } : a);
    }));
    renderHome();
    const play = await screen.findByTestId("demo-play-emberleaf");
    await waitFor(() => expect(within(card()).getByRole("status")).toBeInTheDocument());
    expect(play).toBeDisabled();
    await act(async () => answer([]));
    await waitFor(() => expect(play).toBeEnabled());
  });

  it("the start region's name comes from the name map; without it the line has no start", async () => {
    routes["GET /api/world/worlds/emberleaf/names"] = {
      world_id: "emberleaf", lang: "ko", world: {}, npcs: {}, event_seeds: {},
      regions: { "region-saltwake": { name: "솔트웨이크 항구" } },
    };
    renderHome();
    const meta = await screen.findByTestId("demo-meta-emberleaf");
    await waitFor(() => expect(meta).toHaveTextContent(t("label.startAt", { name: "솔트웨이크 항구" })));
    expect(meta).toHaveTextContent(t("home.regions", { n: 12 }));
  });

  it("a name map without the start region drops the start, keeps the region count", async () => {
    renderHome();
    const meta = await screen.findByTestId("demo-meta-emberleaf");
    await waitFor(() => expect(calls.some((c) => c.url.includes("/names"))).toBe(true));
    expect(meta).toHaveTextContent(t("home.regions", { n: 12 }));
    expect(meta.textContent).not.toMatch(/시작|Starts at/);
    expect(calls.some((c) => c.url.includes("/export"))).toBe(false); // no whole-world export
  });

  it("BR-V4-06: a row's open sessions are a neutral badge", async () => {
    renderHome();
    const badge = await screen.findByTestId("world-open-harrow");
    expect(badge).toHaveTextContent(t("label.openSessions", { n: 1 }));
    expect(badge.className).not.toMatch(/danger/);
  });

  it("a row's [continue] reads the sessions when pressed and goes to the latest open one", async () => {
    routes["GET /api/play/worlds/harrow/sessions"] = [
      { ...sess("h1", "open", "2026-10-01T09:00:00Z"), world_id: "harrow" },
      { ...sess("h2", "open", "2026-10-04T09:00:00Z"), world_id: "harrow" },
    ];
    renderHome();
    const go = await screen.findByTestId("world-continue-harrow");
    expect(calls.some((c) => c.url.includes("/worlds/harrow/sessions"))).toBe(false);
    fireEvent.click(go);
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/h2"));
  });

  it("a row's failed [continue] is a line in the row", async () => {
    routes["GET /api/play/worlds/harrow/sessions"] = { status: 500, body: "down" };
    renderHome();
    fireEvent.click(await screen.findByTestId("world-continue-harrow"));
    expect(within(await screen.findByTestId("world-error-harrow")).getByRole("alert")).toBeInTheDocument();
    expect(screen.queryByTestId("where")).not.toBeInTheDocument();
  });
});

describe("TP-V4-2: both lists follow the display language (BR-V4-12)", () => {
  const listUrls = () => calls.filter((c) => /\/api\/world\/(demos|worlds)(\?|$)/.test(c.url)).map((c) => c.url);

  it("the first read carries ?lang=, and a switch reads both again", async () => {
    act(() => setLang("en"));
    renderHome();
    await screen.findByTestId("world-row-harrow");
    expect(listUrls().sort()).toEqual(["/api/world/demos?lang=en", "/api/world/worlds?lang=en"]);
    act(() => setLang("ko")); // the server default: no ?lang=
    await waitFor(() => expect(listUrls()).toHaveLength(4));
    expect(listUrls().slice(2).sort()).toEqual(["/api/world/demos", "/api/world/worlds"]);
  });

  it("a translated name and card text are shown when the server gives them", async () => {
    routes["GET /api/world/worlds"] = [HELD, { ...MINE, name_ko: "해로" }];
    renderHome();
    expect(await screen.findByTestId("world-row-harrow")).toHaveTextContent("해로");
    expect(card()).toHaveTextContent("엠버리프 섬");
  });
});

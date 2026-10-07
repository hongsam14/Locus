// U3 `/` world list (BR-U3-34, frontend-components §2.1 and §6) and the U8 demo cards.
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import { resetCapabilities } from "../capabilities";
import { t } from "../i18n";
import { HomePage } from "../routes/HomePage";
import type { DemoInfo } from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
    listDemos: vi.fn().mockResolvedValue([]),
    listWorlds: vi.fn(),
    exportWorld: vi.fn(),
    startSession: vi.fn(),
    loadDemo: vi.fn(),
    uploadBuild: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;

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

beforeEach(() => vi.clearAllMocks());

describe("HomePage", () => {
  it("lists worlds with their regions and open sessions, and edits one", async () => {
    (api.listWorlds as Mock).mockResolvedValue([
      { id: "aldermoor", name: "Aldermoor", region_count: 9, open_sessions: 2, updated_at: "2026-10-01T00:00:00Z" },
      { id: "mine", name: "Mine", region_count: 0, open_sessions: 0 },
    ]);
    renderHome();
    await waitFor(() => expect(screen.getByTestId("world-row-aldermoor")).toBeInTheDocument());
    expect(screen.getByTestId("world-row-aldermoor")).toHaveTextContent("Aldermoor");
    expect(screen.getByTestId("world-row-aldermoor")).toHaveTextContent("9");
    expect(screen.getByTestId("world-row-aldermoor")).toHaveTextContent("2");
    fireEvent.click(screen.getByTestId("world-edit-mine"));
    expect(screen.getByTestId("where")).toHaveTextContent("/editor/mine");
  });

  it("starts a player session from a row and goes to the player screen", async () => {
    (api.listWorlds as Mock).mockResolvedValue([{ id: "w", name: "W", region_count: 1, open_sessions: 0 }]);
    (api.exportWorld as Mock).mockResolvedValue({ world_id: "w", regions: [{ id: "r1", name: "Riverton", level: "town" }],
      connections: [], entities: [], knowledge: [], scopes: [] });
    (api.startSession as Mock).mockResolvedValue({ session: { id: "s9" }, player: {} });
    renderHome();
    await waitFor(() => screen.getByTestId("world-start-w"));
    fireEvent.click(screen.getByTestId("world-start-w"));
    await waitFor(() => screen.getByTestId("new-session-form"));
    expect(api.exportWorld).toHaveBeenCalledWith("w");
    fireEvent.change(screen.getByTestId("new-session-name"), { target: { value: "Ann" } });
    fireEvent.change(screen.getByTestId("new-session-region"), { target: { value: "r1" } });
    fireEvent.submit(screen.getByTestId("new-session-form").querySelector("form") as HTMLFormElement);
    await waitFor(() => expect(api.startSession).toHaveBeenCalledWith("w", { name: "Ann", start_region_id: "r1" }));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s9"));
  });

  it("with no world offers the demo and building from sources", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    renderHome();
    await waitFor(() => screen.getByTestId("home-empty"));
    fireEvent.click(screen.getByTestId("home-build"));
    expect(screen.getByTestId("build-panel")).toBeInTheDocument();
    // U8 intended change: BR-U8-1/19 — the demo is a card read from the manifest; the
    // fixed "aldermoor" button and its loadDemo("aldermoor", "aldermoor") are gone
    expect(await screen.findByTestId("demo-card-emberleaf")).toBeInTheDocument();
    expect(screen.queryByTestId("home-load-demo")).not.toBeInTheDocument();
  });
});

// --------------------------------------------------------------------------- //
// U8 demo cards (frontend-components §2.3, business-rules EX-1..3, EX-12..14)
// --------------------------------------------------------------------------- //
const EMBER: DemoInfo = {
  name: "emberleaf",
  title: "Emberleaf Isle",
  description: "An island of three provinces.",
  credits: "Story structure after a fan wiki; names are original.",
  start_region_id: "region-saltwake",
  has_sources: true,
};
const OTHER: DemoInfo = { name: "tiny", title: "Tiny", start_region_id: "r1", has_sources: false };
const OK = { world_id: "emberleaf", format_version: 1, ok: true, warnings: [] };
const held = (open = 0) => [{ id: "emberleaf", name: "Emberleaf Isle", region_count: 12, open_sessions: open }];
const conflict = (detail: object) => new HttpError(409, "Conflict", JSON.stringify({ detail }));

function confirmModal() {
  fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("action.confirm") }));
}

describe("U8 demo cards", () => {
  beforeEach(() => {
    resetCapabilities();
    (api.capabilities as Mock).mockResolvedValue({ llm: true, vlm: true, embedding: true });
    (api.startSession as Mock).mockResolvedValue({ session: { id: "s1" }, player: {} });
  });
  afterEach(() => resetCapabilities());

  it("shows a card per manifest demo, with or without worlds", async () => {
    (api.listWorlds as Mock).mockResolvedValue(held());
    (api.listDemos as Mock).mockResolvedValue([EMBER, OTHER]);
    renderHome();
    expect(await screen.findByTestId("demo-card-emberleaf")).toHaveTextContent("Emberleaf Isle");
    expect(screen.getByTestId("demo-card-tiny")).toBeInTheDocument();
    expect(screen.getByTestId("demo-credits-emberleaf")).toHaveTextContent("names are original");
    expect(screen.getByTestId("world-row-emberleaf")).toBeInTheDocument();
  });

  it("EX-1: no world — [play now] loads once and starts at the demo's start region", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockResolvedValue(OK);
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s1"));
    expect(api.loadDemo).toHaveBeenCalledTimes(1);
    // (worldId, name, options): a demo loads into its own name (FD review 01 R-08)
    // U8 intended change: U8 review #1 — a first load never replaces (replace=false)
    expect(api.loadDemo).toHaveBeenCalledWith("emberleaf", "emberleaf", { replace: false, confirm: false });
    expect(api.startSession).toHaveBeenCalledWith("emberleaf", { name: "여행자", start_region_id: "region-saltwake" });
  });

  it("EX-2: a held world with open sessions — reload asks twice, then loads with confirm", async () => {
    (api.listWorlds as Mock).mockResolvedValue(held(2));
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock)
      .mockRejectedValueOnce(conflict({ message: "open sessions", open_sessions: 2, session_ids: ["a", "b"] }))
      .mockResolvedValueOnce(OK);
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    expect(screen.getByTestId("demo-ask")).toHaveTextContent("Emberleaf Isle");
    fireEvent.click(screen.getByTestId("demo-reload"));
    expect(screen.getByTestId("demo-confirm")).toHaveTextContent(t("demo.replaceConfirm", { title: "Emberleaf Isle" }));
    confirmModal();
    await waitFor(() => expect(screen.getByTestId("demo-confirm")).toHaveTextContent(t("demo.closeSessions", { n: 2 })));
    expect(api.startSession).not.toHaveBeenCalled();
    confirmModal();
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s1"));
    expect((api.loadDemo as Mock).mock.calls.map((c) => c[2])).toEqual([
      { replace: true, confirm: false },
      { replace: true, confirm: true },
    ]);
  });

  it("a held world — [play this world] starts a session without loading", async () => {
    (api.listWorlds as Mock).mockResolvedValue(held());
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    fireEvent.click(screen.getByTestId("demo-keep"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s1"));
    expect(api.loadDemo).not.toHaveBeenCalled();
  });

  it("EX-3: a held world — [view in editor] opens it with no load", async () => {
    (api.listWorlds as Mock).mockResolvedValue(held(1));
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-edit-emberleaf"));
    expect(screen.getByTestId("where")).toHaveTextContent("/editor/emberleaf");
    expect(api.loadDemo).not.toHaveBeenCalled();
  });

  it("no world — [view in editor] loads first, then opens the editor", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockResolvedValue(OK);
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-edit-emberleaf"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/editor/emberleaf"));
    // U8 intended change: U8 review #1 — a first load never replaces (replace=false)
    expect(api.loadDemo).toHaveBeenCalledWith("emberleaf", "emberleaf", { replace: false, confirm: false });
    expect(api.startSession).not.toHaveBeenCalled();
  });

  // U8 intended change: U8 review #1 — "no world + open sessions" cannot happen (a first
  // load is replace=false, which skips the session gate); the real case is a world the
  // list did not show yet, below
  it("U8 review #1: before the list arrives, a world already there is asked about, not replaced", async () => {
    let answer: (v: unknown) => void = () => {};
    (api.listWorlds as Mock).mockImplementation(() => new Promise((r) => (answer = r)));
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"world already exists: emberleaf"}'));
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    expect(await screen.findByTestId("demo-ask")).toHaveTextContent("Emberleaf Isle");
    expect(api.loadDemo).toHaveBeenCalledTimes(1);
    expect((api.loadDemo as Mock).mock.calls[0][2]).toEqual({ replace: false, confirm: false });
    expect(api.startSession).not.toHaveBeenCalled();
    fireEvent.click(screen.getByTestId("demo-keep")); // play the world as it is: no load
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/play/s1"));
    expect(api.loadDemo).toHaveBeenCalledTimes(1);
    answer([]);
  });

  it("U8 review #1: with the list failed, [view in editor] opens a world that is there", async () => {
    (api.listWorlds as Mock).mockRejectedValue(new HttpError(500, "Server Error", "list failed"));
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockRejectedValue(new HttpError(409, "Conflict", '{"detail":"world already exists: emberleaf"}'));
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-edit-emberleaf"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/editor/emberleaf"));
    expect(api.loadDemo).toHaveBeenCalledTimes(1);
    expect((api.loadDemo as Mock).mock.calls[0][2]).toEqual({ replace: false, confirm: false });
  });

  it("EX-12: a load with ok=false shows its errors and backup and starts no session", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockResolvedValue({
      ...OK,
      ok: false,
      backup_path: "/data/backups/emberleaf.json",
      warnings: [
        { severity: "error", message: "commit failed: graph down" },
        { severity: "warning", message: "a soft note" },
      ],
    });
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    const card = await screen.findByTestId("demo-error-emberleaf");
    expect(card).toHaveTextContent(t("demo.loadFailed"));
    expect(card).toHaveTextContent("commit failed: graph down");
    expect(card).not.toHaveTextContent("a soft note");
    expect(card).toHaveTextContent("/data/backups/emberleaf.json");
    expect(api.startSession).not.toHaveBeenCalled();
  });

  it("EX-13: a held world without its start region offers a fresh load", async () => {
    (api.listWorlds as Mock).mockResolvedValue(held());
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.startSession as Mock).mockRejectedValue(new HttpError(404, "Not Found", "region not found"));
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    fireEvent.click(screen.getByTestId("demo-keep"));
    const missing = await screen.findByTestId("demo-start-missing");
    expect(missing).toHaveTextContent(t("demo.startMissing"));
    fireEvent.click(within(missing).getByRole("button", { name: t("demo.reload") }));
    expect(screen.getByTestId("demo-confirm")).toHaveTextContent(t("demo.replaceConfirm", { title: "Emberleaf Isle" }));
  });

  it("EX-14: a session mid-turn answers busy with no confirm", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    (api.loadDemo as Mock).mockRejectedValue(conflict({ message: "mid-turn", busy_sessions: 1, session_ids: ["s1"] }));
    renderHome();
    fireEvent.click(await screen.findByTestId("demo-play-emberleaf"));
    expect(await screen.findByTestId("demo-error-emberleaf")).toHaveTextContent(t("demo.busy"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(api.startSession).not.toHaveBeenCalled();
  });

  it("EX-8: with no LLM the notice shows and [play now] stays on", async () => {
    (api.capabilities as Mock).mockResolvedValue({ llm: false, vlm: false, embedding: false });
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    renderHome();
    // V2 intended change: one sentence for every screen (BR-V2-20)
    expect(await screen.findByTestId("llm-notice")).toHaveTextContent(t("notice.llmOff"));
    expect(screen.getByTestId("demo-play-emberleaf")).toBeEnabled();
  });

  it("an unknown answer (a failed read) shows no notice (BR-U8-26)", async () => {
    (api.capabilities as Mock).mockRejectedValue(new Error("down"));
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockResolvedValue([EMBER]);
    renderHome();
    await screen.findByTestId("demo-card-emberleaf");
    expect(screen.queryByTestId("llm-notice")).not.toBeInTheDocument();
  });

  it("a failed demo list is one line on the screen", async () => {
    (api.listWorlds as Mock).mockResolvedValue([]);
    (api.listDemos as Mock).mockRejectedValue(new HttpError(503, "Service Unavailable", "demo unavailable"));
    renderHome();
    expect(await screen.findByTestId("demo-list-error")).toHaveTextContent("503");
  });
});

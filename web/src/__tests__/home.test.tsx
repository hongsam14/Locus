// U3 `/` world list (BR-U3-34, frontend-components §2.1 and §6).
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HomePage } from "../routes/HomePage";

vi.mock("../api", () => ({
  api: {
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
    (api.loadDemo as Mock).mockResolvedValue({ ok: true });
    renderHome();
    await waitFor(() => screen.getByTestId("home-empty"));
    fireEvent.click(screen.getByTestId("home-build"));
    expect(screen.getByTestId("build-panel")).toBeInTheDocument();
    fireEvent.click(screen.getByTestId("home-load-demo"));
    await waitFor(() => expect(api.loadDemo).toHaveBeenCalledWith("aldermoor", "aldermoor"));
    await waitFor(() => expect(screen.getByTestId("where")).toHaveTextContent("/editor/aldermoor"));
  });
});

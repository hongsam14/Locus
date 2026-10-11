// V8 new editor parts (code plan Step 4, TP-V8-2/5/7/13/15, BR-V8-08/09/12/13/27/28/32/34): the
// one head with its file menu and play start, the keyboard region picker, the map tools and
// legend, the connection form's single weight control, and the danger zone.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { HttpError } from "../api/http";
import { EditorHeader } from "../features/editor/EditorHeader";
import { MapLegend } from "../features/editor/MapLegend";
import { MapTools } from "../features/editor/MapTools";
import { NewConnectionDialog } from "../features/editor/NewConnectionDialog";
import { DangerZone, RegionPicker } from "../features/editor/RegionTab";
import { enumLabel, numberWithMeaning } from "../format";
import { t } from "../i18n";
import type { ConnectionEdge, Region, WorldExport } from "../types";

vi.mock("../api", () => ({
  api: {
    getWorldFile: vi.fn(),
    importWorldFile: vi.fn(),
    startSession: vi.fn(),
  },
}));
import { api } from "../api";

type Mock = ReturnType<typeof vi.fn>;
const region = (id: string, level = "town", name = id.toUpperCase()): Region => ({ id, name, level });
const world = (...regions: Region[]): WorldExport =>
  ({ world_id: "w", regions, connections: [], entities: [], knowledge: [], scopes: [] }) as unknown as WorldExport;

beforeEach(() => vi.resetAllMocks());

function head(props: Partial<Parameters<typeof EditorHeader>[0]> = {}) {
  const onLoaded = vi.fn();
  const onBuild = vi.fn();
  render(
    <MemoryRouter initialEntries={["/editor/w"]}>
      <Routes>
        <Route path="/editor/:worldId" element={
          <EditorHeader worldId="w" world={world(region("a"))} name="Emerald Isle" openSessions={0}
            onLoaded={onLoaded} onBuild={onBuild} {...props} />
        } />
        <Route path="/play/:sid" element={<div data-testid="play-page" />} />
      </Routes>
    </MemoryRouter>,
  );
  return { onLoaded, onBuild };
}

describe("EditorHeader (TP-V8-2, BR-V8-03/28/34)", () => {
  it("the name is the title, the id is not repeated; with no name the id is the title once", () => {
    head();
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Emerald Isle");
    expect(screen.getByTestId("editor-header").textContent).not.toContain("w ·");
    expect(screen.getByTestId("graph-status")).toHaveTextContent(t("label.worldCounts", { regions: 1, connections: 0, knowledge: 0 }));
  });

  it("an id-only world shows the id once", () => {
    head({ worldId: "emberleaf", name: null });
    const text = screen.getByTestId("editor-header").textContent ?? "";
    expect(text.split("emberleaf").length - 1).toBe(1);
  });

  it("open sessions are said in words, and hidden at none", () => {
    head({ openSessions: 2 });
    expect(screen.getByTestId("open-sessions")).toHaveTextContent(t("notice.openSessions", { n: 2 }));
  });

  it("[파일 ▾] opens a row; Esc closes it and focus returns; the file input stays mounted", async () => {
    head();
    const toggle = screen.getByTestId("file-menu");
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.getByTestId("file-input")).toBeInTheDocument(); // outside the row
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    const save = screen.getByTestId("file-save");
    save.focus();
    fireEvent.keyDown(save, { key: "Escape" });
    expect(screen.queryByTestId("file-row")).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });

  it("the opened row wraps under the whole head line, not between [파일 ▾] and [플레이] (V8 captures)", () => {
    head();
    fireEvent.click(screen.getByTestId("file-menu"));
    const line = screen.getByTestId("world-name").parentElement as HTMLElement;
    const row = screen.getByTestId("file-row");
    // a flex item of the head line itself: its parent is the line, or a `contents` box in it
    const box = row.parentElement as HTMLElement;
    expect(box === line || (box.classList.contains("contents") && box.parentElement === line)).toBe(true);
    expect(row).toHaveClass("order-last", "basis-full");
    // the play button is on the same line, before the row in the line's order
    expect(line).toContainElement(screen.getByTestId("play-this-world"));
    expect(screen.getByTestId("play-this-world").closest(".order-last")).toBeNull();
  });

  it("a press outside closes the row; an action starting closes it too", () => {
    const { onBuild } = head();
    fireEvent.click(screen.getByTestId("file-menu"));
    fireEvent.pointerDown(document.body);
    expect(screen.queryByTestId("file-row")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("file-menu"));
    fireEvent.click(screen.getByTestId("file-build"));
    expect(onBuild).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("file-row")).not.toBeInTheDocument();
  });

  it("a refused load says its stage in words, under the head, after the row closed", async () => {
    (api.importWorldFile as Mock).mockResolvedValueOnce({
      ok: false, replaced: false, closed_session_ids: [], counts: {}, world_id: "w", format_version: 1, source_world_id: "w",
      remapped: false, forced: false, warnings: [{ stage: "duplicate-ids", severity: "error", message: "duplicate ids in the World File: a" }],
    });
    const { onLoaded } = head();
    const file = new File(['{"format_version":1}'], "w.world.json", { type: "application/json" });
    fireEvent.change(screen.getByTestId("file-input"), { target: { files: [file] } });
    await screen.findByTestId("file-confirm");
    fireEvent.click(screen.getByRole("button", { name: t("action.confirm") }));
    const err = await screen.findByTestId("file-error");
    expect(err).toHaveTextContent(t("label.stage.duplicate-ids"));
    expect(onLoaded).not.toHaveBeenCalled();
  });
});

describe("PlayThisWorld (TP-V8-13, BR-V8-27)", () => {
  it("the player form starts a session with a name and a start region, then the play screen", async () => {
    (api.startSession as Mock).mockResolvedValueOnce({ session: { id: "s9" } });
    head();
    fireEvent.click(screen.getByTestId("play-this-world"));
    await screen.findByTestId("new-session-form");
    fireEvent.change(screen.getByTestId("new-session-name"), { target: { value: "Ann" } });
    fireEvent.change(screen.getByTestId("new-session-region"), { target: { value: "a" } });
    fireEvent.submit(screen.getByTestId("new-session-form").querySelector("form") as HTMLFormElement);
    await screen.findByTestId("play-page");
    expect(api.startSession).toHaveBeenCalledWith("w", { name: "Ann", start_region_id: "a" });
  });

  it("a failed start is said inside the form", async () => {
    (api.startSession as Mock).mockRejectedValueOnce(new HttpError(500, "Error", "boom"));
    head();
    fireEvent.click(screen.getByTestId("play-this-world"));
    await screen.findByTestId("new-session-form");
    fireEvent.change(screen.getByTestId("new-session-name"), { target: { value: "Ann" } });
    fireEvent.change(screen.getByTestId("new-session-region"), { target: { value: "a" } });
    fireEvent.submit(screen.getByTestId("new-session-form").querySelector("form") as HTMLFormElement);
    expect(await screen.findByTestId("new-session-error")).toBeInTheDocument();
  });

  it("is off without a region", () => {
    head({ world: world() });
    expect(screen.getByTestId("play-this-world")).toBeDisabled();
  });
});

describe("RegionPicker and DangerZone (TP-V8-5, BR-V8-08/12)", () => {
  it("any region by keyboard, grouped by level", () => {
    const onSelect = vi.fn();
    render(<RegionPicker regions={[region("t", "town", "Mill"), region("p", "province", "North")]} selected={null} onSelect={onSelect} />);
    const select = screen.getByTestId("region-picker") as HTMLSelectElement;
    const groups = [...select.querySelectorAll("optgroup")].map((g) => g.label);
    expect(groups).toEqual([enumLabel("regionLevel", "province"), enumLabel("regionLevel", "town")]);
    fireEvent.change(select, { target: { value: "t" } });
    expect(onSelect).toHaveBeenCalledWith("t");
  });

  it("the delete sits in its own named place", () => {
    const onDelete = vi.fn();
    render(<DangerZone onDelete={onDelete} />);
    const zone = screen.getByRole("region", { name: t("label.dangerZone") });
    fireEvent.click(within(zone).getByTestId("region-delete"));
    expect(onDelete).toHaveBeenCalledTimes(1);
  });
});

describe("MapTools and MapLegend (TP-V8-15, BR-V8-09/32)", () => {
  it("one tab stop, arrows move between tools, the chosen one is pressed", () => {
    render(<MapTools tool="select" disabled={false} hint="h" onTool={vi.fn()} />);
    const bar = screen.getByRole("toolbar", { name: t("label.mapTools") });
    const tools = within(bar).getAllByRole("button");
    expect(tools.map((b) => b.tabIndex)).toEqual([0, -1, -1]);
    expect(tools[0]).toHaveAttribute("aria-pressed", "true");
    tools[0].focus();
    fireEvent.keyDown(tools[0], { key: "ArrowRight" });
    expect(tools[1]).toHaveFocus();
    fireEvent.keyDown(tools[1], { key: "End" });
    expect(tools[2]).toHaveFocus();
    fireEvent.keyDown(tools[2], { key: "ArrowRight" });
    expect(tools[0]).toHaveFocus();
  });

  it("the legend says the shapes and every connection kind in words", () => {
    render(<MapLegend />);
    const legend = screen.getByTestId("map-legend");
    for (const level of ["town", "district", "terrain"]) expect(legend).toHaveTextContent(enumLabel("regionLevel", level));
    for (const kind of ["adjacent", "route", "river", "blocked"]) expect(legend).toHaveTextContent(enumLabel("connectionKind", kind));
  });
});

describe("NewConnectionDialog (TP-V8-7 form side, BR-V8-13, R-12)", () => {
  const stored: ConnectionEdge = { source_region_id: "a", target_region_id: "b", kind: "river", weight: 0.35 } as ConnectionEdge;
  const existing = (kind: string) => (kind === "river" ? stored : undefined);

  it("starts at 0.6, says the number and its meaning, and saves only on [저장]", () => {
    const onSubmit = vi.fn();
    render(<NewConnectionDialog title="A – B" busy={false} existing={existing} onSubmit={onSubmit} onCancel={vi.fn()} />);
    expect(screen.getByTestId("connection-weight-label")).toHaveTextContent(numberWithMeaning("weight", 0.6));
    const slider = screen.getByTestId("connection-weight");
    fireEvent.change(slider, { target: { value: "0.8" } });
    fireEvent.pointerUp(slider);
    expect(onSubmit).not.toHaveBeenCalled(); // moving the slider writes nothing
    fireEvent.click(screen.getByTestId("connection-save"));
    expect(onSubmit).toHaveBeenCalledWith("route", 0.8);
  });

  it("another kind starts from that kind's stored weight; the stored line is in words", async () => {
    const onSubmit = vi.fn();
    render(<NewConnectionDialog title="A – B" busy={false} existing={existing} onSubmit={onSubmit} onCancel={vi.fn()} />);
    act(() => {
      fireEvent.change(screen.getByTestId("connection-kind"), { target: { value: "river" } });
    });
    await waitFor(() => expect(screen.getByTestId("connection-exists")).toBeInTheDocument());
    expect(screen.getByTestId("connection-exists")).toHaveTextContent(numberWithMeaning("weight", 0.35));
    expect(screen.getByTestId("connection-exists")).toHaveTextContent(enumLabel("connectionKind", "river"));
    fireEvent.click(screen.getByTestId("connection-save"));
    expect(onSubmit).toHaveBeenCalledWith("river", 0.35); // untouched: the stored weight
  });
});

// U6 deeds & spread on screen (Step 8.3; frontend-components §6): the declaration box,
// the narration card, the deed badge, the player log filter and the GM DeedPanel.
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { HttpError } from "../api/http";
import type { Mock } from "vitest";
import { DeedPanel } from "../features/gm/DeedPanel";
import { ActionBar } from "../features/play/ActionBar";
import { PlayLog } from "../features/play/PlayLog";
import { RegionScene } from "../features/play/RegionScene";
import { t } from "../i18n";
import { PlayPage } from "../routes/PlayPage";
import type { DeedViewOut, RegionView, SessionRumor, TurnRun } from "../types";

vi.mock("../api", () => ({
  api: {
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
    listSeeds: vi.fn().mockResolvedValue([]),
    startSeed: vi.fn(),
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    listNpcs: vi.fn(),
    listDeeds: vi.fn(),
    voidDeed: vi.fn(),
  },
}));

import { api } from "../api";

function rumor(over: Partial<SessionRumor> = {}): SessionRumor {
  return {
    id: "ru1", session_id: "s1", region_id: "a", distorted_from_id: "d1",
    distorted_from_kind: "deed", statement: "The traveler caught a thief!",
    distortion_degree: 0.3, support: 0.4, confidence: 0.7, promoted: false,
    origin_kind: "deed", origin_deed_id: "d1", active: true, ...over,
  };
}

function view(over: Partial<RegionView> = {}): RegionView {
  return {
    session_id: "s1", turn: 0,
    player: { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 },
    region_id: "a", region_name: "Riverton", level: "town", description: "",
    level_path: ["Riverton"], npcs: [], facts: [], hearsay: [], rumors: [rumor()], moves: [],
    turn_running: false, llm_available: true, declare_max_chars: 10, ...over,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("ActionBar declaration box (US-4.5)", () => {
  it("is off for empty, over-limit and busy, and sends the trimmed text", async () => {
    const onDeclare = vi.fn().mockResolvedValue(true);
    const { rerender } = render(
      <ActionBar running={null} disabled={false} onWait={vi.fn()} onDeclare={onDeclare} maxChars={10} />,
    );
    const input = screen.getByTestId("declare-input");
    expect(screen.getByTestId("declare-btn")).toBeDisabled();
    fireEvent.change(input, { target: { value: "x".repeat(11) } });
    expect(screen.getByTestId("declare-btn")).toBeDisabled();
    expect(screen.getByTestId("declare-count")).toHaveTextContent(t("play.chars", { n: 11, max: 10 }));
    fireEvent.change(input, { target: { value: "  sing  " } });
    rerender(
      <ActionBar running={null} disabled={true} onWait={vi.fn()} onDeclare={onDeclare} maxChars={10} />,
    );
    expect(screen.getByTestId("declare-btn")).toBeDisabled();
    rerender(
      <ActionBar running={null} disabled={false} onWait={vi.fn()} onDeclare={onDeclare} maxChars={10} />,
    );
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() => expect(onDeclare).toHaveBeenCalledWith("sing"));
    expect(input).toHaveValue("");
  });

  it("puts the text back when the server refuses", async () => {
    const onDeclare = vi.fn().mockResolvedValue(false);
    render(<ActionBar running={null} disabled={false} onWait={vi.fn()} onDeclare={onDeclare} />);
    fireEvent.change(screen.getByTestId("declare-input"), { target: { value: "dance" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() => expect(screen.getByTestId("declare-input")).toHaveValue("dance"));
  });
});

describe("PlayPage with declarations", () => {
  function renderPlay() {
    return render(
      <MemoryRouter initialEntries={["/play/s1"]}>
        <Routes>
          <Route path="/play/:sessionId?" element={<PlayPage pollMs={5} />} />
        </Routes>
      </MemoryRouter>,
    );
  }

  beforeEach(() => {
    (api.getSession as Mock).mockResolvedValue({ id: "s1", world_id: "w", status: "open", turn: 0 });
    (api.getRegion as Mock).mockResolvedValue(view());
    (api.getLog as Mock).mockResolvedValue([]);
    (api.listTurnRuns as Mock).mockResolvedValue([]);
    (api.listNpcs as Mock).mockResolvedValue([]);
  });

  it("declares with act and shows the narration when the run is done", async () => {
    const running: TurnRun = { id: "r1", session_id: "s1", action: { type: "declare", text: "sing" },
      cost_turns: 1, status: "running", started_turn: 0 };
    (api.act as Mock).mockResolvedValue(running);
    (api.getTurnRun as Mock).mockResolvedValue({
      ...running, status: "done",
      result: { session: { id: "s1", world_id: "w", status: "open", turn: 1 }, player: null,
        turns: [], changes: [], narration: [], llm_calls: 1, budget_exhausted: false,
        llm_failed: false, llm_available: true,
        declaration: { text: "광장이 술렁인다.", record: "Ari sang.", lang: "ko", llm_calls: 1 } },
    });
    renderPlay();
    fireEvent.change(await screen.findByTestId("declare-input"), { target: { value: "sing" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() => expect(api.act).toHaveBeenCalledWith("s1", { type: "declare", text: "sing" }));
    expect(await screen.findByTestId("narration-card")).toHaveTextContent("광장이 술렁인다.");
  });

  it("a 400 keeps the text and shows the error; a 409 keeps the text and notifies", async () => {
    (api.act as Mock).mockRejectedValueOnce(new Error("400 Bad Request: empty declaration"));
    renderPlay();
    fireEvent.change(await screen.findByTestId("declare-input"), { target: { value: "x" } });
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() => expect(screen.getByTestId("play-error")).toHaveTextContent("400"));
    expect(screen.getByTestId("declare-input")).toHaveValue("x");
    (api.act as Mock).mockRejectedValueOnce(new HttpError(409, "Conflict", "turn in progress"));
    fireEvent.click(screen.getByTestId("declare-btn"));
    await waitFor(() =>
      expect(screen.getByTestId("notification-center")).toHaveTextContent(t("play.turnInProgress")),
    );
    expect(screen.getByTestId("declare-input")).toHaveValue("x");
  });

  it("uses the server's declaration limit", async () => {
    renderPlay();
    fireEvent.change(await screen.findByTestId("declare-input"), { target: { value: "x".repeat(11) } });
    expect(screen.getByTestId("declare-btn")).toBeDisabled(); // limit 10 from the region view
  });
});

describe("deed badge and the player log (US-6.5, frontend §2.4/§2.5)", () => {
  it("a deed rumor carries the deed badge, a canonical one does not", () => {
    render(<RegionScene view={view({ rumors: [rumor(), rumor({ id: "ru2", origin_kind: "canonical" })] })} />);
    expect(screen.getByTestId("deed-badge-ru1")).toHaveTextContent(t("badge.deed"));
    expect(screen.queryByTestId("deed-badge-ru2")).not.toBeInTheDocument();
  });

  it("the player log shows what the server kept, in the player's words", () => {
    // U7 intended change: BR-U7-12 — the server filters (where the player was), so the
    // screen draws every line it gets; a deed rumor born here reads as talk about you
    const entry = (id: string, kind: string) => ({
      id, session_id: "s1", turn: 1, kind, summary: kind,
      payload: { region_name: "A", from_region_name: "A", npc_name: "Mara" },
    });
    render(
      <PlayLog entries={[entry("1", "action_declared"), entry("3", "deed_seeded"),
        entry("4", "rumor_spread")]} />,
    );
    expect(screen.getByTestId("log-action_declared")).toBeInTheDocument();
    expect(screen.getByTestId("log-deed_seeded")).toHaveTextContent(t("log.deed_seeded", { region: "A" }));
    expect(screen.getByTestId("log-rumor_spread")).toHaveTextContent(t("log.rumor_spread", { region: "A" }));
  });
});

describe("DeedPanel (US-5.6)", () => {
  const deedView = (over: Partial<DeedViewOut["deed"]> = {}): DeedViewOut => ({
    deed: { id: "d1", session_id: "s1", player_id: "p1", region_id: "a", turn: 2,
      kind: "declared_action", text: "Ari caught a thief.", declaration: "도둑을 잡는다",
      witnessed_npc_ids: ["n1"], voided: false, region_name: "Riverton", witness_names: ["Mara"],
      ...over },
    appraisals: [{ id: "ap1", deed_id: "d1", npc_id: "n1", noteworthy: true, salience: 0.9,
      slant: "admiring", retelling: "The traveler caught a thief!", turn: 2, npc_name: "Mara" }],
    rumors: [rumor(), rumor({ id: "ru2", region_id: "b", active: false })],
    reached_region_ids: ["a", "b"], reached_region_names: ["Riverton", "Hollow"],
  });

  it("shows the appraisals and where the rumors reached", async () => {
    (api.listDeeds as Mock).mockResolvedValue([deedView()]);
    render(<DeedPanel sessionId="s1" closed={false} />);
    expect(await screen.findByTestId("deed-appraisals-d1")).toHaveTextContent("Mara");
    expect(screen.getByTestId("deed-appraisals-d1")).toHaveTextContent("admiring");
    expect(screen.getByTestId("deed-reached-d1")).toHaveTextContent("Riverton · Hollow (1/2)");
  });

  it("voids after the confirmation and tells the page", async () => {
    (api.listDeeds as Mock).mockResolvedValue([deedView()]);
    (api.voidDeed as Mock).mockResolvedValue({ deed_id: "d1", deactivated_rumor_ids: ["ru1"] });
    const onChanged = vi.fn();
    render(<DeedPanel sessionId="s1" closed={false} onChanged={onChanged} />);
    fireEvent.click(await screen.findByTestId("void-d1"));
    expect(screen.getByTestId("void-confirm")).toHaveTextContent(t("deed.voidConfirm", { n: 1 }));
    // The two dialog buttons never share a name (review U6 #2: both read "취소" in ko).
    const dialog = within(screen.getByRole("dialog"));
    expect(dialog.getAllByRole("button").map((b) => b.textContent)).toEqual([
      t("action.cancel"),
      t("deed.voidConfirmBtn"),
    ]);
    expect(t("deed.voidConfirmBtn")).not.toBe(t("action.cancel"));
    await act(async () => fireEvent.click(dialog.getByRole("button", { name: t("deed.voidConfirmBtn") })));
    await waitFor(() => expect(api.voidDeed).toHaveBeenCalledWith("s1", "d1"));
    expect(onChanged).toHaveBeenCalled();
  });

  it("a void during a turn shows a notice; a voided deed has no void button", async () => {
    (api.listDeeds as Mock).mockResolvedValue([deedView(), { ...deedView({ id: "d2", voided: true }) }]);
    (api.voidDeed as Mock).mockRejectedValue(new HttpError(409, "Conflict", "turn in progress"));
    render(<DeedPanel sessionId="s1" closed={false} />);
    expect(await screen.findByTestId("deed-voided-d2")).toBeInTheDocument();
    expect(screen.queryByTestId("void-d2")).not.toBeInTheDocument();
    fireEvent.click(screen.getByTestId("void-d1"));
    await act(async () =>
      fireEvent.click(within(screen.getByRole("dialog")).getByRole("button", { name: t("deed.voidConfirmBtn") })),
    );
    expect(await screen.findByTestId("deed-notice")).toHaveTextContent(t("play.turnInProgress"));
  });
});

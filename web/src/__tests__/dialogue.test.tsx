// U5 NPC dialogue + display language (Step 7.3): DialoguePanel open / send / failed
// send rolls back / no LLM / end talk; NpcList; ko and en have the same keys; the
// toggle switches labels, sends ?lang=en on translated reads (not the timeline) and
// re-reads the region.
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Mock } from "vitest";
import { gmApi } from "../api/gm";
import { withLang } from "../api/http";
import { knowledgeApi } from "../api/knowledge";
import { playApi } from "../api/play";
import { DialoguePanel } from "../features/play/DialoguePanel";
import { NpcList } from "../features/play/NpcList";
import { dicts, lang, setLang, t, timelineText } from "../i18n";
import { PlayPage } from "../routes/PlayPage";
import type { Conversation, Message, NPC, RegionView } from "../types";

// Components import the merged `api` (index); the per-boundary modules above stay
// real so their URLs can be checked against a stubbed fetch.
vi.mock("../api", () => ({
  api: {
    getSession: vi.fn(),
    getRegion: vi.fn(),
    getLog: vi.fn(),
    act: vi.fn(),
    getTurnRun: vi.fn(),
    listTurnRuns: vi.fn(),
    listNpcs: vi.fn(),
    startDialogue: vi.fn(),
    say: vi.fn(),
    dialogueHistory: vi.fn(),
  },
}));

import { api } from "../api";

const MARA: NPC = {
  id: "n1",
  world_id: "w",
  name: "Mara",
  role: "innkeeper",
  description: "Keeps the river inn.",
  home_region_id: "a",
  traits: [],
  provenance: { source: "input" },
};

function msg(role: "player" | "npc", text: string, id = `${role}-${text}`): Message {
  return { id, conversation_id: "c1", role, text, lang: "ko", turn: 0 };
}

function conversation(messages: Message[] = []): Conversation {
  return { id: "c1", session_id: "s1", npc_id: "n1", started_turn: 0, messages };
}

function view(over: Partial<RegionView> = {}): RegionView {
  return {
    session_id: "s1",
    turn: 0,
    player: { id: "p1", session_id: "s1", name: "Ari", region_id: "a", turns_spent: 0 },
    region_id: "a",
    region_name: "Riverton",
    level: "town",
    description: "",
    level_path: ["Aldermoor", "Riverton"],
    npcs: [MARA],
    facts: [],
    hearsay: [
      { knowledge_id: "k9", statement: "Wolves in the pass.", scope_type: "hearsay", is_hearsay: true, confidence: 0.4, path_decay: 0.6 },
    ],
    rumors: [],
    moves: [],
    turn_running: false,
    llm_available: true,
    ...over,
  };
}

function renderPanel(over: Partial<Parameters<typeof DialoguePanel>[0]> = {}) {
  const props = {
    sessionId: "s1",
    npc: MARA,
    llmAvailable: true,
    busy: false,
    onClose: vi.fn(),
    onEndTalk: vi.fn(),
    onSpoke: vi.fn(),
    ...over,
  };
  render(<DialoguePanel {...props} />);
  return props;
}

function typeAndSend(text: string) {
  fireEvent.change(screen.getByTestId("dialogue-input"), { target: { value: text } });
  fireEvent.click(screen.getByTestId("dialogue-send-btn"));
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  act(() => setLang("ko"));
  localStorage.clear();
  vi.unstubAllGlobals();
});

describe("i18n dictionaries (FD-U5 frontend §2.2)", () => {
  it("ko and en carry the same key set", () => {
    expect(Object.keys(dicts.en).sort()).toEqual(Object.keys(dicts.ko).sort());
    for (const v of Object.values(dicts.en)) expect(v.trim()).not.toBe("");
  });

  it("t() falls back to Korean, then to the key", () => {
    setLang("en");
    expect(t("play.npcs")).toBe("People here");
    expect(t("no.such.key")).toBe("no.such.key");
    const saved = dicts.en["play.facts"];
    delete dicts.en["play.facts"];
    try {
      expect(t("play.facts")).toBe(dicts.ko["play.facts"]);
    } finally {
      dicts.en["play.facts"] = saved;
    }
  });

  it("setLang remembers the language and the npc_talked timeline has both languages", () => {
    const payload = { npc_name: "Mara", region_name: "Riverton" };
    expect(timelineText("npc_talked", payload, 3)).toBe("대화: Mara · Riverton");
    setLang("en");
    expect(lang()).toBe("en");
    expect(localStorage.getItem("locus.lang")).toBe("en");
    expect(document.documentElement.lang).toBe("en");
    expect(timelineText("npc_talked", payload, 3)).toBe("spoke with Mara · Riverton");
  });
});

describe("?lang= on translated reads (FD-U5 Q1=A)", () => {
  function stubFetch() {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    return () => fetchMock.mock.calls.map((c) => String(c[0]));
  }

  it("withLang appends with ? or &", () => {
    setLang("en");
    expect(withLang("/x")).toBe("/x?lang=en");
    expect(withLang("/x?a=1")).toBe("/x?a=1&lang=en");
  });

  it("the five reads and say carry the language; the timeline and writes do not", async () => {
    const urls = stubFetch();
    setLang("en");
    await playApi.getRegion("s1");
    await playApi.sessionKnowledge("s1", "r1");
    await knowledgeApi.regionKnowledge("w", "r1");
    await gmApi.listRumors("s1", "r1");
    await gmApi.listEvents("s1", "active");
    await playApi.say("s1", "n1", "hello");
    await gmApi.getTimeline("s1");
    await playApi.getLog("s1");
    await playApi.startDialogue("s1", "n1");
    await playApi.listNpcs("s1");
    const [region, knowledge, canon, rumors, events, say, timeline, log, start, npcs] = urls();
    for (const u of [region, knowledge, canon, rumors, events, say]) expect(u).toContain("lang=en");
    expect(events).toContain("?status=active&lang=en");
    for (const u of [timeline, log, start, npcs]) expect(u).not.toContain("lang=");
  });
});

describe("NpcList (US-4.1)", () => {
  it("shows a card and a talk button per NPC, and marks the ones talked to", () => {
    const onTalk = vi.fn();
    render(<NpcList npcs={[MARA]} counts={{ n1: 4 }} onTalk={onTalk} />);
    expect(screen.getByTestId("npc-n1")).toHaveTextContent("Mara");
    expect(screen.getByTestId("npc-n1-talked")).toHaveTextContent(t("dialogue.has", { n: 4 }));
    fireEvent.click(screen.getByTestId("npc-n1-talk-btn"));
    expect(onTalk).toHaveBeenCalledWith("n1");
  });

  it("has no talked mark before the first conversation", () => {
    render(<NpcList npcs={[MARA]} onTalk={vi.fn()} />);
    expect(screen.queryByTestId("npc-n1-talked")).not.toBeInTheDocument();
  });
});

describe("DialoguePanel (US-4.1 / 4.3)", () => {
  it("opening loads the history without an LLM call", async () => {
    (api.startDialogue as Mock).mockResolvedValue(
      conversation([msg("player", "안녕하세요"), msg("npc", "어서 오게")]),
    );
    renderPanel();
    await waitFor(() => expect(screen.getAllByTestId("dialogue-msg-npc")).toHaveLength(1));
    expect(api.startDialogue).toHaveBeenCalledWith("s1", "n1");
    expect(api.say).not.toHaveBeenCalled();
    expect(screen.getByTestId("dialogue-panel")).toHaveTextContent(t("dialogue.title", { name: "Mara" }));
  });

  it("sending shows the player's line, then appends the NPC's answer", async () => {
    (api.startDialogue as Mock).mockResolvedValue(conversation());
    let answer!: (v: unknown) => void;
    (api.say as Mock).mockReturnValue(new Promise((r) => (answer = r)));
    const props = renderPanel();
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toBeEnabled());
    typeAndSend("  방앗간은 어떻게 됐나요?  ");
    expect(api.say).toHaveBeenCalledWith("s1", "n1", "방앗간은 어떻게 됐나요?");
    expect(screen.getByTestId("dialogue-msg-player")).toHaveTextContent("방앗간은 어떻게 됐나요?");
    expect(screen.getByTestId("dialogue-sending")).toBeInTheDocument();
    await act(async () =>
      answer({ message: msg("npc", "불에 탔다네"), lang: "ko", llm_calls: 1, context_ids: [] }),
    );
    expect(screen.getByTestId("dialogue-msg-npc")).toHaveTextContent("불에 탔다네");
    expect(screen.queryByTestId("dialogue-sending")).not.toBeInTheDocument();
    expect(props.onSpoke).toHaveBeenCalledTimes(1);
  });

  it("a failed send takes the player's line back and keeps it in the input", async () => {
    (api.startDialogue as Mock).mockResolvedValue(conversation());
    (api.say as Mock).mockRejectedValue(new Error("503 Service Unavailable: no llm"));
    renderPanel();
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toBeEnabled());
    typeAndSend("누구세요?");
    await waitFor(() => expect(screen.getByTestId("dialogue-error")).toHaveTextContent("503"));
    expect(screen.queryByTestId("dialogue-msg-player")).not.toBeInTheDocument();
    expect(screen.getByTestId("dialogue-input")).toHaveValue("누구세요?");
  });

  it("without an LLM the history still opens but the input is locked", async () => {
    (api.startDialogue as Mock).mockResolvedValue(conversation([msg("npc", "지난 이야기")]));
    renderPanel({ llmAvailable: false });
    await waitFor(() => expect(screen.getByTestId("dialogue-msg-npc")).toBeInTheDocument());
    expect(screen.getByTestId("dialogue-no-llm")).toHaveTextContent(t("dialogue.noLlm"));
    expect(screen.getByTestId("dialogue-input")).toBeDisabled();
    expect(screen.getByTestId("dialogue-send-btn")).toBeDisabled();
  });

  it("a failed open shows the error and keeps the input locked", async () => {
    (api.startDialogue as Mock).mockRejectedValue(new Error("400 Bad Request: npc not here"));
    renderPanel();
    await waitFor(() => expect(screen.getByTestId("dialogue-error")).toHaveTextContent("400"));
    expect(screen.getByTestId("dialogue-input")).toBeDisabled();
  });

  it("while a turn runs, talking still works but end talk (a turn) is off", async () => {
    (api.startDialogue as Mock).mockResolvedValue(conversation());
    renderPanel({ busy: true });
    await waitFor(() => expect(screen.getByTestId("dialogue-input")).toBeEnabled());
    expect(screen.getByTestId("dialogue-end-btn")).toBeDisabled();
  });

  it("end talk and close call back", async () => {
    (api.startDialogue as Mock).mockResolvedValue(conversation());
    const props = renderPanel();
    fireEvent.click(await screen.findByTestId("dialogue-end-btn"));
    fireEvent.click(screen.getByTestId("dialogue-close-btn"));
    expect(props.onEndTalk).toHaveBeenCalledTimes(1);
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });
});

describe("PlayPage with dialogue and the language toggle", () => {
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
    (api.listNpcs as Mock).mockResolvedValue([
      { npc: MARA, has_conversation: true, message_count: 2 },
    ]);
    (api.startDialogue as Mock).mockResolvedValue(conversation([msg("npc", "어서 오게")]));
  });

  it("the hearsay heading carries the NPCs-do-not-know-this hint", async () => {
    renderPlay();
    expect(await screen.findByTestId("hearsay-hint")).toHaveTextContent(t("play.hearsayHint"));
    await waitFor(() => expect(screen.getByTestId("npc-n1-talked")).toBeInTheDocument());
  });

  it("talk opens the panel; end talk spends a turn with EndTalk and closes it", async () => {
    (api.act as Mock).mockResolvedValue({
      id: "run1", session_id: "s1", status: "running", cost_turns: 1, action: null,
    });
    (api.getTurnRun as Mock).mockResolvedValue({
      id: "run1", session_id: "s1", status: "done", cost_turns: 1, action: null,
      result: { session: { id: "s1", world_id: "w", status: "open", turn: 1 }, changes: [], narration: [], budget_exhausted: false, llm_failed: false },
    });
    renderPlay();
    fireEvent.click(await screen.findByTestId("npc-n1-talk-btn"));
    expect(await screen.findByTestId("dialogue-panel")).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId("dialogue-msg-npc")).toHaveTextContent("어서 오게"));
    fireEvent.click(screen.getByTestId("dialogue-end-btn"));
    await waitFor(() => expect(api.act).toHaveBeenCalledWith("s1", { type: "end_talk", npc_id: "n1" }));
    expect(screen.queryByTestId("dialogue-panel")).not.toBeInTheDocument();
  });

  it("switching to en relabels the screen and re-reads the region", async () => {
    renderPlay();
    await screen.findByTestId("region-scene");
    const readsBefore = (api.getRegion as Mock).mock.calls.length;
    expect(screen.getByTestId("nav-play")).toHaveTextContent("플레이");
    fireEvent.click(screen.getByTestId("lang-en"));
    await waitFor(() => expect((api.getRegion as Mock).mock.calls.length).toBe(readsBefore + 1));
    expect(lang()).toBe("en");
    expect(screen.getByTestId("nav-play")).toHaveTextContent("Play");
    expect(screen.getByTestId("lang-en")).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByTestId("region-scene")).toHaveTextContent("People here");
  });
});

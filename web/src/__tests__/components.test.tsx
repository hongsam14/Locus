import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { MapOverlay } from "../MapOverlay";
import { RegionPanel } from "../RegionPanel";
import { AugmentPanel } from "../AugmentPanel";
import type { ConnectionEdge, Region } from "../types";

vi.mock("../api", () => ({
  api: {
    regionKnowledge: vi.fn(),
    startAugment: vi.fn(),
    submitAnswer: vi.fn(),
    revertAugment: vi.fn(),
    deleteNode: vi.fn(),
  },
}));
import { api } from "../api";

const regions: Region[] = [
  { id: "r1", name: "Riverton", level: "town", position: { x: 0.2, y: 0.3 } },
  { id: "r2", name: "Highcrag", level: "town", position: { x: 0.8, y: 0.7 } },
];
const connections: ConnectionEdge[] = [
  { source_region_id: "r1", target_region_id: "r2", kind: "blocked", weight: 0.2 },
];

describe("MapOverlay", () => {
  it("renders a marker per region and a line per connection", () => {
    render(
      <MapOverlay regions={regions} connections={connections} onSelect={() => {}} onMove={() => {}} />,
    );
    expect(screen.getByTestId("region-marker-r1")).toBeInTheDocument();
    expect(screen.getByTestId("region-marker-r2")).toBeInTheDocument();
    expect(screen.getAllByTestId("connection-line")).toHaveLength(1);
  });

  it("calls onSelect when a marker is clicked", () => {
    const onSelect = vi.fn();
    render(
      <MapOverlay regions={regions} connections={[]} onSelect={onSelect} onMove={() => {}} />,
    );
    fireEvent.click(screen.getByTestId("region-marker-r1"));
    expect(onSelect).toHaveBeenCalledWith("r1");
  });
});

describe("RegionPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("shows region knowledge from the API", async () => {
    (api.regionKnowledge as ReturnType<typeof vi.fn>).mockResolvedValue({
      world_id: "w",
      region_id: "r1",
      items: [
        { knowledge_id: "k1", statement: "Sunday market", scope_type: "direct", is_rumor: false, confidence: 0.9 },
      ],
      shared_ids: [],
      unique_ids: ["k1"],
    });
    render(<RegionPanel worldId="w" regionId="r1" />);
    await waitFor(() => expect(screen.getByTestId("knowledge-item-k1")).toBeInTheDocument());
    expect(screen.getByText(/Sunday market/)).toBeInTheDocument();
  });
});

describe("AugmentPanel", () => {
  beforeEach(() => vi.clearAllMocks());

  it("starts a session and shows questions", async () => {
    (api.startAugment as ReturnType<typeof vi.fn>).mockResolvedValue({
      id: "s1",
      world_id: "w",
      round: 0,
      status: "open",
      open_questions: [{ id: "q1", issue_id: "i1", text: "What is known here?", options: ["add", "ignore"], kind: "confirm" }],
      history: [],
    });
    render(<AugmentPanel worldId="w" />);
    fireEvent.click(screen.getByTestId("augment-start-btn"));
    await waitFor(() => expect(screen.getByText(/What is known here/)).toBeInTheDocument());
    expect(screen.getAllByTestId("augment-answer-btn").length).toBe(2);
  });
});

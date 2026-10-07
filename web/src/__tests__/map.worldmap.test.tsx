// The drawn map: names take presses, a ringed marker keeps its own name beside it, plates
// stay on the map and leave room for a badge, area names show selection and the GM state
// without swallowing presses, and a line has a wide press area (V2 code review 01 #4, #5,
// #10, #11, #12 and § 2).
import { fireEvent, render, screen } from "@testing-library/react";
import { WorldMap } from "../map";
import type { ConnectionEdge, Region } from "../types";

const town = (id: string, x: number, y: number, level = "town"): Region => ({ id, name: id.toUpperCase(), level, position: { x, y } });
const H = 625; // MAP_EXTENT height (1000 × 625 units)

function plate(id: string): { x: number; y: number; h: number } {
  const rect = screen.getByTestId(`region-label-${id}`).querySelector("rect")!;
  return { x: Number(rect.getAttribute("x")), y: Number(rect.getAttribute("y")), h: Number(rect.getAttribute("height")) };
}

describe("WorldMap", () => {
  it("a region's name selects it, as its marker does, and adds nothing (review #4)", () => {
    const onSelect = vi.fn();
    const onAddAt = vi.fn();
    render(<WorldMap regions={[town("a", 0.5, 0.5)]} connections={[]} mode="edit" label="map" onSelect={onSelect} onAddAt={onAddAt} />);
    const name = screen.getByTestId("region-label-a");
    expect(name).not.toHaveAttribute("pointer-events", "none");
    fireEvent.click(name.querySelector("text")!);
    expect(onSelect).toHaveBeenCalledWith("a");
    expect(onAddAt).not.toHaveBeenCalled();
  });

  it("a selected region's name moves aside when a neighbour sits below, not onto it (review #5)", () => {
    // b's marker is 34 units under a: a plate below a would cover it; the right side is free
    render(<WorldMap regions={[town("a", 0.5, 0.5), town("b", 0.5, 0.5 + 34 / H)]} connections={[]} mode="edit"
      label="map" selectedId="a" onSelect={() => {}} />);
    expect(plate("a").x).toBeGreaterThan(500);
  });

  it("a badge under a plate is kept clear like the plate (review § 2)", () => {
    // the plate alone fits below a; plate + badge would reach b's marker
    const regions = [town("a", 0.5, 0.5), town("b", 0.5, 0.5 + 50 / H)];
    const { unmount } = render(<WorldMap regions={regions} connections={[]} mode="gm" label="map" />);
    expect(plate("a").y).toBeGreaterThan(H / 2); // below, with no badge
    unmount();
    render(<WorldMap regions={regions} connections={[]} mode="gm" label="map" overlay={{ a: { badge: "2" } }} />);
    expect(plate("a").x).toBeGreaterThan(500); // beside, with one
  });

  it("a name at the map's edge stays on the map (review #12)", () => {
    render(<WorldMap regions={[town("a", 0.5, 0.995)]} connections={[]} mode="edit" label="map" />);
    const p = plate("a");
    expect(p.y + p.h).toBeLessThanOrEqual(H);
  });

  it("an area shows selection and the GM state; its wide name takes no presses (review #10, #11)", () => {
    const continent = town("c", 0.5, 0.5, "continent");
    const { container, rerender } = render(
      <WorldMap regions={[continent]} connections={[]} mode="edit" label="map" selectedId="c" onSelect={() => {}} />,
    );
    const marker = screen.getByTestId("region-marker-c");
    expect(marker.querySelector("text")).toHaveAttribute("pointer-events", "none");
    const frame = marker.querySelector("rect")!;
    expect(frame.style.stroke).toBe("var(--color-accent)");
    rerender(<WorldMap regions={[continent]} connections={[]} mode="gm" label="map"
      overlay={{ c: { fill: "var(--color-danger)", ring: "event" } }} />);
    expect(screen.getByTestId("region-fill-c").style.fill).toBe("var(--color-danger)");
    expect(screen.getByTestId("region-fill-c").style.stroke).toBe("var(--color-event)");
    expect(container.querySelectorAll('[data-testid="region-marker-c"] rect')).toHaveLength(1);
  });

  it("a line has a wide invisible press area that selects it (review § 2)", () => {
    const onSelectConnection = vi.fn();
    const c: ConnectionEdge = { source_region_id: "a", target_region_id: "b", kind: "blocked", weight: 0.2 };
    render(<WorldMap regions={[town("a", 0.2, 0.3), town("b", 0.8, 0.7)]} connections={[c]} mode="edit" label="map"
      onSelectConnection={onSelectConnection} />);
    const hit = screen.getByTestId("connection-hit");
    expect(Number.parseFloat(hit.style.strokeWidth)).toBeGreaterThan(10);
    fireEvent.click(hit);
    fireEvent.click(screen.getByTestId("connection-line"));
    expect(onSelectConnection).toHaveBeenCalledTimes(2);
  });
});

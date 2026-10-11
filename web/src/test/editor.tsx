// Test helpers for the V8 editor (frontend-components § 7, code plan Step 5.4).
import { fireEvent, screen } from "@testing-library/react";
import { AugmentPanel } from "../features/editor/AugmentPanel";
import type { InspectorOpen } from "../features/editor/RegionInspector";
import { useAugmentation } from "../features/editor/useAugmentation";
import type { ConnectionEdge, Knowledge, NameRef, Region, WikiPrior } from "../types";

/** Every inspector section unfolded, for tests that reach into all four. */
export const ALL_OPEN: InspectorOpen = { basic: true, connections: true, knowledge: true, npcs: true };

/** Save, load and build sit in the row under [파일 ▾] (V8 design review 01 R-05). */
export function openFileMenu() {
  fireEvent.click(screen.getByTestId("file-menu"));
}

/** The page's augmentation hook around the panel that only shows (V8 code plan § 1.1 R-15).
 * `show={false}` takes the panel away while the hook stays, as a hidden tab does. */
export function AugHost({
  worldId = "w",
  regions,
  entities = [],
  knowledge = [],
  connections = [],
  priors = [],
  onChanged = () => {},
  show = true,
}: {
  worldId?: string;
  regions: Region[];
  entities?: NameRef[];
  knowledge?: Knowledge[];
  connections?: ConnectionEdge[];
  priors?: WikiPrior[];
  onChanged?(): void;
  show?: boolean;
}) {
  const aug = useAugmentation(worldId, { onChanged });
  if (!show) return null;
  return <AugmentPanel aug={aug} regions={regions} entities={entities} knowledge={knowledge} connections={connections} priors={priors} />;
}

export { autoLayout } from "./autoLayout";
export { edgeStyle, uniqueEdges } from "./edgeStyle";
export type { EdgeStyle } from "./edgeStyle";
export { focusBox } from "./focus";
export {
  MAP_EXTENT,
  applyMatrix,
  clampNorm,
  inside,
  invert,
  meetMatrix,
  normalizeFromMatrix,
  toClient,
  toPixels,
} from "./geometry";
export type { Matrix, Norm, Point, ViewBox } from "./geometry";
export { candidateBoxes, labelWidth, markerBox, overlaps, placeLabels, plateHeight, within } from "./labels";
export type { Box, LabelAnchor, LabelBox, LabelText, Side } from "./labels";
export { WorldMap } from "./WorldMap";
export type { RegionOverlay, WorldMapProps } from "./WorldMap";

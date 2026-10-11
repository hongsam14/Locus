// The play map's close-up (V2 BLM § 8.5): the player's region and its neighbours with a
// margin, kept at the map's 8:5 shape and inside the map.
import { MAP_EXTENT, type Norm, type ViewBox } from "./geometry";

export function focusBox(
  positions: Record<string, Norm>,
  focus: { id: string; neighbors: string[] },
  pad = 0.12,
): ViewBox {
  const pts = [focus.id, ...focus.neighbors].map((id) => positions[id]).filter((p): p is Norm => p != null);
  if (pts.length === 0) return MAP_EXTENT;
  const xs = pts.map((p) => p.x * MAP_EXTENT.w);
  const ys = pts.map((p) => p.y * MAP_EXTENT.h);
  let x0 = Math.min(...xs) - pad * MAP_EXTENT.w;
  let x1 = Math.max(...xs) + pad * MAP_EXTENT.w;
  let y0 = Math.min(...ys) - pad * MAP_EXTENT.h;
  let y1 = Math.max(...ys) + pad * MAP_EXTENT.h;
  const ratio = MAP_EXTENT.w / MAP_EXTENT.h;
  // widen the short side to 8:5
  if ((x1 - x0) / (y1 - y0) < ratio) {
    const w = (y1 - y0) * ratio;
    const cx = (x0 + x1) / 2;
    [x0, x1] = [cx - w / 2, cx + w / 2];
  } else {
    const h = (x1 - x0) / ratio;
    const cy = (y0 + y1) / 2;
    [y0, y1] = [cy - h / 2, cy + h / 2];
  }
  const w = Math.min(MAP_EXTENT.w, x1 - x0);
  const h = Math.min(MAP_EXTENT.h, y1 - y0);
  const x = Math.min(Math.max(MAP_EXTENT.x, x0), MAP_EXTENT.w - w);
  const y = Math.min(Math.max(MAP_EXTENT.y, y0), MAP_EXTENT.h - h);
  return { x, y, w, h };
}

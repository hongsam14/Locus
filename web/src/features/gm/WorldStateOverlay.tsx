// The world-state colours of the GM map (U7 BR-U7-23). V6: the overlay's switch, legend and
// badge live in MapPane, and the state is read with the session's other reads (useGmData).
const STEPS = [0, 25, 50, 75, 100]; // ink strength per distortion band

/** Five distortion bands, design tokens only: the plain marker for [0, .2), more danger above. */
export function distortionColor(d: number): string {
  const band = Math.min(4, Math.max(0, Math.floor(d * 5)));
  return `color-mix(in srgb, var(--color-danger) ${STEPS[band]}%, var(--color-map-town))`;
}

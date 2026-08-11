import type { InputHTMLAttributes } from "react";

/** Ink-styled range slider (support / distortion). Keeps the native thumb and
 * tints it via `accent-color` — no `appearance-none` (which would remove the
 * draggable thumb without a replacement pseudo-element). Forwards all props. */
export function Range({ className = "", ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      type="range"
      className={`cursor-pointer accent-ink align-middle ${className}`.trim()}
      {...rest}
    />
  );
}

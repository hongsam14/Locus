import { useEffect, useRef, useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Range } from "./Range";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  value: number; // the server's value
  // save; `false` (or a promise of it) = refused: the thumb returns to `value`
  onCommit: (v: number) => void | boolean | Promise<boolean | void>;
}

const COMMIT_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"]);

/** A slider that saves however it was moved (U7 BR-U7-24, FR-D5): pointer or mouse
 * release, touch end, an arrow/Home/End/Page key, or losing focus. The value is kept
 * locally while dragging; a value equal to the last saved one is never sent again.
 *
 * Only a value the user moved to is saved (U7 review #1): a browser snaps an off-step
 * server value (0.375 shows as 0.4), so tabbing past or clicking the thumb must not save
 * that. A value counts as saved only when the save succeeded (review #4): a refused one
 * puts the thumb back and can be sent again. */
export function CommitRange({ value, onCommit, ...rest }: Props) {
  const [draft, setDraft] = useState(value);
  const saved = useRef(value);
  const dirty = useRef(false); // the user moved the thumb since the last save
  useEffect(() => {
    setDraft(value);
    saved.current = value;
    dirty.current = false;
  }, [value]);

  const commit = async (raw: string | number) => {
    if (!dirty.current) return;
    const v = Number(raw);
    if (Number.isNaN(v)) return;
    dirty.current = false;
    if (v === saved.current) return;
    const ok = await onCommit(v);
    if (ok === false) {
      setDraft(value); // refused: back to the server's value, ready to be sent again
    } else {
      saved.current = v;
    }
  };
  const fromEvent = (e: { currentTarget: HTMLInputElement }) => commit(e.currentTarget.value);

  return (
    <Range
      {...rest}
      value={draft}
      onChange={(e) => {
        dirty.current = true;
        setDraft(Number(e.target.value));
      }}
      onMouseUp={(e) => void fromEvent(e)}
      onPointerUp={(e) => void fromEvent(e)}
      onTouchEnd={(e) => void fromEvent(e)}
      onBlur={(e) => void fromEvent(e)}
      onKeyUp={(e) => {
        if (COMMIT_KEYS.has(e.key)) void fromEvent(e);
      }}
    />
  );
}

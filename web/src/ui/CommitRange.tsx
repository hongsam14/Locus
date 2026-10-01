import { useEffect, useRef, useState } from "react";
import type { InputHTMLAttributes } from "react";
import { Range } from "./Range";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "onChange" | "value"> {
  value: number; // the server's value
  onCommit: (v: number) => void; // save
}

const COMMIT_KEYS = new Set(["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "Home", "End", "PageUp", "PageDown"]);

/** A slider that saves however it was moved (U7 BR-U7-24, FR-D5): pointer or mouse
 * release, touch end, an arrow/Home/End/Page key, or losing focus. The value is kept
 * locally while dragging; a value equal to the last saved one is never sent again. */
export function CommitRange({ value, onCommit, ...rest }: Props) {
  const [draft, setDraft] = useState(value);
  const saved = useRef(value);
  useEffect(() => {
    setDraft(value);
    saved.current = value;
  }, [value]);

  const commit = (raw: string | number) => {
    const v = Number(raw);
    if (Number.isNaN(v) || v === saved.current) return;
    saved.current = v;
    onCommit(v);
  };
  const fromEvent = (e: { currentTarget: HTMLInputElement }) => commit(e.currentTarget.value);

  return (
    <Range
      {...rest}
      value={draft}
      onChange={(e) => setDraft(Number(e.target.value))}
      onMouseUp={fromEvent}
      onPointerUp={fromEvent}
      onTouchEnd={fromEvent}
      onBlur={fromEvent}
      onKeyUp={(e) => {
        if (COMMIT_KEYS.has(e.key)) fromEvent(e);
      }}
    />
  );
}

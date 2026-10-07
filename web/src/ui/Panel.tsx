import type { HTMLAttributes, ReactNode } from "react";
import { Card } from "./Card";

/** A titled Card as a section (kept for the screens that use it; V9 folds it into Card). */
export function Panel(props: HTMLAttributes<HTMLElement> & { title?: ReactNode }) {
  return <Card as="section" {...props} />;
}

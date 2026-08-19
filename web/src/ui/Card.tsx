import type { HTMLAttributes } from "react";

export function Card({ className = "", ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={`sketch-border bg-paper-card p-2 ${className}`.trim()} {...rest} />;
}

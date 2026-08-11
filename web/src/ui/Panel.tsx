import type { HTMLAttributes, ReactNode } from "react";

export function Panel({
  title,
  children,
  className = "",
  ...rest
}: HTMLAttributes<HTMLElement> & { title?: ReactNode }) {
  return (
    <section
      className={`sketch-border sketch-shadow bg-paper-card p-3 ${className}`.trim()}
      {...rest}
    >
      {title != null && <h2 className="font-display text-lg mb-2">{title}</h2>}
      {children}
    </section>
  );
}

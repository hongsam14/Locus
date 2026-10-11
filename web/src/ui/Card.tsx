import type { HTMLAttributes, ReactNode } from "react";

// V2: the one panel (Card and Panel were two). A title makes it a titled section.
export function Card({
  as: Tag = "div",
  title,
  actions,
  className = "",
  children,
  ...rest
}: HTMLAttributes<HTMLElement> & { as?: "div" | "section" | "article"; title?: ReactNode; actions?: ReactNode }) {
  return (
    <Tag className={`rounded-lg border border-line-strong bg-surface p-4 shadow-panel ${className}`.trim()} {...rest}>
      {(title != null || actions != null) && (
        <div className="mb-3 flex flex-wrap items-center gap-2">
          {title != null && <h2 className="flex-1 font-heading text-lg">{title}</h2>}
          {actions}
        </div>
      )}
      {children}
    </Tag>
  );
}

import { useId, useState, type ReactNode } from "react";

// A titled group that can fold (V2 FR-D5): the toggle says whether it is open
// (aria-expanded) and which content it controls.
export function Section({
  title,
  collapsible = false,
  defaultOpen = true,
  actions,
  level = 2,
  children,
}: {
  title: ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
  actions?: ReactNode;
  level?: 2 | 3;
  children: ReactNode;
}) {
  const id = useId();
  const [open, setOpen] = useState(defaultOpen);
  const Heading = level === 2 ? "h2" : "h3";
  const shown = !collapsible || open;
  return (
    <section className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <Heading className={`flex-1 font-heading ${level === 2 ? "text-xl" : "text-lg"}`}>
          {collapsible ? (
            <button
              type="button"
              aria-expanded={open}
              aria-controls={id}
              onClick={() => setOpen((o) => !o)}
              className="inline-flex min-h-11 items-center gap-2 text-left"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true" className={open ? "rotate-90" : ""}>
                <path d="M9 6l6 6-6 6" />
              </svg>
              {title}
            </button>
          ) : (
            title
          )}
        </Heading>
        {actions}
      </div>
      <div id={id} hidden={!shown}>
        {shown && children}
      </div>
    </section>
  );
}

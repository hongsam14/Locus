import type { ReactNode } from "react";

// Two columns from 1024 px — the main area and a side panel with its own scroll, 320–420 px
// wide — and one column below, in the order the screen asks for (V2 FR-D5, BR-V2-17).
const WIDTH = {
  wide: "lg:w-[clamp(320px,32vw,420px)]",
  narrow: "lg:w-[clamp(320px,28vw,380px)]",
} as const;

export function SplitView({
  main,
  aside,
  asideLabel,
  stackOrder = "main-first",
  asideWidth = "wide",
}: {
  main: ReactNode;
  aside: ReactNode;
  asideLabel: string;
  stackOrder?: "main-first" | "aside-first";
  asideWidth?: keyof typeof WIDTH;
}) {
  const asideFirst = stackOrder === "aside-first";
  return (
    <div className="mx-auto flex w-full max-w-[1240px] flex-col gap-6 px-4 py-6 sm:px-6 lg:flex-row lg:items-start">
      <div data-testid="split-main" className={`min-w-0 flex-1 ${asideFirst ? "order-2 lg:order-1" : ""}`}>
        {main}
      </div>
      <aside
        aria-label={asideLabel}
        data-testid="split-aside"
        className={`w-full min-w-0 lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:flex-none lg:overflow-y-auto ${WIDTH[asideWidth]} ${asideFirst ? "order-1 lg:order-2" : ""}`}
      >
        {aside}
      </aside>
    </div>
  );
}

import * as RadixTabs from "@radix-ui/react-tabs";
import type { ReactNode } from "react";

// V2 (FR-S6): tablist/tab/tabpanel and the arrow keys come from Radix; the look is ours.
export function Tabs({
  value,
  onValueChange,
  label,
  tabs,
}: {
  value: string;
  onValueChange(v: string): void;
  label: string;
  tabs: { value: string; label: ReactNode; content: ReactNode; badge?: ReactNode }[];
}) {
  return (
    <RadixTabs.Root value={value} onValueChange={onValueChange}>
      <RadixTabs.List aria-label={label} className="inline-flex flex-wrap gap-1 rounded-lg border border-line bg-bg p-1">
        {tabs.map((tab) => (
          <RadixTabs.Trigger
            key={tab.value}
            value={tab.value}
            className="inline-flex min-h-10 items-center gap-1.5 rounded-md px-4 text-[15px] text-muted hover:text-fg data-[state=active]:bg-sunken data-[state=active]:font-bold data-[state=active]:text-accent"
          >
            {tab.label}
            {tab.badge}
          </RadixTabs.Trigger>
        ))}
      </RadixTabs.List>
      {tabs.map((tab) => (
        <RadixTabs.Content key={tab.value} value={tab.value} className="pt-3">
          {tab.content}
        </RadixTabs.Content>
      ))}
    </RadixTabs.Root>
  );
}

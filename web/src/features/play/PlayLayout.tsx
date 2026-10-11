import type { ReactNode } from "react";

export interface PlaySections {
  header: ReactNode;
  result: ReactNode;
  scene: ReactNode;
  actions: ReactNode; // the action box (wide, middle)
  dock: ReactNode; // the fixed bar and its sheets (narrow)
  map: ReactNode;
  moves: ReactNode; // the move list (wide, middle); a phone has it in the move sheet
  people: ReactNode; // the people here, or the talk in their place (wide)
  knowledge: ReactNode;
  log: ReactNode;
}

/** Where each part of the play screen goes, by width (V4 frontend-components § 1 table).
 * Each part is placed once: what a width does not show is not in the page at all, so a
 * test id is never in the page twice (BR-V4-25). V2 `SplitView` puts the whole aside
 * before or after, which cannot make the phone's mixed order, so play does not use it. */
export function PlayLayout({ wide, narrow, s }: { wide: boolean; narrow: boolean; s: PlaySections }) {
  if (wide) {
    return (
      <div className="grid grid-cols-[minmax(0,1fr)_360px] items-start gap-8">
        <div className="flex min-w-0 flex-col gap-6">
          {s.header}
          {s.result}
          {s.scene}
          {s.actions}
          {s.people}
          {s.knowledge}
        </div>
        <aside className="sticky top-4 flex min-w-0 flex-col gap-6">
          {s.map}
          {s.moves}
          {s.log}
        </aside>
      </div>
    );
  }
  if (narrow) {
    return (
      // room under the page for the fixed bar as tall as it is (ActionDock measures it,
      // safe area included); 7rem until it is measured
      <div className="flex flex-col gap-6 pb-[calc(var(--dock-h,7rem)+1rem)]">
        {s.header}
        {s.result}
        {s.scene}
        {s.map}
        {s.people}
        {s.knowledge}
        {s.log}
        {s.dock}
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      {s.header}
      {s.result}
      {s.scene}
      {s.actions}
      {s.map}
      {s.moves}
      {s.people}
      {s.knowledge}
      {s.log}
    </div>
  );
}

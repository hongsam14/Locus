// Render a screen piece the way the app shows it: inside a router, with the one
// notification area (V2 FD § 8.1). Pieces like GmHub that are tested alone need the
// Toaster to show their notifications.
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter } from "react-router-dom";
import { Toaster } from "../ui";

export function renderWithShell(ui: ReactElement, { route = "/", ...options }: { route?: string } & RenderOptions = {}) {
  return render(
    <MemoryRouter initialEntries={[route]}>
      {ui}
      <Toaster />
    </MemoryRouter>,
    options,
  );
}

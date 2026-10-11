// V4 code review 01 #4: a later screen whose code does not arrive (a redeploy removed the
// old chunk, a dropped connection) says so with [reload]; it does not blank the app.
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { App } from "../App";
import { t } from "../i18n";

vi.mock("../routes/EditorPage", () => {
  throw new Error("Failed to fetch dynamically imported module");
});
vi.mock("../api", () => ({
  api: {
    getLangs: vi.fn().mockResolvedValue({ default: "ko", supported: ["ko", "en"] }),
    capabilities: vi.fn().mockResolvedValue({ llm: true, vlm: true, embedding: true }),
  },
}));

// the boundary catches the failure; jsdom still reports it as an uncaught window error
const quiet = (e: ErrorEvent) => e.preventDefault();
beforeEach(() => {
  vi.spyOn(console, "error").mockImplementation(() => {});
  window.addEventListener("error", quiet);
});
afterEach(() => {
  window.removeEventListener("error", quiet);
  vi.restoreAllMocks();
});

it("an editor chunk that fails to load shows the error and [reload], inside the app", async () => {
  render(
    <MemoryRouter initialEntries={["/editor/w"]}>
      <App />
    </MemoryRouter>,
  );
  const failed = await screen.findByTestId("screen-load-failed");
  expect(failed).toHaveTextContent(t("error.screenLoad.title"));
  expect(screen.getByRole("button", { name: t("action.reloadPage") })).toBeInTheDocument();
});

// The frame of every screen (V2 BR-V2-17/20, TP-V2-15). The menu rules moved here from
// AppNav (U8 BR-U8-1).
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { act } from "react";
import { Link, MemoryRouter, Route, Routes } from "react-router-dom";
import { api } from "../api";
import { resetCapabilities } from "../capabilities";
import { t } from "../i18n";
import { AppShell, Section, SplitView } from "../layout";
import { toast } from "../ui";

afterEach(() => {
  vi.restoreAllMocks();
  resetCapabilities();
});

function shell(props: { worldId?: string; sessionId?: string } = {}) {
  return render(
    <MemoryRouter>
      <AppShell {...props}>
        <p>screen</p>
      </AppShell>
    </MemoryRouter>,
  );
}

describe("AppShell", () => {
  it("a screen's cards end with the screen (V2 review #8)", async () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: true, vlm: true, embedding: true });
    render(
      <MemoryRouter initialEntries={["/play/s1"]}>
        <Routes>
          <Route path="/play/:id" element={<AppShell><Link to="/gm/s1">to gm</Link><Link to="/play/s2">other session</Link></AppShell>} />
          <Route path="/gm/:id" element={<AppShell><p>gm</p></AppShell>} />
        </Routes>
      </MemoryRouter>,
    );
    act(() => void toast({ key: "play:run", tone: "danger", title: "The turn failed" }));
    expect(screen.getByText("The turn failed")).toBeInTheDocument();
    fireEvent.click(screen.getByText("other session")); // same screen, another session
    await waitFor(() => expect(screen.queryByText("The turn failed")).not.toBeInTheDocument());
    act(() => void toast({ key: "play:run", tone: "danger", title: "Failed again" }));
    fireEvent.click(screen.getByText("to gm")); // another screen
    await screen.findByText("gm");
    expect(screen.queryByText("Failed again")).not.toBeInTheDocument();
  });

  it("its language buttons are 44 px on a phone (BR-V2-08, review #13)", () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: true, vlm: true, embedding: true });
    shell();
    expect(screen.getByTestId("lang-ko").className).toMatch(/min-h-11 min-w-11.*sm:min-h-9/);
  });

  it("the logo goes home; with no world the editor link is the world list; GM waits for a session", () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: true, vlm: true, embedding: true });
    shell();
    expect(screen.getByTestId("nav-home")).toHaveAttribute("href", "/");
    expect(screen.getByTestId("nav-editor")).toHaveAttribute("href", "/");
    expect(screen.queryByTestId("nav-gm")).not.toBeInTheDocument();
    expect(screen.getByTitle(t("nav.gmLocked"))).toHaveTextContent(t("nav.gm"));
    expect(screen.getByText("screen")).toBeInTheDocument();
  });

  it("with a world and a session the links open them", () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: true, vlm: true, embedding: true });
    shell({ worldId: "emberleaf", sessionId: "s1" });
    expect(screen.getByTestId("nav-editor")).toHaveAttribute("href", "/editor/emberleaf");
    expect(screen.getByTestId("nav-play")).toHaveAttribute("href", "/play/s1");
    expect(screen.getByTestId("nav-gm")).toHaveAttribute("href", "/gm/s1");
  });

  it("shows one LLM-off band, in words for people", async () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: false, vlm: false, embedding: false });
    shell();
    const bands = await screen.findAllByTestId("llm-notice");
    expect(bands).toHaveLength(1);
    expect(bands[0]).toHaveTextContent(t("notice.llmOff"));
  });

  it("no band while the server's answer is unknown or it has a key", async () => {
    vi.spyOn(api, "capabilities").mockRejectedValue(new Error("down"));
    shell();
    await waitFor(() => expect(api.capabilities).toHaveBeenCalled());
    expect(screen.queryByTestId("llm-notice")).not.toBeInTheDocument();
  });

  it("folds the menu behind a button on a phone", () => {
    vi.spyOn(api, "capabilities").mockResolvedValue({ llm: true, vlm: true, embedding: true });
    shell();
    const toggle = screen.getByRole("button", { name: t("action.menu") });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
  });
});

describe("SplitView and Section", () => {
  it("names the side panel and stacks in the asked order", () => {
    render(<SplitView main={<p>map</p>} aside={<p>moves</p>} asideLabel="Map and moves" stackOrder="aside-first" />);
    expect(screen.getByRole("complementary", { name: "Map and moves" })).toHaveTextContent("moves");
    expect(screen.getByTestId("split-aside").className).toContain("order-1");
    expect(screen.getByTestId("split-main").className).toContain("order-2");
  });

  it("a section folds and says so", () => {
    render(<Section title="Knowledge" collapsible defaultOpen={false}><p>inside</p></Section>);
    const toggle = screen.getByRole("button", { name: "Knowledge" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByText("inside")).not.toBeInTheDocument();
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-expanded", "true");
    expect(screen.getByText("inside")).toBeInTheDocument();
  });
});

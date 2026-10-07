// The shared primitives behave as the design says (V2 BR-V2-07/08/21/22/23, TP-V2-12).
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { useState } from "react";
import { t } from "../i18n";
import { Button, ConfirmDialog, Dialog, FileInput, Select, StatusView, Tabs, Toaster, toast } from "../ui";

describe("Button", () => {
  it("shows work in progress and cannot be pressed while busy", () => {
    const onClick = vi.fn();
    render(<Button busy onClick={onClick}>go</Button>);
    const b = screen.getByRole("button", { name: "go" });
    expect(b).toHaveAttribute("aria-busy", "true");
    expect(b).toBeDisabled();
    fireEvent.click(b);
    expect(onClick).not.toHaveBeenCalled();
  });

  it("is 44 px tall on a phone, the small one 36 px from 640 px up", () => {
    render(<><Button>md</Button><Button size="sm">sm</Button></>);
    expect(screen.getByRole("button", { name: "md" }).className).toContain("min-h-11");
    expect(screen.getByRole("button", { name: "sm" }).className).toMatch(/min-h-11.*sm:min-h-9/);
  });
});

function DialogHarness({ onOpenChange }: { onOpenChange?: (o: boolean) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <button type="button" onClick={() => setOpen(true)}>open it</button>
      <Dialog
        open={open}
        onOpenChange={(o) => {
          onOpenChange?.(o);
          setOpen(o);
        }}
        title="Close the session?"
      >
        <input aria-label="first" />
      </Dialog>
    </>
  );
}

describe("Dialog", () => {
  it("moves focus in, is named by its title, closes on Esc and gives focus back", async () => {
    render(<DialogHarness />);
    const opener = screen.getByRole("button", { name: "open it" });
    opener.focus();
    fireEvent.click(opener);
    const dialog = await screen.findByRole("dialog", { name: "Close the session?" });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
    fireEvent.keyDown(document.activeElement!, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(opener));
  });
});

describe("Dialog and the world around it", () => {
  const tick = () => act(() => new Promise((r) => setTimeout(r, 0))); // Radix listens a tick later

  it("a press in the notification area does not close it; any other outside press does (review #3)", async () => {
    const onOpenChange = vi.fn();
    render(<><DialogHarness onOpenChange={onOpenChange} /><Toaster /><p>elsewhere</p></>);
    act(() => void toast({ title: "Turn 3 is done" }));
    fireEvent.click(screen.getByRole("button", { name: "open it" }));
    await screen.findByRole("dialog");
    await tick();
    const close = screen.getByRole("button", { name: t("action.close") });
    fireEvent.pointerDown(close);
    fireEvent.click(close);
    expect(screen.queryByText("Turn 3 is done")).not.toBeInTheDocument(); // the card closed…
    expect(screen.getByRole("dialog")).toBeInTheDocument(); // …the dialog did not
    expect(onOpenChange).not.toHaveBeenCalled();
    fireEvent.pointerDown(screen.getByText("elsewhere"));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("gives focus to <main> when the opener is gone (review § 2)", async () => {
    function Harness() {
      const [open, setOpen] = useState(false);
      const [row, setRow] = useState(true);
      return (
        <main id="main" tabIndex={-1}>
          {row && <button type="button" onClick={() => setOpen(true)}>delete row</button>}
          <ConfirmDialog open={open} title="Delete?" confirmLabel="Delete" onCancel={() => setOpen(false)}
            onConfirm={() => { setRow(false); setOpen(false); }} />
        </main>
      );
    }
    render(<Harness />);
    const opener = screen.getByRole("button", { name: "delete row" });
    opener.focus();
    fireEvent.click(opener);
    fireEvent.click(await screen.findByRole("button", { name: "Delete" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await waitFor(() => expect(document.activeElement).toBe(screen.getByRole("main")));
  });
});

describe("ConfirmDialog", () => {
  it("cannot be confirmed twice while busy and keeps a failure inside", () => {
    const onConfirm = vi.fn();
    const { rerender } = render(
      <ConfirmDialog open title="Delete?" confirmLabel="Delete" onConfirm={onConfirm} onCancel={() => {}} />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    rerender(<ConfirmDialog open busy title="Delete?" confirmLabel="Delete" onConfirm={onConfirm} onCancel={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Delete" }));
    expect(onConfirm).toHaveBeenCalledTimes(1);
    rerender(
      <ConfirmDialog open title="Delete?" confirmLabel="Delete" onConfirm={onConfirm} onCancel={() => {}}
        error={{ title: "Could not reach the server.", code: "network" }} />,
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Could not reach the server.");
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("a confirmation that cannot go ahead still closes by cancel and Esc (review #1)", async () => {
    const onCancel = vi.fn();
    render(<ConfirmDialog open confirmDisabled title="Delete?" confirmLabel="Delete" onConfirm={() => {}} onCancel={onCancel} />);
    expect(screen.getByRole("button", { name: "Delete" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Delete" })).not.toHaveAttribute("aria-busy");
    const cancel = screen.getByRole("button", { name: t("action.cancel") });
    expect(cancel).toBeEnabled();
    fireEvent.click(cancel);
    expect(onCancel).toHaveBeenCalledTimes(1);
    fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
    await waitFor(() => expect(onCancel).toHaveBeenCalledTimes(2));
  });
});

describe("Tabs", () => {
  it("is a tablist moved with the arrow keys", async () => {
    function Harness() {
      const [v, setV] = useState("a");
      return (
        <Tabs value={v} onValueChange={setV} label="GM"
          tabs={[{ value: "a", label: "Rumors", content: "A body" }, { value: "b", label: "Events", content: "B body" }]} />
      );
    }
    render(<Harness />);
    expect(screen.getByRole("tablist", { name: "GM" })).toBeInTheDocument();
    const first = screen.getByRole("tab", { name: "Rumors" });
    first.focus();
    fireEvent.keyDown(first, { key: "ArrowRight" });
    await waitFor(() => expect(screen.getByRole("tab", { name: "Events" })).toHaveFocus());
    expect(screen.getByRole("tabpanel")).toBeInTheDocument();
  });
});

describe("Select and FileInput", () => {
  it("a select is labelled and keeps its test id on the native control", () => {
    const onChange = vi.fn();
    render(<Select label="Start region" value="" placeholder="Pick" data-testid="pick"
      options={[{ value: "a", label: "Harbor" }]} onChange={onChange} />);
    const select = screen.getByLabelText("Start region");
    expect(select).toBe(screen.getByTestId("pick"));
    fireEvent.change(select, { target: { value: "a" } });
    expect(onChange).toHaveBeenCalledWith("a");
  });

  it("a file input hides the browser's words, keeps its test id and can take the same file again", () => {
    const onFiles = vi.fn();
    render(<FileInput label="Map image" data-testid="pick-file" onFiles={onFiles} />);
    expect(screen.getByText(t("empty.noFile"))).toBeInTheDocument();
    expect(screen.getByRole("button", { name: `Map image ${t("action.chooseFile")}` })).toBeInTheDocument();
    const input = screen.getByTestId("pick-file") as HTMLInputElement;
    const file = new File(["x"], "map.png", { type: "image/png" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(onFiles).toHaveBeenCalledWith([file]);
    expect(input.value).toBe("");
  });

  it("one tab stop per file field, each named by its field and described by its file (review #6)", () => {
    render(<>
      <FileInput label="Memos" onFiles={() => {}} chosen={["notes.md"]} />
      <FileInput label="Maps" onFiles={() => {}} />
    </>);
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.getAttribute("type"))).toEqual(["button", "button"]); // no form submit
    expect(screen.getByRole("button", { name: `Memos ${t("action.chooseFile")}` })).toHaveAccessibleDescription("notes.md");
    expect(screen.getByRole("button", { name: `Maps ${t("action.chooseFile")}` })).toHaveAccessibleDescription(t("empty.noFile"));
    for (const input of document.querySelectorAll('input[type="file"]')) {
      expect(input).toHaveAttribute("tabindex", "-1");
    }
  });
});

describe("Toaster", () => {
  afterEach(() => vi.useRealTimers());

  it("closes a plain card after 6 s and keeps a danger card", () => {
    vi.useFakeTimers();
    render(<Toaster />);
    act(() => {
      toast({ title: "Turn passed" });
      toast({ tone: "danger", title: "Turn failed" });
    });
    expect(screen.getByText("Turn passed")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Turn failed");
    act(() => vi.advanceTimersByTime(6100));
    expect(screen.queryByText("Turn passed")).not.toBeInTheDocument();
    expect(screen.getByText("Turn failed")).toBeInTheDocument();
  });

  it("updates a card with the same key and stacks cards without one", () => {
    render(<Toaster />);
    act(() => {
      toast({ key: "turn:r1", title: "Harbor", body: "1 new rumor", region: "r1" });
      toast({ key: "turn:r1", title: "Harbor", body: "2 new rumors", region: "r1" });
      toast({ title: "Event" });
      toast({ title: "Event" });
    });
    const card = screen.getByTestId("notif-turn:r1");
    expect(card).toHaveTextContent("2 new rumors");
    expect(card).toHaveAttribute("data-region", "r1");
    expect(screen.getAllByText("Harbor")).toHaveLength(1);
    expect(screen.getAllByText("Event")).toHaveLength(2);
    expect(screen.getByTestId("notification-center")).toHaveAttribute("aria-live", "polite");
  });
});

describe("StatusView", () => {
  it("tells loading, empty, error and ready apart", () => {
    const { rerender } = render(<StatusView state="loading" emptyText="Nothing yet" />);
    expect(screen.getByRole("status")).toHaveTextContent(t("label.loading"));
    expect(screen.queryByText("Nothing yet")).not.toBeInTheDocument();
    rerender(<StatusView state="empty" emptyText="Nothing yet" />);
    expect(screen.getByText("Nothing yet")).toBeInTheDocument();
    const onRetry = vi.fn();
    rerender(<StatusView state="error" onRetry={onRetry} error={{ title: "Could not load.", raw: "503 · x" }} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Could not load.");
    fireEvent.click(screen.getByRole("button", { name: t("action.retry") }));
    expect(onRetry).toHaveBeenCalled();
    expect(screen.getByText(t("action.details"))).toBeInTheDocument();
    rerender(<StatusView state="ready">content</StatusView>);
    expect(screen.getByText("content")).toBeInTheDocument();
  });
});

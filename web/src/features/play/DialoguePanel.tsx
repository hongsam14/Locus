import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { conflictKind, needsLlm, statusOf } from "../../api/http";
import { describeError, type DescribedError } from "../../errors";
import { lang, t } from "../../i18n";
import type { Message, NPC } from "../../types";
import { Button, Field, InlineError, Panel } from "../../ui";
import { english, type NameOf } from "./names";

let _localSeq = 0;

/** One conversation with one NPC (US-4.1 / 4.3 / 9.2). Opening it loads the history
 * (`start`, no LLM). Each line is one `say` — one LLM call — answered in the display
 * language; the text is the original, so there is no original/translation toggle
 * (A-1). The player's line shows at once and is taken back if the send fails, the
 * same all-or-nothing the server keeps (BR-U5-3). Talking is allowed while a turn
 * runs (BR-U5-27); "end talk" spends a turn, so it waits for the turn (`busy`).
 * Mount it with `key={npc.id}` so another NPC starts from a clean state.
 *
 * V4: the NPC's name from the name map; `bare` drops the panel frame and title for the talk
 * sheet, whose title names the NPC (Q5=A); long words wrap and the input shrinks, so a
 * phone never scrolls sideways; errors are described sentences (BR-V4-15). */
export function DialoguePanel({
  sessionId,
  npc,
  llmAvailable,
  busy,
  readOnly = false,
  onClose,
  onEndTalk,
  onSpoke,
  onClosed,
  nameOf = english,
  bare = false,
}: {
  sessionId: string;
  npc: NPC;
  llmAvailable: boolean;
  busy: boolean;
  /** A closed session: show the history (read, no LLM) and nothing else (review U5 #7). */
  readOnly?: boolean;
  onClose: () => void;
  onEndTalk: () => void;
  onSpoke?: () => void;
  /** The session closed elsewhere (GM tab, CLI, world replace): the page re-reads. */
  onClosed?: () => void;
  nameOf?: NameOf;
  bare?: boolean;
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false); // `start` succeeded
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<DescribedError | null>(null);
  const alive = useRef(true);
  const shownFor = useRef(""); // the session and NPC the error line belongs to

  useEffect(() => {
    // `active` is per run (StrictMode runs effects twice); `alive` is for `send`.
    let active = true;
    alive.current = true;
    setLoading(true);
    setReady(false);
    // a session that just closed re-runs this read (readOnly); its "session closed"
    // line must stay — only another session or NPC starts a clean line (U3 review S04)
    const shown = `${sessionId}|${npc.id}`;
    if (shownFor.current !== shown) {
      shownFor.current = shown;
      setError(null);
    }
    // `start` needs an open session; a closed one is read through `history`, where
    // "never talked" (404) simply means an empty history (BR-U5-4).
    const load = readOnly
      ? api.dialogueHistory(sessionId, npc.id).catch((e: unknown) => {
          if (statusOf(e) === 404) return { messages: [] as Message[] };
          throw e;
        })
      : api.startDialogue(sessionId, npc.id);
    load
      .then((c) => {
        if (!active) return;
        setMessages(c.messages);
        setReady(!readOnly);
      })
      .catch((e) => {
        if (!active) return;
        if (conflictKind(e) === "closed") {
          setError({ title: t("play.sessionClosed") }); // U7 review #12
          onClosed?.();
        } else setError(describeError(e));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      alive.current = false;
    };
  }, [sessionId, npc.id, readOnly]);

  async function send() {
    const text = draft.trim();
    if (!text || sending || !ready || !llmAvailable) return;
    const mine: Message = {
      id: `local-${_localSeq++}`,
      conversation_id: "",
      role: "player",
      text,
      lang: lang(),
      turn: 0,
    };
    setMessages((m) => [...m, mine]);
    setDraft("");
    setSending(true);
    setError(null);
    try {
      const reply = await api.say(sessionId, npc.id, text);
      if (!alive.current) return;
      setMessages((m) => [...m, reply.message]);
      onSpoke?.();
    } catch (e) {
      if (!alive.current) return;
      setMessages((m) => m.filter((x) => x.id !== mine.id));
      setDraft(text);
      // 503: the NPC's call failed (BR-U7-27) — a plain line; the words stay in the box.
      // 409 closed: the session ended elsewhere — say so and let the page lock (#12).
      if (conflictKind(e) === "closed") {
        setError({ title: t("play.sessionClosed") });
        onClosed?.();
      } else if (needsLlm(e)) setError({ title: t("llm.required") }); // no provider (BR-U8-27)
      else setError(statusOf(e) === 503 ? { title: t("dialogue.failed") } : describeError(e));
    } finally {
      if (alive.current) setSending(false);
    }
  }

  // Locked while a line is on its way: a failed send puts that line back in the box,
  // which must not overwrite a next line typed meanwhile (review U5 #9).
  const inputOff = !llmAvailable || !ready || readOnly || sending;
  const name = nameOf("npcs", npc.id, "name", npc.name);
  const content = (
    <>
      <p className="text-xs text-muted">{nameOf("npcs", npc.id, "role", npc.role)}</p>
      {!llmAvailable && (
        <p data-testid="dialogue-no-llm" className="border border-line-strong rounded-md bg-sunken px-2 py-1 my-1 text-sm">
          {t("dialogue.noLlm")}
        </p>
      )}
      {loading && <p className="text-xs text-muted">{t("common.loading")}</p>}
      <ul data-testid="dialogue-messages" className="flex flex-col gap-1.5 my-2 text-sm">
        {messages.map((m) => (
          <li
            key={m.id}
            data-testid={`dialogue-msg-${m.role}`}
            className={`max-w-[80%] min-w-0 rounded-md border border-line-strong px-2 py-1 [overflow-wrap:anywhere] ${m.role === "player" ? "self-end bg-sunken" : "self-start bg-bg"}`}
          >
            <span className="block text-xs text-muted">
              {m.role === "player" ? t("dialogue.you") : name}
            </span>
            {m.text}
          </li>
        ))}
        {!loading && (ready || readOnly) && messages.length === 0 && (
          <li className="text-xs text-muted">{t("dialogue.empty")}</li>
        )}
      </ul>
      {sending && (
        <p data-testid="dialogue-sending" className="text-xs text-muted animate-pulse">
          {t("dialogue.sending")}
        </p>
      )}
      {error && (
        <div data-testid="dialogue-error">
          <InlineError error={error} />
        </div>
      )}
      <form
        className="flex min-w-0 items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <div className="flex min-w-0 flex-1 flex-col">
          <Field
            label={t("dialogue.placeholder")}
            hideLabel
            data-testid="dialogue-input"
            value={draft}
            disabled={inputOff}
            placeholder={t("dialogue.placeholder")}
            onChange={(e) => setDraft(e.target.value)}
            className="w-full min-w-0"
          />
        </div>
        <Button
          type="submit"
          size="sm"
          variant="primary"
          data-testid="dialogue-send-btn"
          disabled={inputOff || sending || draft.trim() === ""}
        >
          {t("dialogue.send")}
        </Button>
      </form>
      <div className="flex gap-2 mt-2">
        <Button
          size="sm"
          data-testid="dialogue-end-btn"
          disabled={busy || sending || readOnly}
          onClick={onEndTalk}
        >
          {t("dialogue.end")}
        </Button>
        <Button size="sm" data-testid="dialogue-close-btn" onClick={onClose}>
          {t("action.close")}
        </Button>
      </div>
    </>
  );
  if (bare) {
    return (
      <div data-testid="dialogue-panel" className="flex min-w-0 flex-col gap-2">
        {content}
      </div>
    );
  }
  return (
    <Panel data-testid="dialogue-panel" title={t("dialogue.title", { name })} className="max-w-2xl">
      {content}
    </Panel>
  );
}

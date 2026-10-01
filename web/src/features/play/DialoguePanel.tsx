import { useEffect, useRef, useState } from "react";
import { api } from "../../api";
import { conflictKind, statusOf } from "../../api/http";
import { lang, t } from "../../i18n";
import type { Message, NPC } from "../../types";
import { Button, Field, Panel } from "../../ui";

let _localSeq = 0;

/** One conversation with one NPC (US-4.1 / 4.3 / 9.2). Opening it loads the history
 * (`start`, no LLM). Each line is one `say` — one LLM call — answered in the display
 * language; the text is the original, so there is no original/translation toggle
 * (A-1). The player's line shows at once and is taken back if the send fails, the
 * same all-or-nothing the server keeps (BR-U5-3). Talking is allowed while a turn
 * runs (BR-U5-27); "end talk" spends a turn, so it waits for the turn (`busy`).
 * Mount it with `key={npc.id}` so another NPC starts from a clean state. */
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
}) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [ready, setReady] = useState(false); // `start` succeeded
  const [draft, setDraft] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const alive = useRef(true);

  useEffect(() => {
    // `active` is per run (StrictMode runs effects twice); `alive` is for `send`.
    let active = true;
    alive.current = true;
    setLoading(true);
    setReady(false);
    setError(null);
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
          setError(t("play.sessionClosed")); // U7 review #12
          onClosed?.();
        } else setError(String(e));
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
        setError(t("play.sessionClosed"));
        onClosed?.();
      } else setError(statusOf(e) === 503 ? t("dialogue.failed") : String(e));
    } finally {
      if (alive.current) setSending(false);
    }
  }

  // Locked while a line is on its way: a failed send puts that line back in the box,
  // which must not overwrite a next line typed meanwhile (review U5 #9).
  const inputOff = !llmAvailable || !ready || readOnly || sending;
  return (
    <Panel
      data-testid="dialogue-panel"
      title={t("dialogue.title", { name: npc.name })}
      className="max-w-2xl"
    >
      <p className="text-xs text-ink-soft">{npc.role}</p>
      {!llmAvailable && (
        <p data-testid="dialogue-no-llm" className="sketch-border bg-highlight px-2 py-1 my-1 text-sm">
          {t("dialogue.noLlm")}
        </p>
      )}
      {loading && <p className="text-xs text-ink-soft">{t("common.loading")}</p>}
      <ul data-testid="dialogue-messages" className="flex flex-col gap-1.5 my-2 text-sm">
        {messages.map((m) => (
          <li
            key={m.id}
            data-testid={`dialogue-msg-${m.role}`}
            className={`sketch-border px-2 py-1 max-w-[80%] ${m.role === "player" ? "self-end bg-highlight" : "self-start bg-paper"}`}
          >
            <span className="block text-xs text-ink-soft">
              {m.role === "player" ? t("dialogue.you") : npc.name}
            </span>
            {m.text}
          </li>
        ))}
        {!loading && (ready || readOnly) && messages.length === 0 && (
          <li className="text-xs text-ink-soft">{t("dialogue.empty")}</li>
        )}
      </ul>
      {sending && (
        <p data-testid="dialogue-sending" className="text-xs text-ink-soft animate-pulse">
          {t("dialogue.sending")}
        </p>
      )}
      {error && (
        <p data-testid="dialogue-error" className="text-danger text-sm">
          {error}
        </p>
      )}
      <form
        className="flex items-end gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <Field
          data-testid="dialogue-input"
          value={draft}
          disabled={inputOff}
          placeholder={t("dialogue.placeholder")}
          onChange={(e) => setDraft(e.target.value)}
          className="w-80"
        />
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
    </Panel>
  );
}

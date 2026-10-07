// Shared fetch helper for the four boundary API modules (U1 §11.2).
import { useState } from "react";
import { requestLang } from "../i18n";

export const BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "";

export const enc = encodeURIComponent;

/** Append the display language to a read whose response carries translated fields
 * (FD-U5 Q1=A), plus `say`, whose answer is generated in it. Not the timeline: it
 * carries no translated field and the backend does not take `lang` there. Write
 * routes stay as they are (their responses are not translated). Nothing is added when
 * the server's default applies or the server does not take the language (review #2). */
export function withLang(path: string): string {
  const l = requestLang();
  return l ? `${path}${path.includes("?") ? "&" : "?"}lang=${enc(l)}` : path;
}

/** A non-2xx answer (U3, U7 review C16). The message keeps the old form
 * `${status} ${statusText}: ${body}` (review 02 R-16): code that prints `String(e)` or
 * looks at the text is unchanged; new code reads `.status` through `statusOf`. Since V2
 * the server's error body is `{"detail", "code"}`: both are read once here (FR-D9). */
export class HttpError extends Error {
  readonly status: number;
  readonly body: string;
  readonly code?: string;
  readonly detail?: unknown;
  constructor(status: number, statusText: string, body: string) {
    super(`${status} ${statusText}: ${body}`);
    this.name = "Error"; // String(e) stays "Error: 409 …"
    this.status = status;
    this.body = body;
    try {
      const parsed = JSON.parse(body) as { detail?: unknown; code?: unknown } | null;
      if (parsed && typeof parsed === "object") {
        this.detail = parsed.detail;
        if (typeof parsed.code === "string" && parsed.code) this.code = parsed.code;
      }
    } catch {
      /* not JSON: no detail, no code */
    }
  }
}

/** The HTTP status of an error from `http()`, or of a `"NNN …"` message; `null` else. */
export function statusOf(err: unknown): number | null {
  if (err instanceof HttpError) return err.status;
  const m = /^(?:Error: )?(\d{3})\b/.exec(String(err));
  return m ? Number(m[1]) : null;
}

/** What a 409 means (U6 review #10/#11): the session is closed for good, or a turn (or
 * another GM write) is running and a retry later will do. `null` for any other error. */
export function conflictKind(err: unknown): "closed" | "busy" | null {
  if (statusOf(err) !== 409) return null;
  if (err instanceof HttpError && err.code) return err.code === "session_closed" ? "closed" : "busy";
  return /session is closed/i.test(String(err)) ? "closed" : "busy"; // a server without codes
}

/** What a 409 body says about the world's sessions (U8; U3 review design memo 10): open
 * sessions a replace would close, sessions mid-turn (retry later), or the sessions whose
 * player stands in a region. `null` when the error is not such a 409. */
export function openSessionsOf(
  err: unknown,
): { open?: number; busy?: number; sessionIds: string[] } | null {
  if (statusOf(err) !== 409) return null;
  // an HttpError's body, or the body part of an "Error: 409 Conflict: {…}" message
  const body = err instanceof HttpError ? err.body : String(err).replace(/^(Error: )?\d{3} [^:]*: /, "");
  try {
    const detail = (JSON.parse(body) as { detail?: unknown }).detail;
    if (!detail || typeof detail !== "object") return null;
    const d = detail as { open_sessions?: number; busy_sessions?: number; session_ids?: string[] };
    if (d.open_sessions == null && d.busy_sessions == null && !d.session_ids) return null;
    return { open: d.open_sessions, busy: d.busy_sessions, sessionIds: d.session_ids ?? [] };
  } catch {
    return null;
  }
}

/** The server's own sentence for a failed request: the JSON ``detail`` when it is text,
 * else the whole message (U3 review #12: the reason, not "lost"). */
export function detailOf(err: unknown): string {
  if (err instanceof HttpError) {
    try {
      const detail = (JSON.parse(err.body) as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    } catch {
      return err.body || String(err);
    }
  }
  return String(err);
}

/** The question a replace is waiting on: "replace?" first, then "close N sessions?". */
export type ReplaceAsk = "replace" | { sessions: number } | null;

/** The two-step replace question (U3 review C8), shared by the screens that replace a
 * world: `askReplace()` opens the first question; `sessionsAsked(err, confirmed)` turns a
 * 409 that names open sessions into the second one (true when it did — a mid-turn
 * `busy_sessions` 409 is not a question); `answer()` closes the dialog and says whether
 * the next send carries `confirm=true` (the session question was the one answered). */
export function useReplaceConfirm() {
  const [ask, setAsk] = useState<ReplaceAsk>(null);
  return {
    ask,
    open: ask != null,
    sessions: typeof ask === "object" && ask ? ask.sessions : 0,
    askReplace: () => setAsk("replace"),
    sessionsAsked(err: unknown, confirmed: boolean): boolean {
      const s = openSessionsOf(err);
      if (confirmed || !s?.open || s.busy) return false;
      setAsk({ sessions: s.open });
      return true;
    },
    answer(): boolean {
      setAsk(null);
      return ask != null && ask !== "replace";
    },
    cancel: () => setAsk(null),
  };
}

/** A 503 because the server has no LLM provider (U8, BR-U8-27). */
export function needsLlm(err: unknown): boolean {
  if (statusOf(err) !== 503) return false;
  if (err instanceof HttpError && err.code) return err.code === "llm_unavailable";
  return /llm|provider|openai_api_key/i.test(String(err)); // a server without codes
}

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new HttpError(res.status, res.statusText, await res.text());
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

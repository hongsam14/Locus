// Shared fetch helper for the four boundary API modules (U1 §11.2).
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
 * looks at the text is unchanged; new code reads `.status` through `statusOf`. */
export class HttpError extends Error {
  readonly status: number;
  readonly body: string;
  constructor(status: number, statusText: string, body: string) {
    super(`${status} ${statusText}: ${body}`);
    this.name = "Error"; // String(e) stays "Error: 409 …"
    this.status = status;
    this.body = body;
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
  return /session is closed/i.test(String(err)) ? "closed" : "busy";
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

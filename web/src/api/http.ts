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

/** What a 409 means (U6 review #10/#11): the session is closed for good, or a turn (or
 * another GM write) is running and a retry later will do. `null` for any other error. */
export function conflictKind(err: unknown): "closed" | "busy" | null {
  const text = String(err);
  if (!text.startsWith("Error: 409") && !text.startsWith("409")) return null;
  return /session is closed/i.test(text) ? "closed" : "busy";
}

export async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(BASE + path, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}: ${await res.text()}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

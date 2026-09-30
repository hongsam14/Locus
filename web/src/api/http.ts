// Shared fetch helper for the four boundary API modules (U1 §11.2).
import { lang } from "../i18n";

export const BASE = (import.meta as { env?: { VITE_API_URL?: string } }).env?.VITE_API_URL ?? "";

export const enc = encodeURIComponent;

/** Append the display language to a read whose response carries translated fields
 * (FD-U5 Q1=A), plus `say`, whose answer is generated in it. Not the timeline: it
 * carries no translated field and the backend does not take `lang` there. Write
 * routes stay as they are (their responses are not translated). */
export function withLang(path: string): string {
  return `${path}${path.includes("?") ? "&" : "?"}lang=${enc(lang())}`;
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

// A failed request as a sentence for people (V2 FR-D9, BLM § 6.2, BR-V2-16): by the
// server's `code` first, then by the HTTP status, then "could not reach the server",
// then "something unexpected". The original text is kept in `raw` for a folded detail —
// never mixed into the title.
import { HttpError, statusOf } from "../api/http";
import { dicts, lang as currentLang } from "../i18n";
import type { Lang } from "../types";

export type DescribedError = {
  title: string;
  action?: string;
  code?: string;
  status?: number;
  raw?: string;
};

// The code a status stands for when the body names none (same table as api/errors.py).
const STATUS_CODES: Record<number, string> = {
  400: "invalid_request",
  404: "not_found",
  405: "method_not_allowed",
  409: "conflict",
  413: "too_large",
  422: "validation_failed",
  500: "error",
  503: "service_unavailable",
};

const RAW_MAX = 300;

function line(lang: Lang, key: string): string | undefined {
  return dicts[lang][key] ?? dicts.ko[key];
}

function sentence(lang: Lang, code: string): { title: string; action?: string } {
  return {
    title: line(lang, `error.${code}.title`) ?? line(lang, "error.unknown.title") ?? code,
    action: line(lang, `error.${code}.action`),
  };
}

function detailText(detail: unknown, body: string): string {
  if (typeof detail === "string") return detail;
  if (detail && typeof detail === "object" && typeof (detail as { message?: unknown }).message === "string")
    return (detail as { message: string }).message;
  if (detail !== undefined) return JSON.stringify(detail);
  return body;
}

function clip(text: string): string {
  return text.length > RAW_MAX ? `${text.slice(0, RAW_MAX)}…` : text;
}

/** A `fetch` that never reached the server rejects with a TypeError whose message is the
 * browser's own: "Failed to fetch" (Chromium), "NetworkError when attempting to fetch
 * resource." (Firefox), "Load failed" (Safari), "fetch failed" (Node). Other TypeErrors —
 * "x.fetchAll is not a function" — are bugs, not the network (V2 review § 2). */
const NETWORK_MESSAGE = /^(failed to fetch|fetch failed|load failed|networkerror when attempting to fetch resource|network request failed)\b/i;
function isNetworkFailure(err: unknown): boolean {
  return err instanceof TypeError && NETWORK_MESSAGE.test(err.message);
}

export function describeError(err: unknown, lang: Lang = currentLang()): DescribedError {
  if (err instanceof HttpError) {
    const known = err.code && line(lang, `error.${err.code}.title`) != null ? err.code : undefined;
    const code = known ?? STATUS_CODES[err.status] ?? "error";
    const head = err.code ? `${err.status} · ${err.code}` : `${err.status}`;
    return {
      ...sentence(lang, code),
      code: err.code ?? code,
      status: err.status,
      raw: clip(`${head} · ${detailText(err.detail, err.body)}`),
    };
  }
  if (isNetworkFailure(err)) {
    return { ...sentence(lang, "network"), code: "network", raw: clip(String(err)) };
  }
  const status = statusOf(err); // an "Error: 409 …" from code that still throws text
  if (status != null) {
    const code = STATUS_CODES[status] ?? "error";
    return { ...sentence(lang, code), code, status, raw: clip(String(err)) };
  }
  return { ...sentence(lang, "unknown"), code: "unknown", raw: clip(String(err)) };
}

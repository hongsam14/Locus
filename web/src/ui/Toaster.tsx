import { useEffect } from "react";
import { t } from "../i18n";
import { dismissToast, useToasts, type ToastItem } from "./toast";

// V2 (BR-V2-22): one place for notifications, in the AppShell. The region is always there
// (a live region must exist before its content to be announced). Plain cards close after
// 6 s; a danger card stays until it is closed. Test ids are the old ones.
const AUTO_MS = 6000;

const DOT: Record<ToastItem["tone"], string> = {
  info: "bg-accent",
  event: "bg-event",
  danger: "bg-danger",
};

function Card({ item }: { item: ToastItem }) {
  useEffect(() => {
    if (item.tone === "danger") return;
    const timer = setTimeout(() => dismissToast(item.id), AUTO_MS);
    return () => clearTimeout(timer);
  }, [item.id, item.version, item.tone]);
  const danger = item.tone === "danger";
  return (
    <div
      data-testid={`notif-${item.key ?? item.id}`}
      data-region={item.region}
      role={danger ? "alert" : undefined}
      className={`flex items-start gap-3 rounded-lg border bg-sunken p-3 shadow-pop ${danger ? "border-tint-danger-line" : "border-line"}`}
    >
      <span className={`mt-2 h-2 w-2 flex-none rounded-full ${DOT[item.tone]}`} aria-hidden="true" />
      <div className="min-w-0 flex-1 text-sm">
        <div className={`font-bold ${danger ? "text-danger" : item.tone === "event" ? "text-event" : "text-fg"}`}>{item.title}</div>
        {item.body && <div className="text-muted">{item.body}</div>}
        {item.action && (
          <button type="button" className="mt-1 inline-flex min-h-11 items-center font-bold text-accent underline sm:min-h-0" onClick={item.action.onClick}>
            {item.action.label}
          </button>
        )}
      </div>
      <button
        type="button"
        aria-label={t("action.close")}
        className="inline-flex min-h-11 min-w-11 items-center justify-center rounded-md text-muted hover:bg-surface hover:text-fg sm:min-h-8 sm:min-w-8"
        onClick={() => dismissToast(item.id)}
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
          <path d="M6 6l12 12M18 6L6 18" />
        </svg>
      </button>
    </div>
  );
}

export function Toaster() {
  const items = useToasts();
  return (
    <div
      data-testid="notification-center"
      data-toaster=""
      aria-live="polite"
      className="pointer-events-none fixed right-3 top-3 z-50 flex w-[min(20rem,calc(100%-1.5rem))] flex-col gap-2 [&>*]:pointer-events-auto"
    >
      {items.map((item) => (
        <Card key={item.id} item={item} />
      ))}
    </div>
  );
}

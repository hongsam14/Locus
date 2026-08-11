import { useEffect } from "react";
import { Toast } from "./Toast";

export interface Notif {
  id: string;
  region_id: string;
  title: string;
  body: string;
}

/** Fixed top-right toast stack for per-region turn-change notifications
 * (FR-UX2.6 / Q1=A): one toast per changed region, auto-dismiss + manual close. */
export function NotificationCenter({
  items,
  onDismiss,
  autoDismissMs = 6000,
}: {
  items: Notif[];
  onDismiss: (id: string) => void;
  autoDismissMs?: number;
}) {
  if (items.length === 0) return null;
  return (
    <div
      data-testid="notification-center"
      className="fixed top-3 right-3 z-50 flex w-72 flex-col gap-2"
    >
      {items.map((n) => (
        <AutoToast key={n.id} notif={n} onDismiss={onDismiss} ms={autoDismissMs} />
      ))}
    </div>
  );
}

function AutoToast({
  notif,
  onDismiss,
  ms,
}: {
  notif: Notif;
  onDismiss: (id: string) => void;
  ms: number;
}) {
  useEffect(() => {
    const timer = setTimeout(() => onDismiss(notif.id), ms);
    return () => clearTimeout(timer);
  }, [notif.id, ms, onDismiss]);
  return (
    // testid keyed on the unique notification id (not region_id) so repeated
    // changes to the same region don't collide (review #6); region_id exposed
    // as a data attribute for automation that needs to target a region.
    <div data-testid={`notif-${notif.id}`} data-region={notif.region_id}>
      <Toast tone="event" title={notif.title} onClose={() => onDismiss(notif.id)}>
        {notif.body}
      </Toast>
    </div>
  );
}

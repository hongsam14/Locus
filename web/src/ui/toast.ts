// The one notification store (V2 FR-D4, BLM § 10, BR-V2-22). `toast()` adds a card; a card
// whose `key` is already showing is updated in place (its timer starts again) instead of
// stacking — an intended change from the old per-screen lists. Without a key cards stack.
import { useSyncExternalStore } from "react";

export type ToastTone = "info" | "event" | "danger";

export interface ToastInput {
  tone?: ToastTone;
  title: string;
  body?: string;
  key?: string;
  region?: string; // kept as data-region on the card (automation)
  action?: { label: string; onClick(): void };
}

export interface ToastItem extends ToastInput {
  id: string;
  tone: ToastTone;
  version: number; // bumps when a keyed card is updated, so its timer restarts
}

let items: ToastItem[] = [];
let seq = 0;
const listeners = new Set<() => void>();

function emit(): void {
  for (const fn of listeners) fn();
}

export function toast(input: ToastInput): string {
  const tone = input.tone ?? "info";
  const existing = input.key != null ? items.find((i) => i.key === input.key) : undefined;
  if (existing) {
    items = items.map((i) => (i === existing ? { ...existing, ...input, tone, version: existing.version + 1 } : i));
    emit();
    return existing.id;
  }
  const id = `t${++seq}`;
  items = [...items, { ...input, tone, id, version: 0 }];
  emit();
  return id;
}

export function dismissToast(id: string): void {
  items = items.filter((i) => i.id !== id);
  emit();
}

/** Tests: forget every card (setupTests calls it after each test — FD review R-10). */
export function clearToasts(): void {
  items = [];
  emit();
}

function subscribe(fn: () => void): () => void {
  listeners.add(fn);
  return () => listeners.delete(fn);
}

export function useToasts(): ToastItem[] {
  return useSyncExternalStore(subscribe, () => items, () => items);
}

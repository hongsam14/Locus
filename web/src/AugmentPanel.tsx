import { useState } from "react";
import { api } from "./api";
import type { AugSession } from "./types";
import { Button, Card, Panel } from "./ui";

export function AugmentPanel({ worldId }: { worldId: string }) {
  const [session, setSession] = useState<AugSession | null>(null);
  const [lastChange, setLastChange] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      setSession(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function answer(questionId: string, action: string) {
    if (!session) return;
    setBusy(true);
    try {
      const change = (await api.submitAnswer(session.id, {
        question_id: questionId,
        action,
      })) as { id?: string };
      if (change?.id) setLastChange(change.id);
      // re-detect: fetch a fresh session reflecting the applied change
      setSession(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function revert() {
    if (!session || !lastChange) return;
    try {
      await api.revertAugment(session.id, lastChange);
      setLastChange(null);
      setSession(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Panel data-testid="augment-panel" title="Knowledge augmentation" className="min-w-80">
      <div className="flex items-center gap-2">
        <Button data-testid="augment-start-btn" variant="primary" onClick={start} disabled={busy}>
          Start session
        </Button>
        {lastChange && (
          <Button data-testid="augment-revert-btn" onClick={revert}>
            Revert last
          </Button>
        )}
      </div>
      {error && <div className="text-danger mt-2">{error}</div>}
      {session && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="text-xs text-ink-soft">
            status: {session.status} · round {session.round}
          </div>
          {session.open_questions.length === 0 && <div>No open questions 🎉</div>}
          {session.open_questions.map((q) => (
            <Card key={q.id} className="flex flex-col gap-1.5">
              <div className="text-sm">{q.text}</div>
              <div className="flex flex-wrap gap-1.5">
                {q.options.map((opt) => (
                  <Button
                    key={opt}
                    size="sm"
                    data-testid="augment-answer-btn"
                    onClick={() => answer(q.id, opt)}
                    disabled={busy}
                  >
                    {opt}
                  </Button>
                ))}
              </div>
            </Card>
          ))}
        </div>
      )}
    </Panel>
  );
}

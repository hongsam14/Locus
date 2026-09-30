import { useState } from "react";
import { api } from "./api";
import type { AugRun } from "./types";
import { Button, Card, Panel } from "./ui";

export function AugmentPanel({ worldId }: { worldId: string }) {
  const [run, setRun] = useState<AugRun | null>(null);
  const [lastChange, setLastChange] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      setRun(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function answer(questionId: string, action: string) {
    if (!run) return;
    setBusy(true);
    try {
      const change = (await api.submitAnswer(run.id, {
        question_id: questionId,
        action,
      })) as { id?: string };
      if (change?.id) setLastChange(change.id);
      // re-detect: start a fresh run reflecting the applied change
      setRun(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    } finally {
      setBusy(false);
    }
  }

  async function revert() {
    if (!run || !lastChange) return;
    try {
      await api.revertAugment(run.id, lastChange);
      setLastChange(null);
      setRun(await api.startAugment(worldId));
    } catch (e) {
      setError(String(e));
    }
  }

  return (
    <Panel data-testid="augment-panel" title="Knowledge augmentation" className="min-w-80">
      <div className="flex items-center gap-2">
        <Button data-testid="augment-start-btn" variant="primary" onClick={start} disabled={busy}>
          Start run
        </Button>
        {lastChange && (
          <Button data-testid="augment-revert-btn" onClick={revert}>
            Revert last
          </Button>
        )}
      </div>
      {error && <div className="text-danger mt-2">{error}</div>}
      {run && (
        <div className="mt-2 flex flex-col gap-2">
          <div className="text-xs text-ink-soft">
            status: {run.status} · round {run.round}
          </div>
          {run.open_questions.length === 0 && <div>No open questions 🎉</div>}
          {run.open_questions.map((q) => (
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

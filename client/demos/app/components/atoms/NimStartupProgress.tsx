"use client";

import Card from "@/app/components/atoms/Card";
import { checkLabel, useNimStartup, type NimStartupStatus } from "@/app/hooks/useNimStartup";

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}m ${secs}s`;
}

export function NimStartupDetails({
  startup,
  ready,
  compact = false,
}: {
  startup?: NimStartupStatus | null;
  ready?: boolean;
  compact?: boolean;
}) {
  const phase = startup?.phase || "unknown";
  const message = startup?.message || "Waiting for model server status…";
  const elapsedSeconds = startup?.elapsed_s || 0;
  const checkEntries = Object.entries(startup?.checks || {});
  const logTail = startup?.log_tail || [];
  const startupError = startup?.error;

  if (ready) {
    if (compact) return null;
    return (
      <Card title="Model server">
        <p className="text-sm text-green-400">Model server is ready for detection.</p>
      </Card>
    );
  }

  const body = (
      <div className="space-y-3 text-sm">
        <p className="text-neutral-300">{message}</p>
        <p className="text-neutral-500">
          Phase: <strong className="text-neutral-200">{phase}</strong>
          {elapsedSeconds > 0 && <> · Elapsed: {formatElapsed(elapsedSeconds)}</>}
        </p>
        {startupError && <p className="text-red-400">{startupError}</p>}
        {checkEntries.length > 0 && (
          <ul className="grid gap-1 sm:grid-cols-2">
            {checkEntries.map(([key, done]) => (
              <li key={key} className={done ? "text-green-400" : "text-neutral-500"}>
                {done ? "✓" : "○"} {checkLabel(key)}
              </li>
            ))}
          </ul>
        )}
        {!compact && logTail.length > 0 && (
          <details className="rounded border border-neutral-800 bg-neutral-950/60 p-3">
            <summary className="cursor-pointer text-neutral-400">Recent model server logs</summary>
            <pre className="mt-2 max-h-48 overflow-auto whitespace-pre-wrap text-xs text-neutral-400">
              {logTail.join("\n")}
            </pre>
          </details>
        )}
        <p className="text-xs text-neutral-500">
          First startup may download Hugging Face weights (several minutes). Log:{" "}
          <code className="text-neutral-400">cai/config/svd_open_model.log</code>
        </p>
      </div>
  );

  if (compact) return body;
  return <Card title="Model server startup">{body}</Card>;
}

export default function NimStartupProgress({ compact = false }: { compact?: boolean }) {
  const { loading, ready, startup } = useNimStartup();

  if (loading && !startup) {
    return (
      <Card title="Model server">
        <p className="text-sm text-neutral-400">Loading model server status…</p>
      </Card>
    );
  }

  return <NimStartupDetails startup={startup} ready={ready} compact={compact} />;
}

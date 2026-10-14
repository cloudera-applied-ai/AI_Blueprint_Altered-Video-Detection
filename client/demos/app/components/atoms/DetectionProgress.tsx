"use client";

export type DetectPhase =
  | "idle"
  | "uploading"
  | "connecting"
  | "analyzing"
  | "finalizing"
  | "done"
  | "error";

type Props = {
  phase: DetectPhase;
  message: string;
  clipsDone: number;
  totalClips: number | null;
  elapsedSeconds: number;
};

const STEPS: Array<{ id: DetectPhase; label: string; hint: string }> = [
  { id: "uploading", label: "Upload", hint: "Video sent to the app" },
  { id: "connecting", label: "Connect", hint: "gRPC session to NIM" },
  { id: "analyzing", label: "Analyze", hint: "Clip scores streaming" },
  { id: "finalizing", label: "Summarize", hint: "Aggregate probability" },
];

function stepIndex(phase: DetectPhase): number {
  if (phase === "uploading") return 0;
  if (phase === "connecting") return 1;
  if (phase === "analyzing") return 2;
  if (phase === "finalizing" || phase === "done") return 3;
  return -1;
}

export default function DetectionProgress({
  phase,
  message,
  clipsDone,
  totalClips,
  elapsedSeconds,
}: Props) {
  if (phase === "idle" || phase === "error") return null;

  const active = stepIndex(phase);
  const clipLabel =
    totalClips != null && totalClips > 0
      ? `${clipsDone} / ${totalClips} clips`
      : clipsDone > 0
        ? `${clipsDone} clips analyzed`
        : null;

  const activeHint = active >= 0 ? STEPS[active]?.hint : "";

  return (
    <div className="mt-4 rounded-lg border border-neutral-700/80 bg-neutral-900/60 p-4">
      <div className="mb-1 flex items-center justify-between text-sm">
        <span className="font-medium text-[var(--nvidia-green)]">{message || "Working…"}</span>
        <span className="text-neutral-500">{elapsedSeconds}s</span>
      </div>
      {activeHint && phase !== "done" && (
        <p className="mb-3 text-xs text-neutral-500">{activeHint}</p>
      )}

      <div className="mb-3 h-2 overflow-hidden rounded-full bg-neutral-800">
        <div
          className="h-full rounded-full bg-[var(--nvidia-green)] transition-all duration-500"
          style={{
            width:
              phase === "done"
                ? "100%"
                : totalClips && clipsDone > 0
                  ? `${Math.min(95, Math.round((clipsDone / totalClips) * 100))}%`
                  : `${Math.min(90, 15 + active * 20)}%`,
          }}
        />
      </div>

      <ol className="flex flex-wrap gap-4 text-xs text-neutral-400">
        {STEPS.map((step, index) => {
          const done = active > index || phase === "done";
          const current = active === index && phase !== "done";
          return (
            <li
              key={step.id}
              className={
                done
                  ? "text-green-400"
                  : current
                    ? "text-[var(--nvidia-green)]"
                    : "text-neutral-600"
              }
            >
              {done ? "✓" : current ? "●" : "○"} {step.label}
            </li>
          );
        })}
      </ol>

      {clipLabel && <p className="mt-2 text-xs text-neutral-500">{clipLabel}</p>}
    </div>
  );
}

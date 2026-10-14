"use client";

const SERVERLESS_STEPS = [
  {
    title: "Upload & validate",
    body: "Your H.264 MP4 is streamed to NVIDIA Synthetic Video Detector on Cloud Functions over gRPC.",
  },
  {
    title: "Temporal clip analysis",
    body: "The hosted model returns clip-level logits aligned to frames on the timeline.",
  },
  {
    title: "Stream results",
    body: "Scores arrive incrementally over gRPC while inference runs.",
  },
  {
    title: "Aggregate verdict",
    body: "Final synthetic probability and timeline chart against your threshold.",
  },
];

const BUNDLED_STEPS = [
  {
    title: "Upload & validate",
    body: "Video stays in your GPU application—no external inference API required for the bundled path.",
  },
  {
    title: "Temporal analysis",
    body: "Each selected Hugging Face model (VideoMAE or frame classifier) scores clips in-pod.",
  },
  {
    title: "Stream results",
    body: "The in-pod model server returns the same clip and aggregate result shape as Detect expects.",
  },
  {
    title: "Consensus verdict",
    body: "Per-model scores combine via your chosen strategy (majority vote, unanimous, any, or mean) against the threshold.",
  },
];

export default function DetectionPipelineExplainer({ deployMode }: { deployMode: string }) {
  const mode = String(deployMode).toUpperCase();
  const bundled = mode === "BUNDLED" || mode === "OPEN" || mode === "OPEN_WEIGHTS";
  const steps = bundled ? BUNDLED_STEPS : SERVERLESS_STEPS;

  return (
    <section className="rounded-xl border border-[var(--border)] bg-gradient-to-br from-[var(--surface)] via-[var(--surface)] to-[#0a1205] p-6 shadow-[var(--shadow-card)]">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">
            Detection pipeline
          </p>
          <h2 className="text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Clip-level synthetic media analysis
          </h2>
        </div>
        <span className="inline-flex w-fit rounded-full border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-1 text-xs text-[var(--text-muted)]">
          {bundled ? "Bundled" : "Serverless"}
        </span>
      </div>
      <p className="mb-6 max-w-3xl text-sm leading-relaxed text-[var(--text-secondary)]">
        {bundled
          ? "Bundled runtimes run Hugging Face presets entirely in your GPU application. Scores reflect the selected open-weights model—not NVIDIA-hosted Synthetic Video Detector inference."
          : "Serverless runtimes use your NGC credentials to call NVIDIA-hosted Synthetic Video Detector inference on Cloud Functions."}
      </p>
      <ol className="grid gap-4 sm:grid-cols-2">
        {steps.map((step, i) => (
          <li
            key={step.title}
            className="rounded-lg border border-[var(--border)] bg-black/30 p-4"
          >
            <div className="mb-2 flex items-center gap-2">
              <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--accent-muted)] text-xs font-bold text-[var(--accent)]">
                {i + 1}
              </span>
              <h3 className="text-sm font-medium text-[var(--text-primary)]">{step.title}</h3>
            </div>
            <p className="text-xs leading-relaxed text-[var(--text-muted)]">{step.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

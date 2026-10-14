"use client";

import type { OpenModelPreset } from "@/app/lib/openModels";

type Props = {
  preset: OpenModelPreset | null;
  onClose: () => void;
};

export default function ModelPresetInfoModal({ preset, onClose }: Props) {
  if (!preset) return null;

  const info = preset.more_info;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="preset-info-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
        aria-label="Close"
        onClick={onClose}
      />
      <div className="relative z-10 max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-[var(--border)] bg-[var(--surface)] p-6 shadow-xl">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-[var(--accent)]">Model preset</p>
            <h2 id="preset-info-title" className="mt-1 text-lg font-semibold text-[var(--text-primary)]">
              {preset.name}
            </h2>
            <p className="mt-1 text-sm text-[var(--text-muted)]">{preset.subtitle}</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="rounded-md border border-[var(--border)] px-2 py-1 text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)]"
          >
            Close
          </button>
        </div>

        <p className="mt-4 text-sm leading-relaxed text-[var(--text-secondary)]">{preset.summary}</p>

        {info ? (
          <div className="mt-5 space-y-4 text-sm text-[var(--text-secondary)]">
            {info.what_it_offers ? (
              <section>
                <h3 className="font-medium text-[var(--text-primary)]">What it offers</h3>
                <p className="mt-1 leading-relaxed">{info.what_it_offers}</p>
              </section>
            ) : null}
            {info.best_for ? (
              <section>
                <h3 className="font-medium text-[var(--text-primary)]">Best for</h3>
                <p className="mt-1 leading-relaxed">{info.best_for}</p>
              </section>
            ) : null}
            {info.limitations ? (
              <section>
                <h3 className="font-medium text-[var(--text-primary)]">Limitations</h3>
                <p className="mt-1 leading-relaxed">{info.limitations}</p>
              </section>
            ) : null}
            {info.highlights && info.highlights.length > 0 ? (
              <section>
                <h3 className="font-medium text-[var(--text-primary)]">Model card highlights</h3>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  {info.highlights.map((item) => (
                    <li key={item}>{item}</li>
                  ))}
                </ul>
              </section>
            ) : null}
          </div>
        ) : null}

        {preset.metrics_hint ? (
          <p className="mt-4 border-t border-[var(--border)] pt-4 text-xs text-[var(--text-muted)]">
            {preset.metrics_hint}
          </p>
        ) : null}

        <p className="mt-3 font-mono text-[11px] text-neutral-500">{preset.hf_model_id}</p>

        <a
          href={preset.hf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-5 inline-flex w-full items-center justify-center rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black transition hover:brightness-110"
        >
          View model on Hugging Face
        </a>
      </div>
    </div>
  );
}

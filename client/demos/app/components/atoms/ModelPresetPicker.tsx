"use client";

import { useState } from "react";
import type { OpenModelCatalog, OpenModelPreset } from "@/app/lib/openModels";
import ModelPresetInfoModal from "@/app/components/atoms/ModelPresetInfoModal";

type Props = {
  catalog: OpenModelCatalog;
  selectedId: string;
  onSelect: (preset: OpenModelPreset) => void;
  disabled?: boolean;
};

export default function ModelPresetPicker({ catalog, selectedId, onSelect, disabled }: Props) {
  const [infoPreset, setInfoPreset] = useState<OpenModelPreset | null>(null);

  return (
    <>
      <ModelPresetInfoModal preset={infoPreset} onClose={() => setInfoPreset(null)} />
      <div className="grid gap-4 lg:grid-cols-3">
      {catalog.presets.map((preset) => {
        const active = preset.id === selectedId;
        return (
          <button
            key={preset.id}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(preset)}
            className={`group relative flex h-full flex-col rounded-xl border p-5 text-left transition-all ${
              active
                ? "border-[var(--accent)] bg-[var(--accent-muted)] shadow-[0_0_0_1px_var(--accent)]"
                : "border-[var(--border)] bg-[var(--surface)] hover:border-neutral-600 hover:bg-[var(--surface-elevated)]"
            } ${disabled ? "cursor-not-allowed opacity-60" : "cursor-pointer"}`}
          >
            {preset.recommended && (
              <span className="absolute right-4 top-4 rounded-full bg-[var(--accent)] px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-black">
                Recommended
              </span>
            )}
            <div className="mb-3 pr-16">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">{preset.name}</h3>
              <p className="mt-1 text-xs text-[var(--text-muted)]">{preset.subtitle}</p>
            </div>
            <p className="mb-4 flex-1 text-sm leading-relaxed text-[var(--text-secondary)]">
              {preset.summary}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {(preset.tags || []).map((tag) => (
                <span
                  key={tag}
                  className="rounded-md border border-[var(--border)] bg-black/30 px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]"
                >
                  {tag}
                </span>
              ))}
              {preset.vram_gb ? (
                <span className="rounded-md border border-[var(--border)] bg-black/30 px-2 py-0.5 text-[10px] font-medium text-[var(--text-muted)]">
                  ~{preset.vram_gb} GB VRAM
                </span>
              ) : null}
            </div>
            {preset.metrics_hint ? (
              <p className="mt-3 border-t border-[var(--border)] pt-3 text-[11px] text-[var(--text-muted)]">
                {preset.metrics_hint}
              </p>
            ) : null}
            <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-[var(--border)] pt-3">
              <button
                type="button"
                disabled={disabled}
                onClick={(e) => {
                  e.stopPropagation();
                  setInfoPreset(preset);
                }}
                className="rounded-md border border-[var(--border)] bg-black/30 px-2.5 py-1 text-[11px] font-medium text-[var(--accent)] hover:bg-[var(--surface-elevated)] disabled:opacity-50"
              >
                More info
              </button>
              <span className="truncate font-mono text-[10px] text-neutral-500">{preset.hf_model_id}</span>
            </div>
          </button>
        );
      })}
      </div>
    </>
  );
}

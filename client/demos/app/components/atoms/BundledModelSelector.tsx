"use client";

import { useMemo, useState } from "react";
import ModelPresetInfoModal from "@/app/components/atoms/ModelPresetInfoModal";
import type {
  OpenConsensusStrategy,
  OpenModelCatalog,
  OpenModelEntry,
  OpenModelPreset,
} from "@/app/lib/openModels";
import { entriesFromPreset, entryKey, presetById } from "@/app/lib/openModels";

const inputClass =
  "mt-1.5 w-full rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]";

type Props = {
  catalog: OpenModelCatalog;
  models: OpenModelEntry[];
  consensus: OpenConsensusStrategy;
  disabled?: boolean;
  onChange: (models: OpenModelEntry[], consensus: OpenConsensusStrategy) => void;
};

const CONSENSUS_OPTIONS: { id: OpenConsensusStrategy; label: string; hint: string }[] = [
  {
    id: "majority",
    label: "Majority vote",
    hint: "Synthetic when more than half of models flag synthetic at the threshold.",
  },
  {
    id: "unanimous",
    label: "Unanimous",
    hint: "Synthetic only when every selected model flags synthetic.",
  },
  {
    id: "any",
    label: "Any model",
    hint: "Synthetic when at least one model flags synthetic.",
  },
  {
    id: "mean",
    label: "Mean score",
    hint: "Use the average synthetic probability across models (no vote).",
  },
];

export default function BundledModelSelector({
  catalog,
  models,
  consensus,
  disabled,
  onChange,
}: Props) {
  const [infoPreset, setInfoPreset] = useState<OpenModelPreset | null>(null);
  const [customId, setCustomId] = useState("");
  const [customKind, setCustomKind] = useState<"image" | "videomae">("image");

  const selectedKeys = useMemo(() => new Set(models.map(entryKey)), [models]);

  const togglePreset = (preset: OpenModelPreset) => {
    const key = preset.hf_model_id.toLowerCase();
    if (selectedKeys.has(key)) {
      const next = models.filter((m) => entryKey(m) !== key);
      onChange(next.length ? next : [entriesFromPreset(preset)], consensus);
      return;
    }
    onChange([...models, entriesFromPreset(preset)], consensus);
  };

  const addCustom = () => {
    const hf = customId.trim();
    if (!hf) return;
    const key = hf.toLowerCase();
    if (selectedKeys.has(key)) return;
    onChange(
      [...models, { hf_model_id: hf, kind: customKind, label: "Custom" }],
      consensus,
    );
    setCustomId("");
  };

  const removeEntry = (key: string) => {
    const next = models.filter((m) => entryKey(m) !== key);
    onChange(next, consensus);
  };

  return (
    <>
      <ModelPresetInfoModal preset={infoPreset} onClose={() => setInfoPreset(null)} />

      <div className="space-y-6">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Curated presets</h3>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Select one or more Hugging Face checkpoints. Bundled mode loads all selected models in
            the GPU pod.
          </p>
          <div className="mt-4 grid gap-3 lg:grid-cols-3">
            {catalog.presets.map((preset) => {
              const active = selectedKeys.has(preset.hf_model_id.toLowerCase());
              return (
                <div
                  key={preset.id}
                  className={`rounded-xl border p-4 transition ${
                    active
                      ? "border-[var(--accent)] bg-[var(--accent-muted)]"
                      : "border-[var(--border)] bg-[var(--surface)]"
                  }`}
                >
                  <label className="flex cursor-pointer items-start gap-3">
                    <input
                      type="checkbox"
                      className="mt-1"
                      disabled={disabled}
                      checked={active}
                      onChange={() => togglePreset(preset)}
                    />
                    <span className="flex-1">
                      <span className="block text-sm font-semibold text-[var(--text-primary)]">
                        {preset.name}
                      </span>
                      <span className="mt-0.5 block text-xs text-[var(--text-muted)]">
                        {preset.subtitle}
                      </span>
                    </span>
                  </label>
                  <div className="mt-3 flex flex-wrap gap-2 pl-7">
                    <button
                      type="button"
                      disabled={disabled}
                      onClick={() => setInfoPreset(preset)}
                      className="rounded-md border border-[var(--border)] px-2 py-0.5 text-[11px] text-[var(--accent)]"
                    >
                      More info
                    </button>
                    <span className="truncate font-mono text-[10px] text-neutral-500">
                      {preset.hf_model_id}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="rounded-xl border border-[var(--border)] bg-black/20 p-4">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Custom Hugging Face model</h3>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            Add any public (or gated, with token) image-classifier or VideoMAE checkpoint.
          </p>
          <div className="mt-3 grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
            <label className="text-sm font-medium text-[var(--text-primary)]">
              Model ID
              <input
                className={inputClass}
                disabled={disabled}
                value={customId}
                onChange={(e) => setCustomId(e.target.value)}
                placeholder="org/model-name"
              />
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)]">
              Kind
              <select
                className={inputClass}
                disabled={disabled}
                value={customKind}
                onChange={(e) => setCustomKind(e.target.value as "image" | "videomae")}
              >
                <option value="image">Frame classifier</option>
                <option value="videomae">VideoMAE</option>
              </select>
            </label>
            <button
              type="button"
              className="rounded-lg border border-[var(--border)] px-4 py-2.5 text-sm font-medium hover:bg-neutral-800 disabled:opacity-50"
              disabled={disabled || !customId.trim()}
              onClick={addCustom}
            >
              Add model
            </button>
          </div>
        </div>

        {models.length > 0 && (
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4">
            <h3 className="text-sm font-semibold text-[var(--text-primary)]">
              Selected models ({models.length})
            </h3>
            <ul className="mt-3 space-y-2">
              {models.map((entry) => {
                const preset = entry.preset_id ? presetById(catalog, entry.preset_id) : undefined;
                const key = entryKey(entry);
                return (
                  <li
                    key={key}
                    className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--border)] bg-black/30 px-3 py-2 text-sm"
                  >
                    <div>
                      <span className="font-medium text-[var(--text-primary)]">
                        {entry.label || preset?.name || entry.hf_model_id}
                      </span>
                      <span className="ml-2 text-xs text-[var(--text-muted)]">{entry.kind}</span>
                      <p className="font-mono text-[10px] text-neutral-500">{entry.hf_model_id}</p>
                    </div>
                    <button
                      type="button"
                      disabled={disabled || models.length <= 1}
                      onClick={() => removeEntry(key)}
                      className="text-xs text-red-400 hover:underline disabled:opacity-40"
                    >
                      Remove
                    </button>
                  </li>
                );
              })}
            </ul>
          </div>
        )}

        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Consensus</h3>
          <p className="mt-1 text-xs text-[var(--text-muted)]">
            How to combine model outputs into a final synthetic / real verdict (bundled only).
          </p>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {CONSENSUS_OPTIONS.map((opt) => (
              <label
                key={opt.id}
                className={`flex cursor-pointer gap-3 rounded-lg border p-3 ${
                  consensus === opt.id
                    ? "border-[var(--accent)] bg-[var(--accent-muted)]"
                    : "border-[var(--border)] bg-[var(--surface)]"
                }`}
              >
                <input
                  type="radio"
                  name="open-consensus"
                  disabled={disabled}
                  checked={consensus === opt.id}
                  onChange={() => onChange(models, opt.id)}
                />
                <span>
                  <span className="block text-sm font-medium text-[var(--text-primary)]">
                    {opt.label}
                  </span>
                  <span className="block text-xs text-[var(--text-muted)]">{opt.hint}</span>
                </span>
              </label>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}

export type OpenModelPresetMoreInfo = {
  what_it_offers?: string;
  best_for?: string;
  limitations?: string;
  highlights?: string[];
};

export type OpenModelPreset = {
  id: string;
  name: string;
  subtitle: string;
  hf_model_id: string;
  kind: "image" | "videomae";
  recommended?: boolean;
  vram_gb?: number;
  tags?: string[];
  summary: string;
  metrics_hint?: string;
  hf_url: string;
  more_info?: OpenModelPresetMoreInfo;
};

export type OpenModelCatalog = {
  default_preset_id: string;
  presets: OpenModelPreset[];
};

export type OpenModelEntry = {
  hf_model_id: string;
  kind: "image" | "videomae";
  preset_id?: string;
  label?: string;
};

export type OpenConsensusStrategy = "majority" | "unanimous" | "any" | "mean";

export function presetById(catalog: OpenModelCatalog, id: string): OpenModelPreset | undefined {
  return catalog.presets.find((p) => p.id === id);
}

export function entryKey(entry: OpenModelEntry): string {
  return entry.hf_model_id.trim().toLowerCase();
}

export function entriesFromPreset(preset: OpenModelPreset): OpenModelEntry {
  return {
    hf_model_id: preset.hf_model_id,
    kind: preset.kind,
    preset_id: preset.id,
    label: preset.name,
  };
}

export function parseOpenModelEntries(raw: unknown): OpenModelEntry[] {
  if (!Array.isArray(raw)) return [];
  const out: OpenModelEntry[] = [];
  const seen = new Set<string>();
  for (const item of raw) {
    if (!item || typeof item !== "object") continue;
    const row = item as Record<string, unknown>;
    const hf = String(row.hf_model_id || "").trim();
    if (!hf) continue;
    const key = hf.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    const kind = row.kind === "videomae" ? "videomae" : "image";
    const entry: OpenModelEntry = { hf_model_id: hf, kind };
    const presetId = String(row.preset_id || "").trim();
    if (presetId) entry.preset_id = presetId;
    const label = String(row.label || "").trim();
    if (label) entry.label = label;
    out.push(entry);
  }
  return out;
}

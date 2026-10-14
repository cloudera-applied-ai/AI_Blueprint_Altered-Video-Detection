export type ClipPoint = {
  index: number;
  score: number;
  logit?: number;
};

export type ModelConsensusRow = {
  hf_model_id: string;
  kind?: string;
  preset_id?: string | null;
  probability: number;
  is_synthetic: boolean;
  total_clips?: number;
};

export type DetectionConsensus = {
  strategy: string;
  threshold: number;
  votes_fake: number;
  votes_real: number;
  model_count: number;
  models: ModelConsensusRow[];
};

export type DetectionResult = {
  probability: number;
  logit?: number;
  synthetic_score_percent: number;
  is_synthetic: boolean;
  total_clips: number;
  threshold: number;
  clip_series: ClipPoint[];
  csv_data?: string;
  consensus?: DetectionConsensus;
};

export function parseClipSeriesFromCsv(csv: string): ClipPoint[] {
  const lines = csv.trim().split("\n");
  if (lines.length < 2) return [];
  const points: ClipPoint[] = [];
  for (let i = 1; i < lines.length; i += 1) {
    const [indexRaw, logitRaw] = lines[i]!.split(",");
    const index = Number(indexRaw);
    const logit = Number(logitRaw);
    if (!Number.isFinite(index) || !Number.isFinite(logit)) continue;
    points.push({ index, logit, score: expit(logit) });
  }
  return points;
}

export function expit(logit: number): number {
  if (logit >= 0) return 1 / (1 + Math.exp(-logit));
  const e = Math.exp(logit);
  return e / (1 + e);
}

export function clipTimeSeconds(index: number, maxIndex: number, durationSec: number): number {
  if (maxIndex <= 0 || durationSec <= 0) return 0;
  return (index / maxIndex) * durationSec;
}

"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { DetectPhase } from "@/app/components/atoms/DetectionProgress";
import type { ClipPoint, DetectionConsensus, DetectionResult } from "@/app/lib/detectionTypes";
import { parseClipSeriesFromCsv } from "@/app/lib/detectionTypes";

export type { DetectionResult };

type StreamEvent = {
  type?: string;
  phase?: string;
  message?: string;
  clips_done?: number;
  total_clips?: number;
  index?: number;
  logit?: number;
  score?: number;
  error?: string;
  synthetic_score_percent?: number;
  is_synthetic?: boolean;
  probability?: number;
  threshold?: number;
  clip_series?: ClipPoint[];
  csv_data?: string;
  logit_final?: number;
  consensus?: DetectionConsensus;
};

function buildResult(event: StreamEvent): DetectionResult {
  let clipSeries = event.clip_series ?? [];
  if (clipSeries.length === 0 && event.csv_data) {
    clipSeries = parseClipSeriesFromCsv(event.csv_data);
  }
  return {
    probability: Number(event.probability ?? 0),
    logit: event.logit,
    synthetic_score_percent: Number(event.synthetic_score_percent ?? 0),
    is_synthetic: Boolean(event.is_synthetic),
    total_clips: Number(event.total_clips ?? clipSeries.length),
    threshold: Number(event.threshold ?? 0.05),
    clip_series: clipSeries,
    csv_data: event.csv_data,
    consensus: event.consensus,
  };
}

export function useVideoDetection() {
  const [busy, setBusy] = useState(false);
  const [phase, setPhase] = useState<DetectPhase>("idle");
  const [progressMessage, setProgressMessage] = useState("");
  const [clipsDone, setClipsDone] = useState(0);
  const [totalClips, setTotalClips] = useState<number | null>(null);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [clipSeriesLive, setClipSeriesLive] = useState<ClipPoint[]>([]);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const clipMapRef = useRef<Map<number, ClipPoint>>(new Map());

  useEffect(() => {
    if (!busy) {
      if (timerRef.current) clearInterval(timerRef.current);
      return;
    }
    setElapsedSeconds(0);
    timerRef.current = setInterval(() => setElapsedSeconds((s) => s + 1), 1000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [busy]);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
    setPhase("idle");
    setClipsDone(0);
    setTotalClips(null);
    setProgressMessage("");
    setClipSeriesLive([]);
    clipMapRef.current.clear();
  }, []);

  const appendClip = useCallback((index: number, score: number, logit?: number) => {
    clipMapRef.current.set(index, { index, score, logit });
    const next = [...clipMapRef.current.values()].sort((a, b) => a.index - b.index);
    setClipSeriesLive(next);
  }, []);

  const applyStreamEvent = useCallback(
    (event: StreamEvent) => {
      if (event.type === "phase" && event.phase) {
        setPhase(event.phase as DetectPhase);
        if (event.message) setProgressMessage(event.message);
        if (typeof event.total_clips === "number") setTotalClips(event.total_clips);
      }
      if (event.type === "clip") {
        setPhase("analyzing");
        if (typeof event.clips_done === "number") setClipsDone(event.clips_done);
        else if (typeof event.index === "number") setClipsDone(event.index + 1);
        if (typeof event.index === "number" && typeof event.score === "number") {
          appendClip(event.index, event.score, event.logit);
        }
        setProgressMessage("Analyzing video clips on GPU…");
      }
      if (event.type === "done" || event.type === "result") {
        setPhase("done");
        setProgressMessage("Detection complete");
        if (typeof event.total_clips === "number") setTotalClips(event.total_clips);
        const built = buildResult(event);
        setResult(built);
        if (built.clip_series.length) setClipSeriesLive(built.clip_series);
      }
      if (event.type === "error") {
        setPhase("error");
        setError(event.error || "Detection failed");
      }
    },
    [appendClip],
  );

  const runDetection = useCallback(
    async (file: File) => {
      setBusy(true);
      setError(null);
      setResult(null);
      setClipsDone(0);
      setTotalClips(null);
      setClipSeriesLive([]);
      clipMapRef.current.clear();
      setPhase("uploading");
      setProgressMessage("Uploading video…");

      const form = new FormData();
      form.append("video", file);

      try {
        let res = await fetch("/api/detect?stream=1", { method: "POST", body: form });
        if (!res.ok && res.headers.get("content-type")?.includes("json")) {
          const data = (await res.json().catch(() => ({}))) as { error?: string };
          throw new Error(data.error || "Detection failed");
        }
        if (!res.ok || !res.body) {
          setPhase("analyzing");
          setProgressMessage("Analyzing video…");
          res = await fetch("/api/detect", { method: "POST", body: form });
          if (!res.ok) {
            const data = (await res.json().catch(() => ({}))) as { error?: string };
            throw new Error(data.error || "Detection failed");
          }
          const data = (await res.json()) as StreamEvent;
          applyStreamEvent({ type: "done", ...data });
          return;
        }

        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            applyStreamEvent(JSON.parse(line) as StreamEvent);
          }
        }
        if (buffer.trim()) {
          applyStreamEvent(JSON.parse(buffer) as StreamEvent);
        }
      } catch (err) {
        setPhase("error");
        setError(err instanceof Error ? err.message : "Detection failed");
      } finally {
        setBusy(false);
      }
    },
    [applyStreamEvent],
  );

  return {
    busy,
    phase,
    progressMessage,
    clipsDone,
    totalClips,
    elapsedSeconds,
    result,
    clipSeriesLive,
    error,
    reset,
    runDetection,
  };
}

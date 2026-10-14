"use client";

import { useCallback, useEffect, useId, useMemo, useRef, useState } from "react";
import type { ClipPoint } from "@/app/lib/detectionTypes";
import { clipTimeSeconds } from "@/app/lib/detectionTypes";

type Props = {
  clipSeries: ClipPoint[];
  threshold: number;
  videoDurationSec: number | null;
  playheadSec: number;
  live?: boolean;
};

const CHART_HEIGHT = 220;
const PAD = { top: 12, right: 12, bottom: 28, left: 40 };

export default function SyntheticScoreChart({
  clipSeries,
  threshold,
  videoDurationSec,
  playheadSec,
  live = false,
}: Props) {
  const descId = useId();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(560);

  const sorted = useMemo(
    () => [...clipSeries].sort((a, b) => a.index - b.index),
    [clipSeries],
  );

  const maxIndex = useMemo(
    () => (sorted.length ? Math.max(...sorted.map((p) => p.index)) : 0),
    [sorted],
  );

  const duration = videoDurationSec && videoDurationSec > 0 ? videoDurationSec : maxIndex > 0 ? 1 : 1;

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!canvas || !container) return;

    const dpr = window.devicePixelRatio || 1;
    const cssW = container.clientWidth;
    const cssH = CHART_HEIGHT;
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const plotW = cssW - PAD.left - PAD.right;
    const plotH = cssH - PAD.top - PAD.bottom;

    ctx.fillStyle = "#0d0d0d";
    ctx.fillRect(0, 0, cssW, cssH);

    ctx.strokeStyle = "#333";
    ctx.lineWidth = 1;
    ctx.strokeRect(PAD.left, PAD.top, plotW, plotH);

    const yForScore = (score: number) => PAD.top + plotH * (1 - Math.min(1, Math.max(0, score)));

    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = "#76b900";
    ctx.globalAlpha = 0.55;
    const threshY = yForScore(threshold);
    ctx.beginPath();
    ctx.moveTo(PAD.left, threshY);
    ctx.lineTo(PAD.left + plotW, threshY);
    ctx.stroke();
    ctx.setLineDash([]);
    ctx.globalAlpha = 1;

    ctx.fillStyle = "#737373";
    ctx.font = "11px system-ui, sans-serif";
    ctx.fillText("1.0", 4, PAD.top + 4);
    ctx.fillText("0.0", 4, PAD.top + plotH);
    ctx.fillText(`${Math.round(threshold * 100)}% threshold`, PAD.left + 4, threshY - 4);

    if (sorted.length === 0) {
      ctx.fillStyle = "#525252";
      ctx.font = "13px system-ui, sans-serif";
      ctx.fillText(
        live ? "Waiting for clip scores…" : "Run detection to see scores over time",
        PAD.left + 8,
        PAD.top + plotH / 2,
      );
      return;
    }

    const xForTime = (t: number) => PAD.left + (t / duration) * plotW;

    ctx.strokeStyle = "#3b82f6";
    ctx.lineWidth = 2;
    ctx.beginPath();
    sorted.forEach((point, i) => {
      const t = clipTimeSeconds(point.index, maxIndex, duration);
      const x = xForTime(t);
      const y = yForScore(point.score);
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    });
    ctx.stroke();

    ctx.fillStyle = "#76b900";
    sorted.forEach((point) => {
      const t = clipTimeSeconds(point.index, maxIndex, duration);
      const x = xForTime(t);
      const y = yForScore(point.score);
      ctx.beginPath();
      ctx.arc(x, y, 2.5, 0, Math.PI * 2);
      ctx.fill();
    });

    if (playheadSec >= 0 && duration > 0) {
      const px = xForTime(Math.min(playheadSec, duration));
      ctx.strokeStyle = "#f5f5f5";
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(px, PAD.top);
      ctx.lineTo(px, PAD.top + plotH);
      ctx.stroke();
    }

    ctx.fillStyle = "#737373";
    ctx.fillText("0:00", PAD.left, cssH - 6);
    const endLabel =
      duration >= 60
        ? `${Math.floor(duration / 60)}:${String(Math.floor(duration % 60)).padStart(2, "0")}`
        : `${duration.toFixed(1)}s`;
    ctx.fillText(endLabel, PAD.left + plotW - 28, cssH - 6);
  }, [sorted, maxIndex, duration, threshold, playheadSec, live]);

  useEffect(() => {
    draw();
    const ro = new ResizeObserver(() => {
      setWidth(containerRef.current?.clientWidth ?? 560);
    });
    if (containerRef.current) ro.observe(containerRef.current);
    return () => ro.disconnect();
  }, [draw, width]);

  return (
    <div ref={containerRef} className="w-full overflow-hidden rounded-md border border-neutral-700 bg-neutral-900/80 p-2">
      <canvas
        ref={canvasRef}
        role="img"
        aria-labelledby={descId}
        className="block w-full cursor-crosshair"
      />
      <p id={descId} className="sr-only">
        Line chart of synthetic likelihood from 0 to 1 across video duration. Threshold{" "}
        {Math.round(threshold * 100)} percent.
      </p>
    </div>
  );
}

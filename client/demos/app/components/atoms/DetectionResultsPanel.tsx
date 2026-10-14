"use client";

import { useEffect, useRef, useState } from "react";
import type { ClipPoint, DetectionResult } from "@/app/lib/detectionTypes";
import DetectionResultSummary from "@/app/components/atoms/DetectionResultSummary";
import SyntheticScoreChart from "@/app/components/atoms/SyntheticScoreChart";

type Props = {
  result: DetectionResult | null;
  clipSeriesLive: ClipPoint[];
  threshold: number;
  analyzing: boolean;
  videoDurationSec?: number | null;
  playheadSec?: number;
  /** Show a dedicated preview player inside the panel (demo cards). */
  embedVideo?: boolean;
  videoSrc?: string | null;
  compact?: boolean;
};

export default function DetectionResultsPanel({
  result,
  clipSeriesLive,
  threshold,
  analyzing,
  videoDurationSec = null,
  playheadSec = 0,
  embedVideo = false,
  videoSrc = null,
  compact = false,
}: Props) {
  const embedRef = useRef<HTMLVideoElement>(null);
  const [embedDuration, setEmbedDuration] = useState<number | null>(null);
  const [embedPlayhead, setEmbedPlayhead] = useState(0);

  const series = result?.clip_series?.length ? result.clip_series : clipSeriesLive;
  const effectiveThreshold = result?.threshold ?? threshold;
  const duration = embedVideo ? embedDuration : videoDurationSec;
  const playhead = embedVideo ? embedPlayhead : playheadSec;

  useEffect(() => {
    setEmbedPlayhead(0);
    setEmbedDuration(null);
  }, [videoSrc, embedVideo]);

  return (
    <div className="flex h-full flex-col gap-5">
      {!compact && (
        <div className="border-b border-neutral-800 pb-2">
          <h2 className="text-lg font-medium text-neutral-100">Output</h2>
          <p className="text-xs text-neutral-500">
            Overall verdict plus per-clip synthetic likelihood over the video timeline.
          </p>
        </div>
      )}

      {result ? (
        <DetectionResultSummary result={result} />
      ) : (
        <div className="rounded-md border border-dashed border-neutral-700 bg-neutral-900/40 p-6 text-sm text-neutral-500">
          {analyzing
            ? "Scores will appear here as each clip is processed…"
            : "Upload a video and run detection to see results."}
        </div>
      )}

      {embedVideo && videoSrc && (
        <div>
          <p className="mb-2 text-xs text-neutral-500">
            Play the video—the chart playhead follows playback so you can correlate spikes with
            on-screen content.
          </p>
          <video
            ref={embedRef}
            src={videoSrc}
            controls
            className="w-full max-h-[280px] rounded-md bg-black"
            onLoadedMetadata={(e) => setEmbedDuration(e.currentTarget.duration)}
            onTimeUpdate={(e) => setEmbedPlayhead(e.currentTarget.currentTime)}
          />
        </div>
      )}

      {!embedVideo && series.length > 0 && (
        <p className="text-xs text-neutral-500">
          Scrub the video on the left—the white line on the chart tracks your playhead.
        </p>
      )}

      <div>
        <h3 className="mb-2 text-sm font-medium text-neutral-200">Video analysis</h3>
        <SyntheticScoreChart
          clipSeries={series}
          threshold={effectiveThreshold}
          videoDurationSec={duration}
          playheadSec={playhead}
          live={analyzing && !result}
        />
        {series.length > 0 && (
          <p className="mt-2 text-xs text-neutral-500">
            {series.length} clip{series.length === 1 ? "" : "s"} plotted. Each point is the
            model&apos;s synthetic likelihood for a short temporal segment (0 = more real, 1 = more
            synthetic).
          </p>
        )}
      </div>

      {result?.csv_data ? (
        <details className="rounded border border-neutral-800 bg-neutral-950/60 p-3 text-xs">
          <summary className="cursor-pointer font-medium text-neutral-400">
            Raw clip CSV (index, logit)
          </summary>
          <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap text-neutral-500">
            {result.csv_data}
          </pre>
        </details>
      ) : null}
    </div>
  );
}

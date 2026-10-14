"use client";

import { useState } from "react";
import DetectionProgress from "@/app/components/atoms/DetectionProgress";
import DetectionResultsPanel from "@/app/components/atoms/DetectionResultsPanel";
import { useVideoDetection } from "@/app/hooks/useVideoDetection";

export type SampleVideo = {
  id: string;
  label: string;
  description: string;
  src: string;
  filename: string;
};

type Props = {
  sample: SampleVideo;
  pipelineReady: boolean;
};

export default function SampleDetectionPanel({ sample, pipelineReady }: Props) {
  const detection = useVideoDetection();
  const [loadError, setLoadError] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const runSampleDetection = async () => {
    setLoadError(null);
    const res = await fetch(sample.src);
    if (!res.ok) {
      setLoadError("Sample video not available");
      return;
    }
    const blob = await res.blob();
    const file = new File([blob], sample.filename, { type: "video/mp4" });
    setPreviewUrl(URL.createObjectURL(blob));
    detection.reset();
    await detection.runDetection(file);
  };

  const analyzing =
    detection.busy ||
    detection.phase === "analyzing" ||
    detection.phase === "connecting" ||
    detection.phase === "finalizing";

  return (
    <div className="flex flex-col rounded-xl border border-neutral-800 bg-neutral-950 p-5">
      <h3 className="text-base font-semibold text-neutral-100">{sample.label}</h3>
      <p className="mb-4 text-sm text-neutral-400">{sample.description}</p>

      <video
        src={previewUrl ?? sample.src}
        controls
        className="mb-4 w-full max-h-48 rounded-lg bg-black ring-1 ring-neutral-800"
        preload="metadata"
      />

      <DetectionProgress
        phase={detection.phase}
        message={detection.progressMessage}
        clipsDone={detection.clipsDone}
        totalClips={detection.totalClips}
        elapsedSeconds={detection.elapsedSeconds}
      />

      <button
        type="button"
        className="mt-4 rounded-lg bg-[var(--nvidia-green)] px-4 py-2.5 text-sm font-semibold text-black disabled:opacity-50"
        disabled={detection.busy || !pipelineReady}
        onClick={() => void runSampleDetection()}
      >
        {detection.busy ? "Analyzing…" : "Run detection"}
      </button>

      {(loadError || detection.error) && (
        <p className="mt-3 text-sm text-red-400">{loadError || detection.error}</p>
      )}

      {(detection.result || detection.clipSeriesLive.length > 0 || analyzing) && (
        <div className="mt-6 border-t border-neutral-800 pt-4">
          <DetectionResultsPanel
            result={detection.result}
            clipSeriesLive={detection.clipSeriesLive}
            threshold={0.05}
            analyzing={analyzing}
            embedVideo
            compact
            videoSrc={previewUrl ?? sample.src}
          />
        </div>
      )}
    </div>
  );
}

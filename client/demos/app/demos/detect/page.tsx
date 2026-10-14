"use client";

import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import Header from "@/app/components/atoms/Header";
import LaunchpadDeployBanner from "@/app/components/atoms/LaunchpadDeployBanner";
import NimStartupProgress from "@/app/components/atoms/NimStartupProgress";
import DetectionPipelineExplainer from "@/app/components/atoms/DetectionPipelineExplainer";
import DetectionProgress from "@/app/components/atoms/DetectionProgress";
import DetectionResultsPanel from "@/app/components/atoms/DetectionResultsPanel";
import { useVideoDetection } from "@/app/hooks/useVideoDetection";
import { useAppRole } from "@/app/hooks/useAppRole";
import { resolveDeployMode, useDeploymentStatus } from "@/app/hooks/useDeploymentStatus";
import { useNimStartup } from "@/app/hooks/useNimStartup";

export default function DetectPage() {
  const { isRuntime } = useAppRole();
  const { pipelineReady, status } = useDeploymentStatus({});
  const deployMode = resolveDeployMode(status);
  const bundledRuntime =
    isRuntime && ["OPEN", "BUNDLED"].includes(String(deployMode).toUpperCase());
  const { ready: modelReady } = useNimStartup({ enabled: bundledRuntime });
  const canRunDetection = isRuntime
    ? bundledRuntime
      ? modelReady
      : true
    : pipelineReady;
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [videoDuration, setVideoDuration] = useState<number | null>(null);
  const [playhead, setPlayhead] = useState(0);
  const detection = useVideoDetection();

  const onDrop = useCallback(
    (accepted: File[]) => {
      const f = accepted[0];
      if (!f) return;
      setFile(f);
      setPreview(URL.createObjectURL(f));
      setVideoDuration(null);
      setPlayhead(0);
      detection.reset();
    },
    [detection],
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "video/mp4": [".mp4"] },
    maxFiles: 1,
    maxSize: 500 * 1024 * 1024,
    disabled: detection.busy,
  });

  const mode = deployMode;
  const analyzing =
    detection.busy ||
    detection.phase === "analyzing" ||
    detection.phase === "connecting" ||
    detection.phase === "finalizing";

  return (
    <div className="min-h-screen bg-[var(--page-bg)] text-[var(--text-primary)]">
      <Header />
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        <LaunchpadDeployBanner pipelineReady={pipelineReady} />
        {isRuntime && ["OPEN", "BUNDLED"].includes(String(mode).toUpperCase()) && <NimStartupProgress />}

        <DetectionPipelineExplainer deployMode={String(mode)} />

        <div className="grid gap-8 lg:grid-cols-2 lg:items-start">
          <section className="rounded-xl border border-neutral-800 bg-neutral-950 p-6">
            <div className="mb-4 border-b border-neutral-800 pb-3">
              <h2 className="text-lg font-medium text-neutral-100">Input</h2>
              <p className="mt-1 text-xs text-neutral-500">
                MP4 input. Clip-level scores and aggregate synthetic probability are produced by
                your deployed runtime (open-weights in-pod model server or optional cloud mode).
              </p>
            </div>

            <div
              {...getRootProps()}
              className={`cursor-pointer rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
                isDragActive
                  ? "border-[var(--nvidia-green)] bg-[var(--nvidia-green)]/5"
                  : "border-neutral-700 hover:border-neutral-600"
              } ${detection.busy ? "pointer-events-none opacity-60" : ""}`}
            >
              <input {...getInputProps()} />
              <p className="text-sm text-neutral-300">
                {file ? file.name : "Drop MP4 here or click to browse"}
              </p>
              {!file && (
                <p className="mt-2 text-xs text-neutral-500">
                  Tip: try a short clip first while the GPU model warms up.
                </p>
              )}
            </div>

            {preview && (
              <video
                src={preview}
                controls
                className="mt-4 w-full max-h-72 rounded-lg bg-black ring-1 ring-neutral-800"
                onLoadedMetadata={(e) => setVideoDuration(e.currentTarget.duration)}
                onTimeUpdate={(e) => setPlayhead(e.currentTarget.currentTime)}
              />
            )}

            <DetectionProgress
              phase={detection.phase}
              message={detection.progressMessage}
              clipsDone={detection.clipsDone}
              totalClips={detection.totalClips}
              elapsedSeconds={detection.elapsedSeconds}
            />

            <button
              type="button"
              className="mt-5 w-full rounded-lg bg-[var(--nvidia-green)] px-4 py-3 text-sm font-semibold text-black transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-50 sm:w-auto"
              disabled={!file || detection.busy || !canRunDetection}
              onClick={() => file && void detection.runDetection(file)}
            >
              {detection.busy ? "Running detection…" : "Run detection"}
            </button>
            {!canRunDetection && file && (
              <p className="mt-3 text-sm text-amber-400/90">
                {bundledRuntime
                  ? "Wait for the Hugging Face model server to finish loading (see status above), then run detection."
                  : "Waiting for the deployed runtime application (model server + UI) to become ready…"}
              </p>
            )}
            {detection.error && <p className="mt-3 text-sm text-red-400">{detection.error}</p>}
          </section>

          <section className="rounded-xl border border-neutral-800 bg-neutral-950 p-6 lg:min-h-[520px]">
            <DetectionResultsPanel
              result={detection.result}
              clipSeriesLive={detection.clipSeriesLive}
              threshold={0.05}
              analyzing={analyzing}
              videoDurationSec={videoDuration}
              playheadSec={playhead}
            />
          </section>
        </div>
      </main>
    </div>
  );
}

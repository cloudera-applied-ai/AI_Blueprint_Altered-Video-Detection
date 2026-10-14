"use client";

import { useCallback, useEffect, useState } from "react";

export type NimStartupStatus = {
  phase?: string;
  message?: string;
  ready?: boolean;
  error?: string | null;
  elapsed_s?: number;
  checks?: Record<string, boolean>;
  log_tail?: string[];
};

export type NimStatusResponse = {
  mode?: string;
  ready?: boolean;
  startup?: NimStartupStatus | null;
  endpoints_published?: boolean;
};

const CHECK_LABELS: Record<string, string> = {
  gpu_visible: "GPU visible",
  config_applied: "Configuration applied",
  endpoints_wired: "Runtime endpoints wired",
  model_process_started: "Model server process started",
  model_server_ready: "Model server healthy",
  nim_process_started: "Model server process started",
  http_ready: "HTTP health ready",
  grpc_ready: "gRPC port listening",
  models_loaded: "Models loaded",
  endpoints_published: "Endpoints published",
};

export function checkLabel(key: string): string {
  return CHECK_LABELS[key] || key.replace(/_/g, " ");
}

export function useNimStartup({ poll = true, enabled = true } = {}) {
  const [data, setData] = useState<NimStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!enabled) return;
    try {
      const res = await fetch("/api/nim-status");
      const json = (await res.json()) as NimStatusResponse;
      if (!res.ok) throw new Error("Failed to load NIM status");
      setData(json);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load NIM status");
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!poll || !enabled) return;
    const ready = Boolean(data?.ready || data?.startup?.ready);
    if (ready) return;
    const id = setInterval(() => void refresh(), 4000);
    return () => clearInterval(id);
  }, [poll, enabled, refresh, data?.ready, data?.startup?.ready, data?.startup?.phase]);

  const startup = data?.startup;
  const checks = startup?.checks || {};
  const checkEntries = Object.entries(checks);

  return {
    loading,
    error,
    refresh,
    mode: data?.mode || "OPEN",
    ready: Boolean(data?.ready),
    startup,
    checkEntries,
    logTail: startup?.log_tail || [],
    elapsedSeconds: startup?.elapsed_s || 0,
    phase: startup?.phase || "unknown",
    message: startup?.message || "Waiting for model server status…",
    startupError: startup?.error,
  };
}

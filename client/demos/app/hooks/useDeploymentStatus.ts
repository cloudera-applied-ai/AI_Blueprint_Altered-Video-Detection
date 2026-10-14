"use client";

import { useCallback, useEffect, useState } from "react";

export type StepStatus = "pending" | "running" | "done" | "error" | "skipped";

export type NimStartupStatus = {
  phase?: string;
  message?: string;
  ready?: boolean;
  error?: string | null;
  elapsed_s?: number;
  checks?: Record<string, boolean>;
  log_tail?: string[];
};

export type ServiceStatus = {
  key?: string;
  name?: string;
  mode?: string;
  ready?: boolean;
  app_running?: boolean;
  app_failed?: boolean;
  application?: { status?: string; id?: string; subdomain?: string } | null;
  nim_startup?: NimStartupStatus | null;
};

export type DeploymentStatus = {
  pipeline_ready?: boolean;
  serverless_ready?: boolean;
  open_ready?: boolean;
  bundled_ready?: boolean;
  pipeline_failed?: boolean;
  build_in_progress?: boolean;
  deploy_active?: boolean;
  nim_deploy_mode?: string;
  config?: {
    serverless?: Record<string, unknown>;
    open?: Record<string, unknown>;
    bundled?: Record<string, unknown>;
  };
  secrets_set?: {
    serverless?: { ngc_api_key?: boolean };
    open?: { hf_token?: boolean };
    bundled?: { hf_token?: boolean };
  };
  mode_summary?: { headline?: string; detail?: string };
  deployments?: Record<string, ServiceStatus>;
  services?: Record<string, ServiceStatus>;
  build?: {
    error?: string;
    message?: string;
    in_progress?: boolean;
    mode?: string;
    steps?: Array<{ id: string; label: string; status: StepStatus; detail?: string }>;
  };
};

/** Resolve active deploy mode from status API or runtime env (all-in-one apps). */
export function resolveDeployMode(status: DeploymentStatus | null): string {
  if (status?.nim_deploy_mode) return status.nim_deploy_mode;
  if (status?.bundled_ready || status?.open_ready) return "BUNDLED";
  if (status?.serverless_ready) return "SERVERLESS";
  const fromEnv = process.env.NEXT_PUBLIC_NIM_DEPLOY_MODE || process.env.NIM_DEPLOY_MODE;
  if (fromEnv) return fromEnv;
  return "unknown";
}

export function useDeploymentStatus({ pollWhilePending = false } = {}) {
  const [status, setStatus] = useState<DeploymentStatus | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [fetchError, setFetchError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const res = await fetch("/api/deployment");
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to load status");
      setStatus(data);
      setFetchError(null);
    } catch (err) {
      setFetchError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setInitialLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    if (!pollWhilePending) return;
    const awaitingOnline = Object.values(status?.deployments || status?.services || {}).some(
      (entry) =>
        entry?.application &&
        !entry.app_running &&
        !entry.app_failed,
    );
    const bundledNimStarting = Object.values(status?.deployments || status?.services || {}).some(
      (entry) =>
        entry?.key === "bundled" &&
        entry.app_running &&
        !entry.ready &&
        !entry.app_failed,
    );
    if (!status?.deploy_active && !status?.build_in_progress && !awaitingOnline && !bundledNimStarting)
      return;
    const id = setInterval(() => void refresh(), 4000);
    return () => clearInterval(id);
  }, [
    pollWhilePending,
    refresh,
    status?.deploy_active,
    status?.build_in_progress,
    status?.deployments,
    status?.services,
  ]);

  return {
    status,
    initialLoading,
    fetchError,
    refresh,
    pipelineReady: Boolean(status?.pipeline_ready),
    serverlessReady: Boolean(status?.serverless_ready),
    bundledReady: Boolean(status?.bundled_ready),
    pipelineFailed: Boolean(status?.pipeline_failed),
    buildInProgress: Boolean(status?.build_in_progress),
    hasPriorBuild: Boolean(status?.build?.steps?.some((s) => s.status === "done")),
  };
}

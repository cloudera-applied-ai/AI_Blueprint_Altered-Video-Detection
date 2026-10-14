"use client";

import { useEffect, useRef, useState } from "react";
import Header from "@/app/components/atoms/Header";
import Card from "@/app/components/atoms/Card";
import SecretInput from "@/app/components/atoms/SecretInput";
import BundledModelSelector from "@/app/components/atoms/BundledModelSelector";
import { NimStartupDetails } from "@/app/components/atoms/NimStartupProgress";
import { useDeploymentStatus, type ServiceStatus } from "@/app/hooks/useDeploymentStatus";
import {
  type OpenConsensusStrategy,
  type OpenModelCatalog,
  type OpenModelEntry,
  entriesFromPreset,
  parseOpenModelEntries,
  presetById,
} from "@/app/lib/openModels";

type DeployMode = "SERVERLESS" | "BUNDLED";

type ServerlessForm = {
  ngc_api_key: string;
  svd_nvidia_function_id: string;
  nvidia_serverless_grpc_host: string;
  nvidia_serverless_grpc_port: string;
  detection_threshold: string;
};

type BundledForm = {
  hf_token: string;
  svd_open_model_preset: string;
  svd_open_model_kind: string;
  svd_hf_model_id: string;
  svd_open_port: string;
  svd_open_consensus: OpenConsensusStrategy;
  svd_open_models: OpenModelEntry[];
  detection_threshold: string;
};

const inputClass =
  "mt-1.5 w-full rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] px-3 py-2.5 text-sm outline-none focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)]";

const btnSecondary =
  "rounded-lg border border-[var(--border)] bg-[var(--surface-elevated)] px-4 py-2.5 text-sm font-medium text-[var(--text-primary)] transition hover:bg-neutral-800 disabled:opacity-50";

const btnPrimary =
  "rounded-lg bg-[var(--accent)] px-4 py-2.5 text-sm font-semibold text-black transition hover:brightness-110 disabled:opacity-50";

const defaultServerless: ServerlessForm = {
  ngc_api_key: "",
  svd_nvidia_function_id: "847b6e53-0133-452d-ab85-d7acf3ace723",
  nvidia_serverless_grpc_host: "grpc.nvcf.nvidia.com",
  nvidia_serverless_grpc_port: "443",
  detection_threshold: "0.05",
};

const defaultBundledModels: OpenModelEntry[] = [
  {
    hf_model_id: "eftt/VideoMae-ffc23-deepfake-detector",
    kind: "videomae",
    preset_id: "videomae-ffc23",
    label: "VideoMAE FF++",
  },
];

const defaultBundled: BundledForm = {
  hf_token: "",
  svd_open_model_preset: "videomae-ffc23",
  svd_open_model_kind: "videomae",
  svd_hf_model_id: "eftt/VideoMae-ffc23-deepfake-detector",
  svd_open_port: "8090",
  svd_open_consensus: "majority",
  svd_open_models: defaultBundledModels,
  detection_threshold: "0.05",
};

function bundledModelsFromConfig(
  bd: Record<string, unknown>,
  catalog: OpenModelCatalog | null,
): OpenModelEntry[] {
  const parsed = parseOpenModelEntries(bd.svd_open_models);
  if (parsed.length) return parsed;
  const presetId = String(bd.svd_open_model_preset || "videomae-ffc23");
  const preset = catalog ? presetById(catalog, presetId) : undefined;
  if (preset) return [entriesFromPreset(preset)];
  const hf = String(bd.svd_hf_model_id || "").trim();
  if (!hf) return defaultBundledModels;
  return [
    {
      hf_model_id: hf,
      kind: bd.svd_open_model_kind === "videomae" ? "videomae" : "image",
      preset_id: presetId || undefined,
    },
  ];
}

function syncBundledLegacyFields(models: OpenModelEntry[]): Pick<
  BundledForm,
  "svd_hf_model_id" | "svd_open_model_kind" | "svd_open_model_preset"
> {
  const primary = models[0];
  if (!primary) {
    return {
      svd_hf_model_id: defaultBundled.svd_hf_model_id,
      svd_open_model_kind: defaultBundled.svd_open_model_kind,
      svd_open_model_preset: defaultBundled.svd_open_model_preset,
    };
  }
  return {
    svd_hf_model_id: primary.hf_model_id,
    svd_open_model_kind: primary.kind,
    svd_open_model_preset: primary.preset_id || defaultBundled.svd_open_model_preset,
  };
}

function appUrl(subdomain?: string): string | null {
  if (!subdomain) return null;
  if (typeof window === "undefined") return null;
  const host = window.location.host.replace(/^[^.]+\./, `${subdomain}.`);
  return `${window.location.protocol}//${host}`;
}

function DeploySection({
  mode,
  title,
  description,
  form,
  onChange,
  deployment,
  secretsSet,
  busy,
  onSave,
  onValidate,
  onDeploy,
  children,
  showNgcKey = true,
}: {
  mode: DeployMode;
  title: string;
  description: string;
  form: ServerlessForm | BundledForm;
  onChange: (patch: Partial<ServerlessForm & BundledForm>) => void;
  showNgcKey?: boolean;
  deployment?: ServiceStatus;
  secretsSet?: boolean;
  busy: boolean;
  onSave: () => void;
  onValidate: () => void;
  onDeploy: () => void;
  children?: React.ReactNode;
}) {
  const app = deployment?.application;
  const status = app?.status || "not deployed";
  const ready = Boolean(deployment?.ready);
  const running = Boolean(deployment?.app_running);
  const failed = Boolean(deployment?.app_failed);
  const url = running ? appUrl(app?.subdomain) : null;
  const starting = Boolean(app?.subdomain) && !running && !failed;

  return (
    <Card title={title} description={description}>
      {showNgcKey && "ngc_api_key" in form && (
        <SecretInput
          label="NGC API Key"
          value={form.ngc_api_key}
          onChange={(v) => onChange({ ngc_api_key: v })}
          placeholder={secretsSet ? "•••••••• (saved)" : "nvapi-…"}
        />
      )}
      {children}
      <label className="mt-6 block text-sm font-medium text-[var(--text-primary)]">
        Detection threshold
        <input
          className={inputClass}
          value={form.detection_threshold}
          onChange={(e) => onChange({ detection_threshold: e.target.value })}
          placeholder="0.05"
        />
      </label>
      <div className="mt-6 flex flex-wrap gap-3">
        <button type="button" className={btnSecondary} disabled={busy} onClick={onSave}>
          Save configuration
        </button>
        <button type="button" className={btnSecondary} disabled={busy} onClick={onValidate}>
          Validate
        </button>
        <button type="button" className={btnPrimary} disabled={busy} onClick={onDeploy}>
          {running || ready ? "Redeploy application" : "Deploy application"}
        </button>
      </div>
      <div className="mt-6 space-y-2 rounded-lg border border-[var(--border)] bg-black/20 p-4 text-sm">
        <p>
          Application: <strong>{deployment?.name || title}</strong> —{" "}
          <span className={failed ? "text-[var(--danger)]" : ready ? "text-[var(--accent)]" : "text-[var(--text-secondary)]"}>
            {status}
          </span>
        </p>
        {starting && (
          <p className="text-amber-400">Application is starting — the app URL will appear when it is online.</p>
        )}
        {url && (
          <p>
            Open app:{" "}
            <a href={url} target="_blank" rel="noreferrer" className="font-medium text-[var(--accent)] underline">
              {url}
            </a>
          </p>
        )}
        {ready && url && (
          <p className="text-green-400">Ready — use the app URL above for Detect and Demo.</p>
        )}
        {mode === "BUNDLED" && running && !ready && (
          <div className="mt-4 space-y-3">
            <p className="text-amber-400">Model server is starting (first run downloads weights from Hugging Face).</p>
            {deployment?.nim_startup && (
              <NimStartupDetails
                startup={deployment.nim_startup}
                ready={ready}
                compact
              />
            )}
          </div>
        )}
      </div>
    </Card>
  );
}

export default function LaunchpadPage() {
  const { status, refresh, buildInProgress } = useDeploymentStatus({ pollWhilePending: true });
  const [serverlessForm, setServerlessForm] = useState(defaultServerless);
  const [bundledForm, setBundledForm] = useState(defaultBundled);
  const [dirty, setDirty] = useState({ serverless: false, bundled: false });
  const serverlessHydrated = useRef(false);
  const bundledHydrated = useRef(false);
  const [busy, setBusy] = useState<DeployMode | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<OpenModelCatalog | null>(null);

  useEffect(() => {
    void fetch("/api/open-models")
      .then((r) => r.json())
      .then((data: OpenModelCatalog) => setCatalog(data))
      .catch(() => setCatalog(null));
  }, []);

  useEffect(() => {
    if (!status?.config || serverlessHydrated.current) return;
    serverlessHydrated.current = true;
    const sl = status.config.serverless as Record<string, unknown> | undefined;
    if (sl) {
      setServerlessForm((prev) => ({
        ...prev,
        svd_nvidia_function_id: String(sl.svd_nvidia_function_id || prev.svd_nvidia_function_id),
        nvidia_serverless_grpc_host: String(sl.nvidia_serverless_grpc_host || prev.nvidia_serverless_grpc_host),
        nvidia_serverless_grpc_port: String(sl.nvidia_serverless_grpc_port || prev.nvidia_serverless_grpc_port),
        detection_threshold: String(sl.detection_threshold || prev.detection_threshold),
      }));
    }
  }, [status]);

  useEffect(() => {
    if (!status?.config || !catalog || bundledHydrated.current) return;
    bundledHydrated.current = true;
    const bd = (status.config.bundled || status.config.open) as Record<string, unknown> | undefined;
    if (!bd) return;
    const models = bundledModelsFromConfig(bd, catalog);
    const legacy = syncBundledLegacyFields(models);
    const consensusRaw = String(bd.svd_open_consensus || "majority");
    const consensus: OpenConsensusStrategy =
      consensusRaw === "unanimous" || consensusRaw === "any" || consensusRaw === "mean"
        ? consensusRaw
        : "majority";
    setBundledForm((prev) => ({
      ...prev,
      ...legacy,
      svd_open_models: models,
      svd_open_consensus: consensus,
      svd_open_port: String(bd.svd_open_port || prev.svd_open_port),
      detection_threshold: String(bd.detection_threshold || prev.detection_threshold),
    }));
  }, [status, catalog]);

  const post = async (mode: DeployMode, action: "save-config" | "validate" | "deploy") => {
    setBusy(mode);
    setError(null);
    setMessage(null);
    const config =
      mode === "SERVERLESS"
        ? { ...serverlessForm, nim_deploy_mode: "SERVERLESS" }
        : { ...bundledForm, nim_deploy_mode: "BUNDLED" };
    try {
      if (action === "deploy") {
        const saveRes = await fetch("/api/deployment", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action: "save-config", mode, config }),
        });
        const saveData = await saveRes.json();
        if (!saveRes.ok) throw new Error(saveData.error || "Save before deploy failed");
      }
      const res = await fetch("/api/deployment", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action, mode, config }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || JSON.stringify(data.errors || data));
      if (action === "deploy") {
        setMessage(`${mode} deployment started — polling status…`);
        setDirty((d) => ({
          ...d,
          [mode.toLowerCase() as "serverless" | "bundled"]: false,
        }));
        void refresh();
      } else if (action === "save-config") {
        setMessage(`${mode} configuration saved.`);
        setDirty((d) => ({
          ...d,
          [mode.toLowerCase() as "serverless" | "bundled"]: false,
        }));
      } else {
        setMessage(data.valid ? `${mode} validation passed.` : data.errors?.join("; "));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Request failed");
    } finally {
      setBusy(null);
    }
  };

  const deployments = status?.deployments || status?.services || {};
  const slSecrets = status?.secrets_set?.serverless?.ngc_api_key;
  const bundledSecrets = status?.secrets_set?.bundled?.hf_token;

  return (
    <div className="min-h-screen bg-[var(--page-bg)]">
      <Header />
      <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6">
        <section className="relative overflow-hidden rounded-2xl border border-[var(--border)] bg-gradient-to-br from-[var(--surface)] via-[var(--surface)] to-[#0a1205] p-8 shadow-[var(--shadow-card)]">
          <div className="relative z-10 max-w-2xl">
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-[var(--accent)]">Launchpad</p>
            <h2 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--text-primary)] sm:text-3xl">
              Deploy production-ready detection runtimes
            </h2>
            <p className="mt-3 text-sm leading-relaxed text-[var(--text-secondary)]">
              Choose a deployment mode: <strong className="text-[var(--text-primary)]">Bundled</strong> runs a
              Hugging Face model and Detect UI in one GPU application;{" "}
              <strong className="text-[var(--text-primary)]">Serverless</strong> calls NVIDIA Synthetic Video
              Detector on Cloud Functions over gRPC from a CPU application.
            </p>
          </div>
          <div
            className="pointer-events-none absolute -right-16 -top-24 h-64 w-64 rounded-full bg-[var(--accent)]/10 blur-3xl"
            aria-hidden
          />
        </section>

        <Card title="Status">
          <p className="text-sm text-[var(--text-secondary)]">{status?.mode_summary?.detail}</p>
          {buildInProgress && (
            <p className="mt-3 text-sm text-amber-400">
              Deployment in progress… {status?.build?.message || ""}
            </p>
          )}
          {status?.build?.error && <p className="mt-2 text-sm text-red-400">{status.build.error}</p>}
          {message && <p className="mt-3 text-sm text-green-400">{message}</p>}
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        </Card>

        <DeploySection
          mode="SERVERLESS"
          title="Deploy Serverless (NVCF)"
          description="CPU application that streams MP4 input to NVIDIA Synthetic Video Detector on Cloud Functions (gRPC). Requires an NGC API key and NVCF function ID."
          form={serverlessForm}
          onChange={(patch) => {
            setDirty((d) => ({ ...d, serverless: true }));
            setServerlessForm((prev) => ({ ...prev, ...patch }));
          }}
          deployment={deployments.serverless as ServiceStatus | undefined}
          secretsSet={slSecrets}
          busy={busy !== null}
          onSave={() => void post("SERVERLESS", "save-config")}
          onValidate={() => void post("SERVERLESS", "validate")}
          onDeploy={() => void post("SERVERLESS", "deploy")}
        >
          <div className="mt-4 grid gap-3">
            <label className="text-sm font-medium text-[var(--text-primary)]">
              NVCF Function ID
              <input
                className={inputClass}
                value={serverlessForm.svd_nvidia_function_id}
                onChange={(e) => {
                  setDirty((d) => ({ ...d, serverless: true }));
                  setServerlessForm((prev) => ({ ...prev, svd_nvidia_function_id: e.target.value }));
                }}
              />
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)]">
              gRPC Host
              <input
                className={inputClass}
                value={serverlessForm.nvidia_serverless_grpc_host}
                onChange={(e) => {
                  setDirty((d) => ({ ...d, serverless: true }));
                  setServerlessForm((prev) => ({ ...prev, nvidia_serverless_grpc_host: e.target.value }));
                }}
              />
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)]">
              gRPC Port
              <input
                className={inputClass}
                value={serverlessForm.nvidia_serverless_grpc_port}
                onChange={(e) => {
                  setDirty((d) => ({ ...d, serverless: true }));
                  setServerlessForm((prev) => ({ ...prev, nvidia_serverless_grpc_port: e.target.value }));
                }}
              />
            </label>
          </div>
        </DeploySection>

        <DeploySection
          mode="BUNDLED"
          title="Deploy Bundled (GPU)"
          description="Single GPU application with one or more Hugging Face models (consensus voting) and Detect/Demo UI in one pod."
          form={bundledForm}
          showNgcKey={false}
          onChange={(patch) => {
            setDirty((d) => ({ ...d, bundled: true }));
            setBundledForm((prev) => ({ ...prev, ...patch }));
          }}
          deployment={deployments.bundled as ServiceStatus | undefined}
          secretsSet={bundledSecrets}
          busy={busy !== null}
          onSave={() => void post("BUNDLED", "save-config")}
          onValidate={() => void post("BUNDLED", "validate")}
          onDeploy={() => void post("BUNDLED", "deploy")}
        >
          <div className="mt-2 space-y-6">
            {catalog ? (
              <BundledModelSelector
                catalog={catalog}
                models={bundledForm.svd_open_models}
                consensus={bundledForm.svd_open_consensus}
                disabled={busy !== null}
                onChange={(models, consensus) => {
                  setDirty((d) => ({ ...d, bundled: true }));
                  setBundledForm((prev) => ({
                    ...prev,
                    ...syncBundledLegacyFields(models.length ? models : prev.svd_open_models),
                    svd_open_models: models.length ? models : prev.svd_open_models,
                    svd_open_consensus: consensus,
                  }));
                }}
              />
            ) : (
              <p className="text-sm text-[var(--text-muted)]">Loading model catalog…</p>
            )}
            <SecretInput
              label="Hugging Face token"
              hint="Optional for public models; required for gated checkpoints."
              value={bundledForm.hf_token}
              onChange={(v) => {
                setDirty((d) => ({ ...d, open: true }));
                setBundledForm((prev) => ({ ...prev, hf_token: v }));
              }}
              placeholder={bundledSecrets ? "•••••••• (saved)" : "hf_…"}
            />
            <details className="rounded-lg border border-[var(--border)] bg-black/20 p-4">
              <summary className="cursor-pointer text-sm font-medium text-[var(--text-secondary)]">
                Advanced settings
              </summary>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                <label className="text-sm font-medium text-[var(--text-primary)]">
                  In-app model port
                  <input
                    className={inputClass}
                    value={bundledForm.svd_open_port}
                    onChange={(e) => {
                      setDirty((d) => ({ ...d, bundled: true }));
                      setBundledForm((prev) => ({ ...prev, svd_open_port: e.target.value }));
                    }}
                  />
                </label>
              </div>
            </details>
          </div>
        </DeploySection>
      </main>
    </div>
  );
}

import path from "path";
import fs from "fs";

export type PersistedConfig = {
  nim_deploy_mode?: string;
  svd_nvidia_function_id?: string;
  nvidia_serverless_grpc_host?: string;
  nvidia_serverless_grpc_port?: string;
  svd_hf_model_id?: string;
  svd_open_model_preset?: string;
  svd_open_model_kind?: string;
  svd_open_port?: string;
  svd_open_consensus?: string;
  svd_open_models?: unknown;
  detection_threshold?: string;
  ngc_api_key?: string;
  hf_token?: string;
};

const ENV_MAP: Record<string, string> = {
  nim_deploy_mode: "NIM_DEPLOY_MODE",
  svd_nvidia_function_id: "SVD_NVIDIA_FUNCTION_ID",
  nvidia_serverless_grpc_host: "NVIDIA_SERVERLESS_GRPC_HOST",
  nvidia_serverless_grpc_port: "NVIDIA_SERVERLESS_GRPC_PORT",
  svd_hf_model_id: "SVD_HF_MODEL_ID",
  svd_open_model_preset: "SVD_OPEN_MODEL_PRESET",
  svd_open_model_kind: "SVD_OPEN_MODEL_KIND",
  svd_open_port: "SVD_OPEN_PORT",
  svd_open_consensus: "SVD_OPEN_CONSENSUS",
  detection_threshold: "SVD_DETECTION_THRESHOLD",
  ngc_api_key: "NGC_API_KEY",
  hf_token: "HF_TOKEN",
};

function projectRoot(): string {
  return process.env.CDSW_PROJECT_DIR || path.resolve(process.cwd(), "../..");
}

export { projectRoot };

export function deploymentConfigPath(): string {
  return path.join(projectRoot(), "cai/config/deployment_config.json");
}

export function endpointsEnvPath(): string {
  return path.join(projectRoot(), "cai/config/runtime_endpoints.env");
}

export function appEnvironmentPath(): string {
  return path.join(projectRoot(), "cai/config/app_environment.env");
}

function applyDotenvFile(targetPath: string, env: NodeJS.ProcessEnv): void {
  if (!fs.existsSync(targetPath)) return;
  for (const line of fs.readFileSync(targetPath, "utf8").split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const eq = trimmed.indexOf("=");
    const key = trimmed.slice(0, eq);
    let val = trimmed.slice(eq + 1).trim();
    if ((val.startsWith('"') && val.endsWith('"')) || (val.startsWith("'") && val.endsWith("'"))) {
      val = val.slice(1, -1);
    }
    env[key] = val;
  }
}

function normalizeMode(mode: string): string {
  const token = mode.toUpperCase();
  if (token === "OPEN" || token === "OPEN_WEIGHTS" || token === "HF") return "BUNDLED";
  if (token === "BUNDLE" || token === "GPU") return "BUNDLED";
  return token;
}

function applyDeploymentJson(env: NodeJS.ProcessEnv): void {
  const configPath = deploymentConfigPath();
  if (!fs.existsSync(configPath)) return;
  try {
    const raw = JSON.parse(fs.readFileSync(configPath, "utf8")) as Record<string, unknown>;
    const mode = normalizeMode(String(env.NIM_DEPLOY_MODE || raw.nim_deploy_mode || "OPEN"));
    let data: PersistedConfig;
    if (raw.serverless || raw.open || raw.bundled) {
      const section =
        mode === "SERVERLESS"
          ? (raw.serverless as PersistedConfig)
          : ((raw.open || raw.bundled) as PersistedConfig);
      data = { ...section, nim_deploy_mode: mode };
    } else {
      data = raw as PersistedConfig;
    }
    for (const [jsonKey, envKey] of Object.entries(ENV_MAP)) {
      const value = data[jsonKey as keyof PersistedConfig];
      if (value) env[envKey] = String(value);
    }
    if (Array.isArray(data.svd_open_models) && data.svd_open_models.length) {
      env.SVD_OPEN_MODELS_JSON = JSON.stringify(data.svd_open_models);
    }
  } catch {
    /* ignore */
  }
}

const BAKED_RUNTIME_KEYS = [
  "NIM_DEPLOY_MODE",
  "NGC_API_KEY",
  "HF_TOKEN",
  "SVD_HF_MODEL_ID",
  "SVD_OPEN_MODEL_PRESET",
  "SVD_OPEN_MODEL_KIND",
  "SVD_OPEN_PORT",
  "SVD_OPEN_SERVER",
  "SVD_NVIDIA_FUNCTION_ID",
  "NVIDIA_SERVERLESS_GRPC_HOST",
  "NVIDIA_SERVERLESS_GRPC_PORT",
  "SVD_DETECTION_THRESHOLD",
  "SVD_OPEN_CONSENSUS",
  "SVD_OPEN_MODELS_JSON",
  "SVD_APP_ROLE",
] as const;

/** Merge env for detect API. Runtime apps use CML-baked env only; Launchpad reads saved config. */
export function buildDetectProcessEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env };
  const role = String(env.SVD_APP_ROLE || "launchpad").toLowerCase();
  const baked: Record<string, string | undefined> = {};
  if (role === "runtime") {
    for (const key of BAKED_RUNTIME_KEYS) {
      if (process.env[key]) baked[key] = process.env[key];
    }
  }

  applyDotenvFile(endpointsEnvPath(), env);

  if (role === "launchpad") {
    applyDotenvFile(appEnvironmentPath(), env);
    applyDeploymentJson(env);
  } else {
    for (const [key, value] of Object.entries(baked)) {
      if (value) env[key] = value;
    }
    const mode = normalizeMode(String(env.NIM_DEPLOY_MODE || "OPEN"));
    if (mode === "OPEN") {
      env.NIM_DEPLOY_MODE = "OPEN";
      const port = String(env.SVD_OPEN_PORT || "8090");
      env.SVD_OPEN_SERVER = String(env.SVD_OPEN_SERVER || `http://127.0.0.1:${port}`);
    }
  }

  const mode = normalizeMode(String(env.NIM_DEPLOY_MODE || "OPEN"));
  if (mode === "SERVERLESS" && role === "launchpad") {
    const server = String(env.SVD_SERVER || "");
    const host = server.split(":")[0]?.toLowerCase() || "";
    if (host === "127.0.0.1" || host === "localhost") {
      delete env.SVD_SERVER;
    }
  }
  return env;
}

function bundledModelStartupReady(): boolean {
  const startupPath = path.join(projectRoot(), "cai/config/nim_startup.json");
  if (!fs.existsSync(startupPath)) return false;
  try {
    const data = JSON.parse(fs.readFileSync(startupPath, "utf8")) as { ready?: boolean };
    return Boolean(data.ready);
  } catch {
    return false;
  }
}

export function validateDetectEnv(env: NodeJS.ProcessEnv): string | null {
  const mode = normalizeMode(String(env.NIM_DEPLOY_MODE || "OPEN"));
  const role = String(env.SVD_APP_ROLE || "runtime");
  if (mode === "SERVERLESS") {
    if (!env.NGC_API_KEY?.trim()) {
      return "NGC API key is not configured. Save serverless configuration on the Launchpad and redeploy.";
    }
    return null;
  }
  const openServer = String(env.SVD_OPEN_SERVER || "");
  if (!openServer && role === "runtime") {
    return "Open model server is not configured. Wait for the app to finish loading the Hugging Face model.";
  }
  if (role === "runtime" && !bundledModelStartupReady()) {
    return "Model server is still loading. Wait until startup shows healthy, then run detection again.";
  }
  if (role === "launchpad") {
    return "Open the deployed Open Weights app URL from the Launchpad to run detection.";
  }
  return null;
}

export function controlPlaneScript(): string {
  return path.join(projectRoot(), "cai/amp/7_deploy/control_plane_cli.py");
}

export function pythonPath(): string {
  const venv = path.join(projectRoot(), ".venv/bin/python");
  if (fs.existsSync(venv)) return venv;
  return process.env.PYTHON || "python3";
}

export function applyPersistedConfigToProcessEnv(): void {
  const merged = buildDetectProcessEnv();
  for (const [key, value] of Object.entries(merged)) {
    if (value !== undefined) process.env[key] = value;
  }
}

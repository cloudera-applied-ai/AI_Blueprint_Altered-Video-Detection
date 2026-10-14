import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

type NimStartup = {
  phase?: string;
  message?: string;
  ready?: boolean;
  error?: string | null;
  elapsed_s?: number;
  checks?: Record<string, boolean>;
  log_tail?: string[];
};

function projectRoot(): string {
  return process.env.CDSW_PROJECT_DIR || path.resolve(process.cwd(), "../..");
}

function readNimStartup(): NimStartup | null {
  const startupPath = path.join(projectRoot(), "cai/config/nim_startup.json");
  if (!fs.existsSync(startupPath)) return null;
  try {
    return JSON.parse(fs.readFileSync(startupPath, "utf8")) as NimStartup;
  } catch {
    return null;
  }
}

export async function GET(): Promise<NextResponse> {
  const mode = (process.env.NIM_DEPLOY_MODE || "OPEN").toUpperCase();
  const role = (process.env.SVD_APP_ROLE || "launchpad").toLowerCase();
  const startup = readNimStartup();
  const endpointsPath = path.join(projectRoot(), "cai/nim_endpoints.json");
  const endpointsPublished = fs.existsSync(endpointsPath);

  const bundledMode = mode === "BUNDLED" || mode === "OPEN" || mode === "OPEN_WEIGHTS";
  const ready = bundledMode
    ? Boolean(startup?.ready)
    : Boolean(startup?.ready || endpointsPublished);

  return NextResponse.json({
    mode,
    role,
    ready,
    startup,
    endpoints_published: endpointsPublished,
  });
}

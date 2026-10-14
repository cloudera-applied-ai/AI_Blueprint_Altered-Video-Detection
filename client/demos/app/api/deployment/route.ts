import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs";
import path from "path";
import { controlPlaneScript, pythonPath } from "../utils/persistedConfig";

export async function GET(): Promise<NextResponse> {
  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonPath(), [controlPlaneScript(), "status"]);
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", (code) => {
      if (code !== 0) {
        resolve(NextResponse.json({ error: stderr || "status failed" }, { status: 500 }));
        return;
      }
      resolve(NextResponse.json(JSON.parse(stdout)));
    });
  });
}

type DeployMode = "SERVERLESS" | "OPEN" | "BUNDLED";

type DeploymentRequestBody = {
  action?: string;
  mode?: DeployMode;
  config?: Record<string, unknown>;
};

export async function POST(request: NextRequest): Promise<NextResponse> {
  if ((process.env.SVD_APP_ROLE || "launchpad").toLowerCase() === "runtime") {
    return NextResponse.json(
      { error: "Deploy actions are only available on the Launchpad application." },
      { status: 403 },
    );
  }

  const body = (await request.json()) as DeploymentRequestBody;
  const action = body.action ?? "";
  const config = body.config;
  const mode = body.mode;

  if (!mode && (action === "save-config" || action === "validate" || action === "deploy")) {
    return NextResponse.json({ error: "mode is required (SERVERLESS or BUNDLED)" }, { status: 400 });
  }

  if (action === "save-config") {
    return runCli(["save-config", "--mode", mode!, "--config-json", JSON.stringify(config)]);
  }
  if (action === "validate") {
    return runCli(["validate", "--mode", mode!, "--config-json", JSON.stringify(config || {})]);
  }
  if (action === "deploy") {
    const logDir = path.join(process.env.CDSW_PROJECT_DIR || path.resolve(process.cwd(), "../.."), "cai/config");
    fs.mkdirSync(logDir, { recursive: true });
    const logPath = path.join(logDir, "deploy_worker.log");
    const out = fs.openSync(logPath, "a");
    const proc = spawn(pythonPath(), [controlPlaneScript(), "deploy", "--mode", mode!], {
      detached: true,
      stdio: ["ignore", out, out],
    });
    proc.unref();
    return NextResponse.json({ started: true, mode, log: logPath });
  }
  if (action === "build") {
    return runDeployWorker(["build"]);
  }
  return NextResponse.json({ error: "Unknown action" }, { status: 400 });
}

function runDeployWorker(args: string[]): Promise<NextResponse> {
  const logDir = path.join(process.env.CDSW_PROJECT_DIR || path.resolve(process.cwd(), "../.."), "cai/config");
  fs.mkdirSync(logDir, { recursive: true });
  const logPath = path.join(logDir, "deploy_worker.log");
  const out = fs.openSync(logPath, "a");
  const proc = spawn(pythonPath(), [controlPlaneScript(), ...args], {
    detached: true,
    stdio: ["ignore", out, out],
  });
  proc.unref();
  return Promise.resolve(NextResponse.json({ started: true, log: logPath }));
}

function runCli(args: string[]): Promise<NextResponse> {
  return new Promise((resolve) => {
    const proc = spawn(pythonPath(), [controlPlaneScript(), ...args]);
    let stdout = "";
    let stderr = "";
    proc.stdout.on("data", (d) => (stdout += d.toString()));
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", (code) => {
      try {
        const payload = stdout ? JSON.parse(stdout) : { error: stderr };
        resolve(NextResponse.json(payload, { status: code === 0 ? 200 : 400 }));
      } catch {
        resolve(NextResponse.json({ error: stderr || stdout || "CLI failed" }, { status: 500 }));
      }
    });
  });
}

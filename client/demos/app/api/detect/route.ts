import { NextRequest, NextResponse } from "next/server";
import { spawn } from "child_process";
import fs from "fs/promises";
import os from "os";
import path from "path";
import {
  buildDetectProcessEnv,
  pythonPath,
  projectRoot,
  validateDetectEnv,
} from "../utils/persistedConfig";

type ClipPoint = { index: number; logit: number; score: number };

type DetectPayload = {
  probability: number;
  logit: number;
  synthetic_score_percent: number;
  is_synthetic: boolean;
  total_clips: number;
  threshold: number;
  clip_series?: ClipPoint[];
  csv_data?: string;
};

export async function POST(request: NextRequest): Promise<NextResponse> {
  const detectEnv = buildDetectProcessEnv();
  const configError = validateDetectEnv(detectEnv);
  if (configError) {
    return NextResponse.json({ error: configError }, { status: 400 });
  }

  const stream = request.nextUrl.searchParams.get("stream") === "1";
  const form = await request.formData();
  const file = form.get("video");
  if (!(file instanceof Blob)) {
    return NextResponse.json({ error: "Missing video file" }, { status: 400 });
  }

  const buffer = Buffer.from(await file.arrayBuffer());
  const tmpDir = await fs.mkdtemp(path.join(os.tmpdir(), "svd-"));
  const videoPath = path.join(tmpDir, "input.mp4");
  const jsonPath = path.join(tmpDir, "result.json");
  await fs.writeFile(videoPath, buffer);

  const root = projectRoot();
  const env = {
    ...detectEnv,
    PYTHONPATH: [root, path.join(root, "src")].join(":"),
  };
  const cliArgs = [
    "-m",
    "src.svd.cli",
    "--video-input",
    videoPath,
    "--output-json",
    jsonPath,
    ...(stream ? ["--progress-jsonl"] : []),
  ];

  if (stream) {
    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        const encoder = new TextEncoder();
        let closed = false;

        const safeClose = () => {
          if (closed) return;
          closed = true;
          try {
            controller.close();
          } catch {
            /* already closed */
          }
        };

        const emit = (event: Record<string, unknown>) => {
          if (closed) return;
          try {
            controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
          } catch {
            closed = true;
          }
        };

        emit({ type: "phase", phase: "uploading", message: "Video received, starting detection…" });

        const proc = spawn(pythonPath(), cliArgs, { env, cwd: root });
        let stderr = "";
        let stdoutBuffer = "";

        proc.stdout.on("data", (chunk: Buffer) => {
          stdoutBuffer += chunk.toString();
          const lines = stdoutBuffer.split("\n");
          stdoutBuffer = lines.pop() ?? "";
          for (const line of lines) {
            if (!line.trim()) continue;
            try {
              emit(JSON.parse(line) as Record<string, unknown>);
            } catch {
              // ignore non-JSON stdout
            }
          }
        });

        proc.stderr.on("data", (d) => {
          stderr += d.toString();
        });

        proc.on("close", async (code) => {
          try {
            if (stdoutBuffer.trim()) {
              try {
                emit(JSON.parse(stdoutBuffer) as Record<string, unknown>);
              } catch {
                // ignore trailing non-JSON stdout
              }
            }
            if (code !== 0) {
              emit({ type: "error", error: stderr.trim() || "Detection failed" });
              return;
            }
            const result = JSON.parse(await fs.readFile(jsonPath, "utf8")) as DetectPayload;
            emit({
              type: "done",
              ...result,
              threshold: result.threshold ?? 0.05,
              clip_series: result.clip_series ?? [],
            });
          } catch (err) {
            emit({
              type: "error",
              error: err instanceof Error ? err.message : "Failed to parse result",
            });
          } finally {
            await fs.rm(tmpDir, { recursive: true, force: true });
            safeClose();
          }
        });

        proc.on("error", async (err) => {
          emit({ type: "error", error: err.message });
          await fs.rm(tmpDir, { recursive: true, force: true });
          safeClose();
        });
      },
    });

    return new NextResponse(body, {
      headers: {
        "Content-Type": "application/x-ndjson",
        "Cache-Control": "no-cache",
      },
    });
  }

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(pythonPath(), cliArgs, { env, cwd: root });
    let stderr = "";
    proc.stderr.on("data", (d) => (stderr += d.toString()));
    proc.on("close", async (code) => {
      try {
        if (code !== 0) {
          resolve(NextResponse.json({ error: stderr || "Detection failed" }, { status: 500 }));
          return;
        }
        const result = JSON.parse(await fs.readFile(jsonPath, "utf8"));
        resolve(NextResponse.json(result));
      } catch (err) {
        resolve(
          NextResponse.json(
            { error: err instanceof Error ? err.message : "Failed to parse result" },
            { status: 500 },
          ),
        );
      } finally {
        await fs.rm(tmpDir, { recursive: true, force: true });
      }
    });
  });
}

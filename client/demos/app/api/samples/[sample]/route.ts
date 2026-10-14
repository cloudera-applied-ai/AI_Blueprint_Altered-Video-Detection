import { createReadStream } from "fs";
import fs from "fs/promises";
import { NextRequest, NextResponse } from "next/server";
import path from "path";
import { projectRoot } from "../../utils/persistedConfig";

const SAMPLES: Record<string, string> = {
  real: "real_sample_video.mp4",
  fake: "fake_sample_video.mp4",
};

export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ sample: string }> },
): Promise<NextResponse> {
  const { sample } = await context.params;
  const filename = SAMPLES[sample];
  if (!filename) {
    return NextResponse.json({ error: "Sample not found" }, { status: 404 });
  }

  const filePath = path.join(projectRoot(), "assets", filename);
  try {
    await fs.access(filePath);
  } catch {
    return NextResponse.json({ error: "Sample file missing" }, { status: 404 });
  }

  const stream = createReadStream(filePath);
  return new NextResponse(stream as unknown as ReadableStream, {
    headers: {
      "Content-Type": "video/mp4",
      "Cache-Control": "public, max-age=86400",
    },
  });
}

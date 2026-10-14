import { NextResponse } from "next/server";

export async function GET(): Promise<NextResponse> {
  const role = (process.env.SVD_APP_ROLE || "launchpad").toLowerCase() === "runtime" ? "runtime" : "launchpad";
  return NextResponse.json({
    role,
    mode: process.env.NIM_DEPLOY_MODE || "OPEN",
  });
}

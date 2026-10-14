import fs from "fs";
import { NextResponse } from "next/server";
import path from "path";
import { projectRoot } from "../utils/persistedConfig";

export async function GET(): Promise<NextResponse> {
  const catalogPath = path.join(projectRoot(), "cai/config/open_model_catalog.json");
  if (!fs.existsSync(catalogPath)) {
    return NextResponse.json({ error: "Catalog not found" }, { status: 404 });
  }
  const data = JSON.parse(fs.readFileSync(catalogPath, "utf8"));
  return NextResponse.json(data);
}

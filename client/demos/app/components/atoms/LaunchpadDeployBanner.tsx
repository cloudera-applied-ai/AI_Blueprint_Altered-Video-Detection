"use client";

import Link from "next/link";
import { useAppRole } from "@/app/hooks/useAppRole";

export default function LaunchpadDeployBanner({ pipelineReady }: { pipelineReady: boolean }) {
  const { isLaunchpad } = useAppRole();
  if (!isLaunchpad || pipelineReady) return null;

  return (
    <p className="rounded border border-amber-800 bg-amber-950/40 px-4 py-3 text-sm">
      Deploy a runtime application from the{" "}
      <Link href="/demos/configure" className="underline">
        Launchpad
      </Link>
      , then open that app&apos;s URL to run detection.
    </p>
  );
}

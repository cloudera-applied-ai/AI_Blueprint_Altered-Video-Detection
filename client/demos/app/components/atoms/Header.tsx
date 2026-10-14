"use client";

import Link from "next/link";
import { useAppRole } from "@/app/hooks/useAppRole";

export default function Header() {
  const { isLaunchpad } = useAppRole();

  return (
    <header className="sticky top-0 z-50 border-b border-[var(--border)] bg-[var(--page-bg)]/85 backdrop-blur-md">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-4 py-4 sm:px-6">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">
            Media integrity · Cloudera AI
          </p>
          <h1 className="truncate text-xl font-semibold tracking-tight text-[var(--text-primary)]">
            Synthetic Video Detector
          </h1>
          <p className="hidden text-sm text-[var(--text-secondary)] sm:block">
            {isLaunchpad
              ? "Deploy Bundled GPU or Serverless NVCF runtime applications"
              : "Clip-level analysis for deepfake and synthetic media workflows"}
          </p>
        </div>
        <nav className="flex shrink-0 items-center gap-1 rounded-lg border border-[var(--border)] bg-[var(--surface)] p-1 text-sm">
          {isLaunchpad ? (
            <Link
              href="/demos/configure"
              className="rounded-md px-3 py-1.5 font-medium text-[var(--text-primary)] hover:bg-[var(--surface-elevated)]"
            >
              Launchpad
            </Link>
          ) : (
            <>
              <Link
                href="/demos/detect"
                className="rounded-md px-3 py-1.5 text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
              >
                Detect
              </Link>
              <Link
                href="/demos/demo"
                className="rounded-md px-3 py-1.5 text-[var(--text-secondary)] hover:bg-[var(--surface-elevated)] hover:text-[var(--text-primary)]"
              >
                Demo
              </Link>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

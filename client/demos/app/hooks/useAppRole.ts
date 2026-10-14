"use client";

import { useEffect, useState } from "react";

export type AppRole = "launchpad" | "runtime";

export function useAppRole() {
  const [role, setRole] = useState<AppRole>("launchpad");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    void (async () => {
      try {
        const res = await fetch("/api/app-info");
        const data = (await res.json()) as { role?: string };
        if (!cancelled) {
          setRole(data.role === "runtime" ? "runtime" : "launchpad");
        }
      } catch {
        if (!cancelled) setRole("launchpad");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return {
    role,
    loading,
    isLaunchpad: role === "launchpad",
    isRuntime: role === "runtime",
  };
}

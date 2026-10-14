/** Resolve app role from runtime env (not NEXT_PUBLIC — that is build-time only). */

export type AppRole = "launchpad" | "runtime";

export function getAppRole(): AppRole {
  const role = (process.env.SVD_APP_ROLE || "launchpad").toLowerCase();
  return role === "runtime" ? "runtime" : "launchpad";
}

export function isLaunchpadRole(): boolean {
  return getAppRole() === "launchpad";
}

export function defaultLandingPath(): string {
  return isLaunchpadRole() ? "/demos/configure" : "/demos/detect";
}

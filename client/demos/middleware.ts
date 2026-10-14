import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

function appRole(): string {
  return (process.env.SVD_APP_ROLE || "launchpad").toLowerCase();
}

export function middleware(request: NextRequest) {
  if (appRole() !== "runtime") return NextResponse.next();

  const { pathname } = request.nextUrl;
  if (pathname === "/" || pathname.startsWith("/demos/configure")) {
    return NextResponse.redirect(new URL("/demos/detect", request.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/demos/configure", "/demos/configure/:path*"],
};

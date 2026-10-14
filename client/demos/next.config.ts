import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  async redirects() {
    return [
      { source: "/", destination: "/demos/configure", permanent: false },
      { source: "/demos", destination: "/demos/configure", permanent: false },
    ];
  },
};

export default nextConfig;

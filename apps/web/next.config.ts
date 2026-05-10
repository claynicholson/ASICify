import path from "node:path";
import type { NextConfig } from "next";

const config: NextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@asicify/shared"],
  // Standalone output bundles a minimal node_modules tree for the production
  // server. Required for the Docker image. The tracing root is the monorepo
  // root, so workspace deps (@asicify/shared) get traced correctly.
  output: "standalone",
  outputFileTracingRoot: path.join(process.cwd(), "../.."),
  async rewrites() {
    return [
      {
        source: "/api/backend/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default config;

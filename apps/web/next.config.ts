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
};

export default config;

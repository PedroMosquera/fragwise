import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // No transpilePackages: 0b has no shared workspace packages emitting code into web.
};

export default nextConfig;

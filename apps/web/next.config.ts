import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Phase 4b ADR-0049: react-markdown@9 + remark-gfm@4 + rehype-sanitize@6 are
  // ESM-only packages. transpilePackages ensures Next 16 bundles them
  // for both server (RSC) and client builds without ESM resolution errors.
  transpilePackages: ["react-markdown", "remark-gfm", "rehype-sanitize"],
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "images.fragwise.app",
        pathname: "/**",
      },
      // Local dev fallback for placeholder paths under /public:
      {
        protocol: "http",
        hostname: "localhost",
        pathname: "/**",
      },
    ],
  },
};

export default nextConfig;

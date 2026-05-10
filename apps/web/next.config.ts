import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // The Next 16 dev indicator (position:fixed bottom-left) gets stitched
  // into every viewport tile of Playwright full-page screenshots, leaving
  // a stray dark "N" badge floating mid-page in the captured PNGs. Off
  // in dev only; production never renders it regardless.
  devIndicators: false,
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

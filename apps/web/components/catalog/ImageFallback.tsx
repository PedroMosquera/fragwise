// W5/F4: oklch panel; theme-aware lightness + glyph FG via
// --fallback-l / --fallback-fg (ADR-0052). Hue is still per-slug
// deterministic; L flips on .dark via tokens.css.
// Note on `node:crypto`: this module runs in the Node runtime (RSC,
// server tier). If any (site) route is later migrated to the Edge
// runtime, swap createHash for an async crypto.subtle.digest("SHA-256",
// ...) wrapper. We do NOT pin Edge runtime today, so the sync hash is
// fine. (S4 fix.)
import { createHash } from "node:crypto";

const BANDS = [25, 35, 45, 70, 200, 280];

function panelHue(slug: string): number {
  // Hash → hue band + small jitter; constant L=0.78 (light) / 0.42
  // (dark) keeps perceived lightness stable across hues so foreground
  // glyph contrast is uniform.
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitterByte = parseInt(h.slice(2, 4), 16);
  const jitter = (jitterByte % 12) - 6; // -6..+5
  return BANDS[band] + jitter;
}

export function ImageFallback({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  const hue = panelHue(slug);
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="absolute inset-0 flex items-end justify-start"
      style={
        {
          "--fallback-h": String(hue),
          backgroundColor: "oklch(var(--fallback-l) 0.06 var(--fallback-h))",
        } as React.CSSProperties
      }
    >
      <span
        className="font-display select-none"
        style={{
          color: "var(--fallback-fg)",
          fontSize: "60%",
          lineHeight: 1,
          padding: "0 0 0.5em 0.4em",
          fontWeight: 600,
        }}
      >
        {initial}
      </span>
    </div>
  );
}

// W5/F4: oklch with constant L=0.78 for perceptually uniform pastel
// panels — dark ink universally passes WCAG AA on all 6 hue bands.
// Note on `node:crypto`: this module runs in the Node runtime (RSC,
// server tier). If any (site) route is later migrated to the Edge
// runtime, swap createHash for an async crypto.subtle.digest("SHA-256",
// ...) wrapper. We do NOT pin Edge runtime today, so the sync hash is
// fine. (S4 fix.)
import { createHash } from "node:crypto";

const BANDS = [25, 35, 45, 70, 200, 280];

function panelOklch(slug: string): { bg: string; fg: string } {
  // Hash → hue band + small jitter; constant L=0.78 keeps perceived
  // lightness stable across hues so dark ink contrast is uniform.
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitterByte = parseInt(h.slice(2, 4), 16);
  const jitter = (jitterByte % 12) - 6; // -6..+5
  const hue = BANDS[band] + jitter;
  return {
    bg: `oklch(0.78 0.06 ${hue})`,
    // Dark ink universally — at L=0.78 with chroma 0.06, every band
    // reads as a soft pastel; the deep-ink foreground passes AA on
    // all six. Foreground variable resolves to oklch(0.21 0.025 270).
    fg: "var(--color-foreground)",
  };
}

export function ImageFallback({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  const { bg, fg } = panelOklch(slug);
  const initial = name.trim().charAt(0).toUpperCase() || "?";
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="absolute inset-0 flex items-end justify-start"
      style={{ backgroundColor: bg }}
    >
      <span
        className="font-display select-none"
        style={{
          color: fg,
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

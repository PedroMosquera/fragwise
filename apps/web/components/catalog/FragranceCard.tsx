// W3 fix: GenderIcon and lib/format.ts removed from inventory; the
// gender icon is inlined here.
// F13 ADJUSTED: lucide-react@0.460.0 does NOT export Mars/Venus
// (those land in 0.488+). To preserve the design's "icon-style" gender
// indicator without a dep bump, we render a small inline SVG variant
// derived from the standard Mars/Venus glyphs. CircleDot exists in
// 0.460 and is used for unisex/genderfree.
import Link from "next/link";
import Image from "next/image";
import { CircleDot } from "lucide-react";
import { ImageFallback } from "./ImageFallback";
import type { FragranceListItem } from "@/lib/api/fetchers";

function MarsGlyph() {
  return (
    <svg
      role="img"
      aria-label="masculine"
      className="h-3.5 w-3.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="10" cy="14" r="5" />
      <path d="M19 5l-6 6" />
      <path d="M14 5h5v5" />
    </svg>
  );
}

function VenusGlyph() {
  return (
    <svg
      role="img"
      aria-label="feminine"
      className="h-3.5 w-3.5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="9" r="5" />
      <path d="M12 14v8" />
      <path d="M9 19h6" />
    </svg>
  );
}

function genderIcon(gender: string) {
  switch (gender) {
    case "masc":
      return <MarsGlyph />;
    case "fem":
      return <VenusGlyph />;
    default:
      // covers "unisex" and "genderfree" — see Gender enum in
      // openapi.json: ["masc", "fem", "unisex", "genderfree"].
      return (
        <CircleDot
          className="h-3.5 w-3.5"
          aria-label="unisex / genderfree"
        />
      );
  }
}

export function FragranceCard({
  fragrance,
}: {
  fragrance: FragranceListItem;
}) {
  // P1 contract has no image_url field today (see fetchers.ts note).
  // ImageFallback is rendered unconditionally; conditional swap kept
  // ready for the day P1+ adds image_url.
  const imageUrl: string | null = null;

  return (
    <Link
      href={`/fragrances/${fragrance.slug}`}
      className="group flex flex-col gap-3 rounded-md outline-none transition-transform focus-visible:ring-2 focus-visible:ring-ring"
    >
      <div className="relative aspect-[3/4] overflow-hidden rounded-md bg-card shadow-sm transition-shadow group-hover:-translate-y-0.5 group-hover:shadow-md">
        {imageUrl ? (
          <Image
            src={imageUrl}
            alt={`${fragrance.name} bottle`}
            fill
            sizes="(max-width: 640px) 100vw, (max-width: 1024px) 33vw, 25vw"
            className="object-cover"
          />
        ) : (
          <ImageFallback slug={fragrance.slug} name={fragrance.name} />
        )}
      </div>
      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[0.65rem] uppercase tracking-[0.18em] text-muted-foreground">
          {fragrance.brand.name}
        </span>
        <span className="font-display text-lg leading-snug text-foreground">
          {fragrance.name}
        </span>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          {fragrance.year_released ? (
            <span className="font-mono">{fragrance.year_released}</span>
          ) : null}
          {genderIcon(fragrance.gender)}
          {fragrance.concentration ? (
            <span className="font-mono uppercase">
              {fragrance.concentration.name}
            </span>
          ) : null}
        </div>
      </div>
    </Link>
  );
}

// Phase 4b: BrandCard — used on /brands (list rows). The arrow span
// is decorative; the row itself is the link target.
import Link from "next/link";

export function BrandCard({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  return (
    <Link
      href={`/brands/${slug}`}
      className="flex items-baseline justify-between border-b border-border py-4 transition-colors hover:text-accent"
    >
      <span className="font-display text-xl">{name}</span>
      <span aria-hidden className="font-mono text-xs text-muted-foreground">
        →
      </span>
    </Link>
  );
}

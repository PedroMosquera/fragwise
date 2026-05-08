// Phase 4b: PerfumerCard — mirrors BrandCard. Used on /perfumers.
import Link from "next/link";

export function PerfumerCard({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  return (
    <Link
      href={`/perfumers/${slug}`}
      className="flex items-baseline justify-between border-b border-border py-4 transition-colors hover:text-accent"
    >
      <span className="font-display text-xl">{name}</span>
      <span aria-hidden className="font-mono text-xs text-muted-foreground">
        →
      </span>
    </Link>
  );
}

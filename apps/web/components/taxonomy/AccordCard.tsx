// Phase 4b: AccordCard — used on /accords (grid). Each card is a tile
// with the editorial typography pair (mono caption + display name).
import Link from "next/link";

export function AccordCard({
  slug,
  name,
  blurb,
}: {
  slug: string;
  name: string;
  blurb?: string;
}) {
  return (
    <Link
      href={`/accords/${slug}`}
      className="group flex aspect-[5/3] flex-col justify-between rounded-md border border-border bg-card p-5 transition-colors hover:bg-accent hover:text-accent-foreground"
    >
      <span className="font-mono text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground group-hover:text-accent-foreground/70">
        Accord
      </span>
      <div className="flex flex-col gap-2">
        <span className="font-display text-2xl">{name}</span>
        {blurb ? (
          <p className="line-clamp-3 text-sm leading-snug text-muted-foreground group-hover:text-accent-foreground/80">
            {blurb}
          </p>
        ) : null}
      </div>
    </Link>
  );
}

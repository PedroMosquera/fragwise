// Phase 4b: ArticleCard — list-row card for /articles and the home
// "From the journal" teaser. Editorial typography pair: mono date
// caption above a display-font headline.
import Link from "next/link";

export function ArticleCard({
  slug,
  title,
  publishedAt,
}: {
  slug: string;
  title: string;
  publishedAt: string | null;
}) {
  const dateLabel = publishedAt
    ? new Date(publishedAt).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Unpublished";
  return (
    <Link
      href={`/articles/${slug}`}
      className="group block border-b border-border py-8 transition-colors hover:bg-secondary/40"
    >
      <p className="font-mono text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground">
        {dateLabel}
      </p>
      <h3 className="mt-3 font-display text-2xl group-hover:text-accent md:text-3xl">
        {title}
      </h3>
    </Link>
  );
}

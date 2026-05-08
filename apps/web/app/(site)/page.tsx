import Link from "next/link";
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { ArticleCard } from "@/components/editorial/ArticleCard";
import {
  getFeaturedFragrances,
  getAllArticles,
  type FragranceListItem,
  type ArticleSummary,
} from "@/lib/api/fetchers";

// Phase 4b update: mood tile hrefs flip from `/fragrances?accord=<slug>`
// (P4a fallback) to `/accords/<slug>` now that real curated detail
// pages ship with this phase. Slugs match the seeded canonical accord
// families.
const MOODS = [
  { slug: "fresh", label: "Fresh & bright" },
  { slug: "woody", label: "Woody & smoky" },
  { slug: "floral", label: "Floral & soft" },
  { slug: "gourmand", label: "Sweet & comforting" },
  { slug: "oriental", label: "Warm & spiced" },
  { slug: "aquatic", label: "Aquatic & cool" },
];

export default async function HomePage() {
  // Build-time graceful degradation: if the API is unreachable at
  // `next build` (CI without a live API, or transient outage), the
  // home shell still renders so the build does not fail. ISR will
  // refresh featured (revalidate: 600) once the API is back online.
  let featured: FragranceListItem[] = [];
  try {
    featured = await getFeaturedFragrances(6);
  } catch (err) {
    console.warn("[home] getFeaturedFragrances failed — rendering empty.", err);
  }

  // Phase 4b: journal teaser — three most-recent articles. Same
  // try/catch posture as `featured` so home still renders without API.
  let recentArticles: ArticleSummary[] = [];
  try {
    const list = await getAllArticles({ limit: 3, offset: 0 });
    recentArticles = list.data;
  } catch (err) {
    console.warn(
      "[home] getAllArticles failed — empty journal teaser.",
      err,
    );
  }

  return (
    <>
      {/* Hero — asymmetric editorial */}
      <section className="border-b border-border bg-secondary/40">
        <Container className="grid gap-10 py-20 md:grid-cols-12 md:py-32">
          <div className="md:col-span-7 md:col-start-2">
            <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
              An open catalogue of perfume
            </p>
            <h1 className="mt-4 font-display text-5xl font-medium leading-[1.05] tracking-tight md:text-7xl">
              Fragrance,{" "}
              <em className="italic text-accent">read closely</em>.
            </h1>
            <p className="mt-6 max-w-xl text-lg text-muted-foreground">
              A reference for the curious — connoisseur and beginner alike.
              Browse by note, accord, or mood, and let the journal explain
              the rest.
            </p>
            <div className="mt-8 flex gap-4">
              <Link
                href="/fragrances"
                className="rounded-md bg-primary px-5 py-2.5 font-mono text-xs uppercase tracking-wider text-primary-foreground"
              >
                Browse the catalogue
              </Link>
            </div>
          </div>
        </Container>
      </section>

      {/* Discover by mood */}
      <section className="py-20">
        <Container>
          <div className="mb-10 flex items-end justify-between">
            <h2 className="font-display text-3xl">Discover by mood</h2>
            <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
              Six accords
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
            {MOODS.map((m) => (
              // Phase 4b: links to the curated /accords/[slug] page
              // shipped this phase (was /fragrances?accord=<slug> in 4a).
              <Link
                key={m.slug}
                href={`/accords/${m.slug}`}
                className="group flex aspect-[5/3] items-end justify-between rounded-md border border-border bg-card p-5 transition-colors hover:bg-accent hover:text-accent-foreground"
              >
                <span className="font-display text-2xl">{m.label}</span>
                <span
                  aria-hidden
                  className="font-mono text-xs uppercase tracking-wider opacity-60 group-hover:opacity-100"
                >
                  →
                </span>
              </Link>
            ))}
          </div>
        </Container>
      </section>

      {/* Featured fragrances */}
      <section className="border-t border-border bg-card/60 py-20">
        <Container>
          <h2 className="mb-10 font-display text-3xl">
            Featured fragrances
          </h2>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {featured.slice(0, 4).map((f) => (
              <FragranceCard key={f.id} fragrance={f} />
            ))}
            {featured.length >= 6 ? (
              <>
                <div className="hidden lg:block" />
                {featured.slice(4, 6).map((f) => (
                  <FragranceCard key={f.id} fragrance={f} />
                ))}
              </>
            ) : null}
          </div>
        </Container>
      </section>

      {/* Phase 4b: journal teaser — three most-recent articles. */}
      <section className="py-20">
        <Container>
          <div className="mb-8 flex items-end justify-between">
            <h2 className="font-display text-3xl">From the journal</h2>
            <Link
              href="/articles"
              className="font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-accent"
            >
              All essays →
            </Link>
          </div>
          {recentArticles.length === 0 ? (
            <p className="text-muted-foreground">
              No essays published yet. Check back soon.
            </p>
          ) : (
            <div className="grid gap-6 md:grid-cols-3">
              {recentArticles.map((a) => (
                <ArticleCard
                  key={a.slug}
                  slug={a.slug}
                  title={a.title}
                  publishedAt={a.published_at ?? null}
                />
              ))}
            </div>
          )}
        </Container>
      </section>
    </>
  );
}

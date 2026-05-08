// Phase 4b: accord detail. Editorial header + (optional) hand-authored
// blurb wrapped through wrapGlossary + paginated FragranceCard grid.
//
// ISR: revalidate=600 / tag=accord:<slug> (set by getAccordBySlug).
// On unknown slug the fetcher calls notFound() (ADR-0046).
// generateMetadata description prefers ACCORD_COPY blurb (ADR-0047)
// truncated to 160 chars; otherwise falls back to a generic line.
import type { Metadata } from "next";
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { Pagination } from "@/components/catalog/Pagination";
import { Glossary } from "@/components/site/Glossary";
import { wrapGlossary } from "@/lib/glossary";
import { ACCORD_COPY } from "@/lib/accord-copy";
import { getAccordBySlug } from "@/lib/api/fetchers";

const LIMIT = 24;

export async function generateMetadata(props: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await props.params;
  const accord = await getAccordBySlug(slug, { limit: 1, offset: 0 });
  return {
    title: `${accord.name} — Accords — Fragwise`,
    description:
      ACCORD_COPY[slug]?.blurb.slice(0, 160) ??
      `Fragrances built on the ${accord.name} accord.`,
  };
}

export default async function AccordDetailPage(props: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ slug }, sp] = await Promise.all([
    props.params,
    props.searchParams,
  ]);
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;
  const accord = await getAccordBySlug(slug, { limit: LIMIT, offset });
  const blurb = ACCORD_COPY[slug]?.blurb;

  return (
    <Container className="py-12 md:py-20">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        Accord
      </p>
      <h1 className="mt-2 font-display text-5xl md:text-7xl">{accord.name}</h1>
      {blurb && (
        <p className="mt-8 max-w-prose text-lg text-foreground/85">
          {wrapGlossary(blurb, Glossary)}
        </p>
      )}
      <section className="mt-16">
        <h2 className="mb-6 font-display text-2xl">Fragrances</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
          {accord.fragrances.data.map((f) => (
            <FragranceCard key={f.id} fragrance={f} />
          ))}
        </div>
        <div className="mt-12">
          <Pagination
            total={accord.fragrances.pagination.total}
            limit={accord.fragrances.pagination.limit}
            offset={accord.fragrances.pagination.offset}
            hrefBase={`/accords/${slug}`}
            searchParams={new URLSearchParams()}
          />
        </div>
      </section>
    </Container>
  );
}

// Phase 4b: brand detail. Editorial header + paginated FragranceCard
// grid (D-DetailLayout reuses 4a primitives).
//
// ISR: revalidate=1800 / tag=brand:<slug>. On unknown slug the fetcher
// calls notFound() (ADR-0046).
import type { Metadata } from "next";
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { Pagination } from "@/components/catalog/Pagination";
import { getBrandBySlug } from "@/lib/api/fetchers";

const LIMIT = 24;

export async function generateMetadata(props: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await props.params;
  const brand = await getBrandBySlug(slug, { limit: 1, offset: 0 });
  return {
    title: `${brand.name} — Brands — Fragwise`,
    description: `Fragrances by ${brand.name} indexed in Fragwise.`,
  };
}

export default async function BrandDetailPage(props: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ slug }, sp] = await Promise.all([
    props.params,
    props.searchParams,
  ]);
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;
  const brand = await getBrandBySlug(slug, { limit: LIMIT, offset });

  return (
    <Container className="py-12 md:py-20">
      <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
        Brand
      </p>
      <h1 className="mt-2 font-display text-5xl md:text-7xl">{brand.name}</h1>
      <section className="mt-16">
        <h2 className="mb-6 font-display text-2xl">Fragrances</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
          {brand.fragrances.data.map((f) => (
            <FragranceCard key={f.id} fragrance={f} />
          ))}
        </div>
        <div className="mt-12">
          <Pagination
            total={brand.fragrances.pagination.total}
            limit={brand.fragrances.pagination.limit}
            offset={brand.fragrances.pagination.offset}
            hrefBase={`/brands/${slug}`}
            searchParams={new URLSearchParams()}
          />
        </div>
      </section>
    </Container>
  );
}

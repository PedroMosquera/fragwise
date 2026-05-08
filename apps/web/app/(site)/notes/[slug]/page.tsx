// Phase 4b: note detail.
// ISR: revalidate=600 / tag=note:<slug> (set by getNoteBySlug fetcher).
// On unknown slug the fetcher calls notFound() (ADR-0046).
import Link from "next/link";
import type { Metadata } from "next";
import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { Pagination } from "@/components/catalog/Pagination";
import { getNoteBySlug } from "@/lib/api/fetchers";

const LIMIT = 24;

export async function generateMetadata(props: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await props.params;
  const note = await getNoteBySlug(slug, { limit: 1, offset: 0 });
  return {
    title: `${note.name} — Notes — Fragwise`,
    description: `Fragrances featuring the ${note.name} note.`,
  };
}

export default async function NoteDetailPage(props: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ slug }, sp] = await Promise.all([
    props.params,
    props.searchParams,
  ]);
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;
  const note = await getNoteBySlug(slug, { limit: LIMIT, offset });

  return (
    <Container className="py-12 md:py-20">
      {note.parent && (
        <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
          <Link
            href={`/notes/${note.parent.slug}`}
            className="hover:text-accent"
          >
            ← {note.parent.name}
          </Link>
        </p>
      )}
      <h1 className="mt-2 font-display text-5xl">{note.name}</h1>
      <section className="mt-12">
        <h2 className="mb-6 font-display text-2xl">Fragrances</h2>
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
          {note.fragrances.data.map((f) => (
            <FragranceCard key={f.id} fragrance={f} />
          ))}
        </div>
        <div className="mt-12">
          <Pagination
            total={note.fragrances.pagination.total}
            limit={note.fragrances.pagination.limit}
            offset={note.fragrances.pagination.offset}
            hrefBase={`/notes/${slug}`}
            searchParams={new URLSearchParams()}
          />
        </div>
      </section>
    </Container>
  );
}

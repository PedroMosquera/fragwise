// Phase 4b: perfumers list with debounced ?q= search input.
// Mirrors the brands list page; ISR posture identical.
import { Container } from "@/components/site/Container";
import { PerfumerCard } from "@/components/taxonomy/PerfumerCard";
import { Pagination } from "@/components/catalog/Pagination";
import { SearchInput } from "@/components/site/SearchInput";
import { getPerfumers } from "@/lib/api/fetchers";

const LIMIT = 50;

export const metadata = {
  title: "Perfumers — Fragwise",
  description: "Perfumers credited in the Fragwise catalogue.",
};

export default async function PerfumersPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await props.searchParams;
  const q = typeof sp.q === "string" ? sp.q : undefined;
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;

  let list;
  try {
    list = await getPerfumers({ q, limit: LIMIT, offset });
  } catch (err) {
    console.warn(
      `[perfumers] getPerfumers failed (q=${q ?? "<none>"}). Rendering empty state.`,
      err,
    );
    list = {
      data: [],
      pagination: { limit: LIMIT, offset, total: 0, has_next: false },
    };
  }

  const usp = new URLSearchParams();
  if (q) usp.set("q", q);

  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-6 font-display text-4xl">Perfumers</h1>
      <div className="mb-10">
        <SearchInput placeholder="Search perfumers…" />
      </div>
      {list.data.length === 0 ? (
        <p className="text-muted-foreground">
          No perfumers match your search.
        </p>
      ) : (
        <ul className="divide-y divide-border">
          {list.data.map((p) => (
            <li key={p.slug}>
              <PerfumerCard slug={p.slug} name={p.name} />
            </li>
          ))}
        </ul>
      )}
      <div className="mt-12">
        <Pagination
          total={list.pagination.total}
          limit={list.pagination.limit}
          offset={list.pagination.offset}
          hrefBase="/perfumers"
          searchParams={usp}
        />
      </div>
    </Container>
  );
}

// Phase 4b: brands list with debounced ?q= search input.
// ISR: revalidate=3600 (no `q`) / 600 (with `q`) / tag=brands:list.
// On API 422 (malformed `q` payload) we fall through to an empty state
// so the page never crashes on user input.
import { Container } from "@/components/site/Container";
import { BrandCard } from "@/components/taxonomy/BrandCard";
import { Pagination } from "@/components/catalog/Pagination";
import { SearchInput } from "@/components/site/SearchInput";
import { getBrands } from "@/lib/api/fetchers";

const LIMIT = 50;

export const metadata = {
  title: "Brands — Fragwise",
  description: "Perfume houses indexed in Fragwise.",
};

export default async function BrandsPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await props.searchParams;
  const q = typeof sp.q === "string" ? sp.q : undefined;
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;

  let list;
  try {
    list = await getBrands({ q, limit: LIMIT, offset });
  } catch (err) {
    console.warn(
      `[brands] getBrands failed (q=${q ?? "<none>"}). Rendering empty state.`,
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
      <h1 className="mb-6 font-display text-4xl">Brands</h1>
      <div className="mb-10">
        <SearchInput placeholder="Search brands…" />
      </div>
      {list.data.length === 0 ? (
        <p className="text-muted-foreground">No brands match your search.</p>
      ) : (
        <ul className="divide-y divide-border">
          {list.data.map((b) => (
            <li key={b.slug}>
              <BrandCard slug={b.slug} name={b.name} />
            </li>
          ))}
        </ul>
      )}
      <div className="mt-12">
        <Pagination
          total={list.pagination.total}
          limit={list.pagination.limit}
          offset={list.pagination.offset}
          hrefBase="/brands"
          searchParams={usp}
        />
      </div>
    </Container>
  );
}

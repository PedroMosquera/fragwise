import { Container } from "@/components/site/Container";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { Pagination } from "@/components/catalog/Pagination";
import { FilterSidebar } from "@/components/catalog/FilterSidebar";
import {
  getFragrances,
  getAllAccords,
  getAllBrands,
  type FragranceListParams,
  type Gender,
} from "@/lib/api/fetchers";

// F3: Concentration filter facet — fallback static list. There is no
// `/api/v1/concentrations` endpoint in `apps/api/openapi.json` today;
// when one lands, swap this constant for `getAllConcentrations()` and
// move it into Promise.all below. Apply-time check: smoke fetch
// `GET /api/v1/fragrances?concentration=edt`; if it 0-results, the
// seed produces different slugs and this list should be hidden until
// the endpoint exists. The conditional `facets.concentrations.length
// > 0` in FilterSidebar avoids rendering an empty accordion if we
// ship `[]` here instead.
const CONCENTRATION_FALLBACK = [
  { slug: "edt", name: "EDT" },
  { slug: "edp", name: "EDP" },
  { slug: "parfum", name: "Parfum" },
];

const GENDER_VALUES: Gender[] = ["masc", "fem", "unisex", "genderfree"];
const YEAR_MIN = 1700;
const YEAR_MAX = 2100;

type Search = Record<string, string | string[] | undefined>;

// F6: validate gender ∈ enum, clamp year_min/year_max ∈ [1700, 2100].
// Drop invalid values silently rather than letting them through to the
// API (which would 422).
function pickQuery(sp: Search): FragranceListParams {
  const arr = (v: string | string[] | undefined) => {
    const list = Array.isArray(v) ? v : v ? [v] : undefined;
    return list ? [...list].sort() : undefined;
  };
  const num = (v: string | string[] | undefined) => {
    const n = typeof v === "string" ? Number(v) : NaN;
    return Number.isFinite(n) ? n : undefined;
  };
  const str = (v: string | string[] | undefined) =>
    typeof v === "string" ? v : undefined;

  const rawGender = str(sp.gender);
  const gender =
    rawGender && (GENDER_VALUES as string[]).includes(rawGender)
      ? (rawGender as Gender)
      : undefined;

  const clampYear = (v: number | undefined) => {
    if (v === undefined) return undefined;
    if (v < YEAR_MIN || v > YEAR_MAX) return undefined;
    return v;
  };

  return {
    limit: num(sp.limit) ?? 24,
    offset: num(sp.offset) ?? 0,
    brand: str(sp.brand),
    gender,
    year_min: clampYear(num(sp.year_min)),
    year_max: clampYear(num(sp.year_max)),
    concentration: str(sp.concentration),
    accord: arr(sp.accord),
    note: arr(sp.note),
    perfumer: arr(sp.perfumer),
  };
}

// Next.js 16: searchParams is a Promise (Context7-verified).
export default async function FragrancesPage(props: {
  searchParams: Promise<Search>;
}) {
  const sp = await props.searchParams;
  const query = pickQuery(sp);

  // W4 + F4 fix: Fetch list + accord facets + brand facets in parallel.
  // Real accord/brand slugs come from the API so the sidebar cannot
  // drift from seed data. Concentration facet remains a static
  // fallback until /api/v1/concentrations exists.
  // F11: getFragrances throws on missing data — at runtime, error.tsx
  // catches it. At build time (CI without a live API) we degrade to
  // an empty list so the build succeeds; ISR (revalidate: 300) hydrates
  // it once the API is reachable.
  const emptyList = {
    data: [] as Awaited<ReturnType<typeof getFragrances>>["data"],
    pagination: { limit: query.limit ?? 24, offset: 0, total: 0, has_next: false },
  };
  const [list, accords, brands] = await Promise.all([
    getFragrances(query).catch((err) => {
      console.warn("[fragrances] getFragrances failed — empty grid.", err);
      return emptyList;
    }),
    getAllAccords().catch((err) => {
      console.warn("[fragrances] getAllAccords failed — empty accord facet.", err);
      return [];
    }),
    getAllBrands().catch((err) => {
      console.warn("[fragrances] getAllBrands failed — empty brand facet.", err);
      return [];
    }),
  ]);

  // Build a canonical URLSearchParams so multi-value selections sort
  // identically across requests (matches canonicalizeQuery on the
  // fetcher tier).
  const usp = new URLSearchParams();
  const sortedKeys = Object.keys(sp).sort();
  for (const k of sortedKeys) {
    const v = sp[k];
    if (v == null) continue;
    const items = Array.isArray(v) ? [...v].sort() : [v];
    for (const vv of items) usp.append(k, vv);
  }

  // S1 fix: convert searchParams to plain Record<string, string |
  // string[]> via Object.fromEntries for cross-boundary safety
  // (Server Component → "use client" FilterSidebar).
  const filterSearchParams: Record<string, string | string[]> =
    Object.fromEntries(
      sortedKeys.map((k) => {
        const v = sp[k];
        return [k, Array.isArray(v) ? [...v].sort() : (v ?? "")];
      }),
    );

  return (
    <Container className="py-10 md:py-16">
      <h1 className="mb-10 font-display text-4xl">Fragrances</h1>
      <div className="grid gap-10 md:grid-cols-[16rem_1fr]">
        <FilterSidebar
          pathname="/fragrances"
          searchParams={filterSearchParams}
          facets={{
            accords,
            brands,
            concentrations: CONCENTRATION_FALLBACK,
          }}
        />
        {/* F9: drop in-page <Suspense> and rely on loading.tsx only.
            With the data fetch above the Suspense boundary, the
            fallback would never trigger. */}
        <section>
          {list.data.length === 0 ? (
            <div className="rounded-md border border-dashed border-border p-12 text-center">
              <p className="font-display text-2xl">No matches.</p>
              <p className="mt-2 text-muted-foreground">
                Try clearing some filters.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-4">
              {list.data.map((f) => (
                <FragranceCard key={f.id} fragrance={f} />
              ))}
            </div>
          )}
          <div className="mt-12">
            <Pagination
              total={list.pagination.total}
              limit={list.pagination.limit}
              offset={list.pagination.offset}
              hrefBase="/fragrances"
              searchParams={usp}
            />
          </div>
        </section>
      </div>
    </Container>
  );
}

// ISR via the fetcher (next: { revalidate: 300 }) — the cache key
// embeds the URL searchParams automatically because the fetcher
// receives them as query params.

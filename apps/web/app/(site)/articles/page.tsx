// Phase 4b: articles list. ISR: revalidate=600 / tag=articles:list.
// API returns ordered by published_at DESC.
import { Container } from "@/components/site/Container";
import { ArticleCard } from "@/components/editorial/ArticleCard";
import { Pagination } from "@/components/catalog/Pagination";
import { getAllArticles } from "@/lib/api/fetchers";

const LIMIT = 12;

export const metadata = {
  title: "Journal — Fragwise",
  description: "Long-form essays on perfume craft, history, and method.",
};

export default async function ArticlesPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await props.searchParams;
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;
  // Build-time graceful degradation: render empty list when API is down.
  let list: Awaited<ReturnType<typeof getAllArticles>>;
  try {
    list = await getAllArticles({ limit: LIMIT, offset });
  } catch (err) {
    console.warn("[articles] getAllArticles failed — rendering empty.", err);
    list = {
      data: [],
      pagination: { limit: LIMIT, offset, total: 0, has_next: false },
    };
  }

  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-10 font-display text-4xl">Journal</h1>
      <div>
        {list.data.map((a) => (
          <ArticleCard
            key={a.slug}
            slug={a.slug}
            title={a.title}
            publishedAt={a.published_at ?? null}
          />
        ))}
      </div>
      <div className="mt-12">
        <Pagination
          total={list.pagination.total}
          limit={list.pagination.limit}
          offset={list.pagination.offset}
          hrefBase="/articles"
          searchParams={new URLSearchParams()}
        />
      </div>
    </Container>
  );
}

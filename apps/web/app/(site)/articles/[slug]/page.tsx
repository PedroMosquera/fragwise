// Phase 4b: article detail. Title + date + sanitized markdown body
// (ArticleBody composes react-markdown + remark-gfm + rehype-sanitize
// per ADRs 0041–0043).
//
// ISR: revalidate=600 / tag=article:<slug>. On unknown slug the
// fetcher calls notFound() (ADR-0046).
// generateMetadata description = first 160 chars of body or title.
import type { Metadata } from "next";
import { Container } from "@/components/site/Container";
import { ArticleBody } from "@/components/editorial/ArticleBody";
import { getArticleBySlug } from "@/lib/api/fetchers";

export async function generateMetadata(props: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await props.params;
  const article = await getArticleBySlug(slug);
  return {
    title: `${article.title} — Journal — Fragwise`,
    description: article.body?.slice(0, 160) ?? article.title,
  };
}

export default async function ArticleDetailPage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;
  const article = await getArticleBySlug(slug);
  const dateLabel = article.published_at
    ? new Date(article.published_at).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : null;

  return (
    <Container className="py-12 md:py-20">
      <article className="mx-auto max-w-prose">
        {dateLabel && (
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            {dateLabel}
          </p>
        )}
        <h1 className="mt-3 font-display text-5xl">{article.title}</h1>
        <div className="mt-12">
          <ArticleBody body={article.body} />
        </div>
      </article>
    </Container>
  );
}

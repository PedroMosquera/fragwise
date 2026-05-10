import { createHash } from "node:crypto";
import Link from "next/link";
import { Container } from "@/components/site/Container";
import { Pyramid } from "@/components/catalog/Pyramid";
import { AccordBadge } from "@/components/catalog/AccordBadge";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import { Glossary } from "@/components/site/Glossary";
import { wrapGlossary } from "@/lib/glossary";
import {
  getFragrances,
  getFragranceBySlug,
  type FragranceListItem,
} from "@/lib/api/fetchers";

// S6 fix: editorial typographic hero fallback. Reuses ImageFallback's
// constant-L oklch palette (ADR-0036) so the panel matches the card
// aesthetic, but at hero scale we set the fragrance name in large
// Fraunces so the panel reads as intentional, not "no image".
const HERO_BANDS = [25, 35, 45, 70, 200, 280];

function heroPanelOklch(slug: string): string {
  const h = createHash("sha256").update(slug).digest("hex");
  const band = parseInt(h.slice(0, 2), 16) % 6;
  const jitter = (parseInt(h.slice(2, 4), 16) % 12) - 6;
  return `oklch(0.78 0.06 ${HERO_BANDS[band] + jitter})`;
}

// F5: long fragrance names ("L'Air du Désert Marocain") would clip
// horizontally inside aspect-[3/4] with overflow-hidden. We use
// break-words + leading-[0.95] + text-balance + clamp() font sizing
// so long names wrap gracefully instead of clipping.
function DetailHeroFallback({
  slug,
  name,
  brandName,
}: {
  slug: string;
  name: string;
  brandName: string;
}) {
  return (
    <div
      role="img"
      aria-label={`${name} (no bottle image available)`}
      className="relative flex aspect-[3/4] flex-col items-center justify-center gap-4 overflow-hidden rounded-md p-8 text-center shadow-md"
      style={{ background: heroPanelOklch(slug) }}
    >
      <span
        className="break-words font-display font-light tracking-tight text-balance text-foreground"
        style={{
          fontSize: "clamp(2rem, 6vw, 4.5rem)",
          lineHeight: 0.95,
        }}
      >
        {name}
      </span>
      <span className="font-mono text-xs uppercase tracking-[0.22em] text-foreground/70">
        {brandName}
      </span>
    </div>
  );
}

export default async function FragranceDetailPage(props: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await props.params;
  const f = await getFragranceBySlug(slug);

  // Sibling fragrances from the same brand. With the v1 seed every
  // brand carries exactly one fragrance, so siblings is usually empty —
  // the section then collapses to a single "Explore the brand" link.
  let siblings: FragranceListItem[] = [];
  try {
    const list = await getFragrances({ brand: f.brand.slug, limit: 5 });
    siblings = list.data.filter((s) => s.slug !== f.slug).slice(0, 4);
  } catch (err) {
    console.warn(
      `[fragrance:${slug}] sibling fetch failed — rendering brand link only.`,
      err,
    );
  }

  return (
    <Container className="py-12 md:py-20">
      {/* Hero split */}
      <div className="grid gap-12 md:grid-cols-12">
        <div className="md:col-span-5">
          {/* Detail hero uses an EDITORIAL typographic fallback rather
              than ImageFallback's letter-bottom-corner pattern (which
              is sized for cards). Same oklch panel, but the fragrance
              name and brand wordmark fill the slot. When P1+ adds an
              `image_url`, swap to `<Image fill priority />`. */}
          <DetailHeroFallback
            slug={f.slug}
            name={f.name}
            brandName={f.brand.name}
          />
        </div>
        <div className="md:col-span-7">
          <p className="font-mono text-xs uppercase tracking-[0.22em] text-muted-foreground">
            {f.brand.name}
          </p>
          <h1 className="mt-3 font-display text-5xl leading-[1.05] tracking-tight md:text-6xl">
            {f.name}
          </h1>
          <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 font-mono text-xs uppercase tracking-wider text-muted-foreground">
            {f.year_released ? <span>{f.year_released}</span> : null}
            <span>{f.gender}</span>
            {f.concentration ? <span>{f.concentration.name}</span> : null}
            {f.perfumers.length > 0 ? (
              <span className="normal-case tracking-normal">
                Nose:{" "}
                {f.perfumers.map((p, i) => (
                  <span key={p.slug}>
                    {p.name}
                    {i < f.perfumers.length - 1 ? ", " : ""}
                  </span>
                ))}
              </span>
            ) : null}
          </div>
          <div className="mt-6 flex flex-wrap gap-2">
            {f.accords.map((a) => (
              <AccordBadge key={a.slug} accord={a} />
            ))}
          </div>
          {f.description ? (
            <p className="mt-8 max-w-xl text-base leading-relaxed text-foreground/90">
              {/* First-mention-per-term wrap (handles ALL 12 terms,
                  case-insensitive, all occurrences past the first per
                  term are left as plain text). */}
              {wrapGlossary(f.description, Glossary)}
            </p>
          ) : null}
        </div>
      </div>

      {/* Pyramid */}
      <section className="mt-20">
        <h2 className="mb-8 font-display text-3xl">
          The <Glossary termKey="top-heart-base">pyramid</Glossary>
        </h2>
        <Pyramid notes={f.notes} />
      </section>

      {/* Articles */}
      <section className="mt-20">
        <h2 className="mb-6 font-display text-2xl">In the journal</h2>
        {f.articles.length === 0 ? (
          <p className="text-muted-foreground">No articles yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {f.articles.map((a) => (
              <li key={a.slug} className="font-display text-lg">
                {a.title}
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* More from this brand */}
      <section className="mt-20">
        <div className="mb-6 flex items-end justify-between gap-4">
          <h2 className="font-display text-2xl">More from {f.brand.name}</h2>
          <Link
            href={`/brands/${f.brand.slug}`}
            className="font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-accent"
          >
            All {f.brand.name} →
          </Link>
        </div>
        {siblings.length === 0 ? (
          <p className="text-muted-foreground">
            No other fragrances from {f.brand.name} in the catalogue yet.
          </p>
        ) : (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
            {siblings.map((s) => (
              <FragranceCard key={s.id} fragrance={s} />
            ))}
          </div>
        )}
      </section>
    </Container>
  );
}

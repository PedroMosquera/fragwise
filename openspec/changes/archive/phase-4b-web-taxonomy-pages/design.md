# Design: Phase 4b — Web Taxonomy Pages

## Technical Approach

Phase 4b adds 10 new App Router routes (notes, accords, brands, perfumers,
articles — list + detail each) plus 7 new components and 2 lib files,
extending the editorial-perfumery shell shipped by Phase 4a (ADR-0033).
All ten pages are server components that consume the locked OpenAPI
contract via the existing `lib/api/fetchers.ts` pattern (typed
`openapi-fetch`, `next: { revalidate, tags }`, throw on missing data,
`notFound()` on 404). One new client component is introduced
(`SearchInput`) to drive debounced URL `?q=` updates on the brand and
perfumer list pages. Article markdown rendering composes
`react-markdown@9` + `remark-gfm@4` + `rehype-sanitize@6` with an
explicit allowlist schema. Header NAV promotion is gated by a
`lib/site-nav.ts` feature-flag map so partial-deploy states cannot
expose broken links. Mood tiles on home flip from
`/fragrances?accord=<slug>` to `/accords/<slug>`. The sitemap loop is
extended with five new resource enumerations, each capped by
`MAX_PAGES = 200`.

The design preserves Phase 4a primitives (`FragranceCard`,
`FragranceCardSkeleton`, `Pagination`, `Container`, `Glossary`,
`ImageFallback`) so taxonomy detail pages inherit the editorial
language without per-resource visual rework. Brand and perfumer detail
reuse the FragranceCard grid under an editorial header (D-DetailLayout);
accord detail is the only standalone curated page (D-AccordDetail) and
draws its blurb from `lib/accord-copy.ts`. The note tree is a recursive
shadcn `Accordion`, all top-level branches collapsed by default
(D-NoteTree).

## Architecture Decisions

### ADR-0041: Markdown stack composition

**Choice**: `react-markdown@9` + `remark-gfm@4` + `rehype-sanitize@6`
in this plugin order: parse → `remark-gfm` (remark plugin) → HAST
conversion → `rehype-sanitize` (rehype plugin, last). Renders inside
the `<ArticleBody>` server component on `/articles/[slug]`.

**Alternatives considered**:
- Plain text in `<p style="white-space: pre-wrap">` — too restrictive
  for editorial content (no headings, no lists, no code).
- `dangerouslySetInnerHTML` of trusted HTML — opens XSS surface
  (R5); contradicts the "harden against future content pipeline
  leaks" stance.
- `markdown-to-jsx` — smaller bundle (~12 KB) but lacks a first-party
  rehype-sanitize integration story and we'd be on our own for plugin
  composition. `react-markdown@9` is the de-facto remark/rehype
  ecosystem entry point and Context7-verified RSC-compatible.

**Rationale**: Markdown is the editorial convention for OSS perfumery
content; `react-markdown@9` is RSC-compatible and exposes
`remarkPlugins` / `rehypePlugins` props for composable safety. The
~30 KB gzipped bundle cost only loads on `/articles/[slug]`, not on
the critical-path home or `/fragrances` routes.

### ADR-0042: Sanitize schema literal

**Choice**: Start from `defaultSchema` in `rehype-sanitize` and
override:
- `tagNames`: explicitly EXCLUDE `script`, `iframe`, `object`,
  `embed`, `style`, `link`, `meta`. Allow defaults for headings
  (`h1`–`h6`), `p`, `em`, `strong`, `del`, `blockquote`, `code`,
  `pre`, `ul`, `ol`, `li`, `table`, `thead`, `tbody`, `tr`, `th`,
  `td`, `a`, `hr`, `br`.
- `attributes`: drop `style`, drop every `on*` event handler. For
  `a`: allow `href`, plus `rel` and `target` (which we will inject
  via the `components` prop). For `code`: allow `className` (used by
  language hints).
- `protocols.href`: `["http", "https", "mailto"]`.

The schema is exported as a named const from
`components/editorial/ArticleBody.tsx` so it is testable in isolation.

**Alternatives considered**:
- Pass `defaultSchema` unchanged — would still allow `style`
  attributes and pass through some attributes that the spec
  explicitly disallows (event handlers stripped already, but
  belt-and-suspenders).
- Build the schema from scratch — high maintenance cost; risks
  forgetting safe defaults like the protocol allowlist.

**Rationale**: Building on `defaultSchema` keeps the safe baseline
while making the deletions auditable. The schema literal is the
single source of XSS truth and pairs with a vitest negative test
asserting `<script>` and `<iframe>` are stripped.

### ADR-0043: Link rewrite via `components` prop

**Choice**: In `<ArticleBody>`, override the `a` mapping in the
`components` prop:
```tsx
a({ href, children, ...rest }) {
  const isExternal = href?.startsWith("http");
  return (
    <a
      href={href}
      {...(isExternal && { rel: "noopener noreferrer", target: "_blank" })}
      {...rest}
    >
      {children}
    </a>
  );
}
```

**Alternatives considered**: Apply `rel`/`target` via a custom
`rehype-` plugin that mutates HAST anchor nodes. More plugins to
maintain; the `components` prop is documented and recommended.

**Rationale**: `components` runs after sanitize so it never
contradicts the schema. External-only application avoids breaking
internal anchors.

### ADR-0044: NAV feature-flag map shape

**Choice**: New module `apps/web/lib/site-nav.ts` exports
```ts
export type NavItem = { href: string; label: string; ready: boolean };
export const NAV: readonly NavItem[] = [...];
```
All seven entries (Home, Fragrances, Notes, Accords, Brands,
Perfumers, Journal) live in the same array; `ready: true` for all
seven once 4b lands.

**Alternatives considered**:
- Flip placeholders to `<Link>` in one atomic commit — risks
  partial-deploy 404s if an earlier task lands first.
- Per-route feature flag in env — overkill for build-time data.

**Rationale**: The map is a 6-line module and removes an entire class
of "broken NAV in staging" risks. Header reads `NAV` and chooses
`<Link>` vs `<span aria-disabled>` per `ready`.

### ADR-0045: ISR posture per route family

**Choice**: Each new route ships `next: { revalidate, tags }` per
the table:

| Surface | revalidate (s) | tags |
|---|---|---|
| `/notes` (tree) | 3600 | `["notes:tree"]` |
| `/notes/[slug]` | 600 | `["note:<slug>"]` |
| `/accords` | 3600 | `["accords:list"]` |
| `/accords/[slug]` | 600 | `["accord:<slug>"]` |
| `/brands` | 3600 (no `q`) / 600 (with `q`) | `["brands:list"]` |
| `/brands/[slug]` | 1800 | `["brand:<slug>"]` |
| `/perfumers` | 3600 / 600 | `["perfumers:list"]` |
| `/perfumers/[slug]` | 1800 | `["perfumer:<slug>"]` |
| `/articles` | 600 | `["articles:list"]` |
| `/articles/[slug]` | 600 | `["article:<slug>"]` |

**Alternatives considered**: A single global revalidate (e.g., 600s)
across all surfaces — wastes invalidation churn on the tree, which
is structurally stable.

**Rationale**: Notes/accords change rarely; articles change daily
during seeding; brand/perfumer fragrance lists change with new
ingestions but not faster than every 30 min.

### ADR-0046: `notFound()` propagation

**Choice**: Every `getXBySlug` fetcher mirrors `getFragranceBySlug`:
```ts
if (response.status === 404) notFound();
if (error) throw new Error(...);
if (!data) notFound();
return data;
```
Detail pages call the fetcher and let the framework's `notFound()`
boundary render `app/(site)/not-found.tsx`.

**Alternatives considered**: Per-page custom 404 components — adds
five `not-found.tsx` files for no behavioral gain.

**Rationale**: 4a's pattern is proven; any drift would silently
return cached `null`.

### ADR-0047: Accord copy shape

**Choice**: New module `apps/web/lib/accord-copy.ts` exports
```ts
export const ACCORD_COPY: Record<string, { blurb: string }> = {
  chypre: { blurb: "..." },
  fougere: { blurb: "..." },
  oriental: { blurb: "..." },
  gourmand: { blurb: "..." },
  aquatic: { blurb: "..." },
  woody: { blurb: "..." },
};
```
Each blurb is one paragraph (~80–120 words) and references at least
one term that triggers Glossary popovers (sillage, drydown, accord,
etc.). Author the blurbs as JSX-compatible strings; the page
component runs `wrapGlossary(blurb, Glossary)` on render.

**Alternatives considered**:
- Hardcode JSX with `<Glossary>` directly in the file — couples copy
  to component imports; harder to lint as plain content.
- Move copy to a CMS — out of scope for 4b.

**Rationale**: Plain strings + `wrapGlossary` reuse keeps content
auditable and matches the FragranceDetail pattern.

### ADR-0048: SearchInput debounce strategy

**Choice**: New client component `components/site/SearchInput.tsx`:
- Controlled `<input>` value held in `useState`.
- On change: schedule `setTimeout(updateUrl, 300)`; clear prior
  timeout. `updateUrl` calls `router.replace(?q=value, { scroll: false })`
  inside `startTransition` so the input stays responsive while the RSC
  refetches.
- Reads initial value from `useSearchParams().get("q")`.

**Alternatives considered**:
- `useDebouncedCallback` from `use-debounce` — adds 1 KB dep for
  ~10 lines we already have via `setTimeout`.
- Live typeahead (`Command` palette) — out of scope (S1, U1).

**Rationale**: `useTransition` + `router.replace` keeps interaction
snappy and matches Next.js 16 App Router idioms (Context7-verified).

### ADR-0049: ESM transpile decision

**Choice**: Add `transpilePackages: ["react-markdown", "remark-gfm",
"rehype-sanitize"]` to `apps/web/next.config.ts`. Verify in apply
by running `next build` after the dep install; remove the entry only
if the build proves it unnecessary on Next.js 16.

**Alternatives considered**: Skip the entry and hope Next 16's
bundler handles ESM-only deps natively. Risk is build-time error
deep in dev that's hard to triage.

**Rationale**: Cheap insurance; Context7 confirms Next 16 supports
the option, and these three packages are documented ESM-only.

## Data Flow

```
Browser ── GET /accords/woody ──► RSC accords/[slug]/page.tsx
              │
              ├─► getAccordBySlug("woody")  ── fetch ──► /api/v1/accords/woody
              │      └─► notFound() on 404
              │      └─► returns AccordDetail { slug, name, fragrances }
              │
              ├─► ACCORD_COPY["woody"]?.blurb (lib/accord-copy.ts)
              │      └─► wrapGlossary(blurb, Glossary) ─► ReactNode
              │
              └─► Render: <Container>
                            <header>{name}</header>
                            <prose>{wrapped blurb}</prose>
                            <FragranceCard grid + Pagination>


Browser ── GET /brands?q=cha ──► RSC brands/page.tsx
              │
              ├─► SearchInput (client) reads ?q=cha, displays "cha"
              ├─► getAllBrands(q="cha", offset, limit) ──► /api/v1/brands?q=cha
              │      └─► returns ListEnvelope[BrandSummary]
              │
              └─► Render: <BrandCard list> + <Pagination>


Browser ── GET /articles/welcome ──► RSC articles/[slug]/page.tsx
              │
              ├─► getArticleBySlug("welcome") ──► /api/v1/articles/welcome
              │      └─► returns ArticleDetail { title, body, published_at, ... }
              │
              └─► <ArticleBody body={...}>
                     ├─► react-markdown(parse) → mdast
                     ├─► remark-gfm (mdast → gfm-mdast)
                     ├─► HAST conversion
                     ├─► rehype-sanitize(SCHEMA) → safe HAST
                     └─► components prop rewrites <a> with rel/target
```

## File Changes

### New files

| File | Purpose |
|---|---|
| `apps/web/app/(site)/notes/page.tsx` | Notes tree |
| `apps/web/app/(site)/notes/[slug]/page.tsx` | Note detail |
| `apps/web/app/(site)/notes/[slug]/loading.tsx` | Skeleton |
| `apps/web/app/(site)/accords/page.tsx` | Accords grid |
| `apps/web/app/(site)/accords/[slug]/page.tsx` | Accord detail |
| `apps/web/app/(site)/accords/[slug]/loading.tsx` | Skeleton |
| `apps/web/app/(site)/brands/page.tsx` | Brands list with q-search |
| `apps/web/app/(site)/brands/[slug]/page.tsx` | Brand detail |
| `apps/web/app/(site)/brands/[slug]/loading.tsx` | Skeleton |
| `apps/web/app/(site)/perfumers/page.tsx` | Perfumers list with q-search |
| `apps/web/app/(site)/perfumers/[slug]/page.tsx` | Perfumer detail |
| `apps/web/app/(site)/perfumers/[slug]/loading.tsx` | Skeleton |
| `apps/web/app/(site)/articles/page.tsx` | Articles list |
| `apps/web/app/(site)/articles/[slug]/page.tsx` | Article detail (markdown) |
| `apps/web/app/(site)/articles/[slug]/loading.tsx` | Skeleton |
| `apps/web/components/taxonomy/NoteTree.tsx` | Recursive Accordion |
| `apps/web/components/taxonomy/AccordCard.tsx` | List card |
| `apps/web/components/taxonomy/BrandCard.tsx` | List card |
| `apps/web/components/taxonomy/PerfumerCard.tsx` | List card |
| `apps/web/components/editorial/ArticleCard.tsx` | List card |
| `apps/web/components/editorial/ArticleBody.tsx` | Markdown renderer + sanitize schema |
| `apps/web/components/site/SearchInput.tsx` | Debounced URL ?q= input |
| `apps/web/lib/accord-copy.ts` | 6 hand-authored blurbs |
| `apps/web/lib/site-nav.ts` | NAV feature-flag map |

### Modified files

| File | Change |
|---|---|
| `apps/web/components/site/Header.tsx` | Drop inline NAV array; `import { NAV } from "@/lib/site-nav"`. Render `<Link>` if `ready`, `<span aria-disabled>` otherwise. |
| `apps/web/components/site/MobileMenu.tsx` | Same NAV import; consistent rendering. |
| `apps/web/app/(site)/page.tsx` | Mood tile hrefs flip to `/accords/<slug>`. Journal teaser activated: fetch `getAllArticles({ limit: 3 })`, render three ArticleCards or fallback if API empty. |
| `apps/web/app/sitemap.ts` | Append five resource loops (notes leaves + branches, accords, brands, perfumers, articles), each bounded by `MAX_PAGES = 200`. |
| `apps/web/lib/api/fetchers.ts` | Add 9 fetchers (see Interfaces). |
| `apps/web/next.config.ts` | Add `transpilePackages: ["react-markdown", "remark-gfm", "rehype-sanitize"]`. |
| `apps/web/package.json` + `pnpm-lock.yaml` | Add the three runtime deps. |

## Per-file content (paste-ready)

### `apps/web/lib/site-nav.ts`

```ts
export type NavItem = { href: string; label: string; ready: boolean };

// All NAV items the header may render. Each `ready` flag flips to
// true as routes land. Items with `ready: false` render as
// `<span aria-disabled>` carrying `title="Coming with phase 4c+"`.
export const NAV: readonly NavItem[] = [
  { href: "/", label: "Home", ready: true },
  { href: "/fragrances", label: "Fragrances", ready: true },
  { href: "/notes", label: "Notes", ready: true },
  { href: "/accords", label: "Accords", ready: true },
  { href: "/brands", label: "Brands", ready: true },
  { href: "/perfumers", label: "Perfumers", ready: true },
  { href: "/articles", label: "Journal", ready: true },
] as const;
```

### `apps/web/lib/accord-copy.ts`

```ts
// Hand-authored blurbs for the six canonical accord families. Each
// blurb is one paragraph (~80–120 words). At render time the
// accord detail page passes the blurb through wrapGlossary() so
// the marked terms (sillage, drydown, accord, etc.) become
// <Glossary> popovers.
export type AccordCopy = { blurb: string };

export const ACCORD_COPY: Record<string, AccordCopy> = {
  woody: {
    blurb:
      "Woody perfumes draw on the dry, resinous heart of a forest: " +
      "cedar, sandalwood, vetiver, oud. The accord can lean smoky and " +
      "smouldering or cool and pencil-shaving sharp; in either reading " +
      "it leaves a long sillage and a slow drydown that anchors the " +
      "rest of the composition. Many traditional masculines are " +
      "essentially woody fougeres in disguise. The modern wave " +
      "lightens the family with iso E super and ambroxan.",
  },
  fougere: {
    blurb:
      "Fougère — French for 'fern' — names a 19th-century accord built " +
      "on lavender, oakmoss and coumarin. Imagine wet stones, freshly " +
      "split wood, the cool green of crushed bracken. It is the " +
      "backbone of barbershop scents and gentleman's colognes; the " +
      "drydown is herbal and dignified rather than sweet. Modern " +
      "fougeres temper the oakmoss with iso E super or amber to " +
      "satisfy IFRA limits while preserving the family's leafy spine.",
  },
  oriental: {
    blurb:
      "Oriental — increasingly relabelled 'amber' — is the warm, " +
      "resinous family: vanilla, labdanum, benzoin, sweet incense, " +
      "powdered spices. It blooms slowly on the skin and projects a " +
      "long, syrupy sillage. Where chypre prizes restraint, the " +
      "oriental accord is unapologetically generous; the drydown is " +
      "honeyed and cinnamon-laced rather than dry. Houses now prefer " +
      "the term 'amber' to step away from the orientalising " +
      "shorthand of an earlier century while keeping the same " +
      "olfactive shape.",
  },
  gourmand: {
    blurb:
      "Gourmand fragrances borrow from the kitchen: vanilla, caramel, " +
      "cocoa, coffee, praline. Calone-era aquatics gave way in the " +
      "1990s to a confectionary turn — Angel by Mugler is the " +
      "lighthouse — and the family has since divided into honeyed " +
      "everyday wears and dense, almost dessert-like extraits. The " +
      "drydown can read as warm milk or as burnt sugar depending on " +
      "the base accord supporting it; sillage is enthusiastic. Pair " +
      "with a cool top to stop it tipping into syrup.",
  },
  aquatic: {
    blurb:
      "Aquatic fragrances trade in the language of clean ocean air: " +
      "calone, sea salt, melon-water accords, ozonic notes. The " +
      "family arrived with the 1988 release of Cool Water and ruled " +
      "the 1990s. Sillage is bright and short; the drydown is more " +
      "musk than mineral, so the accord often pairs with a woody " +
      "base for staying power. Read closely, an aquatic is rarely " +
      "literal water — it is the cool feeling of a sea breeze " +
      "rendered in synthetic molecules.",
  },
  chypre: {
    blurb:
      "Chypre — named for Coty's 1917 perfume of Cyprus — is the " +
      "great refined accord: bergamot at the top, a heart of rose " +
      "or jasmine, oakmoss, labdanum, and patchouli at the base. The " +
      "structure is bitter where oriental is sweet and cool where " +
      "fougere is herbal. IFRA restrictions on oakmoss have forced " +
      "modern reformulations, but the family's signature drydown — " +
      "dry leaves, mineral earth — remains the most distinctive in " +
      "perfumery. The sillage is moderate; chypre prizes restraint.",
  },
};
```

### `apps/web/components/site/SearchInput.tsx`

```tsx
"use client";

import { useEffect, useRef, useState, useTransition } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Input } from "@/components/ui/input";

const DEBOUNCE_MS = 300;

export function SearchInput({
  placeholder = "Search…",
  paramKey = "q",
}: {
  placeholder?: string;
  paramKey?: string;
}) {
  const pathname = usePathname();
  const router = useRouter();
  const sp = useSearchParams();
  const [value, setValue] = useState(() => sp.get(paramKey) ?? "");
  const [, startTransition] = useTransition();
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => {
    if (timer.current) clearTimeout(timer.current);
  }, []);

  function onChange(next: string) {
    setValue(next);
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      const params = new URLSearchParams(sp.toString());
      if (next.length === 0) params.delete(paramKey);
      else params.set(paramKey, next);
      // Reset offset whenever the search term changes.
      params.delete("offset");
      const qs = params.toString();
      startTransition(() => {
        router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
      });
    }, DEBOUNCE_MS);
  }

  return (
    <Input
      type="search"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      aria-label={placeholder}
      className="w-full max-w-sm font-mono text-xs"
    />
  );
}
```

### `apps/web/components/taxonomy/NoteTree.tsx`

```tsx
import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import type { components } from "@/lib/api/types";

type NoteTreeNode = components["schemas"]["NoteTreeNode"];

export function NoteTree({ nodes }: { nodes: NoteTreeNode[] }) {
  if (nodes.length === 0) {
    return (
      <p className="text-muted-foreground">No notes available.</p>
    );
  }
  // All top-level branches collapsed by default.
  return (
    <Accordion type="multiple" className="border-l border-border pl-4">
      {nodes.map((node) => (
        <NoteBranch key={node.slug} node={node} />
      ))}
    </Accordion>
  );
}

function NoteBranch({ node }: { node: NoteTreeNode }) {
  const hasChildren = node.children && node.children.length > 0;
  if (!hasChildren) {
    return (
      <div className="py-1">
        <Link
          href={`/notes/${node.slug}`}
          className="text-sm text-foreground hover:text-accent"
        >
          {node.name}
        </Link>
      </div>
    );
  }
  return (
    <AccordionItem value={node.slug} className="border-none">
      <AccordionTrigger className="font-display text-base hover:no-underline">
        <span className="flex items-center gap-2">
          <Link
            href={`/notes/${node.slug}`}
            className="hover:text-accent"
            onClick={(e) => e.stopPropagation()}
          >
            {node.name}
          </Link>
          <span className="font-mono text-[0.6rem] uppercase tracking-wider text-muted-foreground">
            {node.children.length}
          </span>
        </span>
      </AccordionTrigger>
      <AccordionContent>
        <Accordion type="multiple" className="border-l border-border pl-4">
          {node.children.map((child) => (
            <NoteBranch key={child.slug} node={child} />
          ))}
        </Accordion>
      </AccordionContent>
    </AccordionItem>
  );
}
```

### `apps/web/components/taxonomy/AccordCard.tsx`

```tsx
import Link from "next/link";

export function AccordCard({
  slug,
  name,
}: {
  slug: string;
  name: string;
}) {
  return (
    <Link
      href={`/accords/${slug}`}
      className="group flex aspect-[5/3] flex-col justify-between rounded-md border border-border bg-card p-5 transition-colors hover:bg-accent hover:text-accent-foreground"
    >
      <span className="font-mono text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground group-hover:text-accent-foreground/70">
        Accord
      </span>
      <span className="font-display text-2xl">{name}</span>
    </Link>
  );
}
```

### `apps/web/components/taxonomy/BrandCard.tsx`

```tsx
import Link from "next/link";

export function BrandCard({ slug, name }: { slug: string; name: string }) {
  return (
    <Link
      href={`/brands/${slug}`}
      className="flex items-baseline justify-between border-b border-border py-4 transition-colors hover:text-accent"
    >
      <span className="font-display text-xl">{name}</span>
      <span aria-hidden className="font-mono text-xs text-muted-foreground">
        →
      </span>
    </Link>
  );
}
```

### `apps/web/components/taxonomy/PerfumerCard.tsx`

```tsx
import Link from "next/link";

export function PerfumerCard({ slug, name }: { slug: string; name: string }) {
  return (
    <Link
      href={`/perfumers/${slug}`}
      className="flex items-baseline justify-between border-b border-border py-4 transition-colors hover:text-accent"
    >
      <span className="font-display text-xl">{name}</span>
      <span aria-hidden className="font-mono text-xs text-muted-foreground">
        →
      </span>
    </Link>
  );
}
```

### `apps/web/components/editorial/ArticleCard.tsx`

```tsx
import Link from "next/link";

export function ArticleCard({
  slug,
  title,
  publishedAt,
}: {
  slug: string;
  title: string;
  publishedAt: string | null;
}) {
  const dateLabel = publishedAt
    ? new Date(publishedAt).toLocaleDateString(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Unpublished";
  return (
    <Link
      href={`/articles/${slug}`}
      className="group block border-b border-border py-8 transition-colors hover:bg-secondary/40"
    >
      <p className="font-mono text-[0.6rem] uppercase tracking-[0.22em] text-muted-foreground">
        {dateLabel}
      </p>
      <h3 className="mt-3 font-display text-2xl group-hover:text-accent md:text-3xl">
        {title}
      </h3>
    </Link>
  );
}
```

### `apps/web/components/editorial/ArticleBody.tsx`

```tsx
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";
import type { Schema } from "hast-util-sanitize";

// Explicit allowlist. Built from defaultSchema then narrowed.
// Drops <script>, <iframe>, <object>, <embed>, <style>, <link>,
// <meta>, every on* event handler, and the `style` attribute.
export const SANITIZE_SCHEMA: Schema = {
  ...defaultSchema,
  tagNames: (defaultSchema.tagNames ?? []).filter(
    (t) => !["script", "iframe", "object", "embed", "style", "link", "meta"].includes(t),
  ),
  attributes: {
    ...defaultSchema.attributes,
    "*": (defaultSchema.attributes?.["*"] ?? []).filter((attr) => {
      const name = Array.isArray(attr) ? attr[0] : attr;
      return name !== "style" && !String(name).startsWith("on");
    }),
    a: ["href", "title", "rel", "target"],
    code: ["className"],
  },
  protocols: {
    ...defaultSchema.protocols,
    href: ["http", "https", "mailto"],
  },
};

function ExternalAnchor({
  href,
  children,
  ...rest
}: React.AnchorHTMLAttributes<HTMLAnchorElement>) {
  const isExternal = typeof href === "string" && /^https?:\/\//.test(href);
  return (
    <a
      href={href}
      {...(isExternal && { rel: "noopener noreferrer", target: "_blank" })}
      {...rest}
    >
      {children}
    </a>
  );
}

export function ArticleBody({ body }: { body: string | null }) {
  if (!body) {
    return (
      <p className="text-muted-foreground">No body content available.</p>
    );
  }
  return (
    <div className="prose prose-stone max-w-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, SANITIZE_SCHEMA]]}
        components={{ a: ExternalAnchor }}
      >
        {body}
      </ReactMarkdown>
    </div>
  );
}
```

### `apps/web/lib/api/fetchers.ts` extensions (paste-ready)

```ts
import type { components } from "./types";

export type NoteTreeNode = components["schemas"]["NoteTreeNode"];
export type NoteDetail = components["schemas"]["NoteDetail"];
export type AccordDetail = components["schemas"]["AccordDetail"];
export type BrandDetail = components["schemas"]["BrandDetail"];
export type PerfumerDetail = components["schemas"]["PerfumerDetail"];
export type PerfumerSummary = components["schemas"]["PerfumerSummary"];
export type ArticleSummary = components["schemas"]["ArticleSummary"];
export type ArticleDetail = components["schemas"]["ArticleDetail"];

export interface PaginatedListParams {
  limit?: number;
  offset?: number;
}

export interface QSearchParams extends PaginatedListParams {
  q?: string;
}

/** GET /api/v1/notes — full recursive tree. */
export async function getAllNotes(): Promise<NoteTreeNode[]> {
  const { data, response } = await apiClient.GET("/api/v1/notes", {
    next: { revalidate: 3600, tags: ["notes:tree"] },
  });
  if (!response.ok) {
    throw new Error(`getAllNotes failed (${response.status})`);
  }
  return data?.data ?? [];
}

/** GET /api/v1/notes/{slug} — detail; calls notFound() on 404. */
export async function getNoteBySlug(
  slug: string,
  params: PaginatedListParams = {},
) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/notes/{slug}",
    {
      params: { path: { slug }, query: params },
      next: { revalidate: 600, tags: [`note:${slug}`] },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getNoteBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}

/** GET /api/v1/accords/{slug}. */
export async function getAccordBySlug(
  slug: string,
  params: PaginatedListParams = {},
) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/accords/{slug}",
    {
      params: { path: { slug }, query: params },
      next: { revalidate: 600, tags: [`accord:${slug}`] },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getAccordBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}

/** GET /api/v1/brands — supports limit/offset/q. */
export async function getBrands(params: QSearchParams = {}) {
  const hasQ = typeof params.q === "string" && params.q.length > 0;
  const { data, error, response } = await apiClient.GET("/api/v1/brands", {
    params: { query: params },
    next: {
      revalidate: hasQ ? 600 : 3600,
      tags: ["brands:list"],
    },
  });
  if (error) {
    throw new Error(
      `getBrands failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) {
    throw new Error("getBrands returned no data");
  }
  return data;
}

/** GET /api/v1/brands/{slug}. */
export async function getBrandBySlug(
  slug: string,
  params: PaginatedListParams = {},
) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/brands/{slug}",
    {
      params: { path: { slug }, query: params },
      next: { revalidate: 1800, tags: [`brand:${slug}`] },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getBrandBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}

/** GET /api/v1/perfumers — supports limit/offset/q. */
export async function getPerfumers(params: QSearchParams = {}) {
  const hasQ = typeof params.q === "string" && params.q.length > 0;
  const { data, error, response } = await apiClient.GET("/api/v1/perfumers", {
    params: { query: params },
    next: {
      revalidate: hasQ ? 600 : 3600,
      tags: ["perfumers:list"],
    },
  });
  if (error) {
    throw new Error(
      `getPerfumers failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) {
    throw new Error("getPerfumers returned no data");
  }
  return data;
}

/** GET /api/v1/perfumers/{slug}. */
export async function getPerfumerBySlug(
  slug: string,
  params: PaginatedListParams = {},
) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/perfumers/{slug}",
    {
      params: { path: { slug }, query: params },
      next: { revalidate: 1800, tags: [`perfumer:${slug}`] },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getPerfumerBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}

/** GET /api/v1/articles — paginated list. */
export async function getAllArticles(params: PaginatedListParams = {}) {
  const { data, error, response } = await apiClient.GET("/api/v1/articles", {
    params: { query: params },
    next: { revalidate: 600, tags: ["articles:list"] },
  });
  if (error) {
    throw new Error(
      `getAllArticles failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) {
    throw new Error("getAllArticles returned no data");
  }
  return data;
}

/** GET /api/v1/articles/{slug}. */
export async function getArticleBySlug(slug: string) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/articles/{slug}",
    {
      params: { path: { slug } },
      next: { revalidate: 600, tags: [`article:${slug}`] },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getArticleBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}
```

## Page templates (paste-ready, one per route)

Each page below assumes:
- `searchParams: Promise<Record<string, string | string[] | undefined>>`
  per Next 16 App Router.
- `params: Promise<{ slug: string }>` for dynamic routes.
- `generateMetadata` returns `{ title, description }`.

### `/notes/page.tsx`

```tsx
import { Container } from "@/components/site/Container";
import { NoteTree } from "@/components/taxonomy/NoteTree";
import { getAllNotes } from "@/lib/api/fetchers";

export const metadata = {
  title: "Notes — Fragwise",
  description:
    "The full perfumery taxonomy of olfactive notes — from citrus to oud, browsable as a tree.",
};

export default async function NotesPage() {
  const tree = await getAllNotes();
  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-10 font-display text-4xl">Notes</h1>
      <NoteTree nodes={tree} />
    </Container>
  );
}
```

### `/notes/[slug]/page.tsx`

```tsx
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
          <Link href={`/notes/${note.parent.slug}`} className="hover:text-accent">
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
```

### `/accords/page.tsx`

```tsx
import { Container } from "@/components/site/Container";
import { AccordCard } from "@/components/taxonomy/AccordCard";
import { getAllAccords } from "@/lib/api/fetchers";

export const metadata = {
  title: "Accords — Fragwise",
  description:
    "Browse the canonical accord families: woody, fougère, oriental, gourmand, aquatic, chypre, and more.",
};

export default async function AccordsPage() {
  const accords = await getAllAccords();
  return (
    <Container className="py-12 md:py-20">
      <h1 className="mb-10 font-display text-4xl">Accords</h1>
      <div className="grid gap-3 sm:grid-cols-2 md:grid-cols-3">
        {accords.map((a) => (
          <AccordCard key={a.slug} slug={a.slug} name={a.name} />
        ))}
      </div>
    </Container>
  );
}
```

### `/accords/[slug]/page.tsx`

```tsx
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
```

### `/brands/page.tsx`

```tsx
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
  } catch {
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
```

### `/brands/[slug]/page.tsx`

```tsx
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
```

### `/perfumers/page.tsx` and `/perfumers/[slug]/page.tsx`

Mirror the brands pages with `getPerfumers` / `getPerfumerBySlug` and
`PerfumerCard`. Header copy uses "Perfumer" / "Perfumers".

### `/articles/page.tsx`

```tsx
import { Container } from "@/components/site/Container";
import { ArticleCard } from "@/components/editorial/ArticleCard";
import { Pagination } from "@/components/catalog/Pagination";
import { getAllArticles } from "@/lib/api/fetchers";

const LIMIT = 12;

export const metadata = {
  title: "Journal — Fragwise",
  description:
    "Long-form essays on perfume craft, history, and method.",
};

export default async function ArticlesPage(props: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const sp = await props.searchParams;
  const offsetRaw = typeof sp.offset === "string" ? Number(sp.offset) : 0;
  const offset = Number.isFinite(offsetRaw) ? offsetRaw : 0;
  const list = await getAllArticles({ limit: LIMIT, offset });

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
```

### `/articles/[slug]/page.tsx`

```tsx
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
```

### `loading.tsx` segments

Each detail directory ships a `loading.tsx` rendering a centered
skeleton block. Pattern:

```tsx
import { Container } from "@/components/site/Container";
import { Skeleton } from "@/components/ui/skeleton";

export default function Loading() {
  return (
    <Container className="py-12 md:py-20">
      <Skeleton className="h-4 w-24" />
      <Skeleton className="mt-4 h-12 w-3/4" />
      <Skeleton className="mt-8 h-32 w-full" />
    </Container>
  );
}
```

## Header + MobileMenu modifications

```diff
- const NAV: { href: string; label: string; placeholder?: boolean }[] = [
-   { href: "/", label: "Home" },
-   { href: "/fragrances", label: "Fragrances" },
-   { href: "/notes", label: "Notes", placeholder: true },
-   { href: "/accords", label: "Accords", placeholder: true },
-   { href: "/brands", label: "Brands", placeholder: true },
-   { href: "/perfumers", label: "Perfumers", placeholder: true },
-   { href: "/articles", label: "Journal", placeholder: true },
- ];
+ import { NAV } from "@/lib/site-nav";
```

The render branch becomes `item.ready ? <Link> : <span aria-disabled>`
and the `<span>` carries `title="Coming with phase 4c+"`. The
MobileMenu signature changes from
`{ nav: { href, label, placeholder?: boolean }[] }` to
`{ nav: readonly NavItem[] }` — Header passes `NAV` directly.

The Header should also compute `aria-current="page"` for the matching
ready item by reading the pathname (`headers().get("x-pathname")` is
not available without middleware; the simplest path is converting
Header to import `usePathname` via a small client wrapper, OR passing
the pathname through `<HeaderClient>`). To preserve Header as a
server component (Phase 4a R3 fix) we apply `aria-current` inside a
small `NavLink` client subcomponent that reads `usePathname()`.

## Home page modifications

```diff
- const MOODS = [
-   { slug: "fresh", label: "Fresh & bright" },
-   ...
- ];
+ const MOODS = [
+   { slug: "fresh", label: "Fresh & bright" },
+   { slug: "woody", label: "Woody & smoky" },
+   { slug: "floral", label: "Floral & soft" },
+   { slug: "gourmand", label: "Sweet & comforting" },
+   { slug: "oriental", label: "Warm & spiced" },
+   { slug: "aquatic", label: "Aquatic & cool" },
+ ];
...
- href={`/fragrances?accord=${m.slug}`}
+ href={`/accords/${m.slug}`}
```

Journal teaser activation:

```diff
- {/* Journal teaser placeholder for 4b */}
- <section className="py-20">
-   <Container>
-     <div className="rounded-lg border border-dashed border-border bg-secondary/30 p-10">
-       <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">From the journal</p>
-       <p className="mt-4 font-display text-2xl">
-         Long-form essays on craft, history, and method. <span className="text-muted-foreground">Coming with 4b.</span>
-       </p>
-     </div>
-   </Container>
- </section>
+ {/* Journal teaser — three most-recent articles */}
+ <section className="py-20">
+   <Container>
+     <div className="mb-8 flex items-end justify-between">
+       <h2 className="font-display text-3xl">From the journal</h2>
+       <Link href="/articles" className="font-mono text-xs uppercase tracking-wider text-muted-foreground hover:text-accent">
+         All essays →
+       </Link>
+     </div>
+     <div className="grid gap-6 md:grid-cols-3">
+       {recentArticles.map((a) => (
+         <ArticleCard key={a.slug} slug={a.slug} title={a.title} publishedAt={a.published_at ?? null} />
+       ))}
+     </div>
+   </Container>
+ </section>
```

The `recentArticles` value is fetched in the same try/catch shape as
`featured`:

```ts
let recentArticles: ArticleSummary[] = [];
try {
  const list = await getAllArticles({ limit: 3, offset: 0 });
  recentArticles = list.data;
} catch (err) {
  console.warn("[home] getAllArticles failed — empty journal teaser.", err);
}
```

## Sitemap update

```diff
+ import {
+   getAllNotes,
+   getAllAccords,
+   getBrands,
+   getPerfumers,
+   getAllArticles,
+ } from "@/lib/api/fetchers";

  ...existing fragrance loop...

+ const accords = await getAllAccords().catch(() => []);
+ for (const a of accords.slice(0, MAX_PAGES)) {
+   urls.push({ url: `${SITE}/accords/${a.slug}`, lastModified, changeFrequency: "monthly", priority: 0.6 });
+ }
+
+ // Walk the note tree (branches + leaves), capped at MAX_PAGES.
+ try {
+   const tree = await getAllNotes();
+   const flat: { slug: string }[] = [];
+   const walk = (nodes: typeof tree) => {
+     for (const n of nodes) {
+       if (flat.length >= MAX_PAGES) return;
+       flat.push({ slug: n.slug });
+       if (n.children?.length) walk(n.children);
+     }
+   };
+   walk(tree);
+   for (const n of flat) {
+     urls.push({ url: `${SITE}/notes/${n.slug}`, lastModified, changeFrequency: "monthly", priority: 0.5 });
+   }
+ } catch (err) {
+   console.warn("[sitemap] getAllNotes failed.", err);
+ }
+
+ // Brands, perfumers, articles each follow the same offset-loop pattern
+ // as the existing fragrance loop, capped by MAX_PAGES.
+ for (const [resource, fetcher] of [["brands", getBrands], ["perfumers", getPerfumers], ["articles", getAllArticles]] as const) {
+   let off = 0;
+   for (let i = 0; i < MAX_PAGES; i += 1) {
+     try {
+       const list = await fetcher({ limit: PAGE, offset: off });
+       if (list.data.length === 0) break;
+       for (const item of list.data) {
+         urls.push({ url: `${SITE}/${resource}/${item.slug}`, lastModified, changeFrequency: "monthly", priority: 0.6 });
+       }
+       if (!list.pagination.has_next) break;
+       off += PAGE;
+     } catch (err) {
+       console.warn(`[sitemap] ${resource} fetcher failed.`, err);
+       break;
+     }
+   }
+ }
```

(The existing return block becomes `return urls`; refactor the static
home/fragrances entries above into the same `urls` array.)

## `next.config.ts` update

```diff
  const nextConfig: NextConfig = {
    reactStrictMode: true,
+   transpilePackages: ["react-markdown", "remark-gfm", "rehype-sanitize"],
    images: {
      remotePatterns: [
        ...
      ],
    },
  };
```

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit (vitest) | `NoteTree` renders all top-level branches collapsed; clicking a branch expands children | `@testing-library/react` render with a 3-level mock tree; assert children hidden, click trigger, assert visible |
| Unit (vitest) | `AccordCard` / `BrandCard` / `PerfumerCard` / `ArticleCard` render text and href | Snapshot href + label |
| Unit (vitest) | `ArticleBody` renders headings + tables + code | Pass GFM markdown literal; assert `<h1>`, `<table>`, `<pre><code>` |
| Unit (vitest) | `ArticleBody` strips `<script>`, `<iframe>`, `on*` | Pass malicious markdown; assert resulting HTML contains none of those substrings (use `container.innerHTML`) |
| Unit (vitest) | `ArticleBody` rewrites external links | Pass `[link](https://example.com)`; assert `rel="noopener noreferrer"` and `target="_blank"` |
| Unit (vitest) | `SearchInput` debounces URL update | Mock `useRouter`/`useSearchParams`; type quickly; assert `replace` called once after 300ms |
| Unit (vitest) | NAV map: ready → Link, not-ready → span | Snapshot Header render under both NAV configurations |
| Integration (vitest) | Each detail fetcher calls `notFound()` on 404 | Mock apiClient response 404; assert `notFound` invocation throws Next's NEXT_NOT_FOUND error |
| E2E (Playwright, manual smoke) | Each new route returns 200 with expected heading | Visit `/notes`, `/notes/<seed>`, `/accords`, `/accords/woody`, `/brands`, `/brands/<seed>`, `/perfumers`, `/perfumers/<seed>`, `/articles`, `/articles/<seed>` |
| E2E (Playwright) | Brand list filters by `?q=` after typing | Type "cha" into SearchInput, await URL `?q=cha`, assert filtered list count differs |
| Bundle | `/articles/[slug]` chunk respects `.size-limit.json` | Size-limit CI gate |

## Migration / Rollout

No data migrations. Rollout per the proposal's plan:

1. Land deps in `package.json` + `pnpm-lock.yaml`.
2. Add fetchers, components, lib files.
3. Land all 10 routes in dependency order (notes → accords → brands → perfumers → articles).
4. Replace Header NAV with `import { NAV }` once ALL ready flags are true.
5. Update home page mood tile hrefs and journal teaser.
6. Extend sitemap.
7. Verify `.size-limit.json` budget on `/articles/[slug]`.
8. Tag release; ISR ages out within revalidate windows post-deploy.

## Cross-cutting concerns

- **Bundle**: ~30 KB gzipped on `/articles/[slug]` from the markdown
  stack. Verify the budget gate. Mitigation if breached: dynamic
  import `<ArticleBody>` via `next/dynamic`, or drop `remark-gfm` if
  no seeded article uses tables/strikethrough.
- **a11y**: `NoteTree` inherits shadcn `Accordion` keyboard behavior
  (Tab into trigger, Space/Enter to toggle); preserve via Radix
  defaults. `<ArticleBody>` keeps heading hierarchy; the wrapper page
  already renders `<h1>` so markdown should not produce a second
  `<h1>` — leave it to author discipline (sanitize allows `h1`).
  External anchors include `rel="noopener noreferrer"`.
- **Glossary scope**: `<ArticleBody>` does NOT pass markdown through
  `wrapGlossary`. Only `lib/accord-copy.ts` blurbs are wrapped.
- **Loading states**: Each detail directory ships `loading.tsx` per
  the skeleton pattern; list pages reuse `FragranceCardSkeleton` for
  the grid where applicable, otherwise a generic skeleton block.
- **Error boundaries**: Existing `app/(site)/error.tsx` catches
  thrown fetcher errors at the segment boundary.
- **Cache invalidation**: Tags follow `<resource>:list` /
  `<resource>:<slug>` so Phase 5+ can issue targeted revalidations.

## Open Questions

- [ ] None blocking. The seed dataset MUST contain at least one
  article with a non-null body for Playwright smoke; if not,
  Phase 4b adds a fixture article in `data/seed/` (out-of-scope
  follow-up).

---

## Return Envelope

**Status**: success

**Executive summary**: Design ratifies the 14 exploration decisions
into 9 ADRs (0041–0049) and produces paste-ready content for 24
new files (10 routes + 5 loading.tsx + 7 components + 2 lib files)
plus diffs for 6 modified files (Header, MobileMenu, home, sitemap,
fetchers, next.config.ts). Markdown stack composes
`react-markdown@9` + `remark-gfm@4` + `rehype-sanitize@6` with an
explicit allowlist schema dropping `<script>`, `<iframe>`, every
`on*` handler, and `style`. NAV feature-flag map at
`lib/site-nav.ts` decouples Header/MobileMenu from per-route
deploy ordering. Brand and perfumer search uses a 300ms-debounced
`SearchInput` driving URL `?q=` via `useTransition` +
`router.replace`. ISR posture per route family captured in ADR-0045
(notes/accords 3600s; articles 600s; brand/perfumer detail 1800s).
Sitemap extended with 5 capped loops. `transpilePackages` added to
`next.config.ts` per Context7-verified Next.js 16 guidance. Test
surface covers 7 vitest suites (component rendering, sanitize
negative, debounce) plus Playwright smoke for each new route and
size-limit budget verification.

**Artifacts**:
`openspec/changes/phase-4b-web-taxonomy-pages/design.md`

**Next**: `sdd-tasks: phase-4b-web-taxonomy-pages` (per orchestration
retrospective: judgment-day NOT recommended; P4b is a straightforward
extension of P4a's design system over an existing API. Apply discipline
catches the relevant implementation issues).

**Risks**:
- R1 markdown bundle bloat (~30 KB) — verify size-limit gate during apply.
- R2 thin brand/perfumer pages — mitigated by editorial header hierarchy in this design.
- R5 article XSS — mitigated by explicit ADR-0042 schema + negative test.
- R11 ESM transpile — mitigated by ADR-0049 (transpilePackages entry).
- All other risks from exploration are addressed by adopted decisions.

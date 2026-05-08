import type { MetadataRoute } from "next";
import {
  getFragrances,
  getAllNotes,
  getAllAccords,
  getBrands,
  getPerfumers,
  getAllArticles,
  type NoteTreeNode,
} from "@/lib/api/fetchers";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app";

// Phase 4b: each new resource enumeration is bounded by `MAX_PAGES`
// (200) so a runaway dataset cannot bloat the sitemap unboundedly.
// Each loop is wrapped in try/catch with `console.warn` so a transient
// API outage during `next build` produces a partial sitemap rather
// than failing the build outright.
const MAX_PAGES = 200;
const PAGE = 100;

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const lastModified = new Date();
  const urls: MetadataRoute.Sitemap = [
    {
      url: `${SITE}/`,
      lastModified,
      changeFrequency: "weekly",
      priority: 1,
    },
    {
      url: `${SITE}/fragrances`,
      lastModified,
      changeFrequency: "daily",
      priority: 0.9,
    },
    {
      url: `${SITE}/notes`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE}/accords`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE}/brands`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE}/perfumers`,
      lastModified,
      changeFrequency: "weekly",
      priority: 0.8,
    },
    {
      url: `${SITE}/articles`,
      lastModified,
      changeFrequency: "daily",
      priority: 0.8,
    },
  ];

  // Fragrance slugs (existing P4a loop, retained verbatim).
  let offset = 0;
  for (let i = 0; i < MAX_PAGES; i += 1) {
    try {
      const list = await getFragrances({ limit: PAGE, offset });
      if (list.data.length === 0) break;
      for (const f of list.data) {
        urls.push({
          url: `${SITE}/fragrances/${f.slug}`,
          lastModified,
          changeFrequency: "monthly",
          priority: 0.7,
        });
      }
      if (!list.pagination.has_next) break;
      offset += PAGE;
    } catch (err) {
      console.warn(
        `[sitemap] getFragrances failed at offset=${offset} — emitting partial sitemap.`,
        err,
      );
      break;
    }
  }

  // Phase 4b additions — accords (no pagination; small finite set).
  try {
    const accords = await getAllAccords();
    for (const a of accords.slice(0, MAX_PAGES)) {
      urls.push({
        url: `${SITE}/accords/${a.slug}`,
        lastModified,
        changeFrequency: "monthly",
        priority: 0.6,
      });
    }
  } catch (err) {
    console.warn("[sitemap] getAllAccords failed.", err);
  }

  // Notes — recursive walk over the tree, bounded by MAX_PAGES.
  try {
    const tree = await getAllNotes();
    const flat: { slug: string }[] = [];
    const walk = (nodes: NoteTreeNode[]) => {
      for (const n of nodes) {
        if (flat.length >= MAX_PAGES) return;
        flat.push({ slug: n.slug });
        if (n.children?.length) walk(n.children);
      }
    };
    walk(tree);
    for (const n of flat) {
      urls.push({
        url: `${SITE}/notes/${n.slug}`,
        lastModified,
        changeFrequency: "monthly",
        priority: 0.5,
      });
    }
  } catch (err) {
    console.warn("[sitemap] getAllNotes failed.", err);
  }

  // Brands, perfumers, articles — same offset-loop pattern as
  // fragrances. Each tuple is [resource segment, fetcher].
  const paginatedResources: Array<
    [string, (params: { limit: number; offset: number }) => Promise<{
      data: { slug: string }[];
      pagination: { has_next: boolean };
    }>]
  > = [
    ["brands", getBrands],
    ["perfumers", getPerfumers],
    ["articles", getAllArticles],
  ];
  for (const [resource, fetcher] of paginatedResources) {
    let off = 0;
    let emitted = 0;
    for (let i = 0; i < MAX_PAGES; i += 1) {
      try {
        const list = await fetcher({ limit: PAGE, offset: off });
        if (list.data.length === 0) break;
        for (const item of list.data) {
          if (emitted >= MAX_PAGES) break;
          urls.push({
            url: `${SITE}/${resource}/${item.slug}`,
            lastModified,
            changeFrequency: "monthly",
            priority: 0.6,
          });
          emitted += 1;
        }
        if (emitted >= MAX_PAGES) break;
        if (!list.pagination.has_next) break;
        off += PAGE;
      } catch (err) {
        console.warn(`[sitemap] ${resource} fetcher failed.`, err);
        break;
      }
    }
  }

  return urls;
}

export const revalidate = 3600;

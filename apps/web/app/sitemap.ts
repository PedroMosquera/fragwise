import type { MetadataRoute } from "next";
import { getFragrances } from "@/lib/api/fetchers";

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "https://fragwise.app";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  // Page through results: API caps `limit` at 100 (see openapi.json
  // schema for /api/v1/fragrances; `next build` would 422 if we sent
  // a larger value). FragranceListItem does NOT carry an `updated_at`
  // field today, so we use the build-time `Date.now()` as
  // `lastModified` for every fragrance entry. When P1+ adds an
  // `updated_at` (or equivalent) column, swap in `f.updated_at`.
  const all: Array<{ slug: string }> = [];
  let offset = 0;
  const PAGE = 100;
  // R3 fix: hard cap iterations to prevent an infinite build hang if
  // the API ever lies about pagination.has_next or returns the same
  // offset repeatedly. 200 iterations × 100 = 20k slugs is far above
  // the OSS catalog ceiling.
  const MAX_PAGES = 200;
  for (let i = 0; i < MAX_PAGES; i += 1) {
    try {
      const list = await getFragrances({ limit: PAGE, offset });
      if (list.data.length === 0) break; // empty page guard
      all.push(...list.data.map((f) => ({ slug: f.slug })));
      if (!list.pagination.has_next) break;
      offset += PAGE;
    } catch (err) {
      // Build-time graceful degradation: if the API is unreachable
      // at `next build` (e.g. CI without a live API, or a transient
      // outage), still emit a static sitemap with home + list URLs
      // rather than failing the build. ISR will refresh the sitemap
      // (revalidate: 3600) once the API is back online.
      console.warn(
        `[sitemap] getFragrances failed at offset=${offset} — emitting partial sitemap.`,
        err,
      );
      break;
    }
  }

  const lastModified = new Date();

  return [
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
    ...all.map(({ slug }) => ({
      url: `${SITE}/fragrances/${slug}`,
      lastModified,
      changeFrequency: "monthly" as const,
      priority: 0.7,
    })),
  ];
}

export const revalidate = 3600;

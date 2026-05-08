import { notFound } from "next/navigation";
import { apiClient } from "./client";
import type { components } from "./types";

export type FragranceListItem = components["schemas"]["FragranceListItem"];
export type FragranceDetail = components["schemas"]["FragranceDetail"];
export type Pagination = components["schemas"]["Pagination"];
export type Gender = components["schemas"]["Gender"];
export type AccordSummary = components["schemas"]["AccordSummary"];
export type BrandSummary = components["schemas"]["BrandSummary"];

export interface FragranceListParams {
  limit?: number;
  offset?: number;
  brand?: string;
  perfumer?: string[];
  gender?: Gender;
  year_min?: number;
  year_max?: number;
  concentration?: string;
  accord?: string[];
  note?: string[];
}

/**
 * Sort array-valued query params so `?accord=a&accord=b` and
 * `?accord=b&accord=a` produce the same Vercel cache key. Without
 * canonicalization, two equivalent filter selections fragment the
 * cache and double-fetch upstream. Apply the same canonicalization in
 * the URL the user sees (see `pickQuery` on the list page).
 */
function canonicalizeQuery<T extends object>(params: T): T {
  const out: Record<string, unknown> = { ...(params as Record<string, unknown>) };
  for (const key of Object.keys(out)) {
    const value = out[key];
    if (Array.isArray(value)) {
      out[key] = [...value].sort();
    }
  }
  return out as T;
}

/** GET /api/v1/fragrances — list with filters + pagination. */
export async function getFragrances(params: FragranceListParams = {}) {
  const query = canonicalizeQuery(params);
  const { data, error, response } = await apiClient.GET("/api/v1/fragrances", {
    params: { query },
    // Native fetch options pass through (verified Context7):
    next: {
      revalidate: 300,
      tags: ["fragrances:list"],
    },
  });
  if (error) {
    throw new Error(
      `getFragrances failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) {
    throw new Error("getFragrances returned no data");
  }
  return data;
}

/**
 * GET /api/v1/accords — full taxonomy (no pagination per the spec
 * envelope). Used to populate FilterSidebar's accord facet so we
 * never render a hardcoded slug list that drifts from seed data.
 *
 * The OpenAPI for /api/v1/accords declares only a 200 response, so
 * openapi-fetch infers `error: never`. We still defensively check
 * via the HTTP response.status to surface upstream failures.
 */
export async function getAllAccords(): Promise<AccordSummary[]> {
  const { data, response } = await apiClient.GET("/api/v1/accords", {
    next: { revalidate: 3600, tags: ["accords:all"] },
  });
  if (!response.ok) {
    throw new Error(`getAllAccords failed (${response.status})`);
  }
  return data?.data ?? [];
}

/**
 * GET /api/v1/brands — paginated; we page through to populate the
 * Brand facet on the list page (F4 fix). Brands are a small set
 * (≪ 100) so a single request is normal; the loop is defensive.
 */
export async function getAllBrands(): Promise<BrandSummary[]> {
  const all: BrandSummary[] = [];
  let offset = 0;
  const PAGE = 100;
  const MAX_PAGES = 50;
  for (let i = 0; i < MAX_PAGES; i += 1) {
    const { data, error, response } = await apiClient.GET("/api/v1/brands", {
      params: { query: { limit: PAGE, offset } },
      next: { revalidate: 3600, tags: ["brands:all"] },
    });
    if (error) {
      throw new Error(
        `getAllBrands failed (${response.status}): ${JSON.stringify(error)}`,
      );
    }
    if (!data || data.data.length === 0) break;
    all.push(...data.data);
    if (!data.pagination.has_next) break;
    offset += PAGE;
  }
  return all;
}

// NOTE: there is no `/api/v1/concentrations` endpoint in the current
// `apps/api/openapi.json`. The concentration filter therefore falls
// back to a small static list (EDT/EDP/Parfum) sourced from
// `lib/glossary` term keys until a follow-up phase adds the endpoint.
// Tracked in Open Questions as a P1 follow-up.

/** GET /api/v1/fragrances/{slug} — detail; calls notFound() on 404. */
export async function getFragranceBySlug(slug: string) {
  const { data, error, response } = await apiClient.GET(
    "/api/v1/fragrances/{slug}",
    {
      params: { path: { slug } },
      next: {
        revalidate: 600,
        tags: [`fragrance:${slug}`],
      },
    },
  );
  if (response.status === 404) notFound();
  if (error) {
    throw new Error(
      `getFragranceBySlug(${slug}) failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) notFound();
  return data;
}

/**
 * Featured fragrances strip (home).
 * No `featured=` flag exists in P1 — we read the first N via the list
 * endpoint sorted by default order. When P5 adds curation, swap the
 * underlying call here without touching home/page.tsx.
 *
 * F11: throws on error like getFragrances does, so the caller can
 * decide error UX (page-level error.tsx) rather than silently
 * swallowing failures.
 */
export async function getFeaturedFragrances(limit = 6) {
  const { data, error, response } = await apiClient.GET("/api/v1/fragrances", {
    params: { query: { limit } },
    next: { revalidate: 600, tags: ["featured"] },
  });
  if (error) {
    throw new Error(
      `getFeaturedFragrances failed (${response.status}): ${JSON.stringify(error)}`,
    );
  }
  if (!data) {
    throw new Error("getFeaturedFragrances returned no data");
  }
  return data.data;
}

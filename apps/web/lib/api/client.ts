import createClient from "openapi-fetch";
import type { paths } from "./types";

const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

/**
 * Typed openapi-fetch client. All catalog reads go through this.
 *
 * Per Context7 docs (openapi-fetch v0.13), the per-call init object
 * passes through to the underlying fetch — Next.js's
 * `next: { revalidate, tags }` extensions ride along unchanged when
 * supplied via `fetchers.ts`.
 */
export const apiClient = createClient<paths>({ baseUrl });

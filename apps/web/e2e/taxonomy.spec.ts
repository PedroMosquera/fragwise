// Phase 4b smoke tests — assert each new route returns 200 and
// renders its expected heading. Run with: `pnpm test:e2e taxonomy`.
//
// These specs assume the API is running locally (default
// NEXT_PUBLIC_API_URL=http://localhost:8000) AND that the seed dataset
// has been loaded via `just ingest && just seed`. Without a populated
// dataset, slug-driven specs (notes/[seed-slug] etc.) will fall back
// to a header-only assertion since the seed slug is unknown to the
// test. Bogus-slug 404 specs work in any environment.
import { test, expect } from "@playwright/test";

test.describe("Phase 4b — list routes return 200", () => {
  for (const path of [
    "/notes",
    "/accords",
    "/brands",
    "/perfumers",
    "/articles",
  ]) {
    test(`GET ${path}`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response?.status()).toBe(200);
      await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    });
  }
});

test.describe("Phase 4b — detail routes 404 on bogus slug", () => {
  for (const path of [
    "/notes/__definitely-bogus__",
    "/accords/__definitely-bogus__",
    "/brands/__definitely-bogus__",
    "/perfumers/__definitely-bogus__",
    "/articles/__definitely-bogus__",
  ]) {
    test(`GET ${path} → 404`, async ({ page }) => {
      const response = await page.goto(path);
      expect(response?.status()).toBe(404);
    });
  }
});

test("accords/woody renders editorial header and Accord caption", async ({
  page,
}) => {
  // /accords/woody is the canonical happy-path because lib/accord-copy.ts
  // ships a hand-authored blurb for this slug. We do not assert blurb
  // text directly to avoid coupling the test to the exact paragraph
  // wording — instead we assert the editorial header pair (caption +
  // h1) is present.
  const response = await page.goto("/accords/woody");
  // 200 if seeded, 404 otherwise — accept either, then bail on 404.
  if (response?.status() === 404) test.skip();
  expect(response?.status()).toBe(200);
  await expect(page.getByText(/^Accord$/i).first()).toBeVisible();
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
});

test("brands ?q= updates URL via SearchInput debounce", async ({ page }) => {
  await page.goto("/brands");
  const input = page.getByPlaceholder("Search brands…");
  await input.fill("cha");
  // Debounce is 300ms; wait a bit longer for transition + RSC refetch.
  await page.waitForURL(/[?&]q=cha\b/, { timeout: 2000 });
  expect(page.url()).toMatch(/[?&]q=cha\b/);
});

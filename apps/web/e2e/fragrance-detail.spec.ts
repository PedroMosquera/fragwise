import { test, expect } from "@playwright/test";

// This smoke spec assumes the seed has produced at least one fragrance.
// It pulls the slug from the list page rather than hardcoding one,
// so seed-data drift does not break the spec.
test("fragrance detail page renders the notes pyramid", async ({ page }) => {
  await page.goto("/fragrances");
  const firstCard = page.locator('a[href^="/fragrances/"]').first();
  if (!(await firstCard.count())) test.skip(true, "No fragrances seeded");
  const href = await firstCard.getAttribute("href");
  expect(href).toBeTruthy();
  await page.goto(href!);

  // Pyramid mono labels
  await expect(page.getByText("TOP", { exact: true })).toBeVisible();
  await expect(page.getByText("HEART", { exact: true })).toBeVisible();
  await expect(page.getByText("BASE", { exact: true })).toBeVisible();
});

test("unknown slug renders the custom 404", async ({ page }) => {
  const resp = await page.goto("/fragrances/this-slug-does-not-exist", {
    waitUntil: "domcontentloaded",
  });
  expect(resp?.status()).toBe(404);
  await expect(
    page.getByRole("heading", { name: /not in the catalogue/i }),
  ).toBeVisible();
});

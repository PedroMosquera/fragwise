import { test, expect } from "@playwright/test";

test("home page renders the Fragwise brand and core sections", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.getByRole("link", { name: "Fragwise" }).first()).toBeVisible();
  // Featured strip heading from spec.
  await expect(
    page.getByRole("heading", { name: /featured fragrances/i }),
  ).toBeVisible();
  // Discover by mood section is part of the home spec.
  await expect(
    page.getByRole("heading", { name: /discover by mood/i }),
  ).toBeVisible();
});

test("skip-to-content link is the first focusable", async ({ page }) => {
  await page.goto("/");
  // Tab focuses the first interactive element. SkipToContent uses
  // sr-only + focus styles so it surfaces on focus.
  await page.keyboard.press("Tab");
  const focused = await page.evaluate(() => document.activeElement?.textContent);
  expect(focused).toMatch(/skip to content/i);
});

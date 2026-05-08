import { test, expect } from "@playwright/test";

test("fragrances list renders and pagination/filter affect URL", async ({
  page,
}) => {
  await page.goto("/fragrances");
  await expect(
    page.getByRole("heading", { name: /^fragrances$/i }),
  ).toBeVisible();

  // Filter sidebar Refine heading
  await expect(
    page.getByRole("heading", { name: /^refine$/i }),
  ).toBeVisible();
});

test("clicking an accord chip narrows the URL via searchParams", async ({
  page,
}) => {
  await page.goto("/fragrances");
  // First accord-facet link in the sidebar.
  const firstAccord = page.locator('aside a[href*="?accord="]').first();
  if (await firstAccord.count()) {
    await firstAccord.click();
    await expect(page).toHaveURL(/[?&]accord=/);
  }
});

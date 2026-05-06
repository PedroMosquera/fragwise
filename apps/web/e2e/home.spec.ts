import { test, expect } from "@playwright/test";

test("home page renders the Fragwise brand", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: /fragwise/i })).toBeVisible();
});

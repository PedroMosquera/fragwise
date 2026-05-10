// Ad-hoc full-page screenshots for visual review.
// Not part of the test suite — run on demand via:
//   node scripts/take-screenshots.mjs
import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

const OUT = "/tmp/fragwise-screenshots";
const BASE = process.env.BASE_URL || "http://localhost:3000";

const routes = [
  ["01-home", "/"],
  ["02-fragrances-list", "/fragrances"],
  ["03-fragrance-detail", "/fragrances/creed-aventus"],
  ["04-notes", "/notes"],
  ["05-accords", "/accords"],
  ["06-accord-detail", "/accords/woody"],
  ["07-brands", "/brands"],
  ["08-perfumers", "/perfumers"],
  ["09-articles", "/articles"],
];

await mkdir(OUT, { recursive: true });
const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();
for (const [name, path] of routes) {
  const url = `${BASE}${path}`;
  await page.goto(url, { waitUntil: "networkidle" });
  await page.screenshot({ path: `${OUT}/${name}.png`, fullPage: true });
  console.log(`[ok] ${url} -> ${name}.png`);
}
// Chat panel — open the sheet, click an example chip, let the SSE
// stream play out, then capture. With no OPENAI key in dev the API
// degrades to a generic clarify after ~1s, which is enough to verify
// the wisp avatar + degraded callout + clarify rendering.
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.getByRole("button", { name: /chat with wisp/i }).click();
await page.waitForSelector('[data-slot="sheet-content"]', { state: "visible" });
await page.screenshot({ path: `${OUT}/11-chat-welcome.png`, fullPage: false });
await page.getByRole("button", { name: /smoky leather for winter/i }).click();
// Wait until the SSE stream finishes — the input re-enables when
// `streaming` flips back to false in ChatLauncher.
await page.waitForFunction(
  () => {
    const input = document.getElementById("wisp-input");
    return input instanceof HTMLInputElement && !input.disabled;
  },
  { timeout: 15000 },
);
await page.screenshot({ path: `${OUT}/12-chat-after-send.png`, fullPage: false });
console.log(`[ok] chat panel -> 11-chat-welcome.png + 12-chat-after-send.png`);

await page.emulateMedia({ colorScheme: "dark" });
await page.goto(`${BASE}/`, { waitUntil: "networkidle" });
await page.screenshot({ path: `${OUT}/10-home-dark.png`, fullPage: true });
console.log(`[ok] dark / -> 10-home-dark.png`);
await browser.close();

#!/usr/bin/env node
// Generates apps/web/lib/api/types.ts from apps/api/openapi.json.
// Wired via predev/prebuild + CI stale check.
import { spawnSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve } from "node:path";

const here = new URL(".", import.meta.url).pathname;
const root = resolve(here, "..", "..", "..");
const input = resolve(root, "apps", "api", "openapi.json");
const output = resolve(root, "apps", "web", "lib", "api", "types.ts");

if (!existsSync(input)) {
  console.error(
    `[generate-api-types] missing ${input}\n` +
      `Run \`just emit-openapi\` first (or \`pnpm --filter api emit-openapi\`).`
  );
  process.exit(1);
}

// Context7-verified: openapi-typescript 7.x CLI shape is
// `openapi-typescript <input> -o <output>` (per CLI docs).
const result = spawnSync(
  "pnpm",
  ["exec", "openapi-typescript", input, "-o", output],
  { stdio: "inherit", cwd: resolve(root, "apps", "web") }
);
process.exit(result.status ?? 1);

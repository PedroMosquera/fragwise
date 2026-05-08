// .tsx because wrapGlossary returns React nodes. The Glossary
// component is passed in (not imported) to keep this module
// UI-dependency free and friendly to vitest hot loops.
import type { ComponentType, ReactNode } from "react";

export const glossary = {
  sillage: {
    term: "Sillage",
    definition:
      "The trail of scent a wearer leaves in the air. From French for 'wake'.",
  },
  accord: {
    term: "Accord",
    definition:
      "A blend of notes that produces a single recognisable smell — a perfume's building block.",
  },
  drydown: {
    term: "Drydown",
    definition:
      "The final phase of a fragrance, hours after application, when the base notes settle.",
  },
  chypre: {
    term: "Chypre",
    definition:
      "A family built on bergamot, oakmoss and labdanum. Refined, slightly bitter.",
  },
  fougere: {
    term: "Fougère",
    definition:
      "'Fern-like' — a classic accord of lavender, oakmoss and coumarin. The backbone of barbershop scents.",
  },
  oriental: {
    term: "Oriental (Amber)",
    definition:
      "Warm, resinous family — vanilla, amber, spices. Many houses now prefer 'amber'.",
  },
  gourmand: {
    term: "Gourmand",
    definition:
      "Edible-smelling fragrances — vanilla, caramel, cocoa, coffee.",
  },
  aquatic: {
    term: "Aquatic",
    definition:
      "Fresh, marine, ozonic notes — calone, sea salt, melon-water accords.",
  },
  edt: {
    term: "EDT (Eau de Toilette)",
    definition:
      "Lighter concentration, typically 5–15% aromatic compounds. Lasts 3–5 hours.",
  },
  edp: {
    term: "EDP (Eau de Parfum)",
    definition:
      "Stronger concentration, 15–20%. Longer wear, richer drydown.",
  },
  parfum: {
    term: "Parfum (Extrait)",
    definition:
      "Highest concentration, 20–40%. Worn close to the skin; lasts all day.",
  },
  "top-heart-base": {
    term: "Top, heart, base",
    definition:
      "The pyramid: top notes greet you, heart notes appear after 20–30 min, base notes anchor for hours.",
  },
} as const;

export type GlossaryKey = keyof typeof glossary;

// Optional aliases per term (case-insensitive). The bare key is added
// implicitly by wrapGlossary, so e.g. `parfum` matches "parfum" without
// listing it here. Aliases extend that set with synonyms and inflections.
// R3 fix: `term` field can be a display form like "Parfum (Extrait)";
// we no longer use `term` as an alias source — only the lowercased key
// + this ALIASES map.
const ALIASES: Partial<Record<GlossaryKey, string[]>> = {
  sillage: ["sillages"],
  fougere: ["fougère", "fougeres", "fougères"],
  edt: ["eau de toilette"],
  edp: ["eau de parfum"],
  parfum: ["extrait", "extrait de parfum"],
  oriental: ["amber"],
  "top-heart-base": ["pyramid", "top notes", "heart notes", "base notes"],
};

/**
 * Wraps the FIRST occurrence (case-insensitive, word-boundary) of EACH
 * glossary term in the input with the supplied `<Glossary>` component.
 * All other text is preserved verbatim.
 *
 * Replaces the broken pattern `description.split(term)[0|1]` which:
 *  - silently drops text past the 2nd occurrence
 *  - is case-sensitive
 *  - handles only ONE term out of the 12
 *
 * The alternation pattern is built longest-first so shorter aliases
 * never swallow prefixes of longer ones.
 *
 * R3 fix: alias set = lowercased KEY (always) + ALIASES synonyms.
 * We deliberately do NOT use glossary[key].term because it can be a
 * bracketed display form like "Parfum (Extrait)" that never appears
 * in user-authored prose. The bare key ("parfum") is what readers
 * actually write.
 *
 * R3 fix: use Unicode-aware lookarounds (`u` flag + property escapes)
 * because `\b` is ASCII-only and fails on accented aliases like
 * "fougère". The lookarounds match a transition between letter/digit
 * and non-letter/digit on both sides, including non-ASCII letters.
 */
export function wrapGlossary(
  text: string,
  Glossary: ComponentType<{ termKey: GlossaryKey; children: ReactNode }>,
): ReactNode {
  const aliases: { key: GlossaryKey; alias: string }[] = (
    Object.keys(glossary) as GlossaryKey[]
  ).flatMap((key) => [
    { key, alias: key.replace(/-/g, " ") }, // bare key form, hyphens to spaces
    ...(ALIASES[key] ?? []).map((alias) => ({ key, alias })),
  ]);
  aliases.sort((a, b) => b.alias.length - a.alias.length);

  // Build a Map for O(1) alias→key lookup at match time.
  const aliasIndex = new Map<string, GlossaryKey>();
  for (const { key, alias } of aliases) {
    const lower = alias.toLowerCase();
    if (!aliasIndex.has(lower)) aliasIndex.set(lower, key);
  }

  const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  // Apply-time test requirement: "sillage" inside "no-sillage-here"
  // MUST NOT wrap. We therefore treat ASCII hyphen `-` as part of the
  // word for boundary purposes, in addition to `\p{L}\p{N}_`.
  // Lookarounds remain Unicode-aware via the `u` flag for accented
  // aliases ("fougère").
  const pattern = new RegExp(
    `(?<![\\p{L}\\p{N}_-])(${aliases.map((a) => escape(a.alias)).join("|")})(?![\\p{L}\\p{N}_-])`,
    "giu",
  );

  const seen = new Set<GlossaryKey>();
  const out: ReactNode[] = [];
  let lastIndex = 0;
  for (const match of text.matchAll(pattern)) {
    const matched = match[0];
    const found = aliasIndex.get(matched.toLowerCase());
    if (!found) continue;
    if (seen.has(found)) continue; // first-mention only per term
    seen.add(found);
    const idx = match.index ?? 0;
    out.push(text.slice(lastIndex, idx));
    out.push(
      <Glossary key={`g-${idx}`} termKey={found}>
        {matched}
      </Glossary>,
    );
    lastIndex = idx + matched.length;
  }
  out.push(text.slice(lastIndex));
  return out;
}

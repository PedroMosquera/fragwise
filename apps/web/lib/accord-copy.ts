// Phase 4b ADR-0047: hand-authored editorial blurbs for the six
// canonical accord families. Each blurb is one paragraph (~80–120
// words) and references at least one term that triggers Glossary
// popovers (sillage, drydown, accord, chypre, fougere, oriental,
// gourmand, aquatic, etc.).
//
// At render time the accord detail page passes `blurb` through
// `wrapGlossary(blurb, Glossary)` so the marked terms become
// `<Glossary>` popovers automatically. Plain strings keep this file
// auditable as content rather than coupling it to JSX imports.

export type AccordCopy = { blurb: string };

export const ACCORD_COPY: Record<string, AccordCopy> = {
  woody: {
    blurb:
      "Woody perfumes draw on the dry, resinous heart of a forest: " +
      "cedar, sandalwood, vetiver, oud. The accord can lean smoky and " +
      "smouldering or cool and pencil-shaving sharp; in either reading " +
      "it leaves a long sillage and a slow drydown that anchors the " +
      "rest of the composition. Many traditional masculines are " +
      "essentially woody fougeres in disguise. The modern wave " +
      "lightens the family with iso E super and ambroxan.",
  },
  fougere: {
    blurb:
      "Fougère — French for 'fern' — names a 19th-century accord built " +
      "on lavender, oakmoss and coumarin. Imagine wet stones, freshly " +
      "split wood, the cool green of crushed bracken. It is the " +
      "backbone of barbershop scents and gentleman's colognes; the " +
      "drydown is herbal and dignified rather than sweet. Modern " +
      "fougeres temper the oakmoss with iso E super or amber to " +
      "satisfy IFRA limits while preserving the family's leafy spine.",
  },
  oriental: {
    blurb:
      "Oriental — increasingly relabelled 'amber' — is the warm, " +
      "resinous family: vanilla, labdanum, benzoin, sweet incense, " +
      "powdered spices. It blooms slowly on the skin and projects a " +
      "long, syrupy sillage. Where chypre prizes restraint, the " +
      "oriental accord is unapologetically generous; the drydown is " +
      "honeyed and cinnamon-laced rather than dry. Houses now prefer " +
      "the term 'amber' to step away from the orientalising " +
      "shorthand of an earlier century while keeping the same " +
      "olfactive shape.",
  },
  gourmand: {
    blurb:
      "Gourmand fragrances borrow from the kitchen: vanilla, caramel, " +
      "cocoa, coffee, praline. Calone-era aquatics gave way in the " +
      "1990s to a confectionary turn — Angel by Mugler is the " +
      "lighthouse — and the family has since divided into honeyed " +
      "everyday wears and dense, almost dessert-like extraits. The " +
      "drydown can read as warm milk or as burnt sugar depending on " +
      "the base accord supporting it; sillage is enthusiastic. Pair " +
      "with a cool top to stop it tipping into syrup.",
  },
  aquatic: {
    blurb:
      "Aquatic fragrances trade in the language of clean ocean air: " +
      "calone, sea salt, melon-water accords, ozonic notes. The " +
      "family arrived with the 1988 release of Cool Water and ruled " +
      "the 1990s. Sillage is bright and short; the drydown is more " +
      "musk than mineral, so the accord often pairs with a woody " +
      "base for staying power. Read closely, an aquatic is rarely " +
      "literal water — it is the cool feeling of a sea breeze " +
      "rendered in synthetic molecules.",
  },
  chypre: {
    blurb:
      "Chypre — named for Coty's 1917 perfume of Cyprus — is the " +
      "great refined accord: bergamot at the top, a heart of rose " +
      "or jasmine, oakmoss, labdanum, and patchouli at the base. The " +
      "structure is bitter where oriental is sweet and cool where " +
      "fougere is herbal. IFRA restrictions on oakmoss have forced " +
      "modern reformulations, but the family's signature drydown — " +
      "dry leaves, mineral earth — remains the most distinctive in " +
      "perfumery. The sillage is moderate; chypre prizes restraint.",
  },
};

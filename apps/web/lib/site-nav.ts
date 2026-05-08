// Phase 4b ADR-0044: NAV feature-flag map.
//
// Header and MobileMenu both import this NAV constant. Each entry
// carries `ready: boolean`. `ready: true` items render as a Next
// `<Link>` (with `aria-current="page"` when the pathname matches).
// `ready: false` items render as `<span aria-disabled="true">` carrying
// `title="Coming with phase 4c+"` so partial-deploy states never expose
// broken links.
//
// 4b ships all five remaining placeholders (notes, accords, brands,
// perfumers, articles), so every entry here is `ready: true` once 4b
// lands. Future phases may add new entries with `ready: false` until
// their routes ship.

export type NavItem = {
  href: string;
  label: string;
  ready: boolean;
};

export const NAV: readonly NavItem[] = [
  { href: "/", label: "Home", ready: true },
  { href: "/fragrances", label: "Fragrances", ready: true },
  { href: "/notes", label: "Notes", ready: true },
  { href: "/accords", label: "Accords", ready: true },
  { href: "/brands", label: "Brands", ready: true },
  { href: "/perfumers", label: "Perfumers", ready: true },
  { href: "/articles", label: "Journal", ready: true },
] as const;

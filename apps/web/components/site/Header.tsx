// R3 fix: Header is a Server Component (no "use client"). MobileMenu
// is the only client child; Radix Sheet inside MobileMenu lazy-renders
// its portal natively on `open`, so no `next/dynamic` wrapper is
// needed.
//
// Phase 4b ADR-0044: NAV is now imported from `@/lib/site-nav`. Each
// entry carries `ready: boolean`. `ready: true` items render as a
// NavLink (small client subcomponent that adds `aria-current="page"`
// when the pathname matches). `ready: false` items render as a
// non-interactive `<span aria-disabled="true">` carrying
// `title="Coming with phase 4c+"`.
import Link from "next/link";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { NAV } from "@/lib/site-nav";
import { MobileMenu } from "./MobileMenu";
import { NavLink } from "./NavLink";
import { ThemeToggle } from "./ThemeToggle";

export function Header() {
  return (
    <header className="sticky top-0 z-40 w-full border-b border-border bg-background/85 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-6 px-4 sm:px-6">
        <Link
          href="/"
          className="font-display text-2xl font-medium tracking-tight"
        >
          Fragwise
        </Link>
        <nav className="hidden items-center gap-6 md:flex">
          {NAV.map((item) =>
            item.ready ? (
              <NavLink
                key={item.href}
                href={item.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground aria-[current=page]:text-foreground"
              >
                {item.label}
              </NavLink>
            ) : (
              <span
                key={item.href}
                aria-disabled="true"
                title="Coming with phase 4c+"
                className="cursor-not-allowed text-sm text-muted-foreground/50"
              >
                {item.label}
              </span>
            ),
          )}
        </nav>
        <div className="hidden items-center gap-3 md:flex">
          <label className="relative">
            <Search
              aria-hidden
              className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground"
            />
            <Input
              type="search"
              placeholder="Search coming soon"
              disabled
              aria-label="Search (coming soon)"
              className="w-64 pl-9 font-mono text-xs"
            />
          </label>
          <ThemeToggle />
        </div>
        <div className="flex items-center md:hidden">
          <ThemeToggle />
        </div>
        <MobileMenu nav={NAV} />
      </div>
    </header>
  );
}

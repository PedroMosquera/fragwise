// R3 fix: Header is a Server Component (no "use client"). MobileMenu
// is the only client child; Radix Sheet inside MobileMenu lazy-renders
// its portal natively on `open`, so no `next/dynamic` wrapper is
// needed.
import Link from "next/link";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { MobileMenu } from "./MobileMenu";

const NAV: { href: string; label: string; placeholder?: boolean }[] = [
  { href: "/", label: "Home" },
  { href: "/fragrances", label: "Fragrances" },
  // 4b targets — render as non-interactive labels until those routes ship.
  { href: "/notes", label: "Notes", placeholder: true },
  { href: "/accords", label: "Accords", placeholder: true },
  { href: "/brands", label: "Brands", placeholder: true },
  { href: "/perfumers", label: "Perfumers", placeholder: true },
  { href: "/articles", label: "Journal", placeholder: true },
];

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
            item.placeholder ? (
              // 4b targets — render as non-interactive labels until those
              // routes ship. Avoids 404s on click while signalling the
              // surface is planned.
              <span
                key={item.href}
                aria-disabled="true"
                title="Coming with phase 4b"
                className="cursor-not-allowed text-sm text-muted-foreground/50"
              >
                {item.label}
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className="text-sm text-muted-foreground transition-colors hover:text-foreground"
              >
                {item.label}
              </Link>
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
        </div>
        <MobileMenu nav={NAV} />
      </div>
    </header>
  );
}

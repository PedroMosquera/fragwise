// Phase 4b ADR-0044: MobileMenu accepts the NAV feature-flag map.
// Items where `ready: true` render as `<Link>`; `ready: false` items
// render as `<span aria-disabled>` carrying the same "Coming with
// phase 4c+" hint as the desktop Header.
"use client";
import Link from "next/link";
import { Menu } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import type { NavItem } from "@/lib/site-nav";
import { ThemeToggle } from "./ThemeToggle";

export function MobileMenu({ nav }: { nav: readonly NavItem[] }) {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label="Open menu"
        >
          <Menu />
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-72">
        <SheetHeader>
          <SheetTitle className="font-display">Fragwise</SheetTitle>
        </SheetHeader>
        <nav className="mt-6 flex flex-col gap-3 px-4">
          {nav.map((item) =>
            item.ready ? (
              <Link
                key={item.href}
                href={item.href}
                className="text-base text-foreground transition-colors hover:text-accent"
              >
                {item.label}
              </Link>
            ) : (
              <span
                key={item.href}
                aria-disabled="true"
                title="Coming with phase 4c+"
                className="cursor-not-allowed text-base text-muted-foreground/50"
              >
                {item.label}
              </span>
            ),
          )}
        </nav>
        <div className="mt-6 flex items-center gap-3 border-t border-border px-4 pt-6">
          <span className="text-xs text-muted-foreground font-mono">Theme</span>
          <ThemeToggle />
        </div>
      </SheetContent>
    </Sheet>
  );
}

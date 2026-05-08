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

export function MobileMenu({
  nav,
}: {
  nav: { href: string; label: string; placeholder?: boolean }[];
}) {
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
            item.placeholder ? (
              <span
                key={item.href}
                aria-disabled="true"
                className="cursor-not-allowed text-base text-muted-foreground/50"
              >
                {item.label}
                <span className="ml-2 font-mono text-[0.6rem] uppercase tracking-wider">
                  4b
                </span>
              </span>
            ) : (
              <Link
                key={item.href}
                href={item.href}
                className="text-base text-foreground transition-colors hover:text-accent"
              >
                {item.label}
              </Link>
            ),
          )}
        </nav>
      </SheetContent>
    </Sheet>
  );
}

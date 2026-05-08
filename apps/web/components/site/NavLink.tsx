// Phase 4b: small client subcomponent so the parent Header can stay
// as an RSC. Reads usePathname() and applies `aria-current="page"`
// when the current pathname matches the link's href. Home ("/")
// matches only when pathname is exactly "/" so other routes don't
// claim it.
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ComponentProps } from "react";

type NavLinkProps = ComponentProps<typeof Link> & {
  href: string;
};

export function NavLink({ href, ...rest }: NavLinkProps) {
  const pathname = usePathname();
  const isActive =
    href === "/" ? pathname === "/" : pathname?.startsWith(href);
  return (
    <Link href={href} aria-current={isActive ? "page" : undefined} {...rest} />
  );
}

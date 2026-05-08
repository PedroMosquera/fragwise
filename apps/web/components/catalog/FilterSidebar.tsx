// "use client" REQUIRED because this component renders Radix
// Accordion, which mounts state-bearing client primitives. Server
// Component → Client Component prop boundaries also mean we cannot
// pass a non-serializable URLSearchParams instance — props must be
// plain JSON. The signature accepts Record<string, string | string[]>
// (the same shape Next.js gives us from searchParams) and lazily
// reconstructs a URLSearchParams inside the component for href
// building. (S1 fix.)
"use client";

import Link from "next/link";
import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";

const GENDERS = [
  { slug: "masc", label: "Masculine" },
  { slug: "fem", label: "Feminine" },
  { slug: "unisex", label: "Unisex" },
  { slug: "genderfree", label: "Genderfree" },
];

export interface FilterSidebarProps {
  pathname: string;
  /**
   * Plain serializable shape so this Client Component receives a
   * cross-boundary-safe prop. Convert in the parent via
   * `Object.fromEntries(...)` over the awaited `searchParams`.
   */
  searchParams: Record<string, string | string[]>;
  facets: {
    accords: { slug: string; name: string }[];
    brands: { slug: string; name: string }[];
    concentrations: { slug: string; name: string }[];
  };
}

function toUSP(sp: Record<string, string | string[]>): URLSearchParams {
  const out = new URLSearchParams();
  for (const k of Object.keys(sp).sort()) {
    const v = sp[k];
    if (v == null || v === "") continue;
    const list = Array.isArray(v) ? [...v].sort() : [v];
    list.forEach((vv) => {
      if (vv !== "") out.append(k, vv);
    });
  }
  return out;
}

function withParam(
  sp: URLSearchParams,
  key: string,
  value: string,
  mode: "set" | "add" | "remove",
) {
  const next = new URLSearchParams(sp);
  if (mode === "set") next.set(key, value);
  if (mode === "add") {
    // R3 fix: dedupe via Set so re-clicking an already-active filter
    // doesn't produce `?accord=woody&accord=woody`. Then sort to keep
    // the URL canonical (cache-key stable).
    const merged = [...new Set([...next.getAll(key), value])].sort();
    next.delete(key);
    merged.forEach((v) => next.append(key, v));
  }
  if (mode === "remove") {
    const list = next
      .getAll(key)
      .filter((v) => v !== value)
      .sort();
    next.delete(key);
    list.forEach((v) => next.append(key, v));
  }
  next.delete("offset"); // any filter change resets pagination
  return next.toString();
}

export function FilterSidebar({
  pathname,
  searchParams,
  facets,
}: FilterSidebarProps) {
  const usp = toUSP(searchParams);
  const activeAccords = usp.getAll("accord");
  const activeGender = usp.get("gender");
  const activeBrand = usp.get("brand");

  const hasActive = [...usp.keys()].some((k) =>
    [
      "accord",
      "gender",
      "brand",
      "year_min",
      "year_max",
      "concentration",
      "note",
    ].includes(k),
  );

  return (
    <aside className="flex flex-col gap-6 text-sm" aria-label="Filters">
      <div className="flex items-center justify-between">
        <h2 className="font-display text-xl">Refine</h2>
        {hasActive ? (
          <Link
            href={pathname}
            className="font-mono text-xs uppercase tracking-wider text-accent hover:underline"
          >
            Clear all
          </Link>
        ) : null}
      </div>

      {activeAccords.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {activeAccords.map((slug) => (
            <Link
              key={slug}
              href={`${pathname}?${withParam(usp, "accord", slug, "remove")}`}
              aria-label={`Remove ${slug} filter`}
            >
              <Badge variant="default" className="gap-1">
                {slug} ×
              </Badge>
            </Link>
          ))}
        </div>
      ) : null}

      <Accordion
        type="multiple"
        defaultValue={["gender", "accord", "brand"]}
      >
        <AccordionItem value="gender">
          <AccordionTrigger>Gender</AccordionTrigger>
          <AccordionContent>
            <ul className="flex flex-col gap-2">
              {GENDERS.map((g) => {
                const isActive = activeGender === g.slug;
                const href = isActive
                  ? `${pathname}?${withParam(usp, "gender", g.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "gender", g.slug, "set")}`;
                return (
                  <li key={g.slug}>
                    {/* F7: aria-current="page" is the correct attribute
                        for an anchor representing the currently-applied
                        filter. aria-pressed is for buttons, not links. */}
                    <Link
                      href={href}
                      aria-current={isActive ? "page" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {g.label}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="accord">
          <AccordionTrigger>Accord</AccordionTrigger>
          <AccordionContent>
            <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto">
              {facets.accords.map((a) => {
                const isActive = activeAccords.includes(a.slug);
                const href = isActive
                  ? `${pathname}?${withParam(usp, "accord", a.slug, "remove")}`
                  : `${pathname}?${withParam(usp, "accord", a.slug, "add")}`;
                return (
                  <li key={a.slug}>
                    <Link
                      href={href}
                      aria-current={isActive ? "page" : undefined}
                      className={isActive ? "text-accent" : "text-foreground"}
                    >
                      {a.name}
                    </Link>
                  </li>
                );
              })}
            </ul>
          </AccordionContent>
        </AccordionItem>

        {facets.brands.length > 0 ? (
          <AccordionItem value="brand">
            <AccordionTrigger>Brand</AccordionTrigger>
            <AccordionContent>
              <ul className="flex max-h-72 flex-col gap-2 overflow-y-auto">
                {facets.brands.map((b) => {
                  const isActive = activeBrand === b.slug;
                  const href = isActive
                    ? `${pathname}?${withParam(usp, "brand", b.slug, "remove")}`
                    : `${pathname}?${withParam(usp, "brand", b.slug, "set")}`;
                  return (
                    <li key={b.slug}>
                      <Link
                        href={href}
                        aria-current={isActive ? "page" : undefined}
                        className={isActive ? "text-accent" : "text-foreground"}
                      >
                        {b.name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </AccordionContent>
          </AccordionItem>
        ) : null}

        {facets.concentrations.length > 0 ? (
          <AccordionItem value="concentration">
            <AccordionTrigger>Concentration</AccordionTrigger>
            <AccordionContent>
              <ul className="flex flex-col gap-2">
                {facets.concentrations.map((c) => {
                  const isActive = usp.get("concentration") === c.slug;
                  const href = isActive
                    ? `${pathname}?${withParam(usp, "concentration", c.slug, "remove")}`
                    : `${pathname}?${withParam(usp, "concentration", c.slug, "set")}`;
                  return (
                    <li key={c.slug}>
                      <Link
                        href={href}
                        aria-current={isActive ? "page" : undefined}
                        className={isActive ? "text-accent" : "text-foreground"}
                      >
                        {c.name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </AccordionContent>
          </AccordionItem>
        ) : null}

        <AccordionItem value="year">
          <AccordionTrigger>Year</AccordionTrigger>
          <AccordionContent>
            <p className="text-xs text-muted-foreground">
              Year range filter via URL params{" "}
              <code className="font-mono">year_min</code> /{" "}
              <code className="font-mono">year_max</code>. Slider control
              deferred to 4b; the API params are wired today.
            </p>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </aside>
  );
}

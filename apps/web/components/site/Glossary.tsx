// ADR-0039 (revised): Glossary uses Radix Popover (NOT Tooltip).
// Tooltip fires on hover/focus only; Popover satisfies click/tap +
// keyboard which the spec ("Touch users MUST be able to trigger via
// tap") requires.
// F10 fix: trigger uses cursor-pointer (NOT cursor-help) since the
// trigger now requires a CLICK to open.
"use client";

import { glossary, type GlossaryKey } from "@/lib/glossary";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";

export function Glossary({
  termKey,
  children,
}: {
  termKey: GlossaryKey;
  children: React.ReactNode;
}) {
  const entry = glossary[termKey];
  if (!entry) return <>{children}</>;
  return (
    <Popover>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label={`Glossary: ${entry.term}`}
          className="inline-flex cursor-pointer items-baseline border-b border-dotted border-accent text-current focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          {children}
        </button>
      </PopoverTrigger>
      <PopoverContent side="top" className="max-w-xs text-sm leading-snug">
        <strong className="mb-1 block font-display font-semibold">
          {entry.term}
        </strong>
        <span className="text-foreground/85">{entry.definition}</span>
      </PopoverContent>
    </Popover>
  );
}

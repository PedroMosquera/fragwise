import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { wrapGlossary } from "@/lib/glossary";
import type { GlossaryKey } from "@/lib/glossary";
import type { ReactNode } from "react";

// Stub <Glossary> for isolation: emits <span data-glossary={key}>.
function StubGlossary({
  termKey,
  children,
}: {
  termKey: GlossaryKey;
  children: ReactNode;
}) {
  return <span data-glossary={termKey}>{children}</span>;
}

function html(input: string) {
  return renderToStaticMarkup(<>{wrapGlossary(input, StubGlossary)}</>);
}

describe("wrapGlossary", () => {
  it("wraps a standalone 'sillage'", () => {
    const out = html("Its sillage is impressive.");
    expect(out).toContain('data-glossary="sillage"');
    expect(out).toContain(">sillage</span>");
  });

  it("does NOT wrap 'sillage' inside 'no-sillage-here' (Unicode word boundary)", () => {
    const out = html("This is no-sillage-here, no wrap should occur.");
    expect(out).not.toContain("data-glossary");
  });

  it("wraps the bare key 'parfum' (display term is 'Parfum (Extrait)')", () => {
    // R3 fix: bare key form is the implicit alias, not the display term.
    const out = html("Worn as parfum, it lasts all day.");
    expect(out).toContain('data-glossary="parfum"');
  });

  it("wraps accented alias 'fougère' (Unicode-aware lookarounds)", () => {
    const out = html("A classic fougère composition.");
    expect(out).toContain('data-glossary="fougere"');
  });

  it("wraps only the FIRST mention of each term", () => {
    const out = html("sillage, then sillage again, then sillage once more.");
    // exactly one <span data-glossary="sillage"> occurrence
    const matches = out.match(/data-glossary="sillage"/g) ?? [];
    expect(matches.length).toBe(1);
  });
});

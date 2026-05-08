import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Glossary } from "@/components/site/Glossary";

// Maps to spec scenarios (fragrance-catalog-ui):
// - "Term renders with dotted underline"
// - "Hover shows tooltip with definition" (we assert popover trigger
//   button presence; popover content is portal-mounted on click —
//   covered by the integration/Playwright pass).

describe("Glossary", () => {
  it("renders the term as a button with a dotted-underline border", () => {
    render(
      <Glossary termKey="sillage">
        <span>sillage</span>
      </Glossary>,
    );
    const trigger = screen.getByRole("button", { name: /Glossary: Sillage/i });
    expect(trigger).toBeInTheDocument();
    expect(trigger.className).toMatch(/border-dotted/);
    expect(trigger.className).toMatch(/cursor-pointer/);
  });

  it("renders the children verbatim when termKey unknown", () => {
    // @ts-expect-error: testing the runtime fallback path
    render(<Glossary termKey="not-a-real-key">passthrough</Glossary>);
    expect(screen.getByText("passthrough")).toBeInTheDocument();
  });
});

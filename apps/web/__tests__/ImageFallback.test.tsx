import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ImageFallback } from "@/components/catalog/ImageFallback";

// Maps to spec scenarios (P4c, design-system delta):
// - "Panel reads --fallback-l from active theme" → backgroundColor string
//   contains the literal `var(--fallback-l)` reference (jsdom cannot
//   resolve oklch() so we assert the variable reference, not the
//   computed color — see design.md §"Testing Strategy").
// - "Hue varies per slug, lightness varies per theme" → --fallback-h
//   inline custom property differs between slugs; backgroundColor string
//   is structurally identical (only the resolved hue differs at paint).
// - "First letter glyph rendered" → uppercase initial in DOM.

describe("ImageFallback", () => {
  it("emits a stable --fallback-h custom property for the same slug", () => {
    const { container, unmount } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const first = container.firstChild as HTMLElement;
    const firstHue = first.style.getPropertyValue("--fallback-h");
    expect(firstHue).not.toBe("");
    unmount();
    const { container: c2 } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const second = c2.firstChild as HTMLElement;
    expect(second.style.getPropertyValue("--fallback-h")).toBe(firstHue);
  });

  it("backgroundColor uses var(--fallback-l) so theme controls lightness", () => {
    const { container } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const root = container.firstChild as HTMLElement;
    expect(root.style.backgroundColor).toContain("var(--fallback-l)");
    expect(root.style.backgroundColor).toContain("var(--fallback-h)");
  });

  it("produces different --fallback-h custom properties for different slugs", () => {
    const { container } = render(
      <ImageFallback slug="slug-a" name="Slug A" />,
    );
    const { container: c2 } = render(
      <ImageFallback slug="slug-different-b" name="Slug B" />,
    );
    const hueA = (container.firstChild as HTMLElement).style.getPropertyValue(
      "--fallback-h",
    );
    const hueB = (c2.firstChild as HTMLElement).style.getPropertyValue(
      "--fallback-h",
    );
    expect(hueA).not.toBe("");
    expect(hueB).not.toBe("");
    expect(hueA).not.toBe(hueB);
  });

  it("renders the uppercase first letter of the name", () => {
    const { getByText } = render(
      <ImageFallback slug="chanel-no-5" name="chanel No 5" />,
    );
    expect(getByText("C")).toBeInTheDocument();
  });

  it("glyph color uses var(--fallback-fg) so theme controls foreground", () => {
    const { getByText } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const glyph = getByText("C") as HTMLElement;
    expect(glyph.style.color).toContain("var(--fallback-fg)");
  });
});

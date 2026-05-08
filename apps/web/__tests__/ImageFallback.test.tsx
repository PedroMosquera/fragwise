import { render } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ImageFallback } from "@/components/catalog/ImageFallback";

// Maps to spec scenarios:
// - "Same slug yields same color"
// - "First letter glyph rendered"

describe("ImageFallback", () => {
  it("produces identical inline backgroundColor for the same slug", () => {
    const { container, unmount } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const first = container.firstChild as HTMLElement;
    const firstBg = first.style.backgroundColor;
    unmount();
    const { container: c2 } = render(
      <ImageFallback slug="chanel-no-5" name="Chanel No 5" />,
    );
    const second = c2.firstChild as HTMLElement;
    expect(second.style.backgroundColor).toBe(firstBg);
    expect(firstBg).toContain("oklch");
  });

  it("produces different backgroundColor for different slugs", () => {
    const { container } = render(
      <ImageFallback slug="slug-a" name="Slug A" />,
    );
    const { container: c2 } = render(
      <ImageFallback slug="slug-different-b" name="Slug B" />,
    );
    expect(
      (container.firstChild as HTMLElement).style.backgroundColor,
    ).not.toBe((c2.firstChild as HTMLElement).style.backgroundColor);
  });

  it("renders the uppercase first letter of the name", () => {
    const { getByText } = render(
      <ImageFallback slug="chanel-no-5" name="chanel No 5" />,
    );
    expect(getByText("C")).toBeInTheDocument();
  });
});

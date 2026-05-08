import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Pagination } from "@/components/catalog/Pagination";

// Maps to spec scenarios:
// - "Click page N updates URL offset" (URL composition assertion)
// - "Boundaries disable Prev/Next" (boundary-disabled state)

describe("Pagination", () => {
  it("renders disabled Prev as <span aria-disabled>, NOT <a href='#'>", () => {
    render(
      <Pagination
        total={120}
        limit={24}
        offset={0}
        hrefBase="/fragrances"
        searchParams={new URLSearchParams()}
      />,
    );
    const prev = screen.getByLabelText("No previous page");
    expect(prev.tagName).toBe("SPAN");
    expect(prev.getAttribute("aria-disabled")).toBe("true");
    // Prev MUST NOT be an anchor.
    expect(prev.tagName).not.toBe("A");
  });

  it("renders disabled Next as <span aria-disabled> at the upper boundary", () => {
    render(
      <Pagination
        total={48}
        limit={24}
        offset={24}
        hrefBase="/fragrances"
        searchParams={new URLSearchParams()}
      />,
    );
    const next = screen.getByLabelText("No next page");
    expect(next.tagName).toBe("SPAN");
    expect(next.getAttribute("aria-disabled")).toBe("true");
  });

  it("renders Prev as a link when not at the lower boundary", () => {
    render(
      <Pagination
        total={120}
        limit={24}
        offset={48}
        hrefBase="/fragrances"
        searchParams={new URLSearchParams("accord=woody")}
      />,
    );
    // Prev is a PaginationPrevious link: navigates to page (current-1).
    // currentPage = floor(48/24) + 1 = 3 → prev = page 2 → offset 24
    const links = screen.getAllByRole("link");
    const hrefs = links.map((a) => a.getAttribute("href"));
    expect(hrefs.some((h) => h && h.includes("offset=24"))).toBe(true);
  });
});

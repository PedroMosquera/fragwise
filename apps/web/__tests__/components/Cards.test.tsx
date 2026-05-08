import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { AccordCard } from "@/components/taxonomy/AccordCard";
import { BrandCard } from "@/components/taxonomy/BrandCard";
import { PerfumerCard } from "@/components/taxonomy/PerfumerCard";
import { ArticleCard } from "@/components/editorial/ArticleCard";

// Each card renders the expected text and href.

describe("AccordCard", () => {
  it("links to /accords/[slug] and shows the name", () => {
    render(<AccordCard slug="woody" name="Woody" />);
    const link = screen.getByRole("link", { name: /Woody/i });
    expect(link).toHaveAttribute("href", "/accords/woody");
    expect(screen.getByText("Woody")).toBeInTheDocument();
  });
});

describe("BrandCard", () => {
  it("links to /brands/[slug] and shows the name", () => {
    render(<BrandCard slug="chanel" name="Chanel" />);
    const link = screen.getByRole("link", { name: /Chanel/i });
    expect(link).toHaveAttribute("href", "/brands/chanel");
    expect(screen.getByText("Chanel")).toBeInTheDocument();
  });
});

describe("PerfumerCard", () => {
  it("links to /perfumers/[slug] and shows the name", () => {
    render(<PerfumerCard slug="ellena" name="Jean-Claude Ellena" />);
    const link = screen.getByRole("link", {
      name: /Jean-Claude Ellena/i,
    });
    expect(link).toHaveAttribute("href", "/perfumers/ellena");
    expect(screen.getByText("Jean-Claude Ellena")).toBeInTheDocument();
  });
});

describe("ArticleCard", () => {
  it("links to /articles/[slug] and renders title + date", () => {
    render(
      <ArticleCard
        slug="welcome"
        title="Welcome to Fragwise"
        publishedAt="2026-01-15T00:00:00Z"
      />,
    );
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/articles/welcome");
    expect(screen.getByText("Welcome to Fragwise")).toBeInTheDocument();
    // Date formatting depends on locale; assert year is present.
    expect(screen.getByText(/2026/)).toBeInTheDocument();
  });

  it("renders 'Unpublished' label when publishedAt is null", () => {
    render(
      <ArticleCard slug="draft" title="Draft Essay" publishedAt={null} />,
    );
    expect(screen.getByText("Unpublished")).toBeInTheDocument();
  });
});

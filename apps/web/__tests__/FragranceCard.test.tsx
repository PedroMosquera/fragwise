import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { FragranceCard } from "@/components/catalog/FragranceCard";
import type { FragranceListItem } from "@/lib/api/fetchers";

// Maps to spec scenario:
// - "FragranceCard Renders Image, Brand, Name, Year, Gender, Accords"
//   → "Card renders all required fields"

const sample = (overrides: Partial<FragranceListItem> = {}): FragranceListItem => ({
  id: "00000000-0000-0000-0000-000000000001",
  slug: "sample-fragrance",
  name: "Sample Fragrance",
  brand: { slug: "sample-brand", name: "Sample Brand" },
  year_released: 2024,
  gender: "masc",
  concentration: { slug: "edt", name: "EDT" },
  ...overrides,
});

describe("FragranceCard", () => {
  it("renders brand, name, year and concentration", () => {
    render(<FragranceCard fragrance={sample()} />);
    expect(screen.getByText("Sample Brand")).toBeInTheDocument();
    expect(screen.getByText("Sample Fragrance")).toBeInTheDocument();
    expect(screen.getByText("2024")).toBeInTheDocument();
    expect(screen.getByText("EDT")).toBeInTheDocument();
  });

  it("renders the masculine gender icon for gender='masc'", () => {
    render(<FragranceCard fragrance={sample({ gender: "masc" })} />);
    expect(screen.getByLabelText("masculine")).toBeInTheDocument();
  });

  it("renders the feminine gender icon for gender='fem'", () => {
    render(<FragranceCard fragrance={sample({ gender: "fem" })} />);
    expect(screen.getByLabelText("feminine")).toBeInTheDocument();
  });

  it("renders the unisex/genderfree icon for any other gender", () => {
    render(<FragranceCard fragrance={sample({ gender: "unisex" })} />);
    expect(
      screen.getByLabelText("unisex / genderfree"),
    ).toBeInTheDocument();
  });

  it("links to the fragrance detail route", () => {
    render(<FragranceCard fragrance={sample()} />);
    const link = screen.getByRole("link");
    expect(link).toHaveAttribute("href", "/fragrances/sample-fragrance");
  });
});

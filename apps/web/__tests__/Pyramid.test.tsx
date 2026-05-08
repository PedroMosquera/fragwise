import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Pyramid } from "@/components/catalog/Pyramid";

// Maps to spec scenarios:
// - "All three roles populated"
// - "Missing role renders dash placeholder"

describe("Pyramid", () => {
  it("renders three role labels with note names when all populated", () => {
    render(
      <Pyramid
        notes={{
          top: [{ slug: "bergamot", name: "Bergamot" }],
          heart: [{ slug: "rose", name: "Rose" }],
          base: [{ slug: "musk", name: "Musk" }],
        }}
      />,
    );
    expect(screen.getByText("TOP")).toBeInTheDocument();
    expect(screen.getByText("HEART")).toBeInTheDocument();
    expect(screen.getByText("BASE")).toBeInTheDocument();
    expect(screen.getByText("Bergamot")).toBeInTheDocument();
    expect(screen.getByText("Rose")).toBeInTheDocument();
    expect(screen.getByText("Musk")).toBeInTheDocument();
  });

  it("renders an em-dash for an empty role rather than collapsing", () => {
    render(
      <Pyramid
        notes={{
          top: [{ slug: "bergamot", name: "Bergamot" }],
          heart: [],
          base: [{ slug: "musk", name: "Musk" }],
        }}
      />,
    );
    expect(screen.getByLabelText("No heart notes")).toBeInTheDocument();
  });
});

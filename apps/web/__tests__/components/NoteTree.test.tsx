import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { NoteTree } from "@/components/taxonomy/NoteTree";
import type { NoteTreeNode } from "@/lib/api/fetchers";

// Maps to spec scenarios:
// - "Tree renders with all branches collapsed"
// - "Branch expansion is client-side"
// - leaf nodes render as plain Link

const tree: NoteTreeNode[] = [
  {
    slug: "citrus",
    name: "Citrus",
    children: [
      { slug: "bergamot", name: "Bergamot", children: [] },
      { slug: "lemon", name: "Lemon", children: [] },
    ],
  },
  {
    slug: "woody",
    name: "Woody",
    children: [{ slug: "cedar", name: "Cedar", children: [] }],
  },
];

describe("NoteTree", () => {
  it("renders top-level branches with children collapsed", () => {
    render(<NoteTree nodes={tree} />);
    // Branch headers visible
    expect(screen.getByText("Citrus")).toBeInTheDocument();
    expect(screen.getByText("Woody")).toBeInTheDocument();
    // Children NOT visible until expansion
    expect(screen.queryByText("Bergamot")).toBeNull();
    expect(screen.queryByText("Cedar")).toBeNull();
  });

  it("expands a branch on trigger click", () => {
    render(<NoteTree nodes={tree} />);
    const trigger = screen.getByRole("button", { name: /Citrus/i });
    fireEvent.click(trigger);
    expect(screen.getByText("Bergamot")).toBeInTheDocument();
    expect(screen.getByText("Lemon")).toBeInTheDocument();
  });

  it("renders the empty state when nodes are empty", () => {
    render(<NoteTree nodes={[]} />);
    expect(screen.getByText("No notes available.")).toBeInTheDocument();
  });
});

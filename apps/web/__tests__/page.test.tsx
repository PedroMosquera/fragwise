import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import HomePage from "@/app/page";

describe("HomePage", () => {
  it("renders the brand name", () => {
    render(<HomePage />);
    expect(
      screen.getByRole("heading", { name: /fragwise/i })
    ).toBeInTheDocument();
  });
});

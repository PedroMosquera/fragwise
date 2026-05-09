import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ThemeToggle } from "@/components/site/ThemeToggle";

// Mutable mock state — `useTheme()` returns a fresh snapshot each
// render, so we mutate this object between renders to simulate
// next-themes state changes.
const themeState: { theme: string | undefined } = { theme: "light" };
const setThemeSpy = vi.fn((next: string) => {
  themeState.theme = next;
});

vi.mock("next-themes", () => ({
  useTheme: () => ({
    theme: themeState.theme,
    setTheme: setThemeSpy,
  }),
}));

describe("ThemeToggle", () => {
  beforeEach(() => {
    themeState.theme = "light";
    setThemeSpy.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("starts with the light aria-label and Sun icon", () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button");
    expect(button.getAttribute("aria-label")).toBe(
      "Switch theme: currently light",
    );
  });

  it("cycles light → dark → system → light across three clicks", () => {
    // First render: theme = light → click should call setTheme("dark")
    const { rerender } = render(<ThemeToggle />);
    fireEvent.click(screen.getByRole("button"));
    expect(setThemeSpy).toHaveBeenLastCalledWith("dark");
    expect(themeState.theme).toBe("dark");

    // Second render: theme = dark → click should call setTheme("system")
    rerender(<ThemeToggle />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe(
      "Switch theme: currently dark",
    );
    fireEvent.click(screen.getByRole("button"));
    expect(setThemeSpy).toHaveBeenLastCalledWith("system");
    expect(themeState.theme).toBe("system");

    // Third render: theme = system → click should call setTheme("light")
    rerender(<ThemeToggle />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe(
      "Switch theme: currently system",
    );
    fireEvent.click(screen.getByRole("button"));
    expect(setThemeSpy).toHaveBeenLastCalledWith("light");
    expect(themeState.theme).toBe("light");

    expect(setThemeSpy).toHaveBeenCalledTimes(3);
    expect(setThemeSpy.mock.calls.map((c) => c[0])).toEqual([
      "dark",
      "system",
      "light",
    ]);
  });

  it("aria-label reflects each of the three states", () => {
    themeState.theme = "dark";
    const { rerender } = render(<ThemeToggle />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe(
      "Switch theme: currently dark",
    );

    themeState.theme = "system";
    rerender(<ThemeToggle />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe(
      "Switch theme: currently system",
    );

    themeState.theme = "light";
    rerender(<ThemeToggle />);
    expect(screen.getByRole("button").getAttribute("aria-label")).toBe(
      "Switch theme: currently light",
    );
  });
});

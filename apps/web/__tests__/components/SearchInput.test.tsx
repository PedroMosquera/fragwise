import {
  render,
  screen,
  fireEvent,
  act,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SearchInput } from "@/components/site/SearchInput";

// Mock next/navigation so we can spy on router.replace and feed
// pathname/searchParams into the component.
const replaceSpy = vi.fn();

vi.mock("next/navigation", () => ({
  usePathname: () => "/brands",
  useRouter: () => ({ replace: replaceSpy }),
  useSearchParams: () => new URLSearchParams(""),
}));

describe("SearchInput", () => {
  beforeEach(() => {
    replaceSpy.mockClear();
    vi.useFakeTimers();
  });

  it("debounces URL replace 300ms after typing", () => {
    render(<SearchInput placeholder="Search…" />);
    const input = screen.getByPlaceholderText("Search…");
    fireEvent.change(input, { target: { value: "cha" } });
    // Before 300ms elapses, no router.replace yet.
    expect(replaceSpy).not.toHaveBeenCalled();
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(replaceSpy).toHaveBeenCalledTimes(1);
    const url = replaceSpy.mock.calls[0][0] as string;
    expect(url).toContain("q=cha");
  });

  it("clears the q param when the input is emptied", () => {
    render(<SearchInput placeholder="Search…" />);
    const input = screen.getByPlaceholderText("Search…");
    fireEvent.change(input, { target: { value: "x" } });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    fireEvent.change(input, { target: { value: "" } });
    act(() => {
      vi.advanceTimersByTime(300);
    });
    const lastCall = replaceSpy.mock.calls[
      replaceSpy.mock.calls.length - 1
    ][0] as string;
    expect(lastCall).not.toContain("q=");
  });
});

/**
 * SearchInput Tests
 *
 * TDD tests for debounced search input component.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  act,
  cleanup,
} from "@testing-library/react";
import { SearchInput } from "./SearchInput";

describe("SearchInput", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  describe("Component Structure", () => {
    it("should render search input", () => {
      render(<SearchInput value="" onChange={vi.fn()} />);
      expect(screen.getByRole("searchbox")).toBeInTheDocument();
    });

    it("should render search icon", () => {
      render(<SearchInput value="" onChange={vi.fn()} />);
      expect(screen.getByTestId("search-icon")).toBeInTheDocument();
    });

    it("should display placeholder text", () => {
      render(
        <SearchInput
          value=""
          onChange={vi.fn()}
          placeholder="Search items..."
        />,
      );
      expect(
        screen.getByPlaceholderText("Search items..."),
      ).toBeInTheDocument();
    });

    it("should use default placeholder when none provided", () => {
      render(<SearchInput value="" onChange={vi.fn()} />);
      expect(screen.getByPlaceholderText("Search...")).toBeInTheDocument();
    });
  });

  describe("Value Handling", () => {
    it("should display current value", () => {
      render(<SearchInput value="test query" onChange={vi.fn()} />);
      expect(screen.getByRole("searchbox")).toHaveValue("test query");
    });

    it("should update input when value prop changes", () => {
      const { rerender } = render(
        <SearchInput value="initial" onChange={vi.fn()} />,
      );
      expect(screen.getByRole("searchbox")).toHaveValue("initial");

      rerender(<SearchInput value="updated" onChange={vi.fn()} />);
      expect(screen.getByRole("searchbox")).toHaveValue("updated");
    });
  });

  describe("Debounced onChange", () => {
    it("should not call onChange immediately on input", () => {
      const onChange = vi.fn();
      render(<SearchInput value="" onChange={onChange} />);

      fireEvent.change(screen.getByRole("searchbox"), {
        target: { value: "test" },
      });

      expect(onChange).not.toHaveBeenCalled();
    });

    it("should call onChange after debounce delay", async () => {
      const onChange = vi.fn();
      render(<SearchInput value="" onChange={onChange} debounceMs={300} />);

      fireEvent.change(screen.getByRole("searchbox"), {
        target: { value: "test" },
      });

      expect(onChange).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(300);
      });

      expect(onChange).toHaveBeenCalledWith("test");
    });

    it("should use default debounce of 300ms", async () => {
      const onChange = vi.fn();
      render(<SearchInput value="" onChange={onChange} />);

      fireEvent.change(screen.getByRole("searchbox"), {
        target: { value: "test" },
      });

      act(() => {
        vi.advanceTimersByTime(299);
      });
      expect(onChange).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(1);
      });
      expect(onChange).toHaveBeenCalledWith("test");
    });

    it("should reset debounce timer on subsequent inputs", async () => {
      const onChange = vi.fn();
      render(<SearchInput value="" onChange={onChange} debounceMs={300} />);

      fireEvent.change(screen.getByRole("searchbox"), {
        target: { value: "te" },
      });

      act(() => {
        vi.advanceTimersByTime(200);
      });

      fireEvent.change(screen.getByRole("searchbox"), {
        target: { value: "test" },
      });

      act(() => {
        vi.advanceTimersByTime(200);
      });
      expect(onChange).not.toHaveBeenCalled();

      act(() => {
        vi.advanceTimersByTime(100);
      });
      expect(onChange).toHaveBeenCalledWith("test");
      expect(onChange).toHaveBeenCalledTimes(1);
    });
  });

  describe("Clear Button", () => {
    it("should not show clear button when input is empty", () => {
      render(<SearchInput value="" onChange={vi.fn()} />);
      expect(
        screen.queryByRole("button", { name: /clear/i }),
      ).not.toBeInTheDocument();
    });

    it("should show clear button when input has value", () => {
      render(<SearchInput value="test" onChange={vi.fn()} />);
      expect(
        screen.getByRole("button", { name: /clear/i }),
      ).toBeInTheDocument();
    });

    it("should call onChange with empty string when clear clicked", () => {
      const onChange = vi.fn();
      render(<SearchInput value="test" onChange={onChange} />);

      fireEvent.click(screen.getByRole("button", { name: /clear/i }));

      // Clear should be immediate, not debounced
      expect(onChange).toHaveBeenCalledWith("");
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(<SearchInput value="" onChange={vi.fn()} isLoading={true} />);
      expect(screen.getByTestId("search-loading")).toBeInTheDocument();
    });

    it("should hide search icon when loading", () => {
      render(<SearchInput value="" onChange={vi.fn()} isLoading={true} />);
      expect(screen.queryByTestId("search-icon")).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have correct input type", () => {
      render(<SearchInput value="" onChange={vi.fn()} />);
      expect(screen.getByRole("searchbox")).toHaveAttribute("type", "search");
    });
  });
});

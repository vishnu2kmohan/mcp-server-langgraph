/**
 * FilterChips Component Tests
 *
 * Tests for the FilterChips component that provides
 * clickable filter chips for enum-based filtering.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { FilterChips } from "./FilterChips";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("FilterChips", () => {
  const defaultOptions = [
    { value: "active", label: "Active", color: "green" },
    { value: "archived", label: "Archived", color: "gray" },
  ];

  it("renders all filter options", () => {
    render(
      <FilterChips options={defaultOptions} value={null} onChange={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: /active/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /archived/i }),
    ).toBeInTheDocument();
  });

  it("highlights the selected option", () => {
    render(
      <FilterChips
        options={defaultOptions}
        value="active"
        onChange={vi.fn()}
      />,
    );

    const activeButton = screen.getByRole("button", { name: /active/i });
    expect(activeButton).toHaveAttribute("aria-pressed", "true");
  });

  it("calls onChange with value when clicking an unselected option", () => {
    const handleChange = vi.fn();
    render(
      <FilterChips
        options={defaultOptions}
        value={null}
        onChange={handleChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /active/i }));
    expect(handleChange).toHaveBeenCalledWith("active");
  });

  it("calls onChange with null when clicking the already selected option (toggle off)", () => {
    const handleChange = vi.fn();
    render(
      <FilterChips
        options={defaultOptions}
        value="active"
        onChange={handleChange}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /active/i }));
    expect(handleChange).toHaveBeenCalledWith(null);
  });

  it("renders options without colors", () => {
    const options = [
      { value: "pending", label: "Pending" },
      { value: "completed", label: "Completed" },
    ];

    render(<FilterChips options={options} value={null} onChange={vi.fn()} />);

    expect(
      screen.getByRole("button", { name: /pending/i }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /completed/i }),
    ).toBeInTheDocument();
  });

  it("applies custom className", () => {
    const { container } = render(
      <FilterChips
        options={defaultOptions}
        value={null}
        onChange={vi.fn()}
        className="custom-class"
      />,
    );

    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("has proper accessibility attributes", () => {
    render(
      <FilterChips
        options={defaultOptions}
        value="active"
        onChange={vi.fn()}
        ariaLabel="Filter by status"
      />,
    );

    const group = screen.getByRole("group", { name: /filter by status/i });
    expect(group).toBeInTheDocument();
  });
});

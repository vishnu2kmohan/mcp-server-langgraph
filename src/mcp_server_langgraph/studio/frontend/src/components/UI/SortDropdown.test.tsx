/**
 * SortDropdown Tests
 *
 * TDD tests for sort dropdown component with field and order selection.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { SortDropdown } from "./SortDropdown";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

const mockOptions = [
  { value: "name", label: "Name" },
  { value: "created_at", label: "Date Created" },
  { value: "updated_at", label: "Last Updated" },
];

describe("SortDropdown", () => {
  describe("Component Structure", () => {
    it("should render sort dropdown container", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("sort-dropdown")).toBeInTheDocument();
    });

    it("should render field select", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("combobox", { name: /sort by/i }),
      ).toBeInTheDocument();
    });

    it("should render order toggle button", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /sort order/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Field Selection", () => {
    it("should display all options", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );

      const select = screen.getByRole("combobox", { name: /sort by/i });
      expect(select).toContainHTML("Name");
      expect(select).toContainHTML("Date Created");
      expect(select).toContainHTML("Last Updated");
    });

    it("should have correct option selected", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="created_at"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("combobox", { name: /sort by/i })).toHaveValue(
        "created_at",
      );
    });

    it("should call onChange with new sortBy when field changes", () => {
      const onChange = vi.fn();
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={onChange}
          />
        </TestProvider>,
      );

      fireEvent.change(screen.getByRole("combobox", { name: /sort by/i }), {
        target: { value: "created_at" },
      });

      expect(onChange).toHaveBeenCalledWith("created_at", "asc");
    });
  });

  describe("Sort Order Toggle", () => {
    it("should show ascending indicator when sortOrder is asc", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sort-asc-icon")).toBeInTheDocument();
    });

    it("should show descending indicator when sortOrder is desc", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="desc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sort-desc-icon")).toBeInTheDocument();
    });

    it("should toggle order from asc to desc when clicked", () => {
      const onChange = vi.fn();
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={onChange}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /sort order/i }));

      expect(onChange).toHaveBeenCalledWith("name", "desc");
    });

    it("should toggle order from desc to asc when clicked", () => {
      const onChange = vi.fn();
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="desc"
            options={mockOptions}
            onChange={onChange}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /sort order/i }));

      expect(onChange).toHaveBeenCalledWith("name", "asc");
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria labels", () => {
      render(
        <TestProvider>
          <SortDropdown
            sortBy="name"
            sortOrder="asc"
            options={mockOptions}
            onChange={vi.fn()}
          />
        </TestProvider>,
      );

      expect(
        screen.getByRole("combobox", { name: /sort by/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /sort order/i }),
      ).toBeInTheDocument();
    });
  });
});

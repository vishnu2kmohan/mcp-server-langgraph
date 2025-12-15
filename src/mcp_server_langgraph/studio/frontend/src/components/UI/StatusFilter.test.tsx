/**
 * StatusFilter Tests
 *
 * TDD tests for status filter component with multi-select capability.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { StatusFilter } from "./StatusFilter";

const mockOptions = [
  { value: "active", label: "Active" },
  { value: "pending", label: "Pending" },
  { value: "completed", label: "Completed" },
  { value: "archived", label: "Archived" },
];

describe("StatusFilter", () => {
  describe("Component Structure", () => {
    it("should render status filter container", () => {
      render(
        <StatusFilter value={null} options={mockOptions} onChange={vi.fn()} />,
      );
      expect(screen.getByTestId("status-filter")).toBeInTheDocument();
    });

    it("should render status select", () => {
      render(
        <StatusFilter value={null} options={mockOptions} onChange={vi.fn()} />,
      );
      expect(
        screen.getByRole("combobox", { name: /status/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Option Selection", () => {
    it('should display all options including "All" option', () => {
      render(
        <StatusFilter value={null} options={mockOptions} onChange={vi.fn()} />,
      );

      const select = screen.getByRole("combobox", { name: /status/i });
      expect(select).toContainHTML("All");
      expect(select).toContainHTML("Active");
      expect(select).toContainHTML("Pending");
      expect(select).toContainHTML("Completed");
      expect(select).toContainHTML("Archived");
    });

    it('should show "All" as selected when value is null', () => {
      render(
        <StatusFilter value={null} options={mockOptions} onChange={vi.fn()} />,
      );

      expect(screen.getByRole("combobox", { name: /status/i })).toHaveValue("");
    });

    it("should show correct option selected", () => {
      render(
        <StatusFilter
          value="active"
          options={mockOptions}
          onChange={vi.fn()}
        />,
      );

      expect(screen.getByRole("combobox", { name: /status/i })).toHaveValue(
        "active",
      );
    });

    it("should call onChange with selected value", () => {
      const onChange = vi.fn();
      render(
        <StatusFilter value={null} options={mockOptions} onChange={onChange} />,
      );

      fireEvent.change(screen.getByRole("combobox", { name: /status/i }), {
        target: { value: "active" },
      });

      expect(onChange).toHaveBeenCalledWith("active");
    });

    it('should call onChange with null when "All" selected', () => {
      const onChange = vi.fn();
      render(
        <StatusFilter
          value="active"
          options={mockOptions}
          onChange={onChange}
        />,
      );

      fireEvent.change(screen.getByRole("combobox", { name: /status/i }), {
        target: { value: "" },
      });

      expect(onChange).toHaveBeenCalledWith(null);
    });
  });

  describe("Customization", () => {
    it('should use custom "All" label when provided', () => {
      render(
        <StatusFilter
          value={null}
          options={mockOptions}
          onChange={vi.fn()}
          allLabel="Any Status"
        />,
      );

      const select = screen.getByRole("combobox", { name: /status/i });
      expect(select).toContainHTML("Any Status");
    });

    it("should use custom aria label when provided", () => {
      render(
        <StatusFilter
          value={null}
          options={mockOptions}
          onChange={vi.fn()}
          ariaLabel="Filter by status"
        />,
      );

      expect(
        screen.getByRole("combobox", { name: /filter by status/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have default aria label", () => {
      render(
        <StatusFilter value={null} options={mockOptions} onChange={vi.fn()} />,
      );

      expect(
        screen.getByRole("combobox", { name: /status/i }),
      ).toBeInTheDocument();
    });
  });
});

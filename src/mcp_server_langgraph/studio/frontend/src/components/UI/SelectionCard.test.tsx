/**
 * SelectionCard Component Tests
 *
 * Tests for the reusable selection card component that provides
 * consistent styling across wizard steps, template selectors, and
 * option lists.
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FileCode, Bot, Shield } from "lucide-react";
import { SelectionCard } from "./SelectionCard";

describe("SelectionCard", () => {
  describe("rendering", () => {
    it("renders with title and description", () => {
      render(
        <SelectionCard
          title="Test Option"
          description="This is a test description"
          icon={<FileCode data-testid="icon" />}
          onClick={() => {}}
        />
      );

      expect(screen.getByText("Test Option")).toBeInTheDocument();
      expect(
        screen.getByText("This is a test description")
      ).toBeInTheDocument();
      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });

    it("renders with only title when description is omitted", () => {
      render(
        <SelectionCard
          title="Title Only"
          icon={<Bot data-testid="icon" />}
          onClick={() => {}}
        />
      );

      expect(screen.getByText("Title Only")).toBeInTheDocument();
      expect(screen.getByTestId("icon")).toBeInTheDocument();
    });

    it("renders badge when provided", () => {
      render(
        <SelectionCard
          title="With Badge"
          description="Has a badge"
          icon={<Shield />}
          badge="Recommended"
          onClick={() => {}}
        />
      );

      expect(screen.getByText("Recommended")).toBeInTheDocument();
    });
  });

  describe("selection state", () => {
    it("applies selected styling when selected is true", () => {
      render(
        <SelectionCard
          title="Selected Option"
          description="This is selected"
          icon={<FileCode />}
          selected={true}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-pressed", "true");
      expect(button.className).toContain("border-primary-7");
      expect(button.className).toContain("bg-primary-3");
    });

    it("applies unselected styling when selected is false", () => {
      render(
        <SelectionCard
          title="Unselected Option"
          description="This is not selected"
          icon={<FileCode />}
          selected={false}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-pressed", "false");
      expect(button.className).toContain("border-neutral-6");
      expect(button.className).toContain("bg-neutral-3");
    });

    it("defaults to unselected when selected prop is omitted", () => {
      render(
        <SelectionCard
          title="Default State"
          description="No selected prop"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button).toHaveAttribute("aria-pressed", "false");
    });
  });

  describe("interaction", () => {
    it("calls onClick when clicked", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(
        <SelectionCard
          title="Clickable"
          description="Click me"
          icon={<FileCode />}
          onClick={handleClick}
        />
      );

      await user.click(screen.getByRole("button"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("calls onClick with value when provided", async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(
        <SelectionCard
          title="With Value"
          description="Has a value"
          icon={<FileCode />}
          value="test-value"
          onClick={handleClick}
        />
      );

      await user.click(screen.getByRole("button"));
      expect(handleClick).toHaveBeenCalledWith("test-value");
    });
  });

  describe("accessibility", () => {
    it("has accessible button role", () => {
      render(
        <SelectionCard
          title="Accessible"
          description="Screen reader friendly"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      expect(screen.getByRole("button")).toBeInTheDocument();
    });

    it("uses aria-label when provided", () => {
      render(
        <SelectionCard
          title="Custom Label"
          description="Has aria-label"
          icon={<FileCode />}
          ariaLabel="Select custom option"
          onClick={() => {}}
        />
      );

      expect(screen.getByLabelText("Select custom option")).toBeInTheDocument();
    });

    it("uses title as accessible name by default", () => {
      render(
        <SelectionCard
          title="Default Label"
          description="Uses title"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      expect(
        screen.getByRole("button", { name: /Default Label/i })
      ).toBeInTheDocument();
    });
  });

  describe("icon container styling", () => {
    it("applies selected icon styling when selected", () => {
      const { container } = render(
        <SelectionCard
          title="Selected Icon"
          description="Icon styling test"
          icon={<FileCode data-testid="icon" />}
          selected={true}
          onClick={() => {}}
        />
      );

      const iconContainer = container.querySelector(
        ".bg-primary-4.text-primary-11"
      );
      expect(iconContainer).toBeInTheDocument();
    });

    it("applies unselected icon styling when not selected", () => {
      const { container } = render(
        <SelectionCard
          title="Unselected Icon"
          description="Icon styling test"
          icon={<FileCode data-testid="icon" />}
          selected={false}
          onClick={() => {}}
        />
      );

      const iconContainer = container.querySelector(
        ".bg-neutral-4.text-neutral-11"
      );
      expect(iconContainer).toBeInTheDocument();
    });
  });

  describe("consistent dimensions", () => {
    it("has consistent padding (p-4)", () => {
      render(
        <SelectionCard
          title="Padding Test"
          description="Consistent padding"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button.className).toContain("p-4");
    });

    it("has consistent gap (gap-3)", () => {
      render(
        <SelectionCard
          title="Gap Test"
          description="Consistent gap"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button.className).toContain("gap-3");
    });

    it("has consistent border width (border-2)", () => {
      render(
        <SelectionCard
          title="Border Test"
          description="Consistent border"
          icon={<FileCode />}
          onClick={() => {}}
        />
      );

      const button = screen.getByRole("button");
      expect(button.className).toContain("border-2");
    });
  });
});

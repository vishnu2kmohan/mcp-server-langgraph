/**
 * Tests for ReferenceAutocompleteMenu component
 *
 * TDD: Tests written first per project guidelines.
 * WCAG 2.2 AA accessibility verified.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { ReferenceAutocompleteMenu } from "./ReferenceAutocompleteMenu";
import type { ReferenceSuggestion } from "@/hooks/useReferenceAutocomplete";

import { TestProvider } from "@/test-utils";

// Test fixtures
const typeSuggestions: ReferenceSuggestion[] = [
  {
    value: "tool",
    label: "Tool",
    description: "Reference an MCP tool",
    type: "type",
  },
  {
    value: "skill",
    label: "Skill",
    description: "Reference a skill",
    type: "type",
  },
  {
    value: "artifact",
    label: "Artifact",
    description: "Reference an artifact",
    type: "type",
  },
];

const toolSuggestions: ReferenceSuggestion[] = [
  {
    value: "filesystem:read_file",
    label: "read_file",
    description: "Read a file",
    type: "tool",
    isComplete: true,
  },
  {
    value: "filesystem:write_file",
    label: "write_file",
    description: "Write a file",
    type: "tool",
    isComplete: true,
  },
  {
    value: "database:query",
    label: "query",
    description: "Run SQL query",
    type: "tool",
    isComplete: true,
  },
];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ReferenceAutocompleteMenu", () => {
  describe("rendering", () => {
    it("should render nothing when closed", () => {
      const { container } = render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={false}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should render nothing when no suggestions", () => {
      const { container } = render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={[]}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(container.firstChild).toBeNull();
    });

    it("should render listbox when open with suggestions", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should display all suggestions", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Tool")).toBeInTheDocument();
      expect(screen.getByText("Skill")).toBeInTheDocument();
      expect(screen.getByText("Artifact")).toBeInTheDocument();
    });

    it("should display descriptions", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Reference an MCP tool")).toBeInTheDocument();
    });

    it("should highlight selected suggestion", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={1}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      const options = screen.getAllByRole("option");
      expect(options[1]).toHaveAttribute("aria-selected", "true");
      expect(options[0]).toHaveAttribute("aria-selected", "false");
    });
  });

  describe("keyboard navigation", () => {
    it("should call onSelectedIndexChange on ArrowDown", () => {
      const onSelectedIndexChange = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={onSelectedIndexChange}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "ArrowDown" });
      expect(onSelectedIndexChange).toHaveBeenCalledWith(1);
    });

    it("should call onSelectedIndexChange on ArrowUp", () => {
      const onSelectedIndexChange = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={2}
            onSelectedIndexChange={onSelectedIndexChange}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "ArrowUp" });
      expect(onSelectedIndexChange).toHaveBeenCalledWith(1);
    });

    it("should not go below 0 on ArrowUp at start", () => {
      const onSelectedIndexChange = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={onSelectedIndexChange}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "ArrowUp" });
      expect(onSelectedIndexChange).toHaveBeenCalledWith(0);
    });

    it("should not exceed max on ArrowDown at end", () => {
      const onSelectedIndexChange = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={2}
            onSelectedIndexChange={onSelectedIndexChange}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "ArrowDown" });
      expect(onSelectedIndexChange).toHaveBeenCalledWith(2);
    });

    it("should call onSelect on Enter", () => {
      const onSelect = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={1}
            onSelectedIndexChange={() => {}}
            onSelect={onSelect}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "Enter" });
      expect(onSelect).toHaveBeenCalledWith(typeSuggestions[1]);
    });

    it("should call onClose on Escape", () => {
      const onClose = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={onClose}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "Escape" });
      expect(onClose).toHaveBeenCalled();
    });

    it("should call onClose on Tab", () => {
      const onClose = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={onClose}
          />
        </TestProvider>,
      );

      fireEvent.keyDown(screen.getByRole("listbox"), { key: "Tab" });
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("mouse interaction", () => {
    it("should call onSelect when suggestion is clicked", () => {
      const onSelect = vi.fn();

      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={toolSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={onSelect}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByText("write_file"));
      expect(onSelect).toHaveBeenCalledWith(toolSuggestions[1]);
    });
  });

  describe("accessibility", () => {
    it("should have listbox role", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have aria-label", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("listbox")).toHaveAttribute(
        "aria-label",
        "Reference suggestions",
      );
    });

    it("should have option role on each suggestion", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      const options = screen.getAllByRole("option");
      expect(options).toHaveLength(3);
    });

    it("should have unique ids for each option", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      const options = screen.getAllByRole("option");
      const ids = options.map((o) => o.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(options.length);
    });

    it("should show keyboard hints in footer", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={typeSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      // Check for the footer with keyboard hints using partial text matching
      expect(screen.getByText(/navigate/)).toBeInTheDocument();
      expect(screen.getByText(/select/)).toBeInTheDocument();
      expect(screen.getByText(/close/)).toBeInTheDocument();
    });
  });

  describe("icons", () => {
    it("should render correct icon for tool suggestions", () => {
      render(
        <TestProvider>
          <ReferenceAutocompleteMenu
            isOpen={true}
            suggestions={toolSuggestions}
            selectedIndex={0}
            onSelectedIndexChange={() => {}}
            onSelect={() => {}}
            onClose={() => {}}
          />
        </TestProvider>,
      );

      // Lucide icons are SVGs, check they're rendered
      const options = screen.getAllByRole("option");
      expect(options[0].querySelector("svg")).toBeInTheDocument();
    });
  });
});

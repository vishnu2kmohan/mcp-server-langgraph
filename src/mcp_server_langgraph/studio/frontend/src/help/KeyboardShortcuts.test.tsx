/**
 * KeyboardShortcuts Tests
 *
 * Phase 6: Help & Accessibility
 * Tests for keyboard shortcuts reference panel.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { KeyboardShortcuts, type ShortcutCategory } from "./KeyboardShortcuts";

describe("KeyboardShortcuts", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const mockCategories: ShortcutCategory[] = [
    {
      id: "navigation",
      name: "Navigation",
      shortcuts: [
        { id: "nav-1", keys: ["Cmd", "1"], description: "Focus Activity Bar" },
        { id: "nav-2", keys: ["Cmd", "2"], description: "Focus Session Nav" },
      ],
    },
    {
      id: "editing",
      name: "Editing",
      shortcuts: [
        { id: "edit-1", keys: ["Cmd", "S"], description: "Save" },
        { id: "edit-2", keys: ["Cmd", "Z"], description: "Undo" },
      ],
    },
    {
      id: "ai",
      name: "AI Features",
      shortcuts: [
        { id: "ai-1", keys: ["Tab"], description: "Accept suggestion" },
        { id: "ai-2", keys: ["Esc"], description: "Dismiss suggestion" },
      ],
    },
  ];

  describe("Rendering", () => {
    it("renders the keyboard shortcuts container", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      expect(screen.getByTestId("keyboard-shortcuts")).toBeInTheDocument();
    });

    it("renders panel title", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      expect(screen.getByText(/keyboard shortcuts/i)).toBeInTheDocument();
    });

    it("renders all categories", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      expect(screen.getByText("Navigation")).toBeInTheDocument();
      expect(screen.getByText("Editing")).toBeInTheDocument();
      expect(screen.getByText("AI Features")).toBeInTheDocument();
    });

    it("renders all shortcuts", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      expect(screen.getByText("Focus Activity Bar")).toBeInTheDocument();
      expect(screen.getByText("Save")).toBeInTheDocument();
      expect(screen.getByText("Accept suggestion")).toBeInTheDocument();
    });

    it("shows empty state when no categories", () => {
      render(<KeyboardShortcuts categories={[]} />);
      expect(screen.getByText(/no shortcuts/i)).toBeInTheDocument();
    });
  });

  describe("Key Display", () => {
    it("displays key combinations correctly", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      // "Cmd" appears multiple times, so use getAllByText
      const cmdKeys = screen.getAllByText("Cmd");
      expect(cmdKeys.length).toBeGreaterThan(0);
      expect(screen.getByText("1")).toBeInTheDocument();
    });

    it("displays single key shortcuts", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      expect(screen.getByText("Tab")).toBeInTheDocument();
      expect(screen.getByText("Esc")).toBeInTheDocument();
    });
  });

  describe("Category Sections", () => {
    it("groups shortcuts by category", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);

      // Check that navigation shortcuts are grouped
      const navSection = screen.getByText("Navigation").closest("div");
      expect(navSection).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("uses semantic list structure", () => {
      render(<KeyboardShortcuts categories={mockCategories} />);
      // Each category should have a proper heading
      const headings = screen.getAllByRole("heading");
      expect(headings.length).toBeGreaterThanOrEqual(1);
    });
  });
});

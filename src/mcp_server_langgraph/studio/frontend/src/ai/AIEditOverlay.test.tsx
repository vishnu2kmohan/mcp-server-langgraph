/**
 * AIEditOverlay Tests - Phase 2
 *
 * Tests for inline AI edit overlay in the canvas.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AIEditOverlay } from "./AIEditOverlay";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Data
// =============================================================================

const mockSelection = {
  start: { line: 5, column: 0 },
  end: { line: 10, column: 20 },
  content: "function oldCode() {\n  return 'old';\n}",
};

const mockEditResult = {
  newContent: "function newCode() {\n  return 'new';\n}",
  diff: [
    { type: "remove" as const, content: "function oldCode() {" },
    { type: "add" as const, content: "function newCode() {" },
    { type: "same" as const, content: "  return " },
    { type: "remove" as const, content: "'old'" },
    { type: "add" as const, content: "'new'" },
    { type: "same" as const, content: ";\n}" },
  ],
};

// =============================================================================
// Tests
// =============================================================================

describe("AIEditOverlay", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render overlay when visible", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("ai-edit-overlay")).toBeInTheDocument();
    });

    it("should not render when not visible", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible={false}
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.queryByTestId("ai-edit-overlay")).not.toBeInTheDocument();
    });

    it("should display instruction input", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("instruction-input")).toBeInTheDocument();
    });

    it("should show selected code preview", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("selection-preview")).toBeInTheDocument();
    });
  });

  describe("Instruction Input", () => {
    it("should update instruction on input", async () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      const input = screen.getByTestId("instruction-input");
      await userEvent.type(input, "make this function async");
      expect(input).toHaveValue("make this function async");
    });

    it("should have placeholder text", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText(/describe the change/i),
      ).toBeInTheDocument();
    });
  });

  describe("Edit Request", () => {
    it("should call onRequestEdit when submit clicked", async () => {
      const onRequestEdit = vi.fn().mockResolvedValue(mockEditResult);
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            onRequestEdit={onRequestEdit}
          />
        </TestProvider>,
      );

      const input = screen.getByTestId("instruction-input");
      await userEvent.type(input, "make it better");
      fireEvent.click(screen.getByTestId("submit-edit"));

      await waitFor(() => {
        expect(onRequestEdit).toHaveBeenCalledWith({
          selection: mockSelection,
          instruction: "make it better",
        });
      });
    });

    it("should show loading state while processing", async () => {
      const onRequestEdit = vi
        .fn()
        .mockImplementation(
          () =>
            new Promise((resolve) =>
              setTimeout(() => resolve(mockEditResult), 1000),
            ),
        );

      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            onRequestEdit={onRequestEdit}
          />
        </TestProvider>,
      );

      const input = screen.getByTestId("instruction-input");
      await userEvent.type(input, "make it better");
      fireEvent.click(screen.getByTestId("submit-edit"));

      await waitFor(() => {
        expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
      });
    });
  });

  describe("Diff Preview", () => {
    it("should show diff preview after edit request", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            editResult={mockEditResult}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("diff-preview")).toBeInTheDocument();
    });

    it("should highlight added lines", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            editResult={mockEditResult}
          />
        </TestProvider>,
      );
      const addedLines = screen.getAllByTestId("diff-add");
      expect(addedLines.length).toBeGreaterThan(0);
    });

    it("should highlight removed lines", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            editResult={mockEditResult}
          />
        </TestProvider>,
      );
      const removedLines = screen.getAllByTestId("diff-remove");
      expect(removedLines.length).toBeGreaterThan(0);
    });
  });

  describe("Actions", () => {
    it("should call onApply when apply clicked", () => {
      const onApply = vi.fn();
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={onApply}
            onCancel={() => {}}
            editResult={mockEditResult}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("apply-edit"));
      expect(onApply).toHaveBeenCalledWith(mockEditResult.newContent);
    });

    it("should call onCancel when cancel clicked", () => {
      const onCancel = vi.fn();
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={onCancel}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("cancel-edit"));
      expect(onCancel).toHaveBeenCalled();
    });

    it("should close overlay on Escape", () => {
      const onCancel = vi.fn();
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={onCancel}
          />
        </TestProvider>,
      );
      fireEvent.keyDown(screen.getByTestId("ai-edit-overlay"), {
        key: "Escape",
      });
      expect(onCancel).toHaveBeenCalled();
    });
  });

  describe("Regenerate", () => {
    it("should show regenerate button after first result", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            editResult={mockEditResult}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("regenerate-button")).toBeInTheDocument();
    });

    it("should call onRequestEdit again when regenerate clicked", async () => {
      const onRequestEdit = vi.fn().mockResolvedValue(mockEditResult);
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            onRequestEdit={onRequestEdit}
          />
        </TestProvider>,
      );

      // First, type an instruction and submit to get a result
      const input = screen.getByTestId("instruction-input");
      await userEvent.type(input, "make it better");
      fireEvent.click(screen.getByTestId("submit-edit"));

      await waitFor(() => {
        expect(screen.getByTestId("diff-preview")).toBeInTheDocument();
      });

      // Now click regenerate
      fireEvent.click(screen.getByTestId("regenerate-button"));

      await waitFor(() => {
        expect(onRequestEdit).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error message on failure", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            error="Failed to generate edit"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Failed to generate edit")).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
            error="Failed to generate edit"
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have dialog role", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should focus instruction input when opened", () => {
      render(
        <TestProvider>
          <AIEditOverlay
            selection={mockSelection}
            isVisible
            onApply={() => {}}
            onCancel={() => {}}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("instruction-input")).toHaveFocus();
    });
  });
});

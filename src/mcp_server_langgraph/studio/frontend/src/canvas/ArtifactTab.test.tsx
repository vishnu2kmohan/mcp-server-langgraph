/**
 * ArtifactTab Component Tests
 *
 * TDD: Tests written first to define expected behavior
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ArtifactTab } from "./ArtifactTab";
import type { CanvasArtifact } from "../types/artifacts";

// Mock @dnd-kit/sortable
vi.mock("@dnd-kit/sortable", () => ({
  useSortable: vi.fn(() => ({
    attributes: { role: "button" },
    listeners: { onPointerDown: vi.fn() },
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));

// Mock @dnd-kit/utilities
vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: vi.fn(() => ""),
    },
  },
}));

const mockArtifact: CanvasArtifact = {
  id: "artifact-1",
  type: "code",
  title: "Test Artifact",
  sessionId: "session-1",
  version: 1,
  content: "console.log('hello');",
  contentType: "code",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  editMetadata: {
    origin: "ai",
    modified: false,
    lastEditedBy: "ai",
  },
};

describe("ArtifactTab", () => {
  const defaultProps = {
    artifact: mockArtifact,
    isSelected: false,
    onSelect: vi.fn(),
    onClose: vi.fn(),
    onRename: vi.fn(),
    onDuplicate: vi.fn(),
    onExport: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render artifact title", () => {
      render(<ArtifactTab {...defaultProps} />);
      expect(screen.getByText("Test Artifact")).toBeInTheDocument();
    });

    it("should render 'Untitled' when title is not provided", () => {
      const artifact = { ...mockArtifact, title: undefined };
      render(<ArtifactTab {...defaultProps} artifact={artifact} />);
      expect(screen.getByText("Untitled")).toBeInTheDocument();
    });

    it("should have correct aria role and selected state", () => {
      render(<ArtifactTab {...defaultProps} isSelected={true} />);
      const tab = screen.getByRole("tab");
      expect(tab).toHaveAttribute("aria-selected", "true");
    });

    it("should show close button on hover", () => {
      render(<ArtifactTab {...defaultProps} />);
      // Close button should exist but be hidden initially (controlled via CSS)
      const closeButton = screen.getByLabelText(/close test artifact/i);
      expect(closeButton).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    it("should call onSelect when clicked", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      await user.click(screen.getByRole("tab"));
      expect(defaultProps.onSelect).toHaveBeenCalledTimes(1);
    });

    it("should have tabIndex 0 when selected", () => {
      render(<ArtifactTab {...defaultProps} isSelected={true} />);
      expect(screen.getByRole("tab")).toHaveAttribute("tabIndex", "0");
    });

    it("should have tabIndex -1 when not selected", () => {
      render(<ArtifactTab {...defaultProps} isSelected={false} />);
      expect(screen.getByRole("tab")).toHaveAttribute("tabIndex", "-1");
    });
  });

  describe("close button", () => {
    it("should call onClose when close button is clicked", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      const closeButton = screen.getByLabelText(/close test artifact/i);
      await user.click(closeButton);

      expect(defaultProps.onClose).toHaveBeenCalledTimes(1);
      expect(defaultProps.onSelect).not.toHaveBeenCalled();
    });

    it("should stop propagation when close button is clicked", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      const closeButton = screen.getByLabelText(/close test artifact/i);
      await user.click(closeButton);

      // onSelect should NOT be called (propagation stopped)
      expect(defaultProps.onSelect).not.toHaveBeenCalled();
    });
  });

  describe("inline rename", () => {
    it("should enter rename mode on double click", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      const tab = screen.getByRole("tab");
      await user.dblClick(tab);

      // Should show input field for renaming
      expect(screen.getByRole("textbox")).toBeInTheDocument();
    });

    it("should call onRename when rename is confirmed", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      const tab = screen.getByRole("tab");
      await user.dblClick(tab);

      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "New Title{Enter}");

      expect(defaultProps.onRename).toHaveBeenCalledWith("New Title");
    });

    it("should exit rename mode on Escape without calling onRename", async () => {
      const user = userEvent.setup();
      render(<ArtifactTab {...defaultProps} />);

      const tab = screen.getByRole("tab");
      await user.dblClick(tab);

      const input = screen.getByRole("textbox");
      await user.type(input, "New Title{Escape}");

      expect(defaultProps.onRename).not.toHaveBeenCalled();
      expect(screen.queryByRole("textbox")).not.toBeInTheDocument();
    });
  });

  describe("attribution indicator", () => {
    it("should show insight-colored dot for AI-generated artifacts", () => {
      const artifact: CanvasArtifact = {
        ...mockArtifact,
        editMetadata: {
          origin: "ai",
          modified: false,
          lastEditedBy: "ai",
        },
      };
      render(<ArtifactTab {...defaultProps} artifact={artifact} />);
      expect(screen.getByTestId("attribution-dot")).toHaveClass("bg-insight-9");
    });

    it("should show primary-colored dot for user-modified artifacts", () => {
      const artifact: CanvasArtifact = {
        ...mockArtifact,
        editMetadata: {
          origin: "ai",
          modified: true,
          lastEditedBy: "user",
        },
      };
      render(<ArtifactTab {...defaultProps} artifact={artifact} />);
      expect(screen.getByTestId("attribution-dot")).toHaveClass("bg-primary-9");
    });

    it("should not show attribution dot for user-created artifacts", () => {
      const artifact: CanvasArtifact = {
        ...mockArtifact,
        editMetadata: {
          origin: "user",
          modified: false,
          lastEditedBy: "user",
        },
      };
      render(<ArtifactTab {...defaultProps} artifact={artifact} />);
      expect(screen.queryByTestId("attribution-dot")).not.toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should have selected styles when isSelected is true", () => {
      render(<ArtifactTab {...defaultProps} isSelected={true} />);
      const tab = screen.getByRole("tab");
      expect(tab).toHaveClass("bg-neutral-1");
      expect(tab).toHaveClass("text-neutral-12");
    });

    it("should have unselected styles when isSelected is false", () => {
      render(<ArtifactTab {...defaultProps} isSelected={false} />);
      const tab = screen.getByRole("tab");
      expect(tab).toHaveClass("bg-neutral-2");
      expect(tab).toHaveClass("text-neutral-11");
    });
  });

  describe("drag handle", () => {
    it("should have a drag handle element", () => {
      render(<ArtifactTab {...defaultProps} />);
      expect(screen.getByLabelText(/drag to reorder/i)).toBeInTheDocument();
    });
  });
});

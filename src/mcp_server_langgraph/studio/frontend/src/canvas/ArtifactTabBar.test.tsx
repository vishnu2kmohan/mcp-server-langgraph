/**
 * ArtifactTabBar Component Tests
 *
 * TDD: Tests written first to define expected behavior
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ArtifactTabBar } from "./ArtifactTabBar";
import type { CanvasArtifact } from "../types/artifacts";

// Mock @dnd-kit
vi.mock("@dnd-kit/core", () => ({
  DndContext: ({ children }: { children: React.ReactNode }) => <>{children}</>,
  closestCenter: vi.fn(),
  PointerSensor: vi.fn(),
  useSensor: vi.fn(),
  useSensors: vi.fn(() => []),
}));

vi.mock("@dnd-kit/sortable", () => ({
  SortableContext: ({ children }: { children: React.ReactNode }) => (
    <>{children}</>
  ),
  horizontalListSortingStrategy: {},
  useSortable: vi.fn(() => ({
    attributes: { role: "button" },
    listeners: { onPointerDown: vi.fn() },
    setNodeRef: vi.fn(),
    transform: null,
    transition: undefined,
    isDragging: false,
  })),
}));

vi.mock("@dnd-kit/utilities", () => ({
  CSS: {
    Transform: {
      toString: vi.fn(() => ""),
    },
  },
}));

const createMockArtifact = (
  id: string,
  title: string,
  origin: "ai" | "user" = "user",
): CanvasArtifact => ({
  id,
  type: "code",
  title,
  sessionId: "session-1",
  version: 1,
  content: "console.log('hello');",
  contentType: "code",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  editMetadata: {
    origin,
    modified: false,
    lastEditedBy: origin,
  },
});

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ArtifactTabBar", () => {
  const mockArtifacts = [
    createMockArtifact("artifact-1", "First Artifact", "ai"),
    createMockArtifact("artifact-2", "Second Artifact", "user"),
    createMockArtifact("artifact-3", "Third Artifact", "ai"),
  ];

  const defaultProps = {
    artifacts: mockArtifacts,
    tabOrder: ["artifact-1", "artifact-2", "artifact-3"],
    selectedId: "artifact-1",
    onSelect: vi.fn(),
    onClose: vi.fn(),
    onRename: vi.fn(),
    onDuplicate: vi.fn(),
    onExport: vi.fn(),
    onReorder: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render all artifacts as tabs", () => {
      render(<ArtifactTabBar {...defaultProps} />);
      expect(screen.getByText("First Artifact")).toBeInTheDocument();
      expect(screen.getByText("Second Artifact")).toBeInTheDocument();
      expect(screen.getByText("Third Artifact")).toBeInTheDocument();
    });

    it("should render tabs in tabOrder order", () => {
      const props = {
        ...defaultProps,
        tabOrder: ["artifact-3", "artifact-1", "artifact-2"],
      };
      render(<ArtifactTabBar {...props} />);
      const tabs = screen.getAllByRole("tab");
      expect(tabs[0]).toHaveTextContent("Third Artifact");
      expect(tabs[1]).toHaveTextContent("First Artifact");
      expect(tabs[2]).toHaveTextContent("Second Artifact");
    });

    it("should have tablist role on container", () => {
      render(<ArtifactTabBar {...defaultProps} />);
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    it("should have accessible label on tablist", () => {
      render(<ArtifactTabBar {...defaultProps} />);
      expect(screen.getByRole("tablist")).toHaveAccessibleName(
        /artifact tabs/i,
      );
    });
  });

  describe("selection", () => {
    it("should mark the selected tab as selected", () => {
      render(<ArtifactTabBar {...defaultProps} selectedId="artifact-2" />);
      const tabs = screen.getAllByRole("tab");
      expect(tabs[1]).toHaveAttribute("aria-selected", "true");
    });

    it("should call onSelect when a tab is clicked", async () => {
      const user = userEvent.setup();
      render(<ArtifactTabBar {...defaultProps} />);

      await user.click(screen.getByText("Second Artifact"));
      expect(defaultProps.onSelect).toHaveBeenCalledWith(mockArtifacts[1]);
    });
  });

  describe("close", () => {
    it("should call onClose with artifact id when close button is clicked", async () => {
      const user = userEvent.setup();
      render(<ArtifactTabBar {...defaultProps} />);

      const closeButtons = screen.getAllByLabelText(/close/i);
      await user.click(closeButtons[0]);

      expect(defaultProps.onClose).toHaveBeenCalledWith("artifact-1");
    });
  });

  describe("rename", () => {
    it("should call onRename with artifact id and new title", async () => {
      const user = userEvent.setup();
      render(<ArtifactTabBar {...defaultProps} />);

      const firstTab = screen.getByText("First Artifact");
      await user.dblClick(firstTab);

      const input = screen.getByRole("textbox");
      await user.clear(input);
      await user.type(input, "Renamed{Enter}");

      expect(defaultProps.onRename).toHaveBeenCalledWith(
        "artifact-1",
        "Renamed",
      );
    });
  });

  describe("empty state", () => {
    it("should render empty message when no artifacts", () => {
      render(<ArtifactTabBar {...defaultProps} artifacts={[]} tabOrder={[]} />);
      expect(screen.getByText(/no artifacts/i)).toBeInTheDocument();
    });
  });

  describe("overflow scrolling", () => {
    it("should have overflow-x-auto class for horizontal scrolling", () => {
      render(<ArtifactTabBar {...defaultProps} />);
      const tablist = screen.getByRole("tablist");
      expect(tablist).toHaveClass("overflow-x-auto");
    });
  });
});

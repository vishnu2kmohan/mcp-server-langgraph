/**
 * VersionTimeline Tests - Phase 1
 *
 * Tests for the artifact version history timeline component
 * that displays version history and allows rollback.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { VersionTimeline } from "./VersionTimeline";
import type { ArtifactVersion } from "../types/artifacts";

// =============================================================================
// Test Data
// =============================================================================

const mockVersions: ArtifactVersion[] = [
  {
    id: "version-3",
    artifactId: "artifact-1",
    version: 3,
    content: "Latest version content",
    contentType: "code",
    createdBy: "user-1",
    createdAt: "2024-01-03T12:00:00Z",
    parentVersion: 2,
    metadata: {
      editedBy: "user",
    },
  },
  {
    id: "version-2",
    artifactId: "artifact-1",
    version: 2,
    content: "Second version content",
    contentType: "code",
    createdBy: "ai",
    createdAt: "2024-01-02T12:00:00Z",
    parentVersion: 1,
    metadata: {
      editedBy: "ai",
      aiConfidence: 0.88,
    },
  },
  {
    id: "version-1",
    artifactId: "artifact-1",
    version: 1,
    content: "Initial version content",
    contentType: "code",
    createdBy: "user-1",
    createdAt: "2024-01-01T12:00:00Z",
    metadata: {
      editedBy: "user",
    },
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("VersionTimeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render timeline container", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getByTestId("version-timeline")).toBeInTheDocument();
    });

    it("should render all versions", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getByText(/v1/)).toBeInTheDocument();
      expect(screen.getByText(/v2/)).toBeInTheDocument();
      expect(screen.getByText(/v3/)).toBeInTheDocument();
    });

    it("should show empty state when no versions", () => {
      render(
        <VersionTimeline
          versions={[]}
          currentVersion={0}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getByText(/no version history/i)).toBeInTheDocument();
    });

    it("should highlight current version", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getByTestId("version-item-3")).toHaveClass("current");
    });
  });

  describe("Version Details", () => {
    it("should display version timestamp", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      // Should show relative time or formatted date
      expect(screen.getByTestId("version-item-1")).toHaveTextContent(/Jan/);
    });

    it("should show AI badge for AI-generated versions", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      const v2Item = screen.getByTestId("version-item-2");
      expect(
        v2Item.querySelector('[data-testid="ai-indicator"]'),
      ).toBeInTheDocument();
    });

    it("should show user indicator for user edits", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      const v1Item = screen.getByTestId("version-item-1");
      expect(
        v1Item.querySelector('[data-testid="user-indicator"]'),
      ).toBeInTheDocument();
    });
  });

  describe("Version Selection", () => {
    it("should call onVersionSelect when version clicked", () => {
      const onVersionSelect = vi.fn();
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={onVersionSelect}
        />,
      );

      fireEvent.click(screen.getByTestId("version-item-1"));
      expect(onVersionSelect).toHaveBeenCalledWith(mockVersions[2]);
    });

    it("should not call onVersionSelect when clicking current version", () => {
      const onVersionSelect = vi.fn();
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={onVersionSelect}
        />,
      );

      fireEvent.click(screen.getByTestId("version-item-3"));
      expect(onVersionSelect).not.toHaveBeenCalled();
    });
  });

  describe("Rollback", () => {
    it("should show restore button on hover", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
          onRestore={() => {}}
        />,
      );

      const v1Item = screen.getByTestId("version-item-1");
      fireEvent.mouseEnter(v1Item);

      expect(screen.getByTestId("restore-button-1")).toBeInTheDocument();
    });

    it("should hide restore button on mouse leave", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
          onRestore={() => {}}
        />,
      );

      const v1Item = screen.getByTestId("version-item-1");
      fireEvent.mouseEnter(v1Item);
      expect(screen.getByTestId("restore-button-1")).toBeInTheDocument();

      fireEvent.mouseLeave(v1Item);
      expect(screen.queryByTestId("restore-button-1")).not.toBeInTheDocument();
    });

    it("should call onRestore when restore button clicked", () => {
      const onRestore = vi.fn();
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
          onRestore={onRestore}
        />,
      );

      const v1Item = screen.getByTestId("version-item-1");
      fireEvent.mouseEnter(v1Item);
      fireEvent.click(screen.getByTestId("restore-button-1"));

      expect(onRestore).toHaveBeenCalledWith(mockVersions[2]);
    });

    it("should not show restore button on current version", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
          onRestore={() => {}}
        />,
      );

      const v3Item = screen.getByTestId("version-item-3");
      fireEvent.mouseEnter(v3Item);

      expect(screen.queryByTestId("restore-button-3")).not.toBeInTheDocument();
    });
  });

  describe("Diff Preview", () => {
    it("should show diff preview on hover when enabled", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
          showDiffPreview
        />,
      );

      const v1Item = screen.getByTestId("version-item-1");
      fireEvent.mouseEnter(v1Item);

      expect(screen.getByTestId("diff-preview")).toBeInTheDocument();
    });
  });

  describe("Collapsed State", () => {
    it("should show collapsed view by default when many versions", () => {
      const manyVersions = Array.from({ length: 10 }, (_, i) => ({
        ...mockVersions[0],
        id: `version-${i + 1}`,
        version: i + 1,
        createdAt: `2024-01-${String(i + 1).padStart(2, "0")}T12:00:00Z`,
      }));

      render(
        <VersionTimeline
          versions={manyVersions}
          currentVersion={10}
          onVersionSelect={() => {}}
        />,
      );

      expect(screen.getByTestId("show-more-button")).toBeInTheDocument();
    });

    it("should expand to show all versions when show more clicked", () => {
      const manyVersions = Array.from({ length: 10 }, (_, i) => ({
        ...mockVersions[0],
        id: `version-${i + 1}`,
        version: i + 1,
        createdAt: `2024-01-${String(i + 1).padStart(2, "0")}T12:00:00Z`,
      }));

      render(
        <VersionTimeline
          versions={manyVersions}
          currentVersion={10}
          onVersionSelect={() => {}}
        />,
      );

      fireEvent.click(screen.getByTestId("show-more-button"));

      // Should show all 10 versions
      expect(screen.getByTestId("version-item-1")).toBeInTheDocument();
      expect(screen.getByTestId("version-item-10")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible timeline role", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getByRole("list")).toBeInTheDocument();
    });

    it("should have accessible version items", () => {
      render(
        <VersionTimeline
          versions={mockVersions}
          currentVersion={3}
          onVersionSelect={() => {}}
        />,
      );
      expect(screen.getAllByRole("listitem")).toHaveLength(3);
    });
  });
});

/**
 * ArtifactActions Tests - Phase 1
 *
 * Tests for the artifact action buttons component
 * (Remix/Fork, Share, Export, Copy, Delete).
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { ArtifactActions } from "./ArtifactActions";
import type { CanvasArtifact } from "../types/artifacts";

import { TestProvider } from "@/test-utils";

// Mock clipboard API
Object.assign(navigator, {
  clipboard: {
    writeText: vi.fn().mockResolvedValue(undefined),
  },
});

// =============================================================================
// Test Data
// =============================================================================

const mockArtifact: CanvasArtifact = {
  id: "artifact-1",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: 'console.log("Hello!");',
  contentType: "code",
  title: "Hello Code",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

// =============================================================================
// Tests
// =============================================================================

describe("ArtifactActions", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render actions container", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );
      expect(screen.getByTestId("artifact-actions")).toBeInTheDocument();
    });

    it("should render copy button", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should render fork button", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /fork/i })).toBeInTheDocument();
    });

    it("should render export button", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Copy Action", () => {
    it("should copy content to clipboard when copy clicked", async () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy/i }));

      await waitFor(() => {
        expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
          mockArtifact.content,
        );
      });
    });

    it("should show success feedback after copying", async () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy/i }));

      await waitFor(() => {
        expect(screen.getByTestId("copy-success")).toBeInTheDocument();
      });
    });

    it("should call onCopy callback when provided", async () => {
      const onCopy = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} onCopy={onCopy} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /copy/i }));

      await waitFor(() => {
        expect(onCopy).toHaveBeenCalled();
      });
    });
  });

  describe("Fork Action", () => {
    it("should call onFork when fork clicked", () => {
      const onFork = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} onFork={onFork} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /fork/i }));
      expect(onFork).toHaveBeenCalledWith(mockArtifact);
    });

    it("should disable fork button when disabled", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} disableFork />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /fork/i })).toBeDisabled();
    });
  });

  describe("Export Action", () => {
    it("should show export menu when export clicked", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /export/i }));
      expect(screen.getByTestId("export-menu")).toBeInTheDocument();
    });

    it("should show export format options", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /export/i }));

      expect(screen.getByText(/json/i)).toBeInTheDocument();
      expect(screen.getByText(/markdown/i)).toBeInTheDocument();
    });

    it("should call onExport with selected format", () => {
      const onExport = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} onExport={onExport} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /export/i }));
      fireEvent.click(screen.getByText(/json/i));

      expect(onExport).toHaveBeenCalledWith(mockArtifact, "json");
    });
  });

  describe("Share Action", () => {
    it("should render share button when shareable", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} shareable />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /share/i }),
      ).toBeInTheDocument();
    });

    it("should not render share button when not shareable", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} shareable={false} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /share/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onShare when share clicked", () => {
      const onShare = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions
            artifact={mockArtifact}
            shareable
            onShare={onShare}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /share/i }));
      expect(onShare).toHaveBeenCalledWith(mockArtifact);
    });
  });

  describe("Delete Action", () => {
    it("should render delete button when deletable", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} deletable />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });

    it("should not render delete button when not deletable", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} deletable={false} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /delete/i }),
      ).not.toBeInTheDocument();
    });

    it("should show confirmation dialog when delete clicked", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} deletable />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      expect(screen.getByTestId("delete-confirm-dialog")).toBeInTheDocument();
    });

    it("should call onDelete after confirmation", () => {
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions
            artifact={mockArtifact}
            deletable
            onDelete={onDelete}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByTestId("confirm-delete-button"));

      expect(onDelete).toHaveBeenCalledWith(mockArtifact);
    });

    it("should not call onDelete when confirmation cancelled", () => {
      const onDelete = vi.fn();
      render(
        <TestProvider>
          <ArtifactActions
            artifact={mockArtifact}
            deletable
            onDelete={onDelete}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("button", { name: /delete/i }));
      fireEvent.click(screen.getByTestId("cancel-delete-button"));

      expect(onDelete).not.toHaveBeenCalled();
    });
  });

  describe("Disabled State", () => {
    it("should disable all actions when disabled prop is true", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} disabled />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toBeDisabled();
      });
    });
  });

  describe("Compact Mode", () => {
    it("should render icon-only buttons in compact mode", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} compact />
        </TestProvider>,
      );

      // Should not show button text, only icons
      expect(screen.queryByText("Copy")).not.toBeInTheDocument();
      expect(screen.getByTestId("copy-icon")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible button labels", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} shareable deletable />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /fork/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /export/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /share/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /delete/i }),
      ).toBeInTheDocument();
    });

    it("should have tooltips for icon-only buttons in compact mode", () => {
      render(
        <TestProvider>
          <ArtifactActions artifact={mockArtifact} compact />
        </TestProvider>,
      );

      const copyButton = screen.getByRole("button", { name: /copy/i });
      expect(copyButton).toHaveAttribute(
        "title",
        expect.stringContaining("Copy"),
      );
    });
  });
});

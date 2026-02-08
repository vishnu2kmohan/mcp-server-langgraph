/**
 * ConflictResolutionDialog Tests
 *
 * Sprint 3 - Phase 2.2: Offline Conflict Resolution UI
 *
 * Tests for the dialog that allows users to resolve sync conflicts
 * when coming back online.
 */

import {
  cleanup,
  fireEvent as _fireEvent,
  render,
  screen,
  within as _within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ConflictResolutionDialog } from "./ConflictResolutionDialog";
import type {
  SyncConflict,
  ConflictResolution as _ConflictResolution,
} from "../../hooks/useOfflineQueue";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Fixtures
// =============================================================================

const createMockConflict = (
  overrides: Partial<SyncConflict> = {},
): SyncConflict => ({
  actionId: "action-123",
  localVersion: { title: "Local Title", updatedAt: "2026-01-19T10:00:00Z" },
  serverVersion: { title: "Server Title", updatedAt: "2026-01-19T11:00:00Z" },
  field: "title",
  suggestedResolution: "keep-server",
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ConflictResolutionDialog", () => {
  const defaultProps = {
    conflicts: [createMockConflict()],
    onResolve: vi.fn(),
    onResolveAll: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders nothing when conflicts array is empty", () => {
      const { container } = render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={[]} />
        </TestProvider>,
      );
      expect(container).toBeEmptyDOMElement();
    });

    it("renders dialog when conflicts exist", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("dialog", { name: /sync conflict/i }),
      ).toBeInTheDocument();
    });

    it("displays conflict count in header", () => {
      const conflicts = [
        createMockConflict({ actionId: "1" }),
        createMockConflict({ actionId: "2" }),
        createMockConflict({ actionId: "3" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );
      expect(screen.getByText(/3 conflicts/i)).toBeInTheDocument();
    });

    it("shows field name in conflict details", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );
      // Field name is shown as "Field: title" - use more specific query
      expect(screen.getByText(/^field:/i)).toBeInTheDocument();
    });

    it("displays local and server versions", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/local title/i)).toBeInTheDocument();
      expect(screen.getByText(/server title/i)).toBeInTheDocument();
    });
  });

  describe("Resolution Options", () => {
    it("renders all three resolution options", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /keep local/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /keep server/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /merge/i }),
      ).toBeInTheDocument();
    });

    it("highlights suggested resolution", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );

      const keepServerButton = screen.getByRole("button", {
        name: /keep server/i,
      });
      expect(keepServerButton).toHaveAttribute("data-suggested", "true");
    });

    it("calls onResolve with keep-local when button clicked", async () => {
      const user = userEvent.setup();
      const onResolve = vi.fn();
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} onResolve={onResolve} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /keep local/i }));

      expect(onResolve).toHaveBeenCalledWith("action-123", "keep-local");
    });

    it("calls onResolve with keep-server when button clicked", async () => {
      const user = userEvent.setup();
      const onResolve = vi.fn();
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} onResolve={onResolve} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /keep server/i }));

      expect(onResolve).toHaveBeenCalledWith("action-123", "keep-server");
    });

    it("calls onResolve with merge when button clicked", async () => {
      const user = userEvent.setup();
      const onResolve = vi.fn();
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} onResolve={onResolve} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /merge/i }));

      expect(onResolve).toHaveBeenCalledWith("action-123", "merge");
    });
  });

  describe("Bulk Actions", () => {
    it("renders 'Resolve All' button when multiple conflicts", () => {
      const conflicts = [
        createMockConflict({ actionId: "1" }),
        createMockConflict({ actionId: "2" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /resolve all/i }),
      ).toBeInTheDocument();
    });

    it("does not render 'Resolve All' button for single conflict", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: /resolve all/i }),
      ).not.toBeInTheDocument();
    });

    it("calls onResolveAll when 'Resolve All' button clicked", async () => {
      const user = userEvent.setup();
      const onResolveAll = vi.fn();
      const conflicts = [
        createMockConflict({
          actionId: "1",
          suggestedResolution: "keep-local",
        }),
        createMockConflict({
          actionId: "2",
          suggestedResolution: "keep-server",
        }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog
            {...defaultProps}
            conflicts={conflicts}
            onResolveAll={onResolveAll}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /resolve all/i }));

      expect(onResolveAll).toHaveBeenCalled();
    });
  });

  describe("Navigation", () => {
    it("shows pagination when multiple conflicts", () => {
      const conflicts = [
        createMockConflict({ actionId: "1", field: "title" }),
        createMockConflict({ actionId: "2", field: "description" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      expect(screen.getByText(/1 of 2/i)).toBeInTheDocument();
    });

    it("navigates to next conflict", async () => {
      const user = userEvent.setup();
      const conflicts = [
        createMockConflict({ actionId: "1", field: "title" }),
        createMockConflict({ actionId: "2", field: "description" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /next/i }));

      expect(screen.getByText(/2 of 2/i)).toBeInTheDocument();
      expect(screen.getByText(/description/i)).toBeInTheDocument();
    });

    it("navigates to previous conflict", async () => {
      const user = userEvent.setup();
      const conflicts = [
        createMockConflict({ actionId: "1", field: "title" }),
        createMockConflict({ actionId: "2", field: "description" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      // Go to second conflict
      await user.click(screen.getByRole("button", { name: /next/i }));
      expect(screen.getByText(/2 of 2/i)).toBeInTheDocument();

      // Go back to first
      await user.click(screen.getByRole("button", { name: /previous/i }));
      expect(screen.getByText(/1 of 2/i)).toBeInTheDocument();
    });

    it("disables previous button on first conflict", () => {
      const conflicts = [
        createMockConflict({ actionId: "1" }),
        createMockConflict({ actionId: "2" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /previous/i })).toBeDisabled();
    });

    it("disables next button on last conflict", async () => {
      const user = userEvent.setup();
      const conflicts = [
        createMockConflict({ actionId: "1" }),
        createMockConflict({ actionId: "2" }),
      ];
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} conflicts={conflicts} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /next/i }));

      expect(screen.getByRole("button", { name: /next/i })).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("has accessible dialog role", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("has accessible name for dialog", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("dialog", { name: /sync conflict/i }),
      ).toBeInTheDocument();
    });

    it("resolution buttons have accessible labels", () => {
      render(
        <TestProvider>
          <ConflictResolutionDialog {...defaultProps} />
        </TestProvider>,
      );

      const buttons = screen.getAllByRole("button");
      buttons.forEach((button) => {
        expect(button).toHaveAccessibleName();
      });
    });
  });
});

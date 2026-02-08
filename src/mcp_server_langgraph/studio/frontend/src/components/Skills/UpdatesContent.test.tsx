/**
 * UpdatesContent Component Tests
 *
 * TDD test suite for the skill updates tab component.
 * Tests update display, apply actions, and up-to-date state.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { UpdatesContent } from "./UpdatesContent";

import { TestProvider } from "@/test-utils";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("UpdatesContent", () => {
  const mockUpdates = [
    { name: "web-research", currentVersion: "1.2.0", newVersion: "1.3.0" },
    { name: "code-review", currentVersion: "2.1.0", newVersion: "3.0.0" },
  ];

  const defaultProps = {
    updates: mockUpdates,
    onApplyAll: vi.fn(),
    isApplying: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("Rendering", () => {
    it("renders updates list when updates available", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-updates-list")).toBeInTheDocument();
    });

    it("displays update count", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/2 update\(s\) available/i)).toBeInTheDocument();
    });

    it("shows Apply All Updates button", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-apply-updates")).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /apply all updates/i }),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Empty/Up-to-date State Tests
  // ===========================================================================

  describe("Up-to-date State", () => {
    it("renders up-to-date state when no updates", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[]} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-updates-empty")).toBeInTheDocument();
    });

    it("shows success message when up to date", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[]} />
        </TestProvider>,
      );

      expect(screen.getByText("All skills are up to date")).toBeInTheDocument();
      expect(
        screen.getByText("No updates available at this time."),
      ).toBeInTheDocument();
    });

    it("does not show updates list when up to date", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[]} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("skills-updates-list"),
      ).not.toBeInTheDocument();
    });

    it("does not show apply button when up to date", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[]} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("skills-apply-updates"),
      ).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Single Update Tests
  // ===========================================================================

  describe("Single Update", () => {
    it("displays singular count for one update", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[mockUpdates[0]]} />
        </TestProvider>,
      );

      expect(screen.getByText(/1 update\(s\) available/i)).toBeInTheDocument();
    });

    it("shows apply button for single update", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[mockUpdates[0]]} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-apply-updates")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Apply Updates Action Tests
  // ===========================================================================

  describe("Apply Updates Actions", () => {
    it("calls onApplyAll when button clicked", async () => {
      const user = userEvent.setup();
      const onApplyAll = vi.fn();

      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} onApplyAll={onApplyAll} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("skills-apply-updates"));
      expect(onApplyAll).toHaveBeenCalledTimes(1);
    });

    it("disables button when applying updates", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} isApplying={true} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-apply-updates")).toBeDisabled();
    });

    it("enables button when not applying", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} isApplying={false} />
        </TestProvider>,
      );

      expect(screen.getByTestId("skills-apply-updates")).not.toBeDisabled();
    });
  });

  // ===========================================================================
  // Multiple Updates Tests
  // ===========================================================================

  describe("Multiple Updates", () => {
    it("handles many updates", () => {
      const manyUpdates = [
        { name: "skill-1", currentVersion: "1.0.0", newVersion: "2.0.0" },
        { name: "skill-2", currentVersion: "1.0.0", newVersion: "2.0.0" },
        { name: "skill-3", currentVersion: "1.0.0", newVersion: "2.0.0" },
        { name: "skill-4", currentVersion: "1.0.0", newVersion: "2.0.0" },
        { name: "skill-5", currentVersion: "1.0.0", newVersion: "2.0.0" },
      ];

      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={manyUpdates} />
        </TestProvider>,
      );

      expect(screen.getByText(/5 update\(s\) available/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("Accessibility", () => {
    it("apply button has accessible name", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /apply all updates/i });
      expect(button).toBeInTheDocument();
    });

    it("update count is visible text", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/update\(s\) available/i)).toBeInTheDocument();
    });

    it("success message is visible in up-to-date state", () => {
      render(
        <TestProvider>
          <UpdatesContent {...defaultProps} updates={[]} />
        </TestProvider>,
      );

      expect(screen.getByText("All skills are up to date")).toBeInTheDocument();
    });
  });
});

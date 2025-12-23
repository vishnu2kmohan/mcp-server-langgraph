/**
 * ProblemsTab Tests
 *
 * TDD tests for the Problems tab in DevTools.
 * Aggregates errors and warnings from Redux state.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  within,
  waitFor,
  fireEvent,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

expect.extend(toHaveNoViolations);

import { ProblemsTab } from "./ProblemsTab";

// =============================================================================
// Mock Store Setup
// =============================================================================

const createMockStore = (state: {
  sessionError?: string | null;
  mcpError?: string | null;
}) => {
  return configureStore({
    reducer: {
      session: () => ({
        error: state.sessionError ?? null,
      }),
      mcp: () => ({
        error: state.mcpError ?? null,
      }),
    },
  });
};

const renderWithStore = (
  ui: React.ReactNode,
  options: { sessionError?: string | null; mcpError?: string | null } = {},
) => {
  const store = createMockStore(options);
  return render(<Provider store={store}>{ui}</Provider>);
};

// =============================================================================
// Tests
// =============================================================================

describe("ProblemsTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      renderWithStore(<ProblemsTab />);

      expect(screen.getByTestId("problems-tab")).toBeInTheDocument();
    });

    it("should display problems when errors exist", () => {
      renderWithStore(<ProblemsTab />, {
        sessionError: "Failed to connect to session",
      });

      expect(
        screen.getByText("Failed to connect to session"),
      ).toBeInTheDocument();
    });

    it("should display empty state when no problems", () => {
      renderWithStore(<ProblemsTab />);

      expect(screen.getByTestId("problems-empty-state")).toBeInTheDocument();
      expect(screen.getByText(/no problems detected/i)).toBeInTheDocument();
    });
  });

  describe("problem counts", () => {
    it("should show error count", () => {
      renderWithStore(<ProblemsTab showCount />, {
        sessionError: "Error 1",
        mcpError: "Error 2",
      });

      expect(screen.getByTestId("error-count")).toHaveTextContent("2");
    });

    it("should show warning count", () => {
      renderWithStore(<ProblemsTab showCount />);

      expect(screen.getByTestId("warning-count")).toHaveTextContent("0");
    });

    it("should hide counts when showCount is false", () => {
      renderWithStore(<ProblemsTab showCount={false} />);

      expect(screen.queryByTestId("error-count")).not.toBeInTheDocument();
      expect(screen.queryByTestId("warning-count")).not.toBeInTheDocument();
    });
  });

  describe("problem display", () => {
    it("should display severity icon for errors", () => {
      renderWithStore(<ProblemsTab />, {
        sessionError: "Test error",
      });

      const problem = screen.getByTestId("problem-session-error");
      expect(within(problem).getByTestId("severity-error")).toBeInTheDocument();
    });

    it("should display source badge", () => {
      renderWithStore(<ProblemsTab />, {
        mcpError: "MCP connection failed",
      });

      expect(screen.getByText("mcp")).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("should show filter buttons", () => {
      renderWithStore(<ProblemsTab />);

      expect(screen.getByTestId("filter-all")).toBeInTheDocument();
      expect(screen.getByTestId("filter-errors")).toBeInTheDocument();
      expect(screen.getByTestId("filter-warnings")).toBeInTheDocument();
    });

    it("should filter to errors only", async () => {
      const user = userEvent.setup();

      renderWithStore(<ProblemsTab />, {
        sessionError: "Error 1",
      });

      await user.click(screen.getByTestId("filter-errors"));

      // Should still show the error
      expect(screen.getByText("Error 1")).toBeInTheDocument();
    });

    it("should show empty when filtering to warnings with only errors", async () => {
      const user = userEvent.setup();

      renderWithStore(<ProblemsTab />, {
        sessionError: "Error 1",
      });

      await user.click(screen.getByTestId("filter-warnings"));

      // Should show empty state since there are no warnings
      expect(screen.getByTestId("problems-empty-state")).toBeInTheDocument();
    });
  });

  describe("dismiss problem", () => {
    it("should show dismiss button on hover", async () => {
      const user = userEvent.setup();

      renderWithStore(<ProblemsTab />, {
        sessionError: "Test error",
      });

      const problem = screen.getByTestId("problem-session-error");
      await user.hover(problem);

      expect(within(problem).getByTestId("dismiss-button")).toBeInTheDocument();
    });

    it("should dismiss problem when dismiss button clicked", async () => {
      renderWithStore(<ProblemsTab />, {
        sessionError: "Test error",
      });

      // Verify problem exists
      expect(screen.getByTestId("problem-session-error")).toBeInTheDocument();

      // Trigger hover state using fireEvent
      const problem = screen.getByTestId("problem-session-error");
      fireEvent.mouseEnter(problem);

      // Get dismiss button while hovering
      const dismissButton = within(problem).getByTestId("dismiss-button");

      // Click dismiss - the problem should be removed
      fireEvent.click(dismissButton);

      // After clicking, the empty state should appear since there's only one problem
      await waitFor(() => {
        expect(screen.getByTestId("problems-empty-state")).toBeInTheDocument();
      });
    });
  });

  describe("clear all", () => {
    it("should show clear all button", () => {
      renderWithStore(<ProblemsTab />);

      expect(screen.getByTestId("clear-all-button")).toBeInTheDocument();
    });

    it("should clear all problems when clicked", async () => {
      const user = userEvent.setup();

      renderWithStore(<ProblemsTab />, {
        sessionError: "Error 1",
        mcpError: "Error 2",
      });

      // Verify problems exist
      expect(screen.getByTestId("problem-session-error")).toBeInTheDocument();
      expect(screen.getByTestId("problem-mcp-error")).toBeInTheDocument();

      await user.click(screen.getByTestId("clear-all-button"));

      // All problems should be dismissed
      expect(screen.getByTestId("problems-empty-state")).toBeInTheDocument();
    });
  });

  describe("compact mode", () => {
    it("should render in compact mode", () => {
      renderWithStore(<ProblemsTab compact />);

      const tab = screen.getByTestId("problems-tab");
      expect(tab).toHaveClass("compact");
    });
  });

  describe("accessibility", () => {
    it("should have no accessibility violations when empty", async () => {
      const { container } = renderWithStore(<ProblemsTab />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with problems", async () => {
      const { container } = renderWithStore(<ProblemsTab />, {
        sessionError: "Test error",
      });
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});

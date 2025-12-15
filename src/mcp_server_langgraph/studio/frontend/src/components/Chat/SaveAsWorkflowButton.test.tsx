/**
 * SaveAsWorkflowButton Tests
 *
 * TDD tests for the workflow bootstrap button.
 * Tests cover:
 * - Button rendering
 * - API call on click (via mocked RTK Query)
 * - Loading state
 * - Success message
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  act,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { SaveAsWorkflowButton } from "./SaveAsWorkflowButton";

// Mock the useBootstrapWorkflowMutation hook
const mockUnwrap = vi.fn();
const mockBootstrapWorkflow = vi.fn(() => ({
  unwrap: mockUnwrap,
}));

// Import the mocked module
import * as apiModule from "../../api";

vi.mock("../../api", () => ({
  useBootstrapWorkflowMutation: vi.fn(() => [
    mockBootstrapWorkflow,
    { isLoading: false },
  ]),
  api: {
    reducerPath: "api",
    reducer: (state = {}) => state,
    middleware:
      () => (next: (action: unknown) => unknown) => (action: unknown) =>
        next(action),
  },
}));

const mockedUseBootstrapWorkflowMutation = vi.mocked(
  apiModule.useBootstrapWorkflowMutation,
);

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

// Helper to render with Redux provider
const renderWithProvider = (component: React.ReactNode) => {
  const store = createTestStore();
  return render(<Provider store={store}>{component}</Provider>);
};

describe("SaveAsWorkflowButton", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useRealTimers();

    // Reset to default successful mock
    mockUnwrap.mockResolvedValue({
      workflow_id: "workflow-123",
      name: "My Workflow",
    });
    mockedUseBootstrapWorkflowMutation.mockReturnValue([
      mockBootstrapWorkflow,
      { isLoading: false },
    ]);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("Rendering", () => {
    it("should render button", () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      expect(
        screen.getByRole("button", { name: /Save as Workflow/i }),
      ).toBeInTheDocument();
    });

    it("should display button text", () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      expect(screen.getByText(/Save as Workflow/i)).toBeInTheDocument();
    });
  });

  describe("API Call", () => {
    it("should call bootstrap API on click", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(mockBootstrapWorkflow).toHaveBeenCalledWith("session-123");
      });
    });

    it("should include session ID in API call", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="test-session-456" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(mockBootstrapWorkflow).toHaveBeenCalledWith("test-session-456");
      });
    });
  });

  describe("Loading State", () => {
    it("should be disabled during processing", async () => {
      // Set loading state
      mockedUseBootstrapWorkflowMutation.mockReturnValue([
        mockBootstrapWorkflow,
        { isLoading: true },
      ]);

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });

    it("should show loading spinner during API call", async () => {
      mockedUseBootstrapWorkflowMutation.mockReturnValue([
        mockBootstrapWorkflow,
        { isLoading: true },
      ]);

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });

    it("should re-enable button after successful API call", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole("button");

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(button).not.toBeDisabled();
      });
    });
  });

  describe("Success State", () => {
    it("should show success message after creation", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();
      });
    });

    it("should display workflow name in success message", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/My Workflow/i)).toBeInTheDocument();
      });
    });

    it("should show link to workflow on success", async () => {
      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        const link = screen.getByRole("link", { name: /View Workflow/i });
        expect(link).toBeInTheDocument();
        expect(link).toHaveAttribute(
          "href",
          "/studio/workflows?id=workflow-123",
        );
      });
    });

    it("should auto-dismiss success message after delay", async () => {
      vi.useFakeTimers();

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
        // Let the promise resolve
        await Promise.resolve();
        await Promise.resolve();
      });

      expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();

      await act(async () => {
        vi.advanceTimersByTime(5000);
      });

      expect(screen.queryByText(/Workflow Created/i)).not.toBeInTheDocument();

      vi.useRealTimers();
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors", async () => {
      mockUnwrap.mockRejectedValue({
        data: { detail: "Error creating workflow" },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to Create Workflow/i),
        ).toBeInTheDocument();
      });
    });

    it("should display error message from API", async () => {
      mockUnwrap.mockRejectedValue({
        data: { detail: "Custom error message" },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/Custom error message/i)).toBeInTheDocument();
      });
    });

    it("should re-enable button after error", async () => {
      mockUnwrap.mockRejectedValue({
        data: { detail: "Error" },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      const button = screen.getByRole("button");

      await act(async () => {
        fireEvent.click(button);
      });

      await waitFor(() => {
        expect(button).not.toBeDisabled();
      });
    });

    it("should allow retry after error", async () => {
      // First call fails
      mockUnwrap.mockRejectedValueOnce({
        data: { detail: "Error" },
      });
      // Second call succeeds
      mockUnwrap.mockResolvedValueOnce({
        workflow_id: "workflow-123",
        name: "My Workflow",
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      // First click fails
      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to Create Workflow/i),
        ).toBeInTheDocument();
      });

      // Second click succeeds
      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/Workflow Created/i)).toBeInTheDocument();
      });
    });

    it("should handle network errors", async () => {
      mockUnwrap.mockRejectedValue(new Error("Network error"));

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Failed to Create Workflow/i),
        ).toBeInTheDocument();
      });
    });

    it("should handle Pydantic validation errors", async () => {
      // Pydantic validation errors have detail as an array
      mockUnwrap.mockRejectedValue({
        data: {
          detail: [
            {
              type: "value_error",
              loc: ["body", "name"],
              msg: "Field required",
              input: null,
            },
          ],
        },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/Field required/i)).toBeInTheDocument();
      });
    });

    it("should handle multiple Pydantic validation errors", async () => {
      mockUnwrap.mockRejectedValue({
        data: {
          detail: [{ msg: "Field 1 error" }, { msg: "Field 2 error" }],
        },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Field 1 error; Field 2 error/i),
        ).toBeInTheDocument();
      });
    });

    it("should fallback to type if msg is missing in validation error", async () => {
      mockUnwrap.mockRejectedValue({
        data: {
          detail: [{ type: "missing" }],
        },
      });

      renderWithProvider(<SaveAsWorkflowButton sessionId="session-123" />);

      await act(async () => {
        fireEvent.click(screen.getByRole("button"));
      });

      await waitFor(() => {
        expect(screen.getByText(/missing/i)).toBeInTheDocument();
      });
    });
  });

  describe("Disabled State", () => {
    it("should not call API when disabled", async () => {
      renderWithProvider(
        <SaveAsWorkflowButton sessionId="session-123" disabled />,
      );

      const button = screen.getByRole("button");
      fireEvent.click(button);

      // Wait a bit to ensure no API call happens
      await new Promise((resolve) => setTimeout(resolve, 50));

      expect(mockBootstrapWorkflow).not.toHaveBeenCalled();
    });

    it("should show disabled styling when disabled", () => {
      renderWithProvider(
        <SaveAsWorkflowButton sessionId="session-123" disabled />,
      );

      const button = screen.getByRole("button");
      expect(button).toBeDisabled();
    });
  });
});

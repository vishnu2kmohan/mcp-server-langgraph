/**
 * ProblemsPanel Component Tests
 *
 * TDD tests for the problems panel component.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ProblemsPanel } from "./ProblemsPanel";
import sessionReducer from "../../store/slices/sessionSlice";
import mcpReducer from "../../store/slices/mcpSlice";

// Create test store
const createTestStore = (
  options: {
    sessionError?: string | null;
    mcpError?: string | null;
  } = {},
) => {
  return configureStore({
    reducer: {
      session: sessionReducer,
      mcp: mcpReducer,
    },
    preloadedState: {
      session: {
        currentSessionId: null,
        sessions: [],
        messages: [],
        isLoadingSession: false,
        isLoadingSessions: false,
        isLoadingMore: false,
        isSending: false,
        hasMore: false,
        totalCount: 0,
        error: options.sessionError ?? null,
      },
      mcp: {
        servers: {},
        error: options.mcpError ?? null,
      },
    },
  });
};

const renderWithProviders = (
  ui: React.ReactElement,
  options: {
    sessionError?: string | null;
    mcpError?: string | null;
  } = {},
) => {
  const store = createTestStore(options);
  return {
    store,
    ...render(<Provider store={store}>{ui}</Provider>),
  };
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ProblemsPanel", () => {
  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<ProblemsPanel />);
      expect(screen.getByTestId("problems-panel")).toBeInTheDocument();
    });

    it("should show no problems state when no errors", () => {
      renderWithProviders(<ProblemsPanel />);
      expect(screen.getByText(/no problems detected/i)).toBeInTheDocument();
    });

    it("should display session error when present", () => {
      renderWithProviders(<ProblemsPanel />, {
        sessionError: "Failed to load session",
      });
      expect(screen.getByText("Session Error")).toBeInTheDocument();
      expect(screen.getByText("Failed to load session")).toBeInTheDocument();
    });

    it("should display MCP error when present", () => {
      renderWithProviders(<ProblemsPanel />, {
        mcpError: "Connection failed",
      });
      expect(screen.getByText("MCP Error")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should display both errors when both present", () => {
      renderWithProviders(<ProblemsPanel />, {
        sessionError: "Session error message",
        mcpError: "MCP error message",
      });
      expect(screen.getByText("Session Error")).toBeInTheDocument();
      expect(screen.getByText("MCP Error")).toBeInTheDocument();
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<ProblemsPanel className="custom-class" />);
      expect(screen.getByTestId("problems-panel")).toHaveClass("custom-class");
    });

    it("should accept compact prop for reduced spacing", () => {
      renderWithProviders(<ProblemsPanel compact />);
      expect(screen.getByTestId("problems-panel")).toHaveClass("p-2");
    });
  });

  describe("Problem Count", () => {
    it("should show correct problem count in header", () => {
      renderWithProviders(<ProblemsPanel showCount />, {
        sessionError: "Error 1",
        mcpError: "Error 2",
      });
      expect(screen.getByTestId("problem-count")).toHaveTextContent("2");
    });

    it("should show zero count when no problems", () => {
      renderWithProviders(<ProblemsPanel showCount />);
      expect(screen.getByTestId("problem-count")).toHaveTextContent("0");
    });
  });
});

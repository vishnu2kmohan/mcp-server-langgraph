/**
 * AgentsPage Tests
 *
 * TDD tests for the Agents configuration page.
 * Tests cover:
 * - Page header display
 * - Agent configuration display
 * - Available tools list
 * - Model selection
 * - Temperature slider
 * - Verification toggle
 * - Loading and error states
 *
 * Updated for Sprint 2: Uses custom test wrapper with Redux provider.
 */

import type { ReactNode } from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { createMemoryRouter, RouterProvider } from "react-router";
import { AgentsPage } from "./AgentsPage";
import personaReducer from "../store/slices/personaSlice";

// Mock the RTK Query hooks
const mockRefetch = vi.fn();
const mockUpdateThinkingBudget = vi.fn().mockReturnValue({
  unwrap: vi.fn().mockResolvedValue({}),
});

vi.mock("../api", () => ({
  useGetAgentConfigQuery: vi.fn(),
  useUpdateThinkingBudgetMutation: () => [
    mockUpdateThinkingBudget,
    { isLoading: false },
  ],
  // Mock for AgentMetricsCard (added to AgentsPage)
  useGetAgentMetricsQuery: () => ({
    data: null,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

import { useGetAgentConfigQuery } from "../api";

// Cast to vi.Mock for type safety
const mockUseGetAgentConfigQuery = useGetAgentConfigQuery as ReturnType<
  typeof vi.fn
>;

/**
 * Custom test wrapper for AgentsPage tests.
 * Provides Redux store with persona state without importing the real api module.
 */
function AgentsPageTestWrapper({ children }: { children: ReactNode }) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
    },
  });

  const router = createMemoryRouter([{ path: "*", element: children }], {
    initialEntries: ["/"],
  });

  return (
    <Provider store={store}>
      <RouterProvider router={router} />
    </Provider>
  );
}

// Default mock data - uses camelCase to match API response after transformSnakeToCamel
const mockConfig = {
  model: "gemini-2.5-flash",
  provider: "google",
  temperature: 0.7,
  verificationEnabled: true,
  tools: [
    { name: "calculator", description: "Perform calculations" },
    { name: "web_search", description: "Search the web" },
  ],
};

describe("AgentsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();

    // Default mock: successful config response
    mockUseGetAgentConfigQuery.mockReturnValue({
      data: mockConfig,
      isLoading: false,
      error: null,
      refetch: mockRefetch,
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Header", () => {
    it("should display page title", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      // Default persona is "user" which shows "AI Capabilities" title
      expect(screen.getByText("AI Capabilities")).toBeInTheDocument();
    });

    it("should display page description", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      // Default persona is "user" which shows user-focused description
      expect(
        screen.getByText(/Available AI tools and features/),
      ).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner while fetching data", () => {
      mockUseGetAgentConfigQuery.mockReturnValue({
        data: null,
        isLoading: true,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(document.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should display error message when fetch fails", () => {
      mockUseGetAgentConfigQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500, message: "Server Error" },
        refetch: mockRefetch,
      });

      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      // ErrorState component has role="alert" for accessibility
      expect(screen.getByRole("alert")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", {
          name: /failed to load agent configuration/i,
        }),
      ).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      mockUseGetAgentConfigQuery.mockReturnValue({
        data: null,
        isLoading: false,
        error: { status: 500 },
        refetch: mockRefetch,
      });

      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      // Retry button inside ErrorState
      expect(
        screen.getByRole("button", { name: /retry/i }),
      ).toBeInTheDocument();
    });
  });

  describe("Agent Configuration Display", () => {
    it("should display current model", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText(/gemini-2.5-flash/)).toBeInTheDocument();
    });

    it("should display temperature value", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText(/0.7/)).toBeInTheDocument();
    });

    it("should display verification status", async () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      await waitFor(() => {
        // Toggle uses role="switch" with aria-checked, not checkbox
        const toggle = screen.getByRole("switch", {
          name: /enable verification/i,
        });
        expect(toggle).toHaveAttribute("aria-checked", "true");
      });
    });
  });

  describe("Tools List", () => {
    it("should display available tools", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("web_search")).toBeInTheDocument();
    });

    it("should display tool count", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText(/2 tools/i)).toBeInTheDocument();
    });

    it("should show empty state when no tools available", () => {
      mockUseGetAgentConfigQuery.mockReturnValue({
        data: { ...mockConfig, tools: [] },
        isLoading: false,
        error: null,
        refetch: mockRefetch,
      });

      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText(/No tools available/)).toBeInTheDocument();
    });
  });

  describe("Model Selection", () => {
    it("should have model dropdown", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByLabelText(/Model/i)).toBeInTheDocument();
    });
  });

  describe("Temperature Control", () => {
    it("should have temperature slider", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByLabelText(/Temperature/i)).toBeInTheDocument();
    });

    it("should update temperature value when slider changes", async () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      await waitFor(() => {
        const slider = screen.getByLabelText(/Temperature/i);
        fireEvent.change(slider, { target: { value: "0.9" } });
        expect(screen.getByText(/0.9/)).toBeInTheDocument();
      });
    });
  });

  describe("Verification Toggle", () => {
    it("should have verification toggle", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      // Toggle uses role="switch", not checkbox
      expect(
        screen.getByRole("switch", { name: /enable verification/i }),
      ).toBeInTheDocument();
    });

    it("should toggle verification when clicked", async () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      await waitFor(() => {
        // Toggle uses role="switch" with aria-checked
        const toggle = screen.getByRole("switch", {
          name: /enable verification/i,
        });
        expect(toggle).toHaveAttribute("aria-checked", "true");
        fireEvent.click(toggle);
        expect(toggle).toHaveAttribute("aria-checked", "false");
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should have refresh button", () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      expect(screen.getByText(/Refresh/i)).toBeInTheDocument();
    });

    it("should call refetch when refresh is clicked", async () => {
      render(
        <AgentsPageTestWrapper>
          <AgentsPage />
        </AgentsPageTestWrapper>,
      );

      const refreshButton = screen.getByText(/Refresh/i);
      fireEvent.click(refreshButton);

      // Should call refetch
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });
});

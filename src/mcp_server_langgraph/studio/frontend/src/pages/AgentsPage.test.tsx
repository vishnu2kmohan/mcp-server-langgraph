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
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { AgentsPage } from "./AgentsPage";
import { TestRouter } from "../test-utils";

// Mock the RTK Query hook
const mockRefetch = vi.fn();

vi.mock("../api", () => ({
  useGetAgentConfigQuery: vi.fn(),
}));

import { useGetAgentConfigQuery } from "../api";

// Cast to vi.Mock for type safety
const mockUseGetAgentConfigQuery = useGetAgentConfigQuery as ReturnType<
  typeof vi.fn
>;

// Default mock data
const mockConfig = {
  model: "gemini-2.5-flash",
  provider: "google",
  temperature: 0.7,
  verification_enabled: true,
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText("Agent Configuration")).toBeInTheDocument();
    });

    it("should display page description", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(
        screen.getByText(/Configure your LangGraph agent/),
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText(/gemini-2.5-flash/)).toBeInTheDocument();
    });

    it("should display temperature value", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText(/0.7/)).toBeInTheDocument();
    });

    it("should display verification status", async () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /verification/i,
        });
        expect(checkbox).toBeChecked();
      });
    });
  });

  describe("Tools List", () => {
    it("should display available tools", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText("calculator")).toBeInTheDocument();
      expect(screen.getByText("web_search")).toBeInTheDocument();
    });

    it("should display tool count", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
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
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText(/No tools available/)).toBeInTheDocument();
    });
  });

  describe("Model Selection", () => {
    it("should have model dropdown", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByLabelText(/Model/i)).toBeInTheDocument();
    });
  });

  describe("Temperature Control", () => {
    it("should have temperature slider", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByLabelText(/Temperature/i)).toBeInTheDocument();
    });

    it("should update temperature value when slider changes", async () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      await waitFor(() => {
        const slider = screen.getByLabelText(/Temperature/i);
        fireEvent.change(slider, { target: { value: "0.9" } });
        expect(screen.getByText(/0.9/)).toBeInTheDocument();
      });
    });
  });

  describe("Verification Toggle", () => {
    it("should have verification checkbox", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(
        screen.getByRole("checkbox", { name: /verification/i }),
      ).toBeInTheDocument();
    });

    it("should toggle verification when clicked", async () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      await waitFor(() => {
        const checkbox = screen.getByRole("checkbox", {
          name: /verification/i,
        });
        expect(checkbox).toBeChecked();
        fireEvent.click(checkbox);
        expect(checkbox).not.toBeChecked();
      });
    });
  });

  describe("Refresh Functionality", () => {
    it("should have refresh button", () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      expect(screen.getByText(/Refresh/i)).toBeInTheDocument();
    });

    it("should call refetch when refresh is clicked", async () => {
      render(
        <TestRouter>
          <AgentsPage />
        </TestRouter>,
      );

      const refreshButton = screen.getByText(/Refresh/i);
      fireEvent.click(refreshButton);

      // Should call refetch
      expect(mockRefetch).toHaveBeenCalledTimes(1);
    });
  });
});

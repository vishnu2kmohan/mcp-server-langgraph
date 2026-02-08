/**
 * SimilarSessionsPanel Tests
 *
 * TDD tests for the Similar Sessions panel component.
 * Tests cover:
 * - Loading states
 * - Similar sessions display
 * - Session navigation
 * - Empty state
 * - Error handling
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { SimilarSessionsPanel } from "./SimilarSessionsPanel";

// Mock the useSessionSimilarity hook
vi.mock("../../hooks/useSessionIntelligence", () => ({
  useSessionSimilarity: vi.fn(() => ({
    similarSessions: [],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Import the mocked hook for test manipulation
import { useSessionSimilarity } from "../../hooks/useSessionIntelligence";
import { TestProvider } from "@/test-utils";
const mockUseSessionSimilarity = useSessionSimilarity as ReturnType<
  typeof vi.fn
>;

expect.extend(toHaveNoViolations);

describe("SimilarSessionsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseSessionSimilarity.mockReturnValue({
      similarSessions: [],
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    });
  });

  afterEach(() => {
    cleanup();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the panel with title when sessions exist", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      expect(
        screen.getByRole("heading", { name: /similar sessions/i }),
      ).toBeInTheDocument();
    });

    it("should show loading skeleton when loading", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [],
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("similar-sessions-loading"),
      ).toBeInTheDocument();
    });

    it("should display similar sessions when loaded", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React", "TypeScript"],
          },
          {
            sessionId: "similar-2",
            similarityScore: 0.72,
            commonTopics: ["Testing"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel
            sessionId="session-123"
            userId="user-123"
            sessionNames={{
              "similar-1": "React Component Work",
              "similar-2": "Testing Strategy",
            }}
          />
        </TestProvider>,
      );

      expect(screen.getByText("React Component Work")).toBeInTheDocument();
      expect(screen.getByText("Testing Strategy")).toBeInTheDocument();
      expect(screen.getByText("85%")).toBeInTheDocument();
      expect(screen.getByText("72%")).toBeInTheDocument();
    });

    it("should render nothing when no similar sessions found", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      // Component returns null when no similar sessions
      expect(container.firstChild).toBeNull();
    });
  });

  // ===========================================================================
  // Session Navigation Tests
  // ===========================================================================

  describe("session navigation", () => {
    it("should call onSessionSelect when a similar session is clicked", async () => {
      const onSessionSelect = vi.fn();
      const user = userEvent.setup();

      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel
            sessionId="session-123"
            userId="user-123"
            sessionNames={{ "similar-1": "React Work" }}
            onSessionSelect={onSessionSelect}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("React Work"));

      expect(onSessionSelect).toHaveBeenCalledWith("similar-1");
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe("error handling", () => {
    it("should display error message when fetch fails", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [],
        isLoading: false,
        error: new Error("Failed to fetch similar sessions"),
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      expect(screen.getByTestId("similar-sessions-error")).toBeInTheDocument();
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });

    it("should provide retry button on error", async () => {
      const mockRefetch = vi.fn();
      const user = userEvent.setup();

      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [],
        isLoading: false,
        error: new Error("Failed to fetch"),
        refetch: mockRefetch,
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /retry/i }));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Topic Display Tests
  // ===========================================================================

  describe("topic display", () => {
    it("should display common topics as badges", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React", "TypeScript", "Testing"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel
            sessionId="session-123"
            userId="user-123"
            sessionNames={{ "similar-1": "Work Session" }}
          />
        </TestProvider>,
      );

      expect(screen.getByText("React")).toBeInTheDocument();
      expect(screen.getByText("TypeScript")).toBeInTheDocument();
      expect(screen.getByText("Testing")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      const { container } = render(
        <TestProvider>
          <SimilarSessionsPanel
            sessionId="session-123"
            userId="user-123"
            sessionNames={{ "similar-1": "Work Session" }}
          />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper heading structure when sessions exist", () => {
      mockUseSessionSimilarity.mockReturnValue({
        similarSessions: [
          {
            sessionId: "similar-1",
            similarityScore: 0.85,
            commonTopics: ["React"],
          },
        ],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
      });

      render(
        <TestProvider>
          <SimilarSessionsPanel sessionId="session-123" userId="user-123" />
        </TestProvider>,
      );

      expect(screen.getByRole("heading")).toBeInTheDocument();
    });
  });
});

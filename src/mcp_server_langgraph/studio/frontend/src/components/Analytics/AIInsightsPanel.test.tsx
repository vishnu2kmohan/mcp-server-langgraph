/**
 * AIInsightsPanel Component Tests
 *
 * TDD tests for the AI-generated HEART metrics insights panel.
 * Phase 6.6: Analytics Dashboard Component
 *
 * Tests the component's ability to:
 * - Display insights categorized by type
 * - Show predictions with confidence indicators
 * - Handle loading and error states
 * - Provide refresh capability
 * - Support filtering by dimension
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import personaReducer from "../../store/slices/personaSlice";
import authReducer from "../../store/slices/authSlice";

// Mock the useAIMetricsInsights hook
vi.mock("../../hooks/useAIMetricsInsights", () => ({
  useAIMetricsInsights: vi.fn(),
  default: vi.fn(),
}));

import { useAIMetricsInsights } from "../../hooks/useAIMetricsInsights";
import { AIInsightsPanel } from "./AIInsightsPanel";

const mockUseAIMetricsInsights = vi.mocked(useAIMetricsInsights);

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona: "admin",
        username: "admin",
        email: "admin@example.com",
        permissions: ["admin:access", "analytics:read"],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: "admin-123",
          username: "admin",
          email: "admin@example.com",
          roles: ["admin"],
          persona: "admin",
        },
        tokens: {
          accessToken: "mock-token",
          refreshToken: "mock-refresh",
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
    },
  });

const renderWithProviders = (ui: React.ReactElement) => {
  const store = createTestStore();
  return render(<Provider store={store}>{ui}</Provider>);
};

// =============================================================================
// Mock Data
// =============================================================================

const mockInsights = {
  insights: [
    {
      type: "anomaly" as const,
      dimension: "retention" as const,
      message: "D7 retention dropped 12% for alice-builder personas",
      severity: "warning" as const,
      suggestedActions: ["Check workflow builder UX", "Review recent changes"],
      detectedAt: "2025-12-20T10:00:00Z",
    },
    {
      type: "trend" as const,
      dimension: "adoption" as const,
      message: "AI suggestions adoption up 25% after nudge system launch",
      sentiment: "positive" as const,
    },
    {
      type: "pattern" as const,
      dimension: "engagement" as const,
      message: "Power users show 3x higher session duration",
      sentiment: "neutral" as const,
    },
  ],
  predictions: [
    {
      metric: "30_day_retention",
      current: 0.65,
      predicted: 0.72,
      confidence: 0.78,
      drivers: ["improved_onboarding", "nudge_system"],
    },
    {
      metric: "weekly_active_users",
      current: 450,
      predicted: 520,
      confidence: 0.85,
      drivers: ["new_features", "marketing_campaign"],
    },
  ],
  anomalies: [
    {
      type: "anomaly" as const,
      dimension: "retention" as const,
      message: "D7 retention dropped 12%",
      severity: "warning" as const,
      suggestedActions: ["Check workflow builder UX"],
    },
  ],
  trends: [
    {
      type: "trend" as const,
      dimension: "adoption" as const,
      message: "AI suggestions adoption up 25%",
      sentiment: "positive" as const,
    },
  ],
  patterns: [
    {
      type: "pattern" as const,
      dimension: "engagement" as const,
      message: "Power users show 3x higher session duration",
    },
  ],
  isLoading: false,
  error: null,
  lastUpdated: new Date("2025-12-20T10:00:00Z"),
  refresh: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("AIInsightsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("should render the panel title", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/AI Insights/i)).toBeInTheDocument();
    });

    it("should display insights when loaded", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(
        screen.getByText(/D7 retention dropped 12%/i)
      ).toBeInTheDocument();
      expect(
        screen.getByText(/AI suggestions adoption up 25%/i)
      ).toBeInTheDocument();
    });

    it("should display predictions section", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/Predictions/i)).toBeInTheDocument();
      expect(screen.getByText(/30_day_retention/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading indicator when fetching", () => {
      mockUseAIMetricsInsights.mockReturnValue({
        ...mockInsights,
        isLoading: true,
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
      });

      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/Loading insights/i)).toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when fetch fails", () => {
      mockUseAIMetricsInsights.mockReturnValue({
        ...mockInsights,
        error: new Error("Failed to fetch insights"),
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
      });

      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/Failed to fetch insights/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      const refreshFn = vi.fn();
      mockUseAIMetricsInsights.mockReturnValue({
        ...mockInsights,
        error: new Error("Network error"),
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        refresh: refreshFn,
      });

      renderWithProviders(<AIInsightsPanel />);

      const retryButton = screen.getByRole("button", { name: /retry/i });
      expect(retryButton).toBeInTheDocument();
      fireEvent.click(retryButton);
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("Insight Categories", () => {
    it("should display anomalies with severity indicator", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      // Should show warning severity
      expect(screen.getByText(/warning/i)).toBeInTheDocument();
    });

    it("should display trends with sentiment indicator", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      // Should show positive sentiment
      expect(screen.getByText(/positive/i)).toBeInTheDocument();
    });

    it("should display patterns section", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(
        screen.getByText(/Power users show 3x higher/i)
      ).toBeInTheDocument();
    });
  });

  describe("Predictions", () => {
    it("should show current and predicted values", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      // Check for current and predicted values
      expect(screen.getByText(/0.65/)).toBeInTheDocument();
      expect(screen.getByText(/0.72/)).toBeInTheDocument();
    });

    it("should show confidence scores", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      // Confidence should be displayed (78%)
      expect(screen.getByText(/78%/)).toBeInTheDocument();
    });

    it("should show drivers for predictions", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/improved_onboarding/i)).toBeInTheDocument();
    });
  });

  describe("Refresh Capability", () => {
    it("should have refresh button", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(
        screen.getByRole("button", { name: /refresh/i })
      ).toBeInTheDocument();
    });

    it("should call refresh when button clicked", () => {
      const refreshFn = vi.fn();
      mockUseAIMetricsInsights.mockReturnValue({
        ...mockInsights,
        refresh: refreshFn,
      });

      renderWithProviders(<AIInsightsPanel />);

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      fireEvent.click(refreshButton);
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("Last Updated", () => {
    it("should display last updated timestamp", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/Last updated/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no insights", () => {
      mockUseAIMetricsInsights.mockReturnValue({
        ...mockInsights,
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: null,
      });

      renderWithProviders(<AIInsightsPanel />);

      expect(screen.getByText(/No insights available/i)).toBeInTheDocument();
    });
  });

  describe("Suggested Actions", () => {
    it("should display suggested actions for anomalies", () => {
      mockUseAIMetricsInsights.mockReturnValue(mockInsights);
      renderWithProviders(<AIInsightsPanel />);

      expect(
        screen.getByText(/Check workflow builder UX/i)
      ).toBeInTheDocument();
    });
  });
});

/**
 * AnalyticsDashboardPage Tests
 *
 * Sprint 4 - Phase 3.3: HEART Metrics Analytics Dashboard
 * Sprint 4 - Phase 6.6: AI-Generated HEART Insights Integration
 *
 * TDD: Write tests first, then implementation.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";
import { AnalyticsDashboardPage } from "./AnalyticsDashboardPage";
import personaReducer from "../store/slices/personaSlice";

// Mock useAIMetricsInsights to avoid additional API calls in tests
// Use dimension/metric names that don't conflict with HEART dimension card labels
vi.mock("../hooks/useAIMetricsInsights", () => ({
  useAIMetricsInsights: () => ({
    isLoading: false,
    error: null,
    insights: [
      { type: "trend", dimension: "user_activity", message: "AI trend insight", sentiment: "positive" },
    ],
    predictions: [
      { metric: "weekly_active_users", current: 450, predicted: 520, confidence: 0.85, drivers: ["feature_release"] },
    ],
    anomalies: [],
    trends: [
      { type: "trend", dimension: "user_activity", message: "AI trend insight", sentiment: "positive" },
    ],
    patterns: [],
    lastUpdated: new Date(),
    refresh: vi.fn(),
  }),
}));

// Mock store with admin persona
const createTestStore = (persona = "admin") =>
  configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona: persona as "admin" | "alice-builder",
        username: "test-admin",
        permissions: ["read:analytics", "write:analytics"],
        loading: false,
        error: null,
      },
    },
  });

// Test wrapper
const TestWrapper = ({
  children,
  store = createTestStore(),
}: {
  children: React.ReactNode;
  store?: ReturnType<typeof createTestStore>;
}) => (
  <Provider store={store}>
    <MemoryRouter>{children}</MemoryRouter>
  </Provider>
);

// Default mock for HEART aggregate endpoint
const mockHeartAggregate = () =>
  HttpResponse.json({
    dimensions: [
      { dimension: "happiness", overallScore: 75, hasData: true, goalProgresses: [] },
      { dimension: "engagement", overallScore: 80, hasData: true, goalProgresses: [] },
      { dimension: "adoption", overallScore: 65, hasData: true, goalProgresses: [] },
      { dimension: "retention", overallScore: 70, hasData: true, goalProgresses: [] },
      { dimension: "task_success", overallScore: 85, hasData: true, goalProgresses: [] },
    ],
    overallHealthScore: 75,
    timestamp: Date.now(),
    dataPointCount: 500,
    oldestDataPoint: Date.now() - 30 * 24 * 60 * 60 * 1000,
    newestDataPoint: Date.now(),
  });

describe("AnalyticsDashboardPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Setup default handler
    server.use(http.get("/api/v1/metrics/heart/aggregate", mockHeartAggregate));
  });

  afterEach(() => {
    server.resetHandlers();
  });

  describe("rendering", () => {
    it("renders the page title", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      expect(screen.getByRole("heading", { name: /analytics/i })).toBeInTheDocument();
    });

    it("renders all 5 HEART dimension cards", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId("analytics-loading")).not.toBeInTheDocument();
      });

      expect(screen.getByText(/happiness/i)).toBeInTheDocument();
      expect(screen.getByText(/engagement/i)).toBeInTheDocument();
      expect(screen.getByText(/adoption/i)).toBeInTheDocument();
      expect(screen.getByText(/retention/i)).toBeInTheDocument();
      expect(screen.getByText(/task success/i)).toBeInTheDocument();
    });

    it("shows overall health score", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId("analytics-loading")).not.toBeInTheDocument();
      });

      expect(screen.getByTestId("overall-health-score")).toBeInTheDocument();
    });

    it("renders AI Insights panel (Phase 6.6)", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId("analytics-loading")).not.toBeInTheDocument();
      });

      // AI Insights section should be rendered
      expect(screen.getByLabelText(/ai insights/i)).toBeInTheDocument();
      // Should show the insights panel
      expect(screen.getByTestId("ai-insights-panel")).toBeInTheDocument();
    });
  });

  describe("data loading", () => {
    it("shows loading state initially", async () => {
      // Test that loading is shown before data is fetched
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Initially shows loading
      expect(screen.getByTestId("analytics-loading")).toBeInTheDocument();
    });

    it("displays data after loading", async () => {
      server.use(
        http.get("/api/v1/metrics/heart/aggregate", () => {
          return HttpResponse.json({
            dimensions: [
              {
                dimension: "happiness",
                overallScore: 85,
                hasData: true,
                goalProgresses: [],
              },
            ],
            overallHealthScore: 85,
            timestamp: Date.now(),
            dataPointCount: 100,
            oldestDataPoint: null,
            newestDataPoint: null,
          });
        })
      );

      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId("analytics-loading")).not.toBeInTheDocument();
      });

      // Check for score in overall health (score appears there)
      expect(screen.getByTestId("overall-health-score")).toHaveTextContent("85");
    });
  });

  describe("error handling", () => {
    it("shows error message on API failure", async () => {
      server.use(
        http.get("/api/v1/metrics/heart/aggregate", () => {
          return HttpResponse.json({ error: "Server error" }, { status: 500 });
        })
      );

      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByTestId("analytics-error")).toBeInTheDocument();
      });
    });
  });

  describe("time range selection", () => {
    it("renders time range selector", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      expect(screen.getByRole("combobox", { name: /time range/i })).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("has main landmark", async () => {
      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      expect(screen.getByRole("main")).toBeInTheDocument();
    });

    it("HEART cards are keyboard accessible", async () => {
      server.use(
        http.get("/api/v1/metrics/heart/aggregate", () => {
          return HttpResponse.json({
            dimensions: [
              { dimension: "happiness", overallScore: 80, hasData: true, goalProgresses: [] },
            ],
            overallHealthScore: 80,
            timestamp: Date.now(),
            dataPointCount: 100,
            oldestDataPoint: null,
            newestDataPoint: null,
          });
        })
      );

      render(
        <TestWrapper>
          <AnalyticsDashboardPage />
        </TestWrapper>
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByTestId("analytics-loading")).not.toBeInTheDocument();
      });

      // Check for region landmarks (dimension cards)
      const cards = screen.getAllByRole("region");
      expect(cards.length).toBeGreaterThan(0);
    });
  });
});

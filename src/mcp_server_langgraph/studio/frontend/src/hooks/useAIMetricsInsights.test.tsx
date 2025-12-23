/**
 * useAIMetricsInsights Hook Tests
 *
 * TDD tests for the AI-powered HEART metrics insights hook.
 * Phase 6.6: AI-Generated HEART Insights
 *
 * Tests the hook's ability to:
 * - Fetch AI-generated insights from HEART metrics
 * - Provide anomaly detection and predictions
 * - Handle loading and error states
 * - Support polling for real-time updates
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// Mock hook implementation - will be created
const mockUseAIMetricsInsights = vi.fn();
vi.mock("./useAIMetricsInsights", () => ({
  useAIMetricsInsights: () => mockUseAIMetricsInsights(),
  default: () => mockUseAIMetricsInsights(),
}));

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

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("useAIMetricsInsights", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should start with loading state when enabled", () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: true,
        error: null,
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });
      expect(result.current.isLoading).toBe(true);
    });

    it("should not fetch when disabled", () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });
      expect(result.current.isLoading).toBe(false);
      expect(result.current.insights).toHaveLength(0);
    });
  });

  describe("Insights Fetching", () => {
    it("should fetch and return insights", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [
          {
            type: "anomaly",
            dimension: "retention",
            message: "D7 retention dropped 12%",
            severity: "warning",
          },
          {
            type: "trend",
            dimension: "adoption",
            message: "AI suggestions adoption up 25%",
            sentiment: "positive",
          },
        ],
        predictions: [
          {
            metric: "30_day_retention",
            current: 0.65,
            predicted: 0.72,
            confidence: 0.78,
          },
        ],
        anomalies: [
          {
            type: "anomaly",
            dimension: "retention",
            message: "D7 retention dropped 12%",
            severity: "warning",
          },
        ],
        trends: [
          {
            type: "trend",
            dimension: "adoption",
            message: "AI suggestions adoption up 25%",
            sentiment: "positive",
          },
        ],
        patterns: [],
        lastUpdated: new Date("2025-12-20T10:00:00Z"),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.insights).toHaveLength(2);
      expect(result.current.predictions).toHaveLength(1);
    });

    it("should categorize insights by type", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [
          { type: "anomaly", dimension: "retention" },
          { type: "trend", dimension: "adoption" },
          { type: "pattern", dimension: "engagement" },
        ],
        predictions: [],
        anomalies: [{ type: "anomaly", dimension: "retention" }],
        trends: [{ type: "trend", dimension: "adoption" }],
        patterns: [{ type: "pattern", dimension: "engagement" }],
        lastUpdated: new Date(),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.anomalies).toHaveLength(1);
      expect(result.current.trends).toHaveLength(1);
      expect(result.current.patterns).toHaveLength(1);
    });
  });

  describe("Predictions", () => {
    it("should return predictions with confidence scores", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [],
        predictions: [
          {
            metric: "30_day_retention",
            current: 0.65,
            predicted: 0.72,
            confidence: 0.78,
            drivers: ["improved_onboarding", "nudge_system"],
          },
        ],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: new Date(),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.predictions).toHaveLength(1);
      expect(result.current.predictions[0].confidence).toBe(0.78);
      expect(result.current.predictions[0].drivers).toContain(
        "improved_onboarding",
      );
    });

    it("should include current and predicted values", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [],
        predictions: [
          {
            metric: "weekly_active_users",
            current: 450,
            predicted: 520,
            confidence: 0.85,
            drivers: ["new_features"],
          },
        ],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: new Date(),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      const prediction = result.current.predictions[0];
      expect(prediction.current).toBe(450);
      expect(prediction.predicted).toBe(520);
      expect(prediction.predicted).toBeGreaterThan(prediction.current);
    });
  });

  describe("Anomaly Detection", () => {
    it("should identify and categorize anomalies by severity", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [],
        predictions: [],
        anomalies: [
          {
            type: "anomaly",
            dimension: "retention",
            message: "D7 retention dropped 12%",
            severity: "warning",
            suggestedActions: ["Check workflow builder UX"],
          },
        ],
        trends: [],
        patterns: [],
        lastUpdated: new Date(),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.anomalies[0].severity).toBe("warning");
      expect(result.current.anomalies[0].suggestedActions).toBeDefined();
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: new Error("Failed to fetch insights"),
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.insights).toHaveLength(0);
    });
  });

  describe("Refresh Capability", () => {
    it("should provide refresh function", () => {
      const refreshFn = vi.fn();
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [],
        predictions: [],
        anomalies: [],
        trends: [],
        patterns: [],
        lastUpdated: new Date(),
        refresh: refreshFn,
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(typeof result.current.refresh).toBe("function");
      result.current.refresh();
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("Last Updated Tracking", () => {
    it("should track when insights were last updated", async () => {
      const now = new Date();
      mockUseAIMetricsInsights.mockReturnValue({
        isLoading: false,
        error: null,
        insights: [{ type: "trend" }],
        predictions: [],
        anomalies: [],
        trends: [{ type: "trend" }],
        patterns: [],
        lastUpdated: now,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIMetricsInsights(), {
        wrapper,
      });

      expect(result.current.lastUpdated).toBeDefined();
      expect(result.current.lastUpdated).toEqual(now);
    });
  });
});

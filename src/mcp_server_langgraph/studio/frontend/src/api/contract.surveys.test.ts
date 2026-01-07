/**
 * API Contract Tests - SUS Surveys, HEART Analytics, and Compliance
 *
 * Tests for survey and analytics endpoints.
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isSUSSurveyResponse,
  isSUSSummaryResponse,
  isMetricTrackingResponse,
  isHEARTAnalyticsSummary,
  isComplianceReport,
  isComplianceSummary,
} from "./contract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
});

// =============================================================================
// SUS Surveys Endpoints Tests
// =============================================================================

describe("SUS Surveys Endpoints", () => {
  it("should validate SUSSurveyResponse schema", () => {
    const validResponse = {
      id: "survey-000001",
      sus_score: 72.5,
      recorded_at: "2025-01-15T10:30:00Z",
    };
    expect(isSUSSurveyResponse(validResponse)).toBe(true);
  });

  it("should validate SUSSummaryResponse schema", () => {
    const validResponse = {
      timeframe: "30d",
      avg_score: 68.5,
      response_count: 150,
      score_distribution: {
        excellent: 20,
        good: 50,
        ok: 60,
        poor: 20,
      },
    };
    expect(isSUSSummaryResponse(validResponse)).toBe(true);
  });

  it("should allow null avg_score in SUSSummaryResponse", () => {
    const responseWithNull = {
      timeframe: "7d",
      avg_score: null,
      response_count: 0,
      score_distribution: {
        excellent: 0,
        good: 0,
        ok: 0,
        poor: 0,
      },
    };
    expect(isSUSSummaryResponse(responseWithNull)).toBe(true);
  });
});

// =============================================================================
// HEART Analytics Endpoints Tests
// =============================================================================

describe("HEART Analytics Endpoints", () => {
  it("should validate metric tracking response", () => {
    const validResponse = {
      success: true,
      metric_id: "metric-001",
      recorded_at: "2025-01-15T10:30:00Z",
    };
    expect(isMetricTrackingResponse(validResponse)).toBe(true);
  });

  it("should validate HEART analytics summary", () => {
    const validResponse = {
      period: "7d",
      happiness: { avg_score: 4.2, response_count: 100 },
      engagement: { avg_session_duration_ms: 300000, active_users: 50 },
      adoption: { new_users: 25, activation_rate: 0.75 },
      retention: { returning_users: 80, churn_rate: 0.05 },
      task_success: { completion_rate: 0.85, avg_time_ms: 5000 },
    };
    expect(isHEARTAnalyticsSummary(validResponse)).toBe(true);
  });
});

// =============================================================================
// Compliance Reports Endpoints Tests
// =============================================================================

describe("Compliance Reports Endpoints", () => {
  it("should validate GDPR report schema", () => {
    const validResponse = {
      regulation: "GDPR",
      generated_at: "2025-01-15T10:30:00Z",
      time_range: {
        start: "2025-01-01T00:00:00Z",
        end: "2025-01-15T00:00:00Z",
      },
      processing_activities: [],
      data_subject_requests: { total: 0, completed: 0, pending: 0 },
    };
    expect(isComplianceReport(validResponse)).toBe(true);
  });

  it("should validate compliance summary schema", () => {
    const validResponse = {
      generated_at: "2025-01-15T10:30:00Z",
      regulations: ["GDPR", "HIPAA", "SOC2", "FedRAMP", "EU_AI_Act"],
      overall_status: "compliant",
      findings: [],
    };
    expect(isComplianceSummary(validResponse)).toBe(true);
  });
});

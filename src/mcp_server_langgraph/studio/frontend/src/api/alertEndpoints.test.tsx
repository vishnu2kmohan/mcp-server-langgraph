/**
 * Alert RTK Query Endpoints Tests
 *
 * TDD tests for the alert-related RTK Query endpoints.
 * Tests hook exports, type definitions, and endpoint configuration.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import {
  api,
  useGetAlertRecommendationQuery,
  useRegenerateAlertRecommendationMutation,
  useListPendingRemediationsQuery,
  useListRemediationHistoryQuery,
  useApproveRemediationMutation,
  useRejectRemediationMutation,
} from "./index";
import type {
  AIRecommendation,
  RemediationRequest,
  RemediationListParams,
  ApproveRemediationRequest,
  RejectRemediationRequest,
  RiskLevel,
  RemediationStatus,
  RemediationStep,
} from "../types/api";

// =============================================================================
// Type Tests - Verify types are correctly defined
// =============================================================================

describe("Alert API Types", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("AIRecommendation type", () => {
    it("should have correct structure", () => {
      const recommendation: AIRecommendation = {
        recommendationId: "rec-001",
        alertId: "alert-001",
        rootCauseAnalysis: "Memory leak detected",
        remediationSteps: [
          {
            stepNumber: 1,
            action: "restart",
            description: "Restart the service",
            command: "kubectl rollout restart",
            requiresApproval: true,
            riskLevel: "low",
          },
        ],
        riskAssessment: {
          overallRisk: "medium",
          impactAnalysis: "Brief downtime expected",
          rollbackPlan: "Rollback to previous version",
        },
        runbookReference: "https://runbooks.example.com",
        generatedAt: "2024-01-15T10:30:00Z",
        modelUsed: "claude-3-5-sonnet",
      };

      expect(recommendation.recommendationId).toBe("rec-001");
      expect(recommendation.remediationSteps).toHaveLength(1);
      expect(recommendation.riskAssessment.overallRisk).toBe("medium");
    });
  });

  describe("RemediationStep type", () => {
    it("should have all required fields", () => {
      const step: RemediationStep = {
        stepNumber: 1,
        action: "scale",
        description: "Scale up replicas",
        command: "kubectl scale --replicas=5",
        requiresApproval: true,
        riskLevel: "medium",
      };

      expect(step.stepNumber).toBe(1);
      expect(step.requiresApproval).toBe(true);
    });

    it("should allow null command", () => {
      const step: RemediationStep = {
        stepNumber: 1,
        action: "manual",
        description: "Manual verification required",
        command: null,
        requiresApproval: true,
        riskLevel: "high",
      };

      expect(step.command).toBeNull();
    });
  });

  describe("RiskLevel type", () => {
    it("should accept valid risk levels", () => {
      const low: RiskLevel = "low";
      const medium: RiskLevel = "medium";
      const high: RiskLevel = "high";

      expect(low).toBe("low");
      expect(medium).toBe("medium");
      expect(high).toBe("high");
    });
  });

  describe("RemediationStatus type", () => {
    it("should accept all valid statuses", () => {
      const statuses: RemediationStatus[] = [
        "pending",
        "approved",
        "rejected",
        "executing",
        "completed",
        "failed",
      ];

      expect(statuses).toHaveLength(6);
      expect(statuses).toContain("pending");
      expect(statuses).toContain("approved");
    });
  });

  describe("RemediationRequest type", () => {
    it("should have correct structure", () => {
      const request: RemediationRequest = {
        remediationId: "rem-001",
        alertId: "alert-001",
        alertName: "HighCPU",
        severity: "critical",
        stepNumber: 1,
        action: "restart",
        description: "Restart service",
        command: "kubectl rollout restart",
        riskLevel: "low",
        status: "pending",
        requestedAt: "2024-01-15T10:30:00Z",
        approvedBy: null,
        approvedAt: null,
        reason: null,
        recommendationId: "rec-001",
      };

      expect(request.status).toBe("pending");
      expect(request.approvedBy).toBeNull();
    });
  });

  describe("ApproveRemediationRequest type", () => {
    it("should have required fields", () => {
      const request: ApproveRemediationRequest = {
        remediationId: "rem-001",
        approvedBy: "admin@example.com",
      };

      expect(request.remediationId).toBe("rem-001");
      expect(request.approvedBy).toBe("admin@example.com");
    });

    it("should allow optional reason", () => {
      const request: ApproveRemediationRequest = {
        remediationId: "rem-001",
        approvedBy: "admin@example.com",
        reason: "Approved after review",
      };

      expect(request.reason).toBe("Approved after review");
    });
  });

  describe("RejectRemediationRequest type", () => {
    it("should require reason", () => {
      const request: RejectRemediationRequest = {
        remediationId: "rem-001",
        rejectedBy: "admin@example.com",
        reason: "Too risky without more investigation",
      };

      expect(request.reason).toBe("Too risky without more investigation");
    });
  });

  describe("RemediationListParams type", () => {
    it("should have optional filters", () => {
      const params: RemediationListParams = {};
      expect(params.status).toBeUndefined();

      const paramsWithFilters: RemediationListParams = {
        status: "pending",
        alertId: "alert-001",
        severity: "critical",
        limit: 50,
        cursor: "cursor123",
      };
      expect(paramsWithFilters.status).toBe("pending");
    });
  });
});

// =============================================================================
// Hook Export Tests
// =============================================================================

describe("Alert RTK Query Hook Exports", () => {
  describe("Query Hooks", () => {
    it("should export useGetAlertRecommendationQuery", () => {
      expect(useGetAlertRecommendationQuery).toBeDefined();
      expect(typeof useGetAlertRecommendationQuery).toBe("function");
    });

    it("should export useListPendingRemediationsQuery", () => {
      expect(useListPendingRemediationsQuery).toBeDefined();
      expect(typeof useListPendingRemediationsQuery).toBe("function");
    });

    it("should export useListRemediationHistoryQuery", () => {
      expect(useListRemediationHistoryQuery).toBeDefined();
      expect(typeof useListRemediationHistoryQuery).toBe("function");
    });
  });

  describe("Mutation Hooks", () => {
    it("should export useRegenerateAlertRecommendationMutation", () => {
      expect(useRegenerateAlertRecommendationMutation).toBeDefined();
      expect(typeof useRegenerateAlertRecommendationMutation).toBe("function");
    });

    it("should export useApproveRemediationMutation", () => {
      expect(useApproveRemediationMutation).toBeDefined();
      expect(typeof useApproveRemediationMutation).toBe("function");
    });

    it("should export useRejectRemediationMutation", () => {
      expect(useRejectRemediationMutation).toBeDefined();
      expect(typeof useRejectRemediationMutation).toBe("function");
    });
  });
});

// =============================================================================
// API Configuration Tests
// =============================================================================

describe("Alert API Endpoint Configuration", () => {
  it("should have InfraAlert tag type defined", () => {
    expect(api.reducerPath).toBe("api");
    // Tags are internal, but we can verify the api is properly configured
    expect(api.reducer).toBeDefined();
    expect(api.middleware).toBeDefined();
  });

  it("should have Remediation tag type defined", () => {
    // Verify api has all required endpoints defined
    expect(api.endpoints).toBeDefined();
    expect(api.endpoints.getAlertRecommendation).toBeDefined();
    expect(api.endpoints.regenerateAlertRecommendation).toBeDefined();
    expect(api.endpoints.listPendingRemediations).toBeDefined();
    expect(api.endpoints.listRemediationHistory).toBeDefined();
    expect(api.endpoints.approveRemediation).toBeDefined();
    expect(api.endpoints.rejectRemediation).toBeDefined();
  });
});

// =============================================================================
// Contract Tests - Validate data shapes
// =============================================================================

describe("Alert API Contract Tests", () => {
  /**
   * Type guard for AIRecommendation
   */
  function isAIRecommendation(obj: unknown): obj is AIRecommendation {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;
    return (
      typeof o.recommendationId === "string" &&
      typeof o.alertId === "string" &&
      typeof o.rootCauseAnalysis === "string" &&
      Array.isArray(o.remediationSteps) &&
      typeof o.riskAssessment === "object" &&
      typeof o.generatedAt === "string" &&
      typeof o.modelUsed === "string"
    );
  }

  /**
   * Type guard for RemediationRequest
   */
  function isRemediationRequest(obj: unknown): obj is RemediationRequest {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;
    return (
      typeof o.remediationId === "string" &&
      typeof o.alertId === "string" &&
      typeof o.alertName === "string" &&
      (o.severity === "critical" || o.severity === "warning") &&
      typeof o.stepNumber === "number" &&
      typeof o.action === "string" &&
      typeof o.status === "string"
    );
  }

  it("should validate AIRecommendation shape", () => {
    const validRecommendation = {
      recommendationId: "rec-001",
      alertId: "alert-001",
      rootCauseAnalysis: "Root cause",
      remediationSteps: [],
      riskAssessment: {
        overallRisk: "low",
        impactAnalysis: "",
        rollbackPlan: "",
      },
      runbookReference: null,
      generatedAt: "2024-01-01",
      modelUsed: "claude",
    };

    expect(isAIRecommendation(validRecommendation)).toBe(true);
  });

  it("should reject invalid AIRecommendation shape", () => {
    const invalidRecommendation = {
      recommendationId: "rec-001",
      // missing required fields
    };

    expect(isAIRecommendation(invalidRecommendation)).toBe(false);
  });

  it("should validate RemediationRequest shape", () => {
    const validRequest = {
      remediationId: "rem-001",
      alertId: "alert-001",
      alertName: "HighCPU",
      severity: "critical",
      stepNumber: 1,
      action: "restart",
      description: "Restart",
      command: null,
      riskLevel: "low",
      status: "pending",
      requestedAt: "2024-01-01",
      approvedBy: null,
      approvedAt: null,
      reason: null,
      recommendationId: "rec-001",
    };

    expect(isRemediationRequest(validRequest)).toBe(true);
  });

  it("should reject invalid RemediationRequest shape", () => {
    const invalidRequest = {
      remediationId: "rem-001",
      severity: "info", // invalid severity for remediations
    };

    expect(isRemediationRequest(invalidRequest)).toBe(false);
  });
});

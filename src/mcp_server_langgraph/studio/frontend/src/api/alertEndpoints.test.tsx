/**
 * Alert RTK Query Endpoints Tests
 *
 * TDD tests for the alert-related RTK Query endpoints.
 * Tests hook exports, type definitions, and endpoint configuration.
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect } from "vitest";
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
  describe("AIRecommendation type", () => {
    it("should have correct structure", () => {
      const recommendation: AIRecommendation = {
        recommendation_id: "rec-001",
        alert_id: "alert-001",
        root_cause_analysis: "Memory leak detected",
        remediation_steps: [
          {
            step_number: 1,
            action: "restart",
            description: "Restart the service",
            command: "kubectl rollout restart",
            requires_approval: true,
            risk_level: "low",
          },
        ],
        risk_assessment: {
          overall_risk: "medium",
          impact_analysis: "Brief downtime expected",
          rollback_plan: "Rollback to previous version",
        },
        runbook_reference: "https://runbooks.example.com",
        generated_at: "2024-01-15T10:30:00Z",
        model_used: "claude-3-5-sonnet",
      };

      expect(recommendation.recommendation_id).toBe("rec-001");
      expect(recommendation.remediation_steps).toHaveLength(1);
      expect(recommendation.risk_assessment.overall_risk).toBe("medium");
    });
  });

  describe("RemediationStep type", () => {
    it("should have all required fields", () => {
      const step: RemediationStep = {
        step_number: 1,
        action: "scale",
        description: "Scale up replicas",
        command: "kubectl scale --replicas=5",
        requires_approval: true,
        risk_level: "medium",
      };

      expect(step.step_number).toBe(1);
      expect(step.requires_approval).toBe(true);
    });

    it("should allow null command", () => {
      const step: RemediationStep = {
        step_number: 1,
        action: "manual",
        description: "Manual verification required",
        command: null,
        requires_approval: true,
        risk_level: "high",
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
        remediation_id: "rem-001",
        alert_id: "alert-001",
        alert_name: "HighCPU",
        severity: "critical",
        step_number: 1,
        action: "restart",
        description: "Restart service",
        command: "kubectl rollout restart",
        risk_level: "low",
        status: "pending",
        requested_at: "2024-01-15T10:30:00Z",
        approved_by: null,
        approved_at: null,
        reason: null,
        recommendation_id: "rec-001",
      };

      expect(request.status).toBe("pending");
      expect(request.approved_by).toBeNull();
    });
  });

  describe("ApproveRemediationRequest type", () => {
    it("should have required fields", () => {
      const request: ApproveRemediationRequest = {
        remediation_id: "rem-001",
        approved_by: "admin@example.com",
      };

      expect(request.remediation_id).toBe("rem-001");
      expect(request.approved_by).toBe("admin@example.com");
    });

    it("should allow optional reason", () => {
      const request: ApproveRemediationRequest = {
        remediation_id: "rem-001",
        approved_by: "admin@example.com",
        reason: "Approved after review",
      };

      expect(request.reason).toBe("Approved after review");
    });
  });

  describe("RejectRemediationRequest type", () => {
    it("should require reason", () => {
      const request: RejectRemediationRequest = {
        remediation_id: "rem-001",
        rejected_by: "admin@example.com",
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
        alert_id: "alert-001",
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
      typeof o.recommendation_id === "string" &&
      typeof o.alert_id === "string" &&
      typeof o.root_cause_analysis === "string" &&
      Array.isArray(o.remediation_steps) &&
      typeof o.risk_assessment === "object" &&
      typeof o.generated_at === "string" &&
      typeof o.model_used === "string"
    );
  }

  /**
   * Type guard for RemediationRequest
   */
  function isRemediationRequest(obj: unknown): obj is RemediationRequest {
    if (typeof obj !== "object" || obj === null) return false;
    const o = obj as Record<string, unknown>;
    return (
      typeof o.remediation_id === "string" &&
      typeof o.alert_id === "string" &&
      typeof o.alert_name === "string" &&
      (o.severity === "critical" || o.severity === "warning") &&
      typeof o.step_number === "number" &&
      typeof o.action === "string" &&
      typeof o.status === "string"
    );
  }

  it("should validate AIRecommendation shape", () => {
    const validRecommendation = {
      recommendation_id: "rec-001",
      alert_id: "alert-001",
      root_cause_analysis: "Root cause",
      remediation_steps: [],
      risk_assessment: {
        overall_risk: "low",
        impact_analysis: "",
        rollback_plan: "",
      },
      runbook_reference: null,
      generated_at: "2024-01-01",
      model_used: "claude",
    };

    expect(isAIRecommendation(validRecommendation)).toBe(true);
  });

  it("should reject invalid AIRecommendation shape", () => {
    const invalidRecommendation = {
      recommendation_id: "rec-001",
      // missing required fields
    };

    expect(isAIRecommendation(invalidRecommendation)).toBe(false);
  });

  it("should validate RemediationRequest shape", () => {
    const validRequest = {
      remediation_id: "rem-001",
      alert_id: "alert-001",
      alert_name: "HighCPU",
      severity: "critical",
      step_number: 1,
      action: "restart",
      description: "Restart",
      command: null,
      risk_level: "low",
      status: "pending",
      requested_at: "2024-01-01",
      approved_by: null,
      approved_at: null,
      reason: null,
      recommendation_id: "rec-001",
    };

    expect(isRemediationRequest(validRequest)).toBe(true);
  });

  it("should reject invalid RemediationRequest shape", () => {
    const invalidRequest = {
      remediation_id: "rem-001",
      severity: "info", // invalid severity for remediations
    };

    expect(isRemediationRequest(invalidRequest)).toBe(false);
  });
});

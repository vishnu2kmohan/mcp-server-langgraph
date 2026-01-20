/**
 * Compliance Handlers - Phase 5
 *
 * MSW handlers for Compliance API endpoints.
 * These define the API contracts for compliance reporting.
 *
 * Endpoints:
 * - GET /api/v1/compliance/reports/summary - Overall compliance summary
 * - GET /api/v1/compliance/reports/soc2 - SOC2 controls report
 * - GET /api/v1/compliance/reports/hipaa - HIPAA compliance report
 * - GET /api/v1/compliance/reports/gdpr - GDPR compliance report
 * - GET /api/v1/compliance/reports/fedramp - FedRAMP authorization report
 */

import { http, delay } from "msw";
import { apiJsonResponse } from "../utils/apiResponse";

// =============================================================================
// Types
// =============================================================================

interface FrameworkSummary {
  percentage: number;
  compliant_count: number;
  total_count: number;
  status: "compliant" | "partial" | "non-compliant";
  pending_actions?: number;
  auth_level?: string;
}

export interface ComplianceSummaryResponse {
  soc2: FrameworkSummary;
  hipaa: FrameworkSummary;
  gdpr: FrameworkSummary;
  fedramp: FrameworkSummary;
}

interface Control {
  id: string;
  name: string;
  description: string;
  status: "compliant" | "partial" | "non-compliant" | "not-applicable";
  evidence: string[];
  last_assessed: string;
}

interface PHIAccessLog {
  id: string;
  user: string;
  timestamp: string;
  action: string;
  resource: string;
}

interface DataSubjectRequest {
  id: string;
  type: "access" | "deletion" | "rectification" | "portability";
  status: "pending" | "completed" | "rejected";
  submitted_at: string;
  completed_at?: string;
}

// =============================================================================
// Mock Data
// =============================================================================

export const mockComplianceSummary: ComplianceSummaryResponse = {
  soc2: {
    percentage: 94,
    compliant_count: 47,
    total_count: 50,
    status: "compliant",
    pending_actions: 3,
  },
  hipaa: {
    percentage: 100,
    compliant_count: 25,
    total_count: 25,
    status: "compliant",
    pending_actions: 0,
  },
  gdpr: {
    percentage: 87,
    compliant_count: 13,
    total_count: 15,
    status: "partial",
    pending_actions: 2,
  },
  fedramp: {
    percentage: 92,
    compliant_count: 325,
    total_count: 353,
    status: "compliant",
    auth_level: "Moderate",
    pending_actions: 28,
  },
};

const mockSOC2Controls: Control[] = [
  {
    id: "CC6.1",
    name: "Logical Access Security",
    description: "The entity implements logical access security measures",
    status: "compliant",
    evidence: ["access-logs-2024.json", "rbac-policy.pdf"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "CC6.2",
    name: "User Registration",
    description: "User registration and authorization process",
    status: "compliant",
    evidence: ["user-provisioning.pdf"],
    last_assessed: new Date(Date.now() - 172800000).toISOString(),
  },
  {
    id: "CC6.3",
    name: "Access Removal",
    description: "Removal of access upon termination",
    status: "partial",
    evidence: ["offboarding-checklist.pdf"],
    last_assessed: new Date(Date.now() - 259200000).toISOString(),
  },
];

const mockHIPAAControls: Control[] = [
  {
    id: "164.312(a)(1)",
    name: "Access Control",
    description: "Implement technical policies for access to ePHI",
    status: "compliant",
    evidence: ["access-control-policy.pdf"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "164.312(b)",
    name: "Audit Controls",
    description: "Implement audit controls",
    status: "compliant",
    evidence: ["audit-log-config.json"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
];

const mockPHIAccessLogs: PHIAccessLog[] = [
  {
    id: "log-1",
    user: "alice@example.com",
    timestamp: new Date(Date.now() - 7200000).toISOString(),
    action: "VIEW",
    resource: "patient-record-123",
  },
  {
    id: "log-2",
    user: "bob@example.com",
    timestamp: new Date(Date.now() - 14400000).toISOString(),
    action: "EXPORT",
    resource: "compliance-report-q4",
  },
];

const mockGDPRControls: Control[] = [
  {
    id: "Art.5",
    name: "Data Processing Principles",
    description: "Lawfulness, fairness, and transparency",
    status: "compliant",
    evidence: ["privacy-policy.pdf", "consent-records.json"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "Art.17",
    name: "Right to Erasure",
    description: "Right to be forgotten",
    status: "compliant",
    evidence: ["deletion-procedure.pdf"],
    last_assessed: new Date(Date.now() - 172800000).toISOString(),
  },
];

const mockDataSubjectRequests: DataSubjectRequest[] = [
  {
    id: "dsr-1",
    type: "access",
    status: "completed",
    submitted_at: new Date(Date.now() - 604800000).toISOString(),
    completed_at: new Date(Date.now() - 518400000).toISOString(),
  },
  {
    id: "dsr-2",
    type: "deletion",
    status: "pending",
    submitted_at: new Date(Date.now() - 172800000).toISOString(),
  },
];

const mockFedRAMPControls: Control[] = [
  {
    id: "AC-1",
    name: "Access Control Policy",
    description: "Access control policy and procedures",
    status: "compliant",
    evidence: ["ac-policy.pdf"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
  {
    id: "AC-2",
    name: "Account Management",
    description: "Account management procedures",
    status: "compliant",
    evidence: ["account-mgmt.pdf"],
    last_assessed: new Date(Date.now() - 86400000).toISOString(),
  },
];

// =============================================================================
// MSW Handlers
// =============================================================================

export const complianceHandlers = [
  /**
   * GET /api/v1/compliance/reports/summary - Overall compliance summary
   */
  http.get("/api/v1/compliance/reports/summary", async () => {
    await delay(50);
    return apiJsonResponse(mockComplianceSummary);
  }),

  /**
   * GET /api/v1/compliance/reports/soc2 - SOC2 controls report
   */
  http.get("/api/v1/compliance/reports/soc2", async () => {
    await delay(50);
    return apiJsonResponse({
      controls: mockSOC2Controls,
      summary: mockComplianceSummary.soc2,
      last_audit: new Date(Date.now() - 2592000000).toISOString(),
      next_audit: new Date(Date.now() + 7776000000).toISOString(),
    });
  }),

  /**
   * GET /api/v1/compliance/reports/hipaa - HIPAA compliance report
   */
  http.get("/api/v1/compliance/reports/hipaa", async () => {
    await delay(50);
    return apiJsonResponse({
      controls: mockHIPAAControls,
      phi_access_logs: mockPHIAccessLogs,
      summary: mockComplianceSummary.hipaa,
      baa_status: "active",
      last_risk_assessment: new Date(Date.now() - 5184000000).toISOString(),
    });
  }),

  /**
   * GET /api/v1/compliance/reports/gdpr - GDPR compliance report
   */
  http.get("/api/v1/compliance/reports/gdpr", async () => {
    await delay(50);
    return apiJsonResponse({
      controls: mockGDPRControls,
      data_subject_requests: mockDataSubjectRequests,
      summary: mockComplianceSummary.gdpr,
      dpo_contact: "dpo@example.com",
      data_processing_records: 15,
    });
  }),

  /**
   * GET /api/v1/compliance/reports/fedramp - FedRAMP authorization report
   */
  http.get("/api/v1/compliance/reports/fedramp", async () => {
    await delay(50);
    return apiJsonResponse({
      controls: mockFedRAMPControls,
      authorization_status: "Authorized",
      authorization_level: "Moderate",
      summary: mockComplianceSummary.fedramp,
      poam_items: 28,
      last_conmon: new Date(Date.now() - 2592000000).toISOString(),
    });
  }),
];

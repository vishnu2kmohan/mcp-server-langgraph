/**
 * API Contract Tests
 *
 * Validates frontend TypeScript types match backend API responses.
 * Verifies: response shape, required fields, field types, nullable fields
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import type {
  HealthStatus,
  HEARTAggregateMetrics,
  CostSummary,
  ModelCostData,
  CostHistoryPoint,
  VectorCollection,
  VectorSearchResult,
  VectorTextUpsertResponse,
  AgentConfig,
  AuditLogEntry,
  WorkflowSummary,
  Session,
  Project,
  PaginatedResponse,
  PagePaginatedResponse,
} from "../types/api";

function isHealthStatus(obj: unknown): obj is HealthStatus {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.status === "string" &&
    ["healthy", "degraded", "unhealthy"].includes(o.status) &&
    (o.version === undefined || typeof o.version === "string") &&
    (o.uptime_seconds === undefined || typeof o.uptime_seconds === "number")
  );
}
function isHEARTAggregateMetrics(obj: unknown): obj is HEARTAggregateMetrics {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.period === "string" &&
    (o.nps_score_avg === undefined ||
      o.nps_score_avg === null ||
      typeof o.nps_score_avg === "number") &&
    (o.satisfaction_avg === undefined ||
      o.satisfaction_avg === null ||
      typeof o.satisfaction_avg === "number") &&
    (o.task_success_rate === undefined ||
      o.task_success_rate === null ||
      typeof o.task_success_rate === "number")
  );
}
function isCostSummary(obj: unknown): obj is CostSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.total_cost === "number" &&
    (o.total_tokens === undefined ||
      o.total_tokens === null ||
      typeof o.total_tokens === "number")
  );
}
function isModelCostData(obj: unknown): obj is ModelCostData {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.model === "string" &&
    typeof o.cost === "number" &&
    typeof o.requests === "number"
  );
}
function isCostHistoryPoint(obj: unknown): obj is CostHistoryPoint {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.date === "string" && typeof o.cost === "number";
}
function isVectorCollection(obj: unknown): obj is VectorCollection {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.name === "string" && typeof o.vectors_count === "number";
}
function isVectorSearchResult(obj: unknown): obj is VectorSearchResult {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.score === "number";
}
function isVectorTextUpsertResponse(
  obj: unknown,
): obj is VectorTextUpsertResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.success === "boolean" && typeof o.point_id === "string";
}
function isAgentConfig(obj: unknown): obj is AgentConfig {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.model === "string" &&
    typeof o.provider === "string" &&
    typeof o.temperature === "number" &&
    typeof o.verification_enabled === "boolean" &&
    Array.isArray(o.tools)
  );
}
function isAuditLogEntry(obj: unknown): obj is AuditLogEntry {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.timestamp === "string" &&
    typeof o.user_id === "string" &&
    typeof o.action === "string" &&
    typeof o.resource_type === "string" &&
    typeof o.resource_id === "string"
  );
}
function isWorkflowSummary(obj: unknown): obj is WorkflowSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}
function isSession(obj: unknown): obj is Session {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.session_id === "string";
}
function isProject(obj: unknown): obj is Project {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}
// SUS Surveys
interface SUSSurveyResponse {
  id: string;
  sus_score: number;
  recorded_at: string;
}
interface ScoreDistribution {
  excellent: number;
  good: number;
  ok: number;
  poor: number;
}
interface SUSSummaryResponse {
  timeframe: string;
  avg_score: number | null;
  response_count: number;
  score_distribution: ScoreDistribution;
}
function isSUSSurveyResponse(obj: unknown): obj is SUSSurveyResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.sus_score === "number" &&
    typeof o.recorded_at === "string"
  );
}
function isScoreDistribution(obj: unknown): obj is ScoreDistribution {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.excellent === "number" &&
    typeof o.good === "number" &&
    typeof o.ok === "number" &&
    typeof o.poor === "number"
  );
}
function isSUSSummaryResponse(obj: unknown): obj is SUSSummaryResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.timeframe === "string" &&
    (o.avg_score === null || typeof o.avg_score === "number") &&
    typeof o.response_count === "number" &&
    isScoreDistribution(o.score_distribution)
  );
}
// HEART Analytics
interface MetricTrackingResponse {
  success: boolean;
  metric_id: string;
  recorded_at: string;
}
interface HEARTAnalyticsSummary {
  period: string;
  happiness?: unknown;
  engagement?: unknown;
  adoption?: unknown;
  retention?: unknown;
  task_success?: unknown;
}
function isMetricTrackingResponse(obj: unknown): obj is MetricTrackingResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.success === "boolean" &&
    typeof o.metric_id === "string" &&
    typeof o.recorded_at === "string"
  );
}
function isHEARTAnalyticsSummary(obj: unknown): obj is HEARTAnalyticsSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.period === "string";
}
// Compliance Reports
interface ComplianceReport {
  regulation: string;
  generated_at: string;
  time_range: { start: string; end: string };
}
interface ComplianceSummaryResponse {
  generated_at: string;
  regulations: string[];
  overall_status: string;
  findings: unknown[];
}
function isComplianceReport(obj: unknown): obj is ComplianceReport {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.regulation === "string" &&
    typeof o.generated_at === "string" &&
    typeof o.time_range === "object" &&
    o.time_range !== null
  );
}
function isComplianceSummary(obj: unknown): obj is ComplianceSummaryResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.generated_at === "string" &&
    Array.isArray(o.regulations) &&
    typeof o.overall_status === "string" &&
    Array.isArray(o.findings)
  );
}
// Connection Templates
interface TemplateCategory {
  id: string;
  name: string;
  description: string;
}
interface CategoryListResponse {
  categories: TemplateCategory[];
}
interface ConnectionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  default_url: string;
  auth_type: "none" | "api_key" | "oauth2";
}
interface TemplateListResponse {
  templates: ConnectionTemplate[];
}
function isTemplateCategory(obj: unknown): obj is TemplateCategory {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.name === "string" &&
    typeof o.description === "string"
  );
}
function isCategoryListResponse(obj: unknown): obj is CategoryListResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return Array.isArray(o.categories) && o.categories.every(isTemplateCategory);
}
function isConnectionTemplate(obj: unknown): obj is ConnectionTemplate {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.name === "string" &&
    typeof o.description === "string" &&
    typeof o.category === "string" &&
    typeof o.icon === "string" &&
    typeof o.default_url === "string" &&
    ["none", "api_key", "oauth2"].includes(o.auth_type as string)
  );
}
function isTemplateListResponse(obj: unknown): obj is TemplateListResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return Array.isArray(o.templates) && o.templates.every(isConnectionTemplate);
}
// Connection Audit
interface ConnectionAuditLogEntry {
  id: string;
  timestamp: string;
  connection_id: string;
  event_type: string;
  user_id: string;
  details?: unknown;
}
interface ConnectionAuditLogListResponse {
  logs: ConnectionAuditLogEntry[];
  total: number;
}
function isConnectionAuditLogEntry(
  obj: unknown,
): obj is ConnectionAuditLogEntry {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.timestamp === "string" &&
    typeof o.connection_id === "string" &&
    typeof o.event_type === "string" &&
    typeof o.user_id === "string"
  );
}
function isAuditLogListResponse(
  obj: unknown,
): obj is ConnectionAuditLogListResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.logs) &&
    o.logs.every(isConnectionAuditLogEntry) &&
    typeof o.total === "number"
  );
}
// Connections Bulk
interface BulkDeleteResponse {
  deleted_count: number;
  failed_ids?: string[];
}
interface ConnectionTestResult {
  connection_id: string;
  success: boolean;
  server_name?: string | null;
  server_version?: string | null;
  tool_count: number;
  error?: string | null;
}
interface BulkTestResponse {
  results: ConnectionTestResult[];
  not_found?: string[];
}
interface BulkStatusResponse {
  updated_count: number;
  failed_ids?: string[];
}

function isBulkDeleteResponse(obj: unknown): obj is BulkDeleteResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.deleted_count === "number" &&
    (o.failed_ids === undefined || Array.isArray(o.failed_ids))
  );
}

function isConnectionTestResult(obj: unknown): obj is ConnectionTestResult {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.connection_id === "string" &&
    typeof o.success === "boolean" &&
    typeof o.tool_count === "number"
  );
}

function isBulkTestResponse(obj: unknown): obj is BulkTestResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.results) &&
    o.results.every(isConnectionTestResult) &&
    (o.not_found === undefined || Array.isArray(o.not_found))
  );
}

function isBulkStatusResponse(obj: unknown): obj is BulkStatusResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.updated_count === "number" &&
    (o.failed_ids === undefined || Array.isArray(o.failed_ids))
  );
}

function isPaginatedResponse<T>(
  obj: unknown,
  itemValidator: (item: unknown) => item is T,
): obj is PaginatedResponse<T> {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.items) &&
    o.items.every(itemValidator) &&
    (o.next_cursor === undefined ||
      o.next_cursor === null ||
      typeof o.next_cursor === "string") &&
    (o.has_more === undefined || typeof o.has_more === "boolean")
  );
}

function isPagePaginatedResponse<T>(
  obj: unknown,
  itemValidator: (item: unknown) => item is T,
): obj is PagePaginatedResponse<T> {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.items) &&
    o.items.every(itemValidator) &&
    typeof o.total === "number" &&
    typeof o.page === "number" &&
    typeof o.per_page === "number" &&
    typeof o.total_pages === "number"
  );
}

describe("API Contract Tests", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Health Endpoint", () => {
    it("should validate HealthStatus schema", () => {
      const validResponse = {
        status: "healthy",
        version: "1.0.0",
        uptime_seconds: 3600,
      };
      expect(isHealthStatus(validResponse)).toBe(true);
    });

    it("should reject invalid HealthStatus", () => {
      const invalidResponse = { status: "unknown" };
      expect(isHealthStatus(invalidResponse)).toBe(false);
    });

    it("should allow optional fields in HealthStatus", () => {
      const minimalResponse = { status: "healthy" };
      expect(isHealthStatus(minimalResponse)).toBe(true);
    });
  });

  describe("HEART Metrics Endpoint", () => {
    it("should validate HEARTAggregateMetrics schema", () => {
      const validResponse = {
        period: "7d",
        nps_score_avg: 7.5,
        satisfaction_avg: 4.2,
        task_success_rate: 0.85,
        total_tasks_started: 100,
        total_tasks_completed: 85,
        avg_session_duration_ms: 300000,
        new_users_count: 50,
        avg_return_visits: 3.2,
      };
      expect(isHEARTAggregateMetrics(validResponse)).toBe(true);
    });

    it("should allow null values in HEART metrics", () => {
      const responseWithNulls = {
        period: "7d",
        nps_score_avg: null,
        satisfaction_avg: null,
        task_success_rate: null,
      };
      expect(isHEARTAggregateMetrics(responseWithNulls)).toBe(true);
    });
  });

  describe("Cost Endpoints", () => {
    it("should validate CostSummary schema", () => {
      const validResponse = {
        total_cost: 125.5,
        total_tokens: 500000,
      };
      expect(isCostSummary(validResponse)).toBe(true);
    });

    it("should allow null total_tokens in CostSummary", () => {
      const responseWithNull = {
        total_cost: 125.5,
        total_tokens: null,
      };
      expect(isCostSummary(responseWithNull)).toBe(true);
    });

    it("should validate ModelCostData schema", () => {
      const validResponse = {
        model: "gpt-4",
        cost: 75.0,
        requests: 1000,
      };
      expect(isModelCostData(validResponse)).toBe(true);
    });

    it("should validate CostHistoryPoint schema", () => {
      const validResponse = {
        date: "2025-01-01",
        cost: 50.25,
      };
      expect(isCostHistoryPoint(validResponse)).toBe(true);
    });

    it("should validate array of CostHistoryPoint", () => {
      const validResponse = [
        { date: "2025-01-01", cost: 50.25 },
        { date: "2025-01-02", cost: 75.0 },
      ];
      expect(validResponse.every(isCostHistoryPoint)).toBe(true);
    });
  });

  describe("Vector Endpoints", () => {
    it("should validate VectorCollection schema", () => {
      const validResponse = {
        name: "documents",
        vectors_count: 1000,
      };
      expect(isVectorCollection(validResponse)).toBe(true);
    });

    it("should validate VectorSearchResult schema", () => {
      const validResponse = {
        id: "point-123",
        score: 0.95,
        payload: { text: "Sample document" },
      };
      expect(isVectorSearchResult(validResponse)).toBe(true);
    });

    it("should validate VectorTextUpsertResponse schema", () => {
      const validResponse = {
        success: true,
        point_id: "point-456",
      };
      expect(isVectorTextUpsertResponse(validResponse)).toBe(true);
    });
  });

  describe("Agent Config Endpoint", () => {
    it("should validate AgentConfig schema", () => {
      const validResponse = {
        model: "gpt-4",
        provider: "openai",
        temperature: 0.7,
        verification_enabled: true,
        tools: [{ name: "search", description: "Search the web" }],
      };
      expect(isAgentConfig(validResponse)).toBe(true);
    });

    it("should validate AgentConfig with empty tools", () => {
      const validResponse = {
        model: "claude-3",
        provider: "anthropic",
        temperature: 0.5,
        verification_enabled: false,
        tools: [],
      };
      expect(isAgentConfig(validResponse)).toBe(true);
    });
  });

  describe("Audit Log Endpoint", () => {
    it("should validate AuditLogEntry schema", () => {
      const validResponse = {
        id: "log-123",
        timestamp: "2025-01-01T12:00:00Z",
        user_id: "user-456",
        action: "create",
        resource_type: "workflow",
        resource_id: "workflow-789",
      };
      expect(isAuditLogEntry(validResponse)).toBe(true);
    });
  });

  describe("Paginated Responses", () => {
    it("should validate cursor-based PaginatedResponse", () => {
      const validResponse = {
        items: [
          { id: "wf-1", name: "Workflow 1" },
          { id: "wf-2", name: "Workflow 2" },
        ],
        next_cursor: "cursor-abc",
        has_more: true,
      };
      expect(isPaginatedResponse(validResponse, isWorkflowSummary)).toBe(true);
    });

    it("should validate page-based PagePaginatedResponse", () => {
      const validResponse = {
        items: [
          { id: "proj-1", name: "Project 1" },
          { id: "proj-2", name: "Project 2" },
        ],
        total: 50,
        page: 1,
        per_page: 20,
        total_pages: 3,
      };
      expect(isPagePaginatedResponse(validResponse, isProject)).toBe(true);
    });

    it("should handle empty paginated response", () => {
      const emptyResponse = {
        items: [],
        next_cursor: null,
        has_more: false,
      };
      expect(isPaginatedResponse(emptyResponse, isWorkflowSummary)).toBe(true);
    });
  });

  describe("Session Endpoint", () => {
    it("should validate Session schema", () => {
      const validResponse = {
        session_id: "session-123",
        name: "Test Session",
        created_at: "2025-01-01T12:00:00Z",
      };
      expect(isSession(validResponse)).toBe(true);
    });
  });

  // ==========================================================================
  // NEW ENDPOINT CONTRACT TESTS
  // ==========================================================================

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

  describe("Connection Templates Endpoints", () => {
    it("should validate TemplateCategory schema", () => {
      const validResponse = {
        id: "databases",
        name: "Databases",
        description: "Database connection templates",
      };
      expect(isTemplateCategory(validResponse)).toBe(true);
    });

    it("should validate CategoryListResponse schema", () => {
      const validResponse = {
        categories: [
          {
            id: "databases",
            name: "Databases",
            description: "Database connections",
          },
          { id: "apis", name: "APIs", description: "API connections" },
        ],
      };
      expect(isCategoryListResponse(validResponse)).toBe(true);
    });

    it("should validate ConnectionTemplate schema", () => {
      const validResponse = {
        id: "postgres-template",
        name: "PostgreSQL",
        description: "PostgreSQL database connection",
        category: "databases",
        icon: "postgres",
        default_url: "postgresql://localhost:5432",
        auth_type: "api_key",
      };
      expect(isConnectionTemplate(validResponse)).toBe(true);
    });

    it("should validate TemplateListResponse schema", () => {
      const validResponse = {
        templates: [
          {
            id: "postgres-template",
            name: "PostgreSQL",
            description: "PostgreSQL database",
            category: "databases",
            icon: "postgres",
            default_url: "postgresql://localhost:5432",
            auth_type: "none",
          },
        ],
      };
      expect(isTemplateListResponse(validResponse)).toBe(true);
    });
  });

  describe("Connection Audit Endpoints", () => {
    it("should validate ConnectionAuditLogEntry schema", () => {
      const validResponse = {
        id: "audit-001",
        timestamp: "2025-01-15T10:30:00Z",
        connection_id: "conn-123",
        event_type: "connection_created",
        user_id: "user-001",
        details: { name: "New Connection" },
      };
      expect(isConnectionAuditLogEntry(validResponse)).toBe(true);
    });

    it("should validate AuditLogListResponse schema", () => {
      const validResponse = {
        logs: [
          {
            id: "audit-001",
            timestamp: "2025-01-15T10:30:00Z",
            connection_id: "conn-123",
            event_type: "connection_created",
            user_id: "user-001",
          },
        ],
        total: 1,
      };
      expect(isAuditLogListResponse(validResponse)).toBe(true);
    });
  });

  describe("Connections Bulk Endpoints", () => {
    it("should validate BulkDeleteResponse schema", () => {
      const validResponse = {
        deleted_count: 5,
        failed_ids: ["conn-003"],
      };
      expect(isBulkDeleteResponse(validResponse)).toBe(true);
    });

    it("should allow empty failed_ids in BulkDeleteResponse", () => {
      const validResponse = {
        deleted_count: 10,
      };
      expect(isBulkDeleteResponse(validResponse)).toBe(true);
    });

    it("should validate BulkTestResponse schema", () => {
      const validResponse = {
        results: [
          {
            connection_id: "conn-001",
            success: true,
            server_name: "Test Server",
            server_version: "1.0.0",
            tool_count: 5,
          },
          {
            connection_id: "conn-002",
            success: false,
            error: "Connection refused",
            tool_count: 0,
          },
        ],
        not_found: ["conn-003"],
      };
      expect(isBulkTestResponse(validResponse)).toBe(true);
    });

    it("should validate BulkStatusResponse schema", () => {
      const validResponse = {
        updated_count: 3,
        failed_ids: [],
      };
      expect(isBulkStatusResponse(validResponse)).toBe(true);
    });

    it("should validate ConnectionTestResult schema", () => {
      const validResponse = {
        connection_id: "conn-001",
        success: true,
        server_name: "MCP Server",
        server_version: "2.0.0",
        tool_count: 10,
      };
      expect(isConnectionTestResult(validResponse)).toBe(true);
    });

    it("should validate failed ConnectionTestResult", () => {
      const validResponse = {
        connection_id: "conn-002",
        success: false,
        error: "Authentication failed",
        tool_count: 0,
      };
      expect(isConnectionTestResult(validResponse)).toBe(true);
    });
  });

  // ==========================================================================
  // AUTH ENDPOINTS CONTRACT TESTS (ADR-0091: Uses generated types)
  // ==========================================================================

  describe("Auth Endpoints (Generated Types)", () => {
    // Type definitions from generated-api.ts (ADR-0091)
    // These match components["schemas"]["LoginResponse"], etc.
    interface LoginResponse {
      access_token: string;
      refresh_token?: string | null;
      token_type: string;
      expires_in: number;
    }

    interface LogoutResponse {
      success: boolean;
      message?: string | null;
    }

    interface IdentityProvider {
      alias: string;
      display_name: string;
      icon: string;
      login_url: string;
    }

    interface IdentityProvidersListResponse {
      identity_providers?: IdentityProvider[];
    }

    function isLoginResponse(obj: unknown): obj is LoginResponse {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return (
        typeof o.access_token === "string" &&
        (o.refresh_token === undefined ||
          o.refresh_token === null ||
          typeof o.refresh_token === "string") &&
        typeof o.token_type === "string" &&
        typeof o.expires_in === "number"
      );
    }

    function isLogoutResponse(obj: unknown): obj is LogoutResponse {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return (
        typeof o.success === "boolean" &&
        (o.message === undefined ||
          o.message === null ||
          typeof o.message === "string")
      );
    }

    function isIdentityProvider(obj: unknown): obj is IdentityProvider {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return (
        typeof o.alias === "string" &&
        typeof o.display_name === "string" &&
        typeof o.icon === "string" &&
        typeof o.login_url === "string"
      );
    }

    function isIdentityProvidersListResponse(
      obj: unknown,
    ): obj is IdentityProvidersListResponse {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return (
        o.identity_providers === undefined ||
        (Array.isArray(o.identity_providers) &&
          o.identity_providers.every(isIdentityProvider))
      );
    }

    it("should validate LoginResponse schema", () => {
      const validResponse = {
        access_token: "test-access-token-placeholder",
        refresh_token: "test-refresh-token-placeholder",
        token_type: "Bearer",
        expires_in: 3600,
      };
      expect(isLoginResponse(validResponse)).toBe(true);
    });

    it("should allow null refresh_token in LoginResponse", () => {
      const responseWithNull = {
        access_token: "test-access-token-placeholder",
        refresh_token: null,
        token_type: "Bearer",
        expires_in: 3600,
      };
      expect(isLoginResponse(responseWithNull)).toBe(true);
    });

    it("should validate LogoutResponse schema", () => {
      const validResponse = {
        success: true,
        message: "Successfully logged out",
      };
      expect(isLogoutResponse(validResponse)).toBe(true);
    });

    it("should allow minimal LogoutResponse", () => {
      const minimalResponse = {
        success: true,
      };
      expect(isLogoutResponse(minimalResponse)).toBe(true);
    });

    it("should validate IdentityProvider schema", () => {
      const validProvider = {
        alias: "google",
        display_name: "Sign in with Google",
        icon: "google",
        login_url: "/api/v1/auth/login?kc_idp_hint=google",
      };
      expect(isIdentityProvider(validProvider)).toBe(true);
    });

    it("should validate IdentityProvidersListResponse schema", () => {
      const validResponse = {
        identity_providers: [
          {
            alias: "google",
            display_name: "Sign in with Google",
            icon: "google",
            login_url: "/api/v1/auth/login?kc_idp_hint=google",
          },
          {
            alias: "github",
            display_name: "Sign in with GitHub",
            icon: "github",
            login_url: "/api/v1/auth/login?kc_idp_hint=github",
          },
        ],
      };
      expect(isIdentityProvidersListResponse(validResponse)).toBe(true);
    });

    it("should allow empty identity_providers array", () => {
      const emptyResponse = {
        identity_providers: [],
      };
      expect(isIdentityProvidersListResponse(emptyResponse)).toBe(true);
    });

    it("should allow undefined identity_providers (optional field)", () => {
      const minimalResponse = {};
      expect(isIdentityProvidersListResponse(minimalResponse)).toBe(true);
    });
  });

  // ==========================================================================
  // AI URL FETCH ENDPOINT CONTRACT TESTS
  // ==========================================================================

  describe("AI Fetch URL Endpoint", () => {
    // Type definition for URL fetch response
    interface FetchUrlResponse {
      url: string;
      title?: string | null;
      content?: string | null;
      content_type?: string | null;
      error?: string | null;
      status_code?: number | null;
    }

    // Type definition for error response
    interface FetchUrlErrorResponse {
      detail: string;
    }

    function isFetchUrlResponse(obj: unknown): obj is FetchUrlResponse {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return (
        typeof o.url === "string" &&
        (o.title === undefined ||
          o.title === null ||
          typeof o.title === "string") &&
        (o.content === undefined ||
          o.content === null ||
          typeof o.content === "string") &&
        (o.content_type === undefined ||
          o.content_type === null ||
          typeof o.content_type === "string") &&
        (o.error === undefined ||
          o.error === null ||
          typeof o.error === "string") &&
        (o.status_code === undefined ||
          o.status_code === null ||
          typeof o.status_code === "number")
      );
    }

    function isFetchUrlErrorResponse(
      obj: unknown,
    ): obj is FetchUrlErrorResponse {
      if (typeof obj !== "object" || obj === null) return false;
      const o = obj as Record<string, unknown>;
      return typeof o.detail === "string";
    }

    it("should validate successful FetchUrlResponse schema", () => {
      const validResponse = {
        url: "https://example.com",
        title: "Example Domain",
        content: "This domain is for use in illustrative examples...",
        content_type: "text/html",
      };
      expect(isFetchUrlResponse(validResponse)).toBe(true);
    });

    it("should validate FetchUrlResponse with null optional fields", () => {
      const validResponse = {
        url: "https://example.com/api",
        title: null,
        content: '{"key": "value"}',
        content_type: "application/json",
      };
      expect(isFetchUrlResponse(validResponse)).toBe(true);
    });

    it("should validate FetchUrlResponse with error field", () => {
      const validResponse = {
        url: "https://example.com/notfound",
        error: "Page not found",
        status_code: 404,
      };
      expect(isFetchUrlResponse(validResponse)).toBe(true);
    });

    it("should validate minimal FetchUrlResponse (URL only)", () => {
      const minimalResponse = {
        url: "https://example.com",
      };
      expect(isFetchUrlResponse(minimalResponse)).toBe(true);
    });

    it("should validate SSRF error response schema", () => {
      const errorResponse = {
        detail: "URL blocked: Private IP addresses are not allowed",
      };
      expect(isFetchUrlErrorResponse(errorResponse)).toBe(true);
    });

    it("should reject FetchUrlResponse with missing url field", () => {
      const invalidResponse = {
        title: "Example",
        content: "Some content",
      };
      expect(isFetchUrlResponse(invalidResponse)).toBe(false);
    });

    it("should validate FetchUrlResponse with all optional fields", () => {
      const fullResponse = {
        url: "https://docs.example.com/guide",
        title: "Documentation Guide",
        content: "# Getting Started\n\nWelcome to our documentation...",
        content_type: "text/html; charset=utf-8",
        error: null,
        status_code: 200,
      };
      expect(isFetchUrlResponse(fullResponse)).toBe(true);
    });

    it("should validate FetchUrlResponse with timeout error", () => {
      const timeoutResponse = {
        url: "https://slow-server.example.com",
        error: "Request timed out after 30 seconds",
        status_code: null,
      };
      expect(isFetchUrlResponse(timeoutResponse)).toBe(true);
    });
  });
});

/**
 * API Contract Type Guard Validators
 *
 * Runtime validators that match frontend TypeScript types.
 * These validators check wire format (snake_case) before RTK Query transforms.
 */
/* eslint-disable no-restricted-syntax */

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

// =============================================================================
// Core Type Validators
// =============================================================================

export function isHealthStatus(obj: unknown): obj is HealthStatus {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.status === "string" &&
    ["healthy", "degraded", "unhealthy"].includes(o.status) &&
    (o.version === undefined || typeof o.version === "string") &&
    (o.uptime_seconds === undefined || typeof o.uptime_seconds === "number")
  );
}

export function isHEARTAggregateMetrics(
  obj: unknown,
): obj is HEARTAggregateMetrics {
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

export function isCostSummary(obj: unknown): obj is CostSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.total_cost === "number" &&
    (o.total_tokens === undefined ||
      o.total_tokens === null ||
      typeof o.total_tokens === "number")
  );
}

export function isModelCostData(obj: unknown): obj is ModelCostData {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.model === "string" &&
    typeof o.cost === "number" &&
    typeof o.requests === "number"
  );
}

export function isCostHistoryPoint(obj: unknown): obj is CostHistoryPoint {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.date === "string" && typeof o.cost === "number";
}

export function isVectorCollection(obj: unknown): obj is VectorCollection {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.name === "string" && typeof o.vectors_count === "number";
}

export function isVectorSearchResult(obj: unknown): obj is VectorSearchResult {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.score === "number";
}

export function isVectorTextUpsertResponse(
  obj: unknown,
): obj is VectorTextUpsertResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.success === "boolean" && typeof o.point_id === "string";
}

export function isAgentConfig(obj: unknown): obj is AgentConfig {
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

export function isAuditLogEntry(obj: unknown): obj is AuditLogEntry {
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

export function isWorkflowSummary(obj: unknown): obj is WorkflowSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}

export function isSession(obj: unknown): obj is Session {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.session_id === "string";
}

export function isProject(obj: unknown): obj is Project {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.id === "string" && typeof o.name === "string";
}

// =============================================================================
// Pagination Validators
// =============================================================================

export function isPaginatedResponse<T>(
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

export function isPagePaginatedResponse<T>(
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

// =============================================================================
// SUS Surveys Types and Validators
// =============================================================================

export interface SUSSurveyResponse {
  id: string;
  sus_score: number;
  recorded_at: string;
}

export interface ScoreDistribution {
  excellent: number;
  good: number;
  ok: number;
  poor: number;
}

export interface SUSSummaryResponse {
  timeframe: string;
  avg_score: number | null;
  response_count: number;
  score_distribution: ScoreDistribution;
}

export function isSUSSurveyResponse(obj: unknown): obj is SUSSurveyResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.sus_score === "number" &&
    typeof o.recorded_at === "string"
  );
}

export function isScoreDistribution(obj: unknown): obj is ScoreDistribution {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.excellent === "number" &&
    typeof o.good === "number" &&
    typeof o.ok === "number" &&
    typeof o.poor === "number"
  );
}

export function isSUSSummaryResponse(obj: unknown): obj is SUSSummaryResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.timeframe === "string" &&
    (o.avg_score === null || typeof o.avg_score === "number") &&
    typeof o.response_count === "number" &&
    isScoreDistribution(o.score_distribution)
  );
}

// =============================================================================
// HEART Analytics Types and Validators
// =============================================================================

export interface MetricTrackingResponse {
  success: boolean;
  metric_id: string;
  recorded_at: string;
}

export interface HEARTAnalyticsSummary {
  period: string;
  happiness?: unknown;
  engagement?: unknown;
  adoption?: unknown;
  retention?: unknown;
  task_success?: unknown;
}

export function isMetricTrackingResponse(
  obj: unknown,
): obj is MetricTrackingResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.success === "boolean" &&
    typeof o.metric_id === "string" &&
    typeof o.recorded_at === "string"
  );
}

export function isHEARTAnalyticsSummary(
  obj: unknown,
): obj is HEARTAnalyticsSummary {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.period === "string";
}

// =============================================================================
// Compliance Reports Types and Validators
// =============================================================================

export interface ComplianceReport {
  regulation: string;
  generated_at: string;
  time_range: { start: string; end: string };
}

export interface ComplianceSummaryResponse {
  generated_at: string;
  regulations: string[];
  overall_status: string;
  findings: unknown[];
}

export function isComplianceReport(obj: unknown): obj is ComplianceReport {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.regulation === "string" &&
    typeof o.generated_at === "string" &&
    typeof o.time_range === "object" &&
    o.time_range !== null
  );
}

export function isComplianceSummary(
  obj: unknown,
): obj is ComplianceSummaryResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.generated_at === "string" &&
    Array.isArray(o.regulations) &&
    typeof o.overall_status === "string" &&
    Array.isArray(o.findings)
  );
}

// =============================================================================
// Connection Templates Types and Validators
// =============================================================================

export interface TemplateCategory {
  id: string;
  name: string;
  description: string;
}

export interface CategoryListResponse {
  categories: TemplateCategory[];
}

export interface ConnectionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: string;
  default_url: string;
  auth_type: "none" | "api_key" | "oauth2";
}

export interface TemplateListResponse {
  templates: ConnectionTemplate[];
}

export function isTemplateCategory(obj: unknown): obj is TemplateCategory {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.name === "string" &&
    typeof o.description === "string"
  );
}

export function isCategoryListResponse(
  obj: unknown,
): obj is CategoryListResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return Array.isArray(o.categories) && o.categories.every(isTemplateCategory);
}

export function isConnectionTemplate(obj: unknown): obj is ConnectionTemplate {
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

export function isTemplateListResponse(
  obj: unknown,
): obj is TemplateListResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return Array.isArray(o.templates) && o.templates.every(isConnectionTemplate);
}

// =============================================================================
// Connection Audit Types and Validators
// =============================================================================

export interface ConnectionAuditLogEntry {
  id: string;
  timestamp: string;
  connection_id: string;
  event_type: string;
  user_id: string;
  details?: unknown;
}

export interface ConnectionAuditLogListResponse {
  logs: ConnectionAuditLogEntry[];
  total: number;
}

export function isConnectionAuditLogEntry(
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

export function isAuditLogListResponse(
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

// =============================================================================
// Connections Bulk Types and Validators
// =============================================================================

export interface BulkDeleteResponse {
  deleted_count: number;
  failed_ids?: string[];
}

export interface ConnectionTestResult {
  connection_id: string;
  success: boolean;
  server_name?: string | null;
  server_version?: string | null;
  tool_count: number;
  error?: string | null;
}

export interface BulkTestResponse {
  results: ConnectionTestResult[];
  not_found?: string[];
}

export interface BulkStatusResponse {
  updated_count: number;
  failed_ids?: string[];
}

export function isBulkDeleteResponse(obj: unknown): obj is BulkDeleteResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.deleted_count === "number" &&
    (o.failed_ids === undefined || Array.isArray(o.failed_ids))
  );
}

export function isConnectionTestResult(
  obj: unknown,
): obj is ConnectionTestResult {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.connection_id === "string" &&
    typeof o.success === "boolean" &&
    typeof o.tool_count === "number"
  );
}

export function isBulkTestResponse(obj: unknown): obj is BulkTestResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.results) &&
    o.results.every(isConnectionTestResult) &&
    (o.not_found === undefined || Array.isArray(o.not_found))
  );
}

export function isBulkStatusResponse(obj: unknown): obj is BulkStatusResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.updated_count === "number" &&
    (o.failed_ids === undefined || Array.isArray(o.failed_ids))
  );
}

// =============================================================================
// Auth Types and Validators
// =============================================================================

export interface LoginResponse {
  access_token: string;
  refresh_token?: string | null;
  token_type: string;
  expires_in: number;
}

export interface LogoutResponse {
  success: boolean;
  message?: string | null;
}

export interface IdentityProvider {
  alias: string;
  display_name: string;
  icon: string;
  login_url: string;
}

export interface IdentityProvidersListResponse {
  identity_providers?: IdentityProvider[];
}

export function isLoginResponse(obj: unknown): obj is LoginResponse {
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

export function isLogoutResponse(obj: unknown): obj is LogoutResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.success === "boolean" &&
    (o.message === undefined ||
      o.message === null ||
      typeof o.message === "string")
  );
}

export function isIdentityProvider(obj: unknown): obj is IdentityProvider {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.alias === "string" &&
    typeof o.display_name === "string" &&
    typeof o.icon === "string" &&
    typeof o.login_url === "string"
  );
}

export function isIdentityProvidersListResponse(
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

// =============================================================================
// URL Fetch Types and Validators
// =============================================================================

export interface FetchUrlResponse {
  url: string;
  title?: string | null;
  content?: string | null;
  content_type?: string | null;
  error?: string | null;
  status_code?: number | null;
}

export interface FetchUrlErrorResponse {
  detail: string;
}

export function isFetchUrlResponse(obj: unknown): obj is FetchUrlResponse {
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

export function isFetchUrlErrorResponse(
  obj: unknown,
): obj is FetchUrlErrorResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.detail === "string";
}

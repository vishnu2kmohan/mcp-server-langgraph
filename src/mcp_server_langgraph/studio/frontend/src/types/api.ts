/**
 * Centralized API Type Definitions
 *
 * All API request/response types are defined here to ensure consistency
 * across the application and avoid duplication.
 *
 * ADR-0091 Phase 6: Types use snake_case to match backend API responses.
 * RTK Query transforms responses to camelCase at runtime.
 * Use `SnakeToCamelCaseDeep<T>` to get the frontend-friendly type.
 */

import type { SnakeToCamelCaseDeep } from "../api/transforms";

// =============================================================================
// Common Types
// =============================================================================

/**
 * Sort order type
 */
export type SortOrder = "asc" | "desc";

/**
 * Model lifecycle status.
 *
 * Used by the model selector to indicate model maturity and deprecation status.
 * Matches the backend ModelStatus type in model_registry.py.
 *
 * - current: Production-ready, actively maintained models
 * - preview: Experimental or beta models (may have bugs or limited features)
 * - legacy: Older models superseded by newer versions (still functional)
 * - deprecated: Models scheduled for removal (shows sunset date warning)
 */
export type ModelStatus = "current" | "preview" | "legacy" | "deprecated";

/**
 * Known model vendor values.
 *
 * Distinguishes between native provider APIs and hosted/proxy versions.
 * Used for display differentiation in model selectors.
 */
export type KnownModelVendor =
  | "anthropic"
  | "google"
  | "openai"
  | "vertex_ai"
  | "vertex_ai_anthropic"
  | "azure";

/**
 * Model vendor type.
 *
 * Allows known vendors plus arbitrary strings for forward compatibility
 * with new vendors from the API. Use KnownModelVendor for switch/match.
 */
export type ModelVendor = KnownModelVendor | (string & {});

/**
 * Model option for model selectors.
 *
 * Unified interface for model selection UI components.
 * Used by HeaderModelSelector, PreferencesMenu, ChatInput, etc.
 */
export interface ModelOption {
  /** Unique model identifier (e.g., "claude-opus-4.5", "gpt-4o") */
  id: string;
  /** Human-readable model name (e.g., "Claude Opus 4.5") */
  name: string;
  /** Provider identifier (e.g., "anthropic", "openai", "google") */
  provider: string;
  /** Vendor distinguishes native API vs Vertex AI/Azure (Issue 5) */
  vendor?: ModelVendor;
  /** Whether this model supports extended thinking/reasoning */
  supportsThinking?: boolean;
  /** Whether this model supports vision/image inputs */
  supportsVision?: boolean;
  /** Whether this model supports tool/function calling */
  supportsTools?: boolean;
  /** Model lifecycle status for UI badges */
  status?: ModelStatus;
  /** Sunset date for deprecated models (ISO 8601 format) */
  sunsetDate?: string;
}

/**
 * Cursor-based pagination metadata from backend.
 *
 * IMPORTANT: `count` is the number of items in the CURRENT page, NOT total count.
 * Cursor-based pagination deliberately omits total for efficiency.
 */
export interface CursorPaginationMetadata {
  /** Number of items in current page (NOT total count across all pages) */
  count: number;
  /** Whether there is a next page */
  has_next: boolean;
  /** Whether there is a previous page */
  has_prev: boolean;
  /** Cursor for the next page (null if on last page) */
  next_cursor?: string | null;
  /** Cursor for the previous page (null if on first page) */
  prev_cursor?: string | null;
}

/**
 * Backend cursor-paginated response format.
 * This is the raw response from the API before transformation.
 */
export interface BackendCursorPaginatedResponse<T> {
  /** Array of items for the current page */
  data: T[];
  /** Cursor pagination metadata */
  pagination: CursorPaginationMetadata;
}

/**
 * Frontend-friendly cursor-paginated response.
 * Transformed from BackendCursorPaginatedResponse for easier use in components.
 *
 * @deprecated Use `CursorPaginatedFrontendResponse` for new code.
 * Legacy components may still use `items`, `total`, `limit`, `next_cursor`.
 */
export interface PaginatedResponse<T> {
  items: T[];
  /** @deprecated Cursor pagination does not provide total. Use `count` instead. */
  total?: number;
  limit: number;
  cursor?: string;
  next_cursor?: string;
}

/**
 * CamelCase version of PaginatedResponse for transformed API responses.
 * ADR-0091 Phase 6: Use this type when RTK Query applies transformSnakeToCamel.
 */
export interface PaginatedResponseCamelCase<T> {
  items: T[];
  /** @deprecated Cursor pagination does not provide total. Use `count` instead. */
  total?: number;
  limit: number;
  cursor?: string;
  nextCursor?: string;
}

/**
 * Cursor-paginated frontend response with full pagination access.
 * Preserves raw pagination for components needing direct cursor access.
 */
export interface CursorPaginatedFrontendResponse<T> {
  /** Array of items for the current page */
  items: T[];
  /** Raw pagination metadata for components needing cursor access */
  pagination: CursorPaginationMetadata;
  /** Number of items in current page (NOT total count) */
  count: number;
  /** Whether there is a next page */
  hasNext: boolean;
  /** Whether there is a previous page */
  hasPrev: boolean;
  /** Cursor for the next page (undefined if on last page) */
  nextCursor?: string;
  /** Cursor for the previous page (undefined if on first page) */
  prevCursor?: string;
}

/**
 * Page-based paginated response wrapper
 */
export interface PagePaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

// =============================================================================
// Query Parameter Types
// =============================================================================

/**
 * Common list query parameters for cursor-based pagination
 */
export interface CursorPaginationParams {
  cursor?: string;
  limit?: number;
}

/**
 * Common list query parameters for page-based pagination
 */
export interface PagePaginationParams {
  page?: number;
  per_page?: number;
}

/**
 * Sort parameters
 */
export interface SortParams {
  sort_by?: string;
  sort_order?: SortOrder;
}

/**
 * Search parameters
 */
export interface SearchParams {
  search?: string;
}

/**
 * Workflow list query parameters
 */
export interface WorkflowListParams
  extends CursorPaginationParams, SortParams, SearchParams {
  status?: string;
  owner_id?: string;
}

/**
 * Session list query parameters
 */
export interface SessionListParams
  extends CursorPaginationParams, SortParams, SearchParams {
  workflow_id?: string;
  status?: string;
}

/**
 * Trace list query parameters
 */
export interface TraceListParams
  extends CursorPaginationParams, SortParams, SearchParams {
  session_id?: string;
  user_id?: string;
  workflow_id?: string;
  project_id?: string;
  organization_id?: string;
  status?: string;
  start_time?: string;
  end_time?: string;
}

/**
 * Project list query parameters
 */
export interface ProjectListParams
  extends PagePaginationParams, SortParams, SearchParams {
  organization_id?: string;
  owner_id?: string;
  status?: string;
}

/**
 * Cost query parameters (camelCase for frontend use)
 * Either provide period OR startDate/endDate, not both
 */
export interface CostQueryParams {
  /** Preset period like "day", "week", "month", "30d" */
  period?: string;
  /** Custom start date (YYYY-MM-DD) - takes precedence over period */
  startDate?: string;
  /** Custom end date (YYYY-MM-DD) - takes precedence over period */
  endDate?: string;
}

/**
 * Cost history query parameters
 */
export interface CostHistoryParams {
  period?: string;
  start_date?: string;
  end_date?: string;
  granularity?: "hour" | "day" | "week" | "month";
}

/**
 * Cost history data point matching backend DailyCostResponse
 */
export interface CostHistoryPoint {
  date: string;
  cost: number;
  requests?: number | null;
}

/**
 * Standard API error response
 */
export interface ApiError {
  message: string;
  code?: string;
  details?: Record<string, unknown>;
}

// =============================================================================
// Feature Flags
// =============================================================================
// API Response Format: The backend API returns short names (e.g., "workflows")
// not backend field names (e.g., "enable_workflows_feature").
// See: src/mcp_server_langgraph/core/feature_flags.py - get_ui_features_for_role()
// =============================================================================

export interface FeatureFlags {
  // ==========================================================================
  // Core Features (API response uses SHORT NAMES)
  // ==========================================================================
  /** Enable workflows feature */
  workflows?: boolean;
  /** Enable sessions feature */
  sessions?: boolean;
  /** Enable cost dashboard (admins always, users if cost_dashboard_users enabled) */
  cost_dashboard?: boolean;
  /** Enable observability UI */
  observability?: boolean;
  /** Enable code export feature */
  code_export?: boolean;
  /** Enable AI suggestions */
  ai_suggestions?: boolean;
  /** Enable LLM suggestions (DEPRECATED: use suggestion_strategy) */
  llm_suggestions?: boolean;
  /** Suggestion generation strategy: "llm" | "heuristic" | "hybrid" (Sprint Block 5) */
  suggestion_strategy?: "llm" | "heuristic" | "hybrid";
  /** Multi-agent coordination strategy: "orchestrator" | "peer" | "hybrid" (Sprint Block 5) */
  multi_agent_strategy?: "orchestrator" | "peer" | "hybrid";
  /** Enable notification preferences */
  notification_preferences?: boolean;
  /** Enable hallucination reporting in chat UI (flag AI responses as inaccurate) */
  hallucination_reporting?: boolean;
  /** Enable AI Quality Metrics card in Admin Dashboard */
  ai_quality_metrics?: boolean;
  /** Enable MCP WebSocket connections */
  mcp_websocket?: boolean;
  /** Enable interactive artifact rendering in chat messages (Sandpack for JSX/TSX/MDX) */
  interactive_artifacts?: boolean;
  /** Enable URL content fetching */
  url_content_fetch?: boolean;
  /** Enable slash commands */
  slash_commands?: boolean;
  /** Enable rich text input with formatting toolbar (bold, italic, code, mentions) */
  rich_text_chat_input?: boolean;
  /** Enable style presets */
  style_presets?: boolean;

  // ==========================================================================
  // UX Enhancement Features (API response uses SHORT NAMES)
  // ==========================================================================
  /** Enable user preferences sync */
  user_preferences_sync?: boolean;
  /** Enable session export */
  session_export?: boolean;
  /** Enable project context */
  project_context?: boolean;
  /** Enable onboarding wizard */
  onboarding_wizard?: boolean;
  /** Enable guided tour */
  guided_tour?: boolean;
  /** Enable SUS survey */
  sus_survey?: boolean;
  /** Enable command palette */
  command_palette?: boolean;
  /** Enable keyboard shortcuts */
  keyboard_shortcuts?: boolean;
  /** Enable theme customization */
  theme_customization?: boolean;
  /** Enable confirmation dialogs */
  confirmation_dialogs?: boolean;
  /** Enable enhanced model selector (Sprint 1: recent models, search, capability badges) */
  enhanced_model_selector?: boolean;
  /** Enable manual tool selection dropdown in chat input (auto/manual/none modes) */
  manual_tool_selection?: boolean;
  /** Enable panel zoom/maximize (Sprint 4) */
  panel_zoom?: boolean;
  /** Enable mobile drawer navigation (Sprint 4) */
  mobile_drawer?: boolean;
  /** Enable KB focus mode (ADR-0094: Perplexity-style) */
  kb_focus?: boolean;
  /** Enable AI nudges feature */
  nudges?: boolean;
  /** Enable AI persona analysis */
  persona_analysis?: boolean;

  // ==========================================================================
  // Session AI Features
  // ==========================================================================
  /** Enable AI-powered session cards */
  session_ai?: boolean;
  /** Enable AI-generated session summaries */
  session_summary?: boolean;
  /** Enable AI-extracted session topics */
  session_topics?: boolean;

  // ==========================================================================
  // DevTools Features
  // ==========================================================================
  /** Enable DevTools panel */
  devtools_panel?: boolean;
  /** Enable AI insights in DevTools */
  devtools_ai_insights?: boolean;
  /** Enable AI layout suggestions in DevTools */
  devtools_ai_layout?: boolean;
  /** Enable network tab in DevTools */
  devtools_network_tab?: boolean;

  // ==========================================================================
  // Execution Mode Features (Ctrl/Cmd+Shift+M Toggle)
  // ==========================================================================
  /** Enable execution mode toggle in chat input (default, plan, auto_accept, bypass) */
  execution_mode_toggle?: boolean;
  /** Enable plan generation for audit trail */
  plan_generation?: boolean;
  /** Enable HITL approval flow for medium/high risk plans */
  plan_approval_flow?: boolean;
  /** Restrict bypass mode to admin role only */
  bypass_mode_admin_only?: boolean;
  /** Enable risk-aware bypass mode with auto-approval for low-risk plans */
  bypass_risk_aware?: boolean;
  /** Enable consolidated preferences menu in chat input */
  preferences_menu?: boolean;

  // ==========================================================================
  // Studio Canvas Shell Feature Flags (Phase 0+)
  // ==========================================================================
  /** Enable Studio Canvas shell at /studio (Phase 1) */
  studio_canvas_shell?: boolean;
  /** Enable editable artifacts in Canvas panel (Phase 2) */
  canvas_editable?: boolean;
  /** Enable background agent panel (Phase 4) */
  canvas_agents?: boolean;
  /** Enable AI fallback in command palette (Phase 4) */
  canvas_ai_palette?: boolean;
  /** Enable compliance dashboards (Phase 5) */
  canvas_compliance?: boolean;
  /** Enable in-app help pane (Phase 6) */
  canvas_help?: boolean;

  // Allow dynamic flag access (includes strategy string literals)
  [key: string]:
    | boolean
    | "llm"
    | "heuristic"
    | "hybrid"
    | "orchestrator"
    | "peer"
    | undefined;
}

// =============================================================================
// Workflows
// =============================================================================

export interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  user_id?: string;
  created_at: string;
  updated_at: string;
  /** Current version number (1 for new workflows) */
  version?: number;
  /** Workflow lifecycle status */
  status?: "draft" | "published" | "archived";
  /** ID of the head (latest) version */
  head_version_id?: string;
  /** Source code representation (Python/YAML) */
  source_text?: string;
}

// =============================================================================
// Workflow Versions (Plan: greedy-wiggling-marshmallow.md, Phase 3)
// =============================================================================

/**
 * Workflow version history entry.
 * Enables draft/publish lifecycle, diffing, rollback, and audit trails.
 */
export interface WorkflowVersion {
  id: string;
  workflow_id: string;
  version_number: number;
  /** Snapshot of workflow state (nodes + edges) */
  graph_json: {
    nodes: Array<Record<string, unknown>>;
    edges: Array<Record<string, unknown>>;
  };
  /** Source code representation at this version */
  source_text?: string;
  /** Commit message describing the change */
  commit_message?: string;
  /** User who created this version */
  created_by: string;
  created_at: string;
  /** Prompt version used to generate this version (telemetry linkage) */
  prompt_version?: string;
  /** LLM model used for generation */
  prompt_model?: string;
}

export interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRef {
  id: string;
  name: string;
  created_at: string | null;
}

// Workflow Bootstrap (create workflow from session)
export interface BootstrapWorkflowRequest {
  session_id: string;
}

export interface BootstrapWorkflowResponse {
  workflow_id: string;
  name: string;
}

/**
 * BootstrapWorkflowResponse with camelCase keys (after RTK Query transformation).
 */
export type BootstrapWorkflowResponseCamelCase =
  SnakeToCamelCaseDeep<BootstrapWorkflowResponse>;

// Workflow Sharing
export interface WorkflowShare {
  user_id: string;
  email: string;
  permission: "view" | "edit" | "execute";
}

export interface WorkflowSharesResponse {
  shares: WorkflowShare[];
  is_public: boolean;
  share_link: string | null;
}

export interface AddWorkflowShareRequest {
  workflow_id: string;
  email: string;
  permission: "view" | "edit" | "execute";
}

export interface RemoveWorkflowShareRequest {
  workflow_id: string;
  user_id: string;
}

export interface UpdateWorkflowPublicRequest {
  workflow_id: string;
  is_public: boolean;
}

// Workflow Code Generation
export interface GenerateWorkflowCodeRequest {
  workflow_id: string;
  language?: string;
}

export interface GenerateWorkflowCodeResponse {
  code: string;
  language: string;
}

// =============================================================================
// Workflow Validation (ADR-0089, Plan Review Consensus)
// =============================================================================

/**
 * Request to validate a workflow's graph structure.
 * Currently empty - workflow is fetched by ID.
 */
export interface ValidateWorkflowRequest {
  workflow_id: string;
}

/**
 * Response from workflow validation.
 * Uses centralized WorkflowValidator service (NO JS DUPLICATION).
 */
export interface ValidateWorkflowResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

// =============================================================================
// Chat-to-Workflow Generation (ADR-0089, Plan Review Consensus)
// =============================================================================

/**
 * Metadata about the prompt used for workflow generation.
 * Enables telemetry linkage for prompt optimization analytics.
 */
export interface PromptMetadata {
  name: string;
  version: string;
  hash: string;
  model: string;
}

/**
 * Request to generate a workflow from chat session history.
 */
export interface GenerateWorkflowFromChatRequest {
  session_id: string;
  refinement_mode?: "auto" | "plan";
  template_id?: string;
}

/**
 * Response containing generated workflow from chat.
 * Workflow is persisted with status='draft' and version=1.
 */
export interface GenerateWorkflowFromChatResponse {
  workflow: Workflow;
  confidence: number;
  suggestions: string[];
  prompt_metadata: PromptMetadata;
  plan?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Workflow Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * Workflow type with camelCase keys (after RTK Query transformation).
 */
export type WorkflowCamelCase = SnakeToCamelCaseDeep<Workflow>;

/**
 * WorkflowSummary type with camelCase keys (after RTK Query transformation).
 */
export type WorkflowSummaryCamelCase = SnakeToCamelCaseDeep<WorkflowSummary>;

/**
 * WorkflowVersion type with camelCase keys (after RTK Query transformation).
 */
export type WorkflowVersionCamelCase = SnakeToCamelCaseDeep<WorkflowVersion>;

/**
 * WorkflowSharesResponse type with camelCase keys (after RTK Query transformation).
 */
export type WorkflowSharesResponseCamelCase =
  SnakeToCamelCaseDeep<WorkflowSharesResponse>;

// =============================================================================
// Sessions
// =============================================================================

/**
 * Session configuration for LLM settings (API response format)
 */
export interface ApiSessionConfig {
  model: string;
  temperature: number;
  max_tokens: number;
}

/**
 * Request to update session configuration (all fields optional for partial updates)
 */
export interface SessionConfigUpdateRequest {
  session_id: string;
  model?: string;
  temperature?: number;
  max_tokens?: number;
}

/**
 * Session type matching backend API response (snake_case).
 * Use SessionCamelCase for frontend code after RTK Query transformation.
 */
export interface Session {
  id: string;
  name: string;
  workflow_id?: string;
  user_id?: string;
  project_id?: string;
  status: "active" | "archived" | "deleted";
  created_at: string;
  updated_at: string;
  config?: ApiSessionConfig;
}

/**
 * SessionRef type matching backend API response (snake_case).
 * Use SessionRefCamelCase for frontend code after RTK Query transformation.
 */
export interface SessionRef {
  id: string;
  name: string;
  message_count: number;
  created_at: string | null;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Session Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * Session type with camelCase keys (after RTK Query transformation).
 *
 * Use this type in components that consume data from RTK Query endpoints
 * with `transformResponse: transformSnakeToCamel`.
 *
 * @example
 * ```typescript
 * const { data } = useGetSessionQuery(sessionId);
 * // data is SessionCamelCase, not Session
 * console.log(data?.createdAt); // camelCase property access
 * ```
 */
export type SessionCamelCase = SnakeToCamelCaseDeep<Session>;

/**
 * SessionRef type with camelCase keys (after RTK Query transformation).
 */
export type SessionRefCamelCase = SnakeToCamelCaseDeep<SessionRef>;

/**
 * ApiSessionConfig type with camelCase keys (after RTK Query transformation).
 */
export type ApiSessionConfigCamelCase = SnakeToCamelCaseDeep<ApiSessionConfig>;

// =============================================================================
// Messages & Chat
// =============================================================================

/**
 * Source citation for AI responses
 */
export interface SourceCitation {
  title: string;
  url: string;
}

export interface Message {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  /** Optional source citations for AI responses */
  sources?: SourceCitation[];
}

export interface ChatCompletionRequest {
  session_id?: string;
  messages: Array<{ role: string; content: string }>;
  model?: string;
  stream?: boolean;
  /** Knowledge Base focus mode: all, kb_only, web_only, or none */
  kb_focus?: "all" | "kb_only" | "web_only" | "none";
}

export interface ChatCompletionResponse {
  id: string;
  session_id: string;
  message: Message;
  model: string;
  usage?: TokenUsage;
}

export interface TokenUsage {
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Message/Chat Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * Message type with camelCase keys (after RTK Query transformation).
 */
export type MessageCamelCase = SnakeToCamelCaseDeep<Message>;

/**
 * ChatCompletionResponse type with camelCase keys (after RTK Query transformation).
 */
export type ChatCompletionResponseCamelCase =
  SnakeToCamelCaseDeep<ChatCompletionResponse>;

/**
 * TokenUsage type with camelCase keys (after RTK Query transformation).
 */
export type TokenUsageCamelCase = SnakeToCamelCaseDeep<TokenUsage>;

// =============================================================================
// Projects
// =============================================================================

export interface Project {
  id: string;
  name: string;
  description: string | null;
  organization_id: string | null;
  owner_id: string;
  /** Owner display name (if resolved by backend) */
  owner_name?: string;
  created_at: string;
  updated_at: string;
  status: string;
  /** Resource counts - included in list responses */
  workflow_count?: number;
  session_count?: number;
  connection_count?: number;
}

export interface ProjectDetail extends Project {
  workflow_count: number;
  session_count: number;
  connection_count: number;
  workflows: WorkflowRef[];
  sessions: SessionRef[];
  connections: ConnectionRef[];
  members: ProjectMember[];
}

export interface ProjectMember {
  user_id: string;
  role: "owner" | "editor" | "viewer" | "executor";
  added_at: string;
}

export interface ConnectionRef {
  id: string;
  type: string;
  name: string;
  status: string;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Project Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * Project type with camelCase keys (after RTK Query transformation).
 */
export type ProjectCamelCase = SnakeToCamelCaseDeep<Project>;

/**
 * ProjectDetail type with camelCase keys (after RTK Query transformation).
 */
export type ProjectDetailCamelCase = SnakeToCamelCaseDeep<ProjectDetail>;

/**
 * ProjectMember type with camelCase keys (after RTK Query transformation).
 */
export type ProjectMemberCamelCase = SnakeToCamelCaseDeep<ProjectMember>;

// =============================================================================
// Cost & Billing
// =============================================================================

/**
 * Cost summary response matching backend CostSummaryResponse
 */
export interface CostSummary {
  total_cost: number;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number | null;
  period_start?: string | null;
  period_end?: string | null;
}

/**
 * Model cost response matching backend ModelCostResponse
 */
export interface ModelCostData {
  model: string;
  cost: number;
  requests: number;
  prompt_tokens?: number | null;
  completion_tokens?: number | null;
}

/**
 * Legacy cost data interface (kept for compatibility)
 */
export interface CostData {
  totalCost: number;
  promptTokens: number;
  completionTokens: number;
  sessionCount: number;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Cost Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * CostSummary type with camelCase keys (after RTK Query transformation).
 */
export type CostSummaryCamelCase = SnakeToCamelCaseDeep<CostSummary>;

/**
 * ModelCostData type with camelCase keys (after RTK Query transformation).
 */
export type ModelCostDataCamelCase = SnakeToCamelCaseDeep<ModelCostData>;

// =============================================================================
// Observability
// =============================================================================

/**
 * Single span within a trace
 */
export interface TraceSpan {
  span_id: string;
  parent_span_id?: string | null;
  name: string;
  start_time: string;
  end_time?: string | null;
  duration_ms?: number | null;
  status: string;
  attributes: Record<string, unknown>;
  events?: unknown[];
  error_message?: string;
  depth?: number;
  /**
   * Thinking object structure with content and tokens from extended thinking models.
   * Matches SpanThinkingResponse from generated-api.ts (both fields optional).
   */
  thinking?: {
    content?: string | null;
    tokens?: number | null;
  } | null;
  /** Model name that generated this span's content */
  model_name?: string;
}

/**
 * Full trace with all spans (returned by GET /api/v1/observability/traces/{id})
 */
export interface TraceDetail {
  trace_id: string;
  name: string;
  start_time: string | null;
  end_time: string | null;
  duration_ms: number | null;
  span_count: number | null;
  spans: TraceSpan[];
  service_name?: string;
}

/**
 * Trace list item (returned by GET /api/v1/observability/traces - list endpoint)
 */
export interface TraceListItem {
  trace_id: string;
  name: string;
  start_time: string | null;
  duration_ms: number | null;
  span_count: number | null;
  status?: string;
  end_time?: string | null;
  /** Whether this trace includes LLM thinking/reasoning */
  has_thinking?: boolean;
  /** Total thinking tokens used in this trace */
  thinking_tokens_total?: number;
}

export interface ObservabilityData {
  traceCount: number;
  requestsTotal: number;
  errorsTotal: number;
  avgLatencyMs: number;
}

export interface LogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warn" | "error";
  message: string;
  service?: string;
}

export interface ObservabilityMetrics {
  requests_total: number;
  errors_total: number;
  avg_latency_ms: number;
  p99_latency_ms: number;
  tokens_used: number;
  active_sessions: number;
}

export interface LogListParams extends CursorPaginationParams, SortParams {
  level?: string;
  service?: string;
  search?: string;
  start_time?: string;
  end_time?: string;
}

export interface AlertEntry {
  id: string;
  severity: "info" | "warning" | "critical";
  message: string;
  created_at: string;
}

/**
 * Observability alert from LGTM stack (Grafana Alerting)
 */
export interface ObservabilityAlert {
  alert_id: string;
  name: string;
  severity: "info" | "warning" | "error" | "critical";
  state: "pending" | "firing" | "resolved" | "silenced";
  message: string;
  labels: Record<string, string>;
  annotations: Record<string, string>;
  started_at: string | null;
  ended_at: string | null;
  generator_url: string | null;
}

/**
 * Observability alerting rule (Grafana Unified Alerting)
 */
export interface ObservabilityAlertRule {
  rule_id: string;
  name: string;
  expression: string;
  severity: "info" | "warning" | "error" | "critical";
  labels: Record<string, string>;
  annotations: Record<string, string>;
  evaluation_interval_seconds: number;
  for_duration_seconds: number | null;
  enabled: boolean;
}

/**
 * Alert list query parameters
 */
export interface AlertListParams {
  state?: "pending" | "firing" | "resolved" | "silenced";
  severity?: "info" | "warning" | "error" | "critical";
  service_name?: string;
  limit?: number;
}

/**
 * Alert rules list query parameters
 */
export interface AlertRulesListParams {
  enabled_only?: boolean;
  limit?: number;
}

/**
 * Project-scoped observability response
 */
export interface ProjectObservabilityResponse {
  traceCount: number;
  requestsTotal: number;
  errorsTotal: number;
  avgLatencyMs: number;
}

/**
 * Project-scoped logs response
 */
export interface ProjectLogsResponse {
  logs: LogEntry[];
  total: number;
}

/**
 * Project-scoped alerts response
 */
export interface ProjectAlertsResponse {
  alerts: AlertEntry[];
  total: number;
}

/**
 * Project-scoped cost summary response
 */
export interface ProjectCostSummaryResponse {
  total_cost: number;
  prompt_tokens: number;
  completion_tokens: number;
  session_count: number;
}

/**
 * Project-scoped cost by model response item
 */
export interface ProjectModelCost {
  model: string;
  cost: number;
  tokens: number;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Observability Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * TraceSpan type with camelCase keys (after RTK Query transformation).
 */
export type TraceSpanCamelCase = SnakeToCamelCaseDeep<TraceSpan>;

/**
 * TraceDetail type with camelCase keys (after RTK Query transformation).
 */
export type TraceDetailCamelCase = SnakeToCamelCaseDeep<TraceDetail>;

/**
 * TraceListItem type with camelCase keys (after RTK Query transformation).
 */
export type TraceListItemCamelCase = SnakeToCamelCaseDeep<TraceListItem>;

/**
 * ObservabilityMetrics type with camelCase keys (after RTK Query transformation).
 */
export type ObservabilityMetricsCamelCase =
  SnakeToCamelCaseDeep<ObservabilityMetrics>;

/**
 * ObservabilityAlert type with camelCase keys (after RTK Query transformation).
 */
export type ObservabilityAlertCamelCase =
  SnakeToCamelCaseDeep<ObservabilityAlert>;

/**
 * LogEntry type with camelCase keys (after RTK Query transformation).
 */
export type LogEntryCamelCase = SnakeToCamelCaseDeep<LogEntry>;

/**
 * ObservabilityAlertRule type with camelCase keys (after RTK Query transformation).
 * ADR-0091 Phase 9: Added for transform consistency.
 */
export type ObservabilityAlertRuleCamelCase =
  SnakeToCamelCaseDeep<ObservabilityAlertRule>;

// =============================================================================
// Organizational Cost Attribution (new endpoints)
// =============================================================================

/**
 * Organization cost breakdown response
 * GET /api/v1/cost/summary/by-organization
 */
export interface OrganizationCostResponse {
  organization_id: string;
  total_cost: number;
  total_tokens: number;
  request_count: number;
}

/**
 * Project cost breakdown response
 * GET /api/v1/cost/summary/by-project
 */
export interface ProjectCostBreakdown {
  project_id: string;
  organization_id: string | null;
  total_cost: number;
  total_tokens: number;
  request_count: number;
}

/**
 * Team cost breakdown response
 * GET /api/v1/cost/summary/by-team
 */
export interface TeamCostResponse {
  team_id: string;
  organization_id: string | null;
  project_id: string | null;
  total_cost: number;
  total_tokens: number;
  request_count: number;
}

/**
 * Parameters for organizational cost queries
 *
 * ADR-0091 Phase 6: Uses camelCase - transformed to snake_case at API boundary
 */
export interface OrganizationalCostParams {
  organizationId?: string;
  projectId?: string;
  startDate?: string;
  endDate?: string;
}

// =============================================================================
// Budget Status & Forecasting
// =============================================================================

/**
 * Budget status response
 * GET /api/v1/cost/budget/status
 */
export interface BudgetStatusResponse {
  status: "ok" | "warning" | "critical" | "exceeded";
  percent_used: number;
  current_spend: number;
  remaining: number;
  monthly_limit: number;
  entity_type: "organization" | "project" | "team" | "user";
  entity_id: string;
  message: string;
}

/**
 * Parameters for budget status query
 */
export interface BudgetStatusParams {
  entity_type: "organization" | "project" | "team" | "user";
  entity_id: string;
}

/**
 * Cost forecast response
 * GET /api/v1/cost/budget/forecast
 */
export interface CostForecastResponse {
  projected_total: number;
  confidence_low: number;
  confidence_high: number;
  trend: "increasing" | "decreasing" | "stable";
  days_analyzed: number;
  message: string;
  monthly_limit: number;
}

/**
 * Parameters for cost forecast query
 */
export interface CostForecastParams {
  entity_type: "organization" | "project" | "team" | "user";
  entity_id: string;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Cost Attribution Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * OrganizationCostResponse type with camelCase keys (after RTK Query transformation).
 */
export type OrganizationCostResponseCamelCase =
  SnakeToCamelCaseDeep<OrganizationCostResponse>;

/**
 * ProjectCostBreakdown type with camelCase keys (after RTK Query transformation).
 */
export type ProjectCostBreakdownCamelCase =
  SnakeToCamelCaseDeep<ProjectCostBreakdown>;

/**
 * TeamCostResponse type with camelCase keys (after RTK Query transformation).
 */
export type TeamCostResponseCamelCase = SnakeToCamelCaseDeep<TeamCostResponse>;

/**
 * BudgetStatusResponse type with camelCase keys (after RTK Query transformation).
 */
export type BudgetStatusResponseCamelCase =
  SnakeToCamelCaseDeep<BudgetStatusResponse>;

/**
 * CostForecastResponse type with camelCase keys (after RTK Query transformation).
 */
export type CostForecastResponseCamelCase =
  SnakeToCamelCaseDeep<CostForecastResponse>;

/**
 * Add project member request
 */
export interface AddProjectMemberRequest {
  project_id: string;
  user_id: string;
  role: string;
}

/**
 * Remove project member request
 */
export interface RemoveProjectMemberRequest {
  project_id: string;
  user_id: string;
}

/**
 * Add project connection request
 */
export interface AddProjectConnectionRequest {
  project_id: string;
  connection_type: string;
  connection_id: string;
  connection_name: string;
}

// =============================================================================
// User & Auth
// =============================================================================

export interface UserInfo {
  id: string;
  username: string;
  email?: string;
  roles: string[];
}

export interface UserProfile {
  username: string;
  email?: string;
  roles: string[];
  preferences?: Record<string, unknown>;
}

// =============================================================================
// Vectors (Qdrant)
// =============================================================================

export interface VectorCollection {
  name: string;
  vectors_count: number | null;
}

export interface VectorCollectionDetail {
  name: string;
  vector_size: number;
  distance: "Cosine" | "Euclidean" | "Dot";
  point_count: number;
}

export interface VectorCollectionsResponse {
  collections: VectorCollection[];
}

export interface VectorSearchRequest {
  collection_name: string;
  query_vector: number[];
  limit?: number;
  filter?: Record<string, unknown>;
}

export interface VectorSearchResult {
  id: string | number;
  score: number;
  payload?: Record<string, unknown>;
}

export interface VectorUpsertRequest {
  collection_name: string;
  points: VectorPoint[];
}

export interface VectorPoint {
  id: string | number;
  vector: number[];
  payload?: Record<string, unknown>;
}

export interface VectorCreateCollectionRequest {
  name: string;
  vectors: {
    size: number;
    distance: "Cosine" | "Euclidean" | "Dot";
  };
}

export interface VectorTextSearchRequest {
  collection_name: string;
  query_text: string;
  limit?: number;
}

export interface VectorTextUpsertRequest {
  collection_name: string;
  text: string;
  metadata?: Record<string, unknown>;
}

export interface VectorTextUpsertResponse {
  collection: string;
  point_id: string;
  status: "created";
}

// =============================================================================
// Agents
// =============================================================================

/**
 * Information about a specific thinking level
 */
/**
 * ADR-0091 Phase 6: Uses camelCase - data transformed at API boundary
 */
export interface ThinkingLevelInfo {
  /** Thinking level (low, medium, high, ultra) */
  level: string;
  /** Effort parameter for Claude Opus 4.5 (low, medium, high) */
  claudeOpusEffort: string;
  /** Token budget for non-Opus models */
  otherModelsTokens: number;
  /** Description of this thinking level */
  description: string;
}

/**
 * Thinking budget default configuration
 *
 * ADR-0091 Phase 6: Uses camelCase - data transformed at API boundary
 */
export interface ThinkingBudgetDefaults {
  /** Whether thinking budget is enabled */
  enabled: boolean;
  /** Default thinking level (low, medium, high, ultra) */
  defaultLevel: string;
  /** Available thinking levels with model-specific behavior */
  levels: ThinkingLevelInfo[];
  /** Task complexity to thinking level mapping */
  complexityMapping: Record<string, string>;
}

/**
 * Agent configuration response from backend
 *
 * Extended in Sprint 1 with optional fields:
 * - thinking_budget_defaults: Thinking level configuration
 * - feature_flags_snapshot: Agent-related feature flags
 */
export interface AgentConfig {
  model: string;
  provider: string;
  temperature: number;
  verification_enabled: boolean;
  tools: AgentTool[];

  /** Thinking budget default configuration (optional, Sprint 1 extension) */
  thinking_budget_defaults?: ThinkingBudgetDefaults | null;
  /** Snapshot of agent-related feature flags (optional, Sprint 1 extension) */
  feature_flags_snapshot?: Record<string, boolean> | null;
  /** List of registered orchestrators (optional, Phase 6 extension) */
  orchestrators?: OrchestratorInfo[] | null;
  /** List of supported LLM providers (optional) */
  providers?: ProviderInfo[] | null;
}

/**
 * AgentConfig with camelCase keys for frontend use.
 * Used after transformSnakeToCamel transformation.
 */
export type AgentConfigCamelCase = SnakeToCamelCaseDeep<AgentConfig>;

/**
 * Request for updating thinking budget configuration
 */
export interface ThinkingBudgetUpdateRequest {
  /** Default thinking level (low, medium, high, ultra) */
  default_level?: string | null;
  /** Whether thinking budget is enabled */
  enabled?: boolean | null;
}

/**
 * Response from thinking budget update
 */
export interface ThinkingBudgetUpdateResponse {
  /** Whether the update was successful */
  success: boolean;
  /** List of fields that were updated */
  updated_fields: string[];
  /** Current thinking budget configuration after update */
  current_config?: ThinkingBudgetDefaults | null;
  /** Optional message about the update */
  message?: string | null;
}

export interface AgentTool {
  name: string;
  description: string;
  enabled?: boolean;
}

/**
 * Information about an orchestrator
 * Matches backend OrchestratorInfo from agents/registry.py
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface OrchestratorInfo {
  /** Orchestrator class name */
  name: string;
  /** Human-readable display name */
  displayName: string;
  /** Description of orchestrator purpose */
  description: string;
  /** Feature flag controlling this orchestrator */
  featureFlag: string;
  /** Task categories this orchestrator handles */
  taskCategories: string[];
}

/**
 * Information about an LLM provider
 * Matches backend ProviderInfo from llm/providers.py
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface ProviderInfo {
  /** Provider identifier (e.g., "anthropic") */
  name: string;
  /** Human-readable display name */
  displayName: string;
  /** Description of the provider */
  description: string;
  /** Model types this provider supports */
  supportedModelTypes: string[];
  /** Whether this provider requires an API key */
  requiresApiKey: boolean;
  /** Environment variable name for API key */
  apiKeyEnvVar: string | null;
}

// =============================================================================
// Agent Metrics
// =============================================================================

/**
 * Metrics for orchestrator execution
 * Matches backend OrchestratorMetrics from api/v1/agents.py
 */
export interface OrchestratorMetrics {
  /** Total orchestrator executions */
  total_executions: number;
  /** Successful executions */
  successful_executions: number;
  /** Failed executions */
  failed_executions: number;
  /** Average execution duration in ms */
  avg_duration_ms: number;
  /** 50th percentile duration */
  p50_duration_ms?: number | null;
  /** 95th percentile duration */
  p95_duration_ms?: number | null;
  /** 99th percentile duration */
  p99_duration_ms?: number | null;
}

/**
 * Metrics for Human-in-the-Loop interactions
 * Matches backend HITLMetrics from api/v1/agents.py
 */
export interface HITLMetrics {
  /** Total HITL requests */
  total_requests: number;
  /** Approved requests */
  approved_count: number;
  /** Rejected requests */
  rejected_count: number;
  /** Pending requests */
  pending_count: number;
  /** Average response latency in ms */
  avg_response_latency_ms: number;
}

/**
 * Metrics for LLM cost tracking
 * Matches backend CostMetrics from api/v1/agents.py
 */
export interface CostMetrics {
  /** Total cost in USD */
  total_cost_usd: number;
  /** Total tokens consumed */
  total_tokens: number;
  /** Average cost per request in USD */
  avg_cost_per_request_usd: number;
}

/**
 * Response from agent metrics endpoint
 * Matches backend AgentMetricsResponse from api/v1/agents.py
 */
export interface AgentMetricsResponse {
  /** Timestamp of metrics collection */
  timestamp: string;
  /** Time range for metrics in hours */
  time_range_hours: number;
  /** Orchestrator metrics */
  orchestrator: OrchestratorMetrics;
  /** HITL metrics */
  hitl: HITLMetrics;
  /** Cost metrics */
  cost: CostMetrics;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 6: CamelCase Agent Metrics Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * AgentMetricsResponse type with camelCase keys (after RTK Query transformation).
 */
export type AgentMetricsResponseCamelCase =
  SnakeToCamelCaseDeep<AgentMetricsResponse>;

/**
 * OrchestratorMetrics type with camelCase keys (after RTK Query transformation).
 */
export type OrchestratorMetricsCamelCase =
  SnakeToCamelCaseDeep<OrchestratorMetrics>;

/**
 * HITLMetrics type with camelCase keys (after RTK Query transformation).
 */
export type HITLMetricsCamelCase = SnakeToCamelCaseDeep<HITLMetrics>;

/**
 * CostMetrics type with camelCase keys (after RTK Query transformation).
 */
export type CostMetricsCamelCase = SnakeToCamelCaseDeep<CostMetrics>;

// =============================================================================
// Audit Logs
// =============================================================================

export interface AuditLogEntry {
  id: string;
  action: string;
  user_id: string;
  user_email?: string;
  resource_type: string;
  resource_id: string;
  timestamp: string;
  ip_address?: string;
  details?: Record<string, unknown>;
}

export interface AuditLogListParams extends CursorPaginationParams, SortParams {
  user_id?: string;
  action?: string;
  resource_type?: string;
  start_time?: string;
  end_time?: string;
}

// =============================================================================
// Health & Metrics
// =============================================================================

/**
 * Health check response
 */
export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  version?: string;
  uptime_seconds?: number;
}

/**
 * HEART aggregate metrics matching backend AggregateMetrics
 */
export interface HEARTAggregateMetrics {
  period: string;
  app_name?: string | null;
  // Happiness
  nps_score_avg?: number | null;
  satisfaction_avg?: number | null;
  // Task Success
  task_success_rate?: number | null;
  total_tasks_started: number;
  total_tasks_completed: number;
  total_tasks_errored: number;
  // Engagement
  avg_session_duration_ms?: number | null;
  total_interactions: number;
  top_features: Record<string, number>;
  // Adoption
  new_users_count: number;
  onboarding_completion_rate?: number | null;
  // Retention
  avg_return_visits?: number | null;
  avg_days_active?: number | null;
}

// -----------------------------------------------------------------------------
// ADR-0091 Phase 9: CamelCase Health & Metrics Types (for transformed responses)
// -----------------------------------------------------------------------------

/**
 * HealthStatus type with camelCase keys (after RTK Query transformation).
 * ADR-0091 Phase 9: Added for transform consistency.
 */
export type HealthStatusCamelCase = SnakeToCamelCaseDeep<HealthStatus>;

/**
 * HEARTAggregateMetrics type with camelCase keys (after RTK Query transformation).
 * ADR-0091 Phase 9: Added for transform consistency.
 */
export type HEARTAggregateMetricsCamelCase =
  SnakeToCamelCaseDeep<HEARTAggregateMetrics>;

// -----------------------------------------------------------------------------
// KB Status Types (Knowledge Base / DynamicContextLoader)
// -----------------------------------------------------------------------------

/**
 * KB status values
 */
export type KBStatusValue = "ready" | "misconfigured" | "unavailable";

/**
 * KB Status response from backend (snake_case).
 */
export interface KBStatusResponse {
  status: KBStatusValue;
  qdrant_connected: boolean;
  collection_name?: string | null;
  vectors_count?: number;
  embedding_provider?: string | null;
  embedding_model?: string | null;
  embedding_dimensions?: number | null;
  last_updated?: string | null;
  context_token_budget?: number | null;
  context_top_k?: number | null;
  message?: string | null;
}

/**
 * KBStatusResponse type with camelCase keys (after RTK Query transformation).
 * ADR-0091: Added for transform consistency.
 */
export type KBStatusResponseCamelCase = SnakeToCamelCaseDeep<KBStatusResponse>;

/**
 * Knowledge Base context statistics.
 * Used for displaying KB context usage in StatusBar and related components.
 */
export interface KBContextStats {
  /** Number of context references loaded */
  refsCount: number;
  /** Tokens used for context */
  tokensUsed: number;
  /** Token budget limit */
  tokenBudget: number;
}

// =============================================================================
// AI Suggestions
// =============================================================================

/**
 * Request for AI workflow suggestions
 */
export interface SuggestionRequest {
  workflow: Record<string, unknown>;
  max_suggestions?: number;
  confidence_threshold?: number;
}

/**
 * A single AI suggestion
 */
export interface AISuggestion {
  type: string;
  description: string;
  confidence: number;
  metadata: Record<string, unknown>;
}

/**
 * Response containing AI suggestions
 */
export interface SuggestionsResponse {
  suggestions: AISuggestion[];
  workflow_id?: string;
}

// =============================================================================
// Unified AI Suggestions Types (new /api/v1/ai/suggestions endpoint)
// =============================================================================

/**
 * Suggestion type discriminator
 */
export type UnifiedSuggestionType = "chat_followup" | "workflow";

/**
 * Category for chat follow-up suggestions
 */
export type ChatFollowUpCategory =
  | "explore"
  | "clarify"
  | "example"
  | "alternative"
  | "continue";

/**
 * A chat follow-up suggestion
 */
export interface ChatFollowUpSuggestion {
  id: string;
  text: string;
  category: ChatFollowUpCategory;
}

/**
 * A workflow optimization suggestion
 */
export interface WorkflowSuggestion {
  type: string;
  description: string;
  confidence: number;
  metadata?: Record<string, unknown>;
}

/**
 * Request for unified AI suggestions
 */
export interface UnifiedSuggestionsRequest {
  type: UnifiedSuggestionType;
  /** Content to analyze (required for chat_followup) */
  content?: string;
  /** Session ID for context */
  session_id?: string;
  /** Workflow to analyze (required for workflow) */
  workflow?: Record<string, unknown>;
  /** Maximum suggestions to return. Default: 4 */
  max_suggestions?: number;
}

/**
 * Response from unified AI suggestions endpoint
 */
export interface UnifiedSuggestionsResponse {
  suggestions: (ChatFollowUpSuggestion | WorkflowSuggestion)[];
}

/**
 * Request to track a suggestion click
 */
export interface SuggestionClickRequest {
  suggestion_id: string;
  suggestion_type: UnifiedSuggestionType;
  category?: string;
  session_id?: string;
}

/**
 * Response confirming click tracking
 */
export interface SuggestionClickResponse {
  tracked: boolean;
}

/**
 * Request to submit feedback on a suggestion (thumbs up/down)
 */
export interface SuggestionFeedbackRequest {
  suggestion_id: string;
  suggestion_type: UnifiedSuggestionType;
  feedback: "positive" | "negative";
  category?: string;
  session_id?: string;
  /** Optional text feedback for negative ratings */
  comment?: string;
}

/**
 * Response confirming feedback submission
 */
export interface SuggestionFeedbackResponse {
  recorded: boolean;
  feedback_id?: string;
}

// =============================================================================
// Node Config Assistant Types
// =============================================================================

/**
 * Request for node configuration help
 */
export interface NodeConfigHelpRequest {
  node_type: string;
  node_config: Record<string, unknown>;
  question: string;
  context?: string;
}

/**
 * Response with node configuration help
 */
export interface NodeConfigHelpResponse {
  answer: string;
  suggested_config?: Record<string, unknown>;
  examples?: string[];
}

// =============================================================================
// Feedback (NPS/CSAT)
// =============================================================================

/**
 * Request to submit user feedback
 */
export interface FeedbackRequest {
  nps_score?: number; // 0-10 scale
  csat_rating?: number; // 1-5 stars
  comment?: string;
}

/**
 * Response after feedback submission
 */
export interface FeedbackResponse {
  success: boolean;
  feedback_id?: string;
}

// =============================================================================
// Message Rating (Thumbs Up/Down)
// =============================================================================

/**
 * Message rating value
 */
export type MessageRatingValue = "up" | "down" | null;

/**
 * Request to submit a message rating
 */
export interface MessageRatingRequest {
  /** The session ID containing the message */
  session_id: string;
  /** The message ID being rated */
  message_id: string;
  /** The rating value (up, down, or null to remove) */
  rating: MessageRatingValue;
  /** Optional feedback text (for negative ratings) */
  feedback?: string;
}

/**
 * Response after message rating submission
 */
export interface MessageRatingResponse {
  success: boolean;
  rating_id?: string;
  message_id: string;
  rating: MessageRatingValue;
}

// =============================================================================
// Hallucination Reporting
// =============================================================================

/**
 * Category of hallucination being reported
 */
export type HallucinationCategory =
  | "factual_error"
  | "outdated_info"
  | "made_up_source"
  | "other";

/**
 * Severity level for hallucination reports
 */
export type HallucinationSeverity = "low" | "medium" | "high";

/**
 * Request to submit a hallucination report
 * POST /api/v1/feedback/hallucination
 */
export interface HallucinationReportRequest {
  /** The message ID being reported */
  message_id: string;
  /** The session ID containing the message */
  session_id: string;
  /** Category of hallucination */
  category: HallucinationCategory;
  /** User description of the issue */
  description: string;
  /** Severity level (optional, defaults to medium) */
  severity?: HallucinationSeverity;
}

/**
 * Response after hallucination report submission
 */
export interface HallucinationReportResponse {
  success: boolean;
  report_id?: string;
  message_id: string;
  category: HallucinationCategory;
}

/**
 * HallucinationReportResponse type with camelCase keys (after RTK Query transformation).
 */
export type HallucinationReportResponseCamelCase =
  SnakeToCamelCaseDeep<HallucinationReportResponse>;

/**
 * Counts by hallucination category.
 * Used in FeedbackSummaryResponse.
 */
export interface HallucinationCategoryCounts {
  /** Count of factual error reports */
  factual_error: number;
  /** Count of outdated information reports */
  outdated_info: number;
  /** Count of made up source reports */
  made_up_source: number;
  /** Count of other category reports */
  other: number;
}

/**
 * HallucinationCategoryCounts type with camelCase keys (after RTK Query transformation).
 */
export type HallucinationCategoryCountsCamelCase =
  SnakeToCamelCaseDeep<HallucinationCategoryCounts>;

/**
 * Aggregated feedback summary response.
 * GET /api/v1/feedback/summary
 */
export interface FeedbackSummaryResponse {
  /** Time period for aggregation (e.g., "7d", "30d", "90d") */
  timeframe: string;
  /** Total number of feedback entries */
  total_feedback: number;
  /** Count of positive ratings */
  positive_count: number;
  /** Count of negative ratings */
  negative_count: number;
  /** Positive rating percentage (0.0 - 1.0) */
  positive_rate: number;
  /** Total hallucination reports */
  hallucination_reports: number;
  /** Breakdown by hallucination category */
  hallucination_categories?: HallucinationCategoryCounts;
}

/**
 * FeedbackSummaryResponse type with camelCase keys (after RTK Query transformation).
 */
export type FeedbackSummaryResponseCamelCase =
  SnakeToCamelCaseDeep<FeedbackSummaryResponse>;

/**
 * Parameters for getFeedbackSummary query.
 */
export interface FeedbackSummaryParams {
  /** Time period for aggregation (default: "7d") */
  timeframe?: string;
}

// =============================================================================
// Admin User Management
// =============================================================================

/**
 * Admin user response model
 */
export interface AdminUser {
  user_id: string;
  username: string;
  email: string;
  roles: string[];
  active: boolean;
}

/**
 * AdminUser with camelCase keys for frontend use.
 * Used after transformSnakeToCamel transformation.
 */
export type AdminUserCamelCase = SnakeToCamelCaseDeep<AdminUser>;

/**
 * Admin user list query parameters
 */
export interface AdminUserListParams {
  search?: string;
}

/**
 * Create user request
 */
export interface CreateAdminUserRequest {
  username: string;
  email: string;
  password: string;
  roles?: string[];
}

/**
 * Update user request
 */
export interface UpdateAdminUserRequest {
  user_id: string;
  email?: string;
  roles?: string[];
  active?: boolean;
}

/**
 * Admin user paginated response
 */
export interface AdminUserListResponse {
  items: AdminUser[];
  total: number;
}

// =============================================================================
// Workflow Executions
// =============================================================================

/**
 * Workflow execution response model
 */
export interface WorkflowExecution {
  id: string;
  workflow_id: string;
  status: "pending" | "running" | "completed" | "failed";
  started_at: string;
  completed_at?: string | null;
  input_data?: Record<string, unknown> | null;
  output_data?: Record<string, unknown> | null;
  error?: string | null;
}

/**
 * Workflow execution list query parameters
 */
export interface WorkflowExecutionListParams extends CursorPaginationParams {
  workflow_id: string;
  status?: string;
}

/**
 * Workflow execution paginated response
 */
export interface WorkflowExecutionListResponse {
  items: WorkflowExecution[];
  total: number;
  next_cursor?: string | null;
}

/**
 * WorkflowExecution type with camelCase keys (after RTK Query transformation).
 */
export type WorkflowExecutionCamelCase =
  SnakeToCamelCaseDeep<WorkflowExecution>;

/**
 * WorkflowExecutionListResponse type with camelCase keys (after RTK Query transformation).
 */
export interface WorkflowExecutionListResponseCamelCase {
  items: WorkflowExecutionCamelCase[];
  total: number;
  nextCursor?: string | null;
}

// =============================================================================
// Notification Preferences
// =============================================================================

/**
 * User notification preferences (backend snake_case)
 */
export interface NotificationPreferences {
  user_id: string;
  info_enabled: boolean;
  success_enabled: boolean;
  warning_enabled: boolean;
  error_enabled: boolean;
}

/**
 * User notification preferences (frontend camelCase)
 */
export interface NotificationPreferencesCamelCase {
  userId: string;
  infoEnabled: boolean;
  successEnabled: boolean;
  warningEnabled: boolean;
  errorEnabled: boolean;
}

/**
 * Request to update notification preferences (partial update)
 */
export interface UpdateNotificationPreferencesRequest {
  info_enabled?: boolean;
  success_enabled?: boolean;
  warning_enabled?: boolean;
  error_enabled?: boolean;
}

// =============================================================================
// User Preferences (UX Enhancement)
// =============================================================================

/**
 * User preferences for personalization
 */
export interface UserPreferences {
  // General
  theme: "light" | "dark" | "system";
  language: string;
  auto_scroll: boolean;

  // Accessibility
  reduced_motion: boolean;
  high_contrast: boolean;
  screen_reader_mode: boolean;
  font_size: "small" | "medium" | "large";

  // Model Defaults
  default_model: string | null;
  default_temperature: number;
  default_max_tokens: number;

  // Session
  pinned_sessions: string[];

  // Privacy
  notifications_enabled: boolean;

  // Keyboard Shortcuts
  keyboard_shortcuts: Record<string, string>;
}

/**
 * UserPreferences with camelCase keys for frontend use.
 * Used after transformSnakeToCamel transformation.
 */
export type UserPreferencesCamelCase = SnakeToCamelCaseDeep<UserPreferences>;

/**
 * Request to update user preferences (partial update)
 */
export interface UserPreferencesUpdate {
  theme?: "light" | "dark" | "system";
  language?: string;
  auto_scroll?: boolean;
  reduced_motion?: boolean;
  high_contrast?: boolean;
  screen_reader_mode?: boolean;
  font_size?: "small" | "medium" | "large";
  default_model?: string | null;
  default_temperature?: number;
  default_max_tokens?: number;
  pinned_sessions?: string[];
  notifications_enabled?: boolean;
  keyboard_shortcuts?: Record<string, string>;
}

// =============================================================================
// Session Export (UX Enhancement)
// =============================================================================

/**
 * Session export format
 */
export type ExportFormat = "markdown" | "json" | "html";

/**
 * Request to export a session
 */
export interface SessionExportRequest {
  format: ExportFormat;
  include_metadata?: boolean;
}

// =============================================================================
// Infrastructure Alerts & Remediations (Admin Dashboard)
// =============================================================================

/**
 * Risk level for remediation steps
 */
export type RiskLevel = "low" | "medium" | "high";

/**
 * Remediation status
 */
export type RemediationStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "executing"
  | "completed"
  | "failed";

/**
 * A single remediation step recommended by AI
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface RemediationStep {
  stepNumber: number;
  action: string;
  description: string;
  command: string | null;
  requiresApproval: boolean;
  riskLevel: RiskLevel;
}

/**
 * Risk assessment for a recommendation
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface RiskAssessment {
  overallRisk: RiskLevel;
  impactAnalysis: string;
  rollbackPlan: string;
}

/**
 * AI-generated recommendation for an alert
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface AIRecommendation {
  recommendationId: string;
  alertId: string;
  rootCauseAnalysis: string;
  remediationSteps: RemediationStep[];
  riskAssessment: RiskAssessment;
  runbookReference: string | null;
  generatedAt: string;
  modelUsed: string;
}

/**
 * A remediation request pending approval
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface RemediationRequest {
  remediationId: string;
  alertId: string;
  alertName: string;
  severity: "critical" | "warning";
  stepNumber: number;
  action: string;
  description: string;
  command: string | null;
  riskLevel: RiskLevel;
  status: RemediationStatus;
  requestedAt: string;
  approvedBy: string | null;
  approvedAt: string | null;
  reason: string | null;
  recommendationId: string;
}

/**
 * Remediation list query parameters
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface RemediationListParams {
  status?: RemediationStatus;
  alertId?: string;
  severity?: "critical" | "warning";
  limit?: number;
  cursor?: string;
}

/**
 * Request to approve a remediation
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface ApproveRemediationRequest {
  remediationId: string;
  approvedBy: string;
  reason?: string;
}

/**
 * Request to reject a remediation
 * Note: Uses camelCase per ADR-0091 (transformed at API boundary)
 */
export interface RejectRemediationRequest {
  remediationId: string;
  rejectedBy: string;
  reason: RejectionReason;
  reasonDetail?: string;
}

/**
 * Structured rejection reason for AI model learning
 */
export type RejectionReason =
  | "too_risky"
  | "incorrect_diagnosis"
  | "wrong_command"
  | "incomplete_steps"
  | "not_relevant"
  | "prefer_manual"
  | "other";

/**
 * Request to reject a remediation with structured reason (for AI learning)
 */
export interface RejectRemediationWithReasonRequest {
  remediation_id: string;
  rejected_by: string;
  reason: RejectionReason;
  reason_detail?: string;
}

/**
 * Alert severity for grouping (subset of full severity)
 */
export type GroupAlertSeverity = "critical" | "warning";

/**
 * Alert state for grouping
 */
export type GroupAlertState = "firing" | "resolved";

/**
 * A group of related alerts aggregated by service + alert name.
 * Used for reducing noise in the Admin Dashboard.
 */
export interface AlertGroup {
  /** Composite key: "service:alertname" */
  groupKey: string;
  /** Service name from alert labels (may be undefined) */
  service?: string;
  /** Alert name (alertname label) */
  alertName: string;
  /** Highest severity in the group */
  severity: GroupAlertSeverity;
  /** "firing" if any alert is firing, else "resolved" */
  state: GroupAlertState;
  /** Number of alerts in this group */
  count: number;
  /** Most recent alert for display */
  mostRecentAlert: ObservabilityAlert;
  /** All alerts in this group */
  alerts: ObservabilityAlert[];
  /** Earliest start time */
  firstFiredAt: string;
  /** Most recent update time */
  lastUpdatedAt: string;
}

// =============================================================================
// Agent HITL Request Types
// =============================================================================

/**
 * Agent request status from backend
 */
export type AgentRequestStatus =
  | "pending"
  | "approved"
  | "rejected"
  | "expired"
  | "responded";

/**
 * Agent request type discriminator
 */
export type AgentRequestType = "approval" | "clarification";

/**
 * Response for listing pending agent requests
 */
export interface PendingAgentRequestsResponse {
  approvals: Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    confidence: number;
    threshold: number;
    proposed_action: string;
    trigger_reason: string;
    context: Record<string, unknown>;
    requested_at: string;
  }>;
  clarifications: Array<{
    request_id: string;
    session_id: string;
    task_id: string;
    agent_name: string;
    clarification_type: "text" | "choice" | "confirmation";
    question: string;
    options: Array<{
      id: string;
      label: string;
      description?: string;
      is_recommended?: boolean;
    }>;
    placeholder: string | null;
    required: boolean;
    context: Record<string, unknown>;
    requested_at: string;
  }>;
  total_count: number;
}

/**
 * Response for single request action (approve/reject/respond)
 */
export interface AgentRequestActionResponse {
  success: boolean;
  request_id: string;
  status: AgentRequestStatus;
  message?: string;
}

/**
 * Parameters for approve request mutation
 */
export interface ApproveAgentRequestParams {
  requestId: string;
  approved_by: string;
  reason?: string;
  modifications?: Record<string, unknown>;
}

/**
 * Parameters for reject request mutation
 */
export interface RejectAgentRequestParams {
  requestId: string;
  rejected_by: string;
  reason?: string;
}

/**
 * Parameters for respond to clarification mutation
 *
 * Backend expects (from agent_requests.py ClarificationResponseRequest):
 * - responded_by: Required - email/ID of responder
 * - response_type: Required - type of response
 * - value: For text responses (NOT text_response)
 * - selected_option_id: For choice responses (NOT selected_option)
 * - confirmed: For confirmation responses
 */
export interface RespondAgentRequestParams {
  request_id: string;
  responded_by: string;
  response_type: "choice" | "text" | "confirm";
  value?: string;
  selected_option_id?: string;
  confirmed?: boolean;
}

/**
 * Parameters for batch operations
 *
 * NOTE: approved_by/rejected_by are NOT included - backend derives from auth
 * See: src/mcp_server_langgraph/api/v1/agent_requests.py BatchApproveRequest
 */
export interface BatchApproveAgentRequestParams {
  request_ids: string[];
  reason?: string;
}

export interface BatchRejectAgentRequestParams {
  request_ids: string[];
  reason?: string;
}

/**
 * Response for batch operations
 */
export interface BatchAgentRequestResponse {
  success: boolean;
  processed: number;
  failed: number;
  results: Array<{
    request_id: string;
    success: boolean;
    error?: string;
  }>;
}

/**
 * Parameters for listing pending requests
 */
export interface ListPendingAgentRequestsParams {
  session_id?: string;
  status?: AgentRequestStatus;
  request_type?: AgentRequestType;
}

// =============================================================================
// MCP Protocol Types (2025-11-25)
// =============================================================================

/**
 * MCP Resource (backend snake_case)
 */
export interface McpResource {
  uri: string;
  name: string;
  title?: string | null;
  description?: string | null;
  mime_type?: string | null;
}

/**
 * MCP Resource (frontend camelCase)
 */
export interface McpResourceCamelCase {
  uri: string;
  name: string;
  title?: string | null;
  description?: string | null;
  mimeType?: string | null;
}

/**
 * Response for listing MCP resources
 */
export interface McpResourceListResponse {
  resources: McpResource[];
}

/**
 * MCP Resource content item (backend snake_case)
 */
export interface McpResourceContentItem {
  uri: string;
  mime_type?: string | null;
  text?: string | null;
  blob?: string | null;
}

/**
 * MCP Resource content item (frontend camelCase)
 */
export interface McpResourceContentItemCamelCase {
  uri: string;
  mimeType?: string | null;
  text?: string | null;
  blob?: string | null;
}

/**
 * Response for reading MCP resource content
 */
export interface McpResourceContentResponse {
  contents: McpResourceContentItem[];
}

/**
 * Request for reading MCP resource
 */
export interface McpReadResourceRequest {
  uri: string;
}

/**
 * MCP Tool definition
 */
export interface McpTool {
  name: string;
  description: string;
  inputSchema?: Record<string, unknown>;
}

/**
 * Response for listing MCP tools
 */
export interface McpToolListResponse {
  tools: McpTool[];
}

/**
 * Request for invoking MCP tool
 */
export interface McpInvokeToolRequest {
  name: string;
  arguments: Record<string, unknown>;
}

/**
 * Response for MCP tool invocation
 */
export interface McpToolInvocationResponse {
  content: Array<{
    type: string;
    text?: string;
    data?: string;
    mimeType?: string;
  }>;
  isError: boolean;
}

/**
 * Request for MCP sampling (LLM completion)
 */
export interface McpSamplingRequest {
  messages: Array<{
    role: string;
    content: {
      type: string;
      text?: string;
      data?: string;
      mimeType?: string;
    };
  }>;
  max_tokens?: number;
  system_prompt?: string | null;
  model_hints?: string[] | null;
  intelligence_priority?: number;
  speed_priority?: number;
  cost_priority?: number;
}

/**
 * Response for MCP sampling
 */
export interface McpSamplingResponse {
  role: string;
  content: {
    type: string;
    text?: string;
    data?: string;
    mimeType?: string;
  };
  model?: string | null;
  stop_reason?: string | null;
}

/**
 * Request for MCP elicitation (user input)
 */
export interface McpElicitationRequest {
  message: string;
  schema?: Record<string, unknown> | null;
}

/**
 * Response for MCP elicitation
 */
export interface McpElicitationResponse {
  action: "accept" | "decline" | "cancel";
  content?: Record<string, unknown> | null;
}

/**
 * MCP Prompt argument
 */
export interface McpPromptArgument {
  name: string;
  description?: string;
  required?: boolean;
}

/**
 * MCP Prompt definition
 */
export interface McpPrompt {
  name: string;
  description?: string;
  arguments?: McpPromptArgument[];
}

/**
 * Response for listing MCP prompts
 */
export interface McpPromptListResponse {
  prompts: McpPrompt[];
}

/**
 * Request for getting MCP prompt
 */
export interface McpGetPromptRequest {
  name: string;
  arguments?: Record<string, string>;
}

/**
 * Response for getting MCP prompt
 */
export interface McpGetPromptResponse {
  messages: Array<{
    role: string;
    content: {
      type: string;
      text?: string;
      resource?: {
        uri: string;
        text?: string;
        blob?: string;
        mimeType?: string;
      };
    };
  }>;
}

/**
 * MCP Task status
 */
export type McpTaskStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled";

/**
 * MCP Task
 */
export interface McpTask {
  task_id: string;
  status: McpTaskStatus;
  created_at: string;
  last_updated_at: string;
  ttl?: number | null;
  poll_interval?: number | null;
  status_message?: string | null;
}

/**
 * Response for listing MCP tasks
 */
export interface McpTaskListResponse {
  tasks: McpTask[];
}

// =============================================================================
// Studio Analyze Types (ADR-0091 Phase 9)
// =============================================================================

/**
 * Task categories for Studio AI analysis
 */
export type StudioAnalyzeTaskCategory =
  | "UX"
  | "SESSION"
  | "CONVERSATION"
  | "CANVAS"
  | "DIAGRAM"
  | "TRACE"
  | "HITL"
  | "COMMAND";

/**
 * Individual task request for Studio AI analysis
 */
export interface StudioAnalyzeTaskRequest {
  category: StudioAnalyzeTaskCategory | string;
  type: string;
  data?: Record<string, unknown>;
}

/**
 * Request model for unified Studio AI analysis.
 * Matches backend StudioAnalyzeRequest schema.
 */
export interface StudioAnalyzeRequest {
  user_id: string;
  session_id: string;
  persona?: string | null;
  tasks: StudioAnalyzeTaskRequest[];
  context?: Record<string, unknown>;
}

/**
 * CamelCase version of StudioAnalyzeRequest for frontend use.
 */
export interface StudioAnalyzeRequestCamelCase {
  userId: string;
  sessionId: string;
  persona?: string | null;
  tasks: StudioAnalyzeTaskRequest[];
  context?: Record<string, unknown>;
}

/**
 * Response model for unified Studio AI analysis.
 * Matches backend StudioAnalyzeResponse schema.
 */
export interface StudioAnalyzeResponse {
  user_id: string;
  session_id: string;
  analyses?: Record<string, unknown>;
  cross_insights?: string[];
  failed_analyses?: string[];
  total_cost: string;
}

/**
 * CamelCase version of StudioAnalyzeResponse for frontend use.
 */
export interface StudioAnalyzeResponseCamelCase {
  userId: string;
  sessionId: string;
  analyses?: Record<string, unknown>;
  crossInsights?: string[];
  failedAnalyses?: string[];
  totalCost: string;
}

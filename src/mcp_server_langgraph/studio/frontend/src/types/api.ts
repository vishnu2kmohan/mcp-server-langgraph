/**
 * Centralized API Type Definitions
 *
 * All API request/response types are defined here to ensure consistency
 * across the application and avoid duplication.
 */

// =============================================================================
// Common Types
// =============================================================================

/**
 * Sort order type
 */
export type SortOrder = "asc" | "desc";

/**
 * Generic paginated response wrapper
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  limit: number;
  cursor?: string;
  next_cursor?: string;
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
  /** Enable LLM suggestions */
  llm_suggestions?: boolean;
  /** Enable notification preferences */
  notification_preferences?: boolean;
  /** Enable MCP WebSocket connections */
  mcp_websocket?: boolean;
  /** Enable interactive artifact rendering in chat messages (Sandpack for JSX/TSX/MDX) */
  interactive_artifacts?: boolean;
  /** Enable URL content fetching */
  url_content_fetch?: boolean;
  /** Enable slash commands */
  slash_commands?: boolean;
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

  // ==========================================================================
  // Canvas Hybrid Shell Feature Flags (Phase 0+)
  // ==========================================================================
  /** Enable Hybrid Canvas shell at /studio/v2 (Phase 1) */
  canvas_studio_shell?: boolean;
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

  // Allow dynamic flag access
  [key: string]: boolean | undefined;
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

export interface Session {
  id: string; // Changed from session_id to match REST convention
  name: string;
  workflow_id?: string;
  user_id?: string;
  status: "active" | "archived" | "deleted"; // Constrained to valid values
  created_at: string;
  updated_at: string;
  config?: ApiSessionConfig;
}

export interface SessionRef {
  id: string;
  name: string;
  message_count: number;
  created_at: string | null;
}

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
  /** LLM thinking/reasoning content (from Claude extended thinking, etc.) */
  thinking_content?: string;
  /** Number of tokens used for thinking/reasoning */
  thinking_tokens?: number;
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

export interface AgentConfig {
  model: string;
  provider: string;
  temperature: number;
  verification_enabled: boolean;
  tools: AgentTool[];
}

export interface AgentTool {
  name: string;
  description: string;
  enabled: boolean;
}

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

// =============================================================================
// Notification Preferences
// =============================================================================

/**
 * User notification preferences
 */
export interface NotificationPreferences {
  user_id: string;
  info_enabled: boolean;
  success_enabled: boolean;
  warning_enabled: boolean;
  error_enabled: boolean;
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
 */
export interface RemediationStep {
  step_number: number;
  action: string;
  description: string;
  command: string | null;
  requires_approval: boolean;
  risk_level: RiskLevel;
}

/**
 * Risk assessment for a recommendation
 */
export interface RiskAssessment {
  overall_risk: RiskLevel;
  impact_analysis: string;
  rollback_plan: string;
}

/**
 * AI-generated recommendation for an alert
 */
export interface AIRecommendation {
  recommendation_id: string;
  alert_id: string;
  root_cause_analysis: string;
  remediation_steps: RemediationStep[];
  risk_assessment: RiskAssessment;
  runbook_reference: string | null;
  generated_at: string;
  model_used: string;
}

/**
 * A remediation request pending approval
 */
export interface RemediationRequest {
  remediation_id: string;
  alert_id: string;
  alert_name: string;
  severity: "critical" | "warning";
  step_number: number;
  action: string;
  description: string;
  command: string | null;
  risk_level: RiskLevel;
  status: RemediationStatus;
  requested_at: string;
  approved_by: string | null;
  approved_at: string | null;
  reason: string | null;
  recommendation_id: string;
}

/**
 * Remediation list query parameters
 */
export interface RemediationListParams {
  status?: RemediationStatus;
  alert_id?: string;
  severity?: "critical" | "warning";
  limit?: number;
  cursor?: string;
}

/**
 * Request to approve a remediation
 */
export interface ApproveRemediationRequest {
  remediation_id: string;
  approved_by: string;
  reason?: string;
}

/**
 * Request to reject a remediation
 */
export interface RejectRemediationRequest {
  remediation_id: string;
  rejected_by: string;
  reason: RejectionReason;
  reason_detail?: string;
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
 */
export interface RespondAgentRequestParams {
  request_id: string;
  response_type: "choice" | "text" | "confirm";
  selected_option?: string;
  text_response?: string;
  confirmed?: boolean;
}

/**
 * Parameters for batch operations
 */
export interface BatchApproveAgentRequestParams {
  request_ids: string[];
  approved_by: string;
  reason?: string;
}

export interface BatchRejectAgentRequestParams {
  request_ids: string[];
  rejected_by: string;
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
 * MCP Resource
 */
export interface McpResource {
  uri: string;
  name: string;
  title?: string | null;
  description?: string | null;
  mime_type?: string | null;
}

/**
 * Response for listing MCP resources
 */
export interface McpResourceListResponse {
  resources: McpResource[];
}

/**
 * MCP Resource content item
 */
export interface McpResourceContentItem {
  uri: string;
  mime_type?: string | null;
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

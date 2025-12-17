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

export interface FeatureFlags {
  enable_workflows_feature?: boolean;
  enable_sessions_feature?: boolean;
  enable_cost_dashboard?: boolean;
  enable_cost_dashboard_users?: boolean;
  enable_observability_ui?: boolean;
  enable_code_export?: boolean;
  enable_ai_suggestions?: boolean;
  enable_mcp_websocket?: boolean;
  /** Enable interactive artifact rendering in chat messages (Sandpack for JSX/TSX/MDX) */
  enable_interactive_artifacts?: boolean;
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

export interface Session {
  id: string; // Changed from session_id to match REST convention
  name: string;
  workflow_id?: string;
  user_id?: string;
  status: "active" | "archived" | "deleted"; // Constrained to valid values
  created_at: string;
  updated_at: string;
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

/**
 * Type-Safe Mock Factories for E2E Tests
 *
 * These factories create complete mock objects that match the actual API types.
 * Using factories prevents field mismatches between E2E test mocks and the real API.
 *
 * Benefits:
 * 1. Type safety - TypeScript catches missing required fields
 * 2. Consistency - All mocks use the same structure
 * 3. Maintainability - Update factory when API changes, all tests get updates
 * 4. DRY - No copy-paste of mock data across tests
 *
 * Usage in E2E tests:
 * ```typescript
 * import { mockProject, mockSession, mockUser } from './fixtures/mock-factories';
 *
 * await page.route('**/api/v1/projects/*', (route) => {
 *   route.fulfill({
 *     body: JSON.stringify(mockProject({ name: 'Custom Name' })),
 *   });
 * });
 * ```
 */

import type {
  AdminUser,
  AgentConfig,
  AgentTool,
  AuditLogEntry,
  ConnectionRef,
  CostHistoryPoint,
  CostSummary,
  FeatureFlags,
  HealthStatus,
  HEARTAggregateMetrics,
  LogEntry,
  Message,
  ModelCostData,
  Project,
  ProjectDetail,
  ProjectMember,
  Session,
  SessionRef,
  TokenUsage,
  TraceSpan,
  UserInfo,
  VectorCollection,
  VectorCollectionDetail,
  Workflow,
  WorkflowExecution,
  WorkflowRef,
  WorkflowShare,
} from '../../src/types/api';

// =============================================================================
// Base Factory Utilities
// =============================================================================

let idCounter = 0;

/**
 * Generate a unique ID for mock objects
 */
function uniqueId(prefix: string = 'id'): string {
  return `${prefix}-${++idCounter}`;
}

/**
 * Get current ISO timestamp
 */
function now(): string {
  return new Date().toISOString();
}

/**
 * Get a past timestamp
 */
function pastTime(hoursAgo: number = 1): string {
  return new Date(Date.now() - hoursAgo * 60 * 60 * 1000).toISOString();
}

// =============================================================================
// User & Auth Factories
// =============================================================================

/**
 * Create a mock UserInfo object
 */
export function mockUser(overrides: Partial<UserInfo> = {}): UserInfo {
  return {
    id: uniqueId('user'),
    username: 'alice',
    email: 'alice@example.com',
    roles: ['developer'],
    ...overrides,
  };
}

/**
 * Create a mock AdminUser object
 */
export function mockAdminUser(overrides: Partial<AdminUser> = {}): AdminUser {
  return {
    user_id: uniqueId('user'),
    username: 'admin',
    email: 'admin@example.com',
    roles: ['admin'],
    active: true,
    ...overrides,
  };
}

// =============================================================================
// Project Factories
// =============================================================================

/**
 * Create a mock ProjectMember object
 */
export function mockProjectMember(overrides: Partial<ProjectMember> = {}): ProjectMember {
  return {
    user_id: uniqueId('user'),
    role: 'owner',
    added_at: now(),
    ...overrides,
  };
}

/**
 * Create a mock ConnectionRef object
 */
export function mockConnectionRef(overrides: Partial<ConnectionRef> = {}): ConnectionRef {
  return {
    id: uniqueId('conn'),
    type: 'mcp',
    name: 'MCP Server',
    status: 'connected',
    ...overrides,
  };
}

/**
 * Create a mock Project object (list item)
 */
export function mockProject(overrides: Partial<Project> = {}): Project {
  return {
    id: uniqueId('project'),
    name: 'Test Project',
    description: 'A test project for E2E testing',
    organization_id: null,
    owner_id: 'alice',
    owner_name: 'Alice',
    created_at: pastTime(24),
    updated_at: now(),
    status: 'active',
    workflow_count: 2,
    session_count: 5,
    connection_count: 1,
    ...overrides,
  };
}

/**
 * Create a mock ProjectDetail object (full detail view)
 *
 * This factory ensures all required fields for ProjectDetailPage are included,
 * preventing E2E failures like "Sessions tab not visible" due to missing fields.
 */
export function mockProjectDetail(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  const baseProject = mockProject(overrides);
  return {
    ...baseProject,
    workflow_count: overrides.workflow_count ?? 2,
    session_count: overrides.session_count ?? 5,
    connection_count: overrides.connection_count ?? 1,
    workflows: overrides.workflows ?? [
      mockWorkflowRef({ name: 'Workflow 1' }),
      mockWorkflowRef({ name: 'Workflow 2' }),
    ],
    sessions: overrides.sessions ?? [
      mockSessionRef({ name: 'Session 1', message_count: 5 }),
      mockSessionRef({ name: 'Session 2', message_count: 10 }),
      mockSessionRef({ name: 'Session 3', message_count: 3 }),
      mockSessionRef({ name: 'Session 4', message_count: 7 }),
      mockSessionRef({ name: 'Session 5', message_count: 2 }),
    ],
    connections: overrides.connections ?? [mockConnectionRef()],
    members: overrides.members ?? [mockProjectMember({ user_id: 'alice', role: 'owner' })],
  };
}

// =============================================================================
// Workflow Factories
// =============================================================================

/**
 * Create a mock WorkflowRef object (reference in lists)
 */
export function mockWorkflowRef(overrides: Partial<WorkflowRef> = {}): WorkflowRef {
  return {
    id: uniqueId('workflow'),
    name: 'Test Workflow',
    created_at: pastTime(12),
    ...overrides,
  };
}

/**
 * Create a mock Workflow object (full workflow)
 */
export function mockWorkflow(overrides: Partial<Workflow> = {}): Workflow {
  return {
    id: uniqueId('workflow'),
    name: 'Test Workflow',
    description: 'A test workflow for E2E testing',
    nodes: [],
    edges: [],
    user_id: 'alice',
    created_at: pastTime(24),
    updated_at: now(),
    ...overrides,
  };
}

/**
 * Create a mock WorkflowShare object
 */
export function mockWorkflowShare(overrides: Partial<WorkflowShare> = {}): WorkflowShare {
  return {
    user_id: uniqueId('user'),
    email: 'bob@example.com',
    permission: 'view',
    ...overrides,
  };
}

/**
 * Create a mock WorkflowExecution object
 */
export function mockWorkflowExecution(overrides: Partial<WorkflowExecution> = {}): WorkflowExecution {
  return {
    id: uniqueId('exec'),
    workflow_id: uniqueId('workflow'),
    status: 'completed',
    started_at: pastTime(1),
    completed_at: now(),
    input_data: { input: 'test' },
    output_data: { output: 'result' },
    error: null,
    ...overrides,
  };
}

// =============================================================================
// Session Factories
// =============================================================================

/**
 * Create a mock SessionRef object (reference in lists)
 */
export function mockSessionRef(overrides: Partial<SessionRef> = {}): SessionRef {
  return {
    id: uniqueId('session'),
    name: 'Test Session',
    message_count: 5,
    created_at: pastTime(6),
    ...overrides,
  };
}

/**
 * Create a mock Session object (full session)
 */
export function mockSession(overrides: Partial<Session> = {}): Session {
  return {
    session_id: uniqueId('session'),
    name: 'Test Session',
    workflow_id: undefined,
    user_id: 'alice',
    status: 'active',
    created_at: pastTime(6),
    updated_at: now(),
    ...overrides,
  };
}

/**
 * Create a mock Message object
 */
export function mockMessage(overrides: Partial<Message> = {}): Message {
  return {
    message_id: uniqueId('msg'),
    role: 'user',
    content: 'Test message content',
    timestamp: now(),
    metadata: {},
    ...overrides,
  };
}

/**
 * Create a mock TokenUsage object
 */
export function mockTokenUsage(overrides: Partial<TokenUsage> = {}): TokenUsage {
  return {
    prompt_tokens: 100,
    completion_tokens: 50,
    total_tokens: 150,
    ...overrides,
  };
}

// =============================================================================
// Cost Factories
// =============================================================================

/**
 * Create a mock CostSummary object
 */
export function mockCostSummary(overrides: Partial<CostSummary> = {}): CostSummary {
  return {
    total_cost: 12.5,
    prompt_tokens: 50000,
    completion_tokens: 25000,
    total_tokens: 75000,
    period_start: pastTime(24 * 30), // 30 days ago
    period_end: now(),
    ...overrides,
  };
}

/**
 * Create a mock ModelCostData object
 */
export function mockModelCost(overrides: Partial<ModelCostData> = {}): ModelCostData {
  return {
    model: 'gpt-4',
    cost: 5.25,
    requests: 150,
    prompt_tokens: 25000,
    completion_tokens: 12000,
    ...overrides,
  };
}

/**
 * Create a mock CostHistoryPoint object
 */
export function mockCostHistoryPoint(overrides: Partial<CostHistoryPoint> = {}): CostHistoryPoint {
  return {
    date: new Date().toISOString().split('T')[0],
    cost: 2.5,
    requests: 50,
    ...overrides,
  };
}

// =============================================================================
// Observability Factories
// =============================================================================

/**
 * Create a mock TraceSpan object
 */
export function mockTraceSpan(overrides: Partial<TraceSpan> = {}): TraceSpan {
  return {
    trace_id: uniqueId('trace'),
    span_id: uniqueId('span'),
    parent_span_id: undefined,
    name: 'chat.completion',
    start_time: pastTime(0.01),
    end_time: now(),
    status: 'OK',
    attributes: {},
    ...overrides,
  };
}

/**
 * Create a mock LogEntry object
 */
export function mockLogEntry(overrides: Partial<LogEntry> = {}): LogEntry {
  return {
    id: uniqueId('log'),
    timestamp: now(),
    level: 'info',
    message: 'Request processed successfully',
    service: 'mcp-server',
    ...overrides,
  };
}

/**
 * Create a mock AuditLogEntry object
 */
export function mockAuditLogEntry(overrides: Partial<AuditLogEntry> = {}): AuditLogEntry {
  return {
    id: uniqueId('audit'),
    action: 'session.created',
    user_id: 'alice',
    user_email: 'alice@example.com',
    resource_type: 'session',
    resource_id: uniqueId('session'),
    timestamp: now(),
    ip_address: '192.168.1.100',
    details: {},
    ...overrides,
  };
}

// =============================================================================
// Vector Factories
// =============================================================================

/**
 * Create a mock VectorCollection object
 */
export function mockVectorCollection(overrides: Partial<VectorCollection> = {}): VectorCollection {
  return {
    name: 'test-collection',
    vectors_count: 1000,
    ...overrides,
  };
}

/**
 * Create a mock VectorCollectionDetail object
 */
export function mockVectorCollectionDetail(
  overrides: Partial<VectorCollectionDetail> = {}
): VectorCollectionDetail {
  return {
    name: 'test-collection',
    vector_size: 1536,
    distance: 'Cosine',
    point_count: 1000,
    ...overrides,
  };
}

// =============================================================================
// Agent Factories
// =============================================================================

/**
 * Create a mock AgentTool object
 */
export function mockAgentTool(overrides: Partial<AgentTool> = {}): AgentTool {
  return {
    name: 'web_search',
    description: 'Search the web for information',
    enabled: true,
    ...overrides,
  };
}

/**
 * Create a mock AgentConfig object
 */
export function mockAgentConfig(overrides: Partial<AgentConfig> = {}): AgentConfig {
  return {
    model: 'gpt-4',
    provider: 'openai',
    temperature: 0.7,
    verification_enabled: false,
    tools: [mockAgentTool()],
    ...overrides,
  };
}

// =============================================================================
// Health & Metrics Factories
// =============================================================================

/**
 * Create a mock HealthStatus object
 */
export function mockHealthStatus(overrides: Partial<HealthStatus> = {}): HealthStatus {
  return {
    status: 'healthy',
    version: '1.0.0',
    uptime_seconds: 86400,
    ...overrides,
  };
}

/**
 * Create a mock HEARTAggregateMetrics object
 */
export function mockHeartMetrics(
  overrides: Partial<HEARTAggregateMetrics> = {}
): HEARTAggregateMetrics {
  return {
    period: 'day',
    app_name: 'mcp-server',
    nps_score_avg: 8.5,
    satisfaction_avg: 4.2,
    task_success_rate: 0.95,
    total_tasks_started: 1000,
    total_tasks_completed: 950,
    total_tasks_errored: 50,
    avg_session_duration_ms: 120000,
    total_interactions: 5000,
    top_features: { chat: 3000, workflows: 1500, cost: 500 },
    new_users_count: 25,
    onboarding_completion_rate: 0.85,
    avg_return_visits: 5.2,
    avg_days_active: 12.5,
    ...overrides,
  };
}

/**
 * Create a mock FeatureFlags object
 */
export function mockFeatureFlags(overrides: Partial<FeatureFlags> = {}): FeatureFlags {
  return {
    enable_workflows_feature: true,
    enable_sessions_feature: true,
    enable_cost_dashboard: true,
    enable_cost_dashboard_users: true,
    enable_observability_ui: true,
    enable_code_export: true,
    enable_ai_suggestions: true,
    enable_mcp_websocket: true,
    ...overrides,
  };
}

// =============================================================================
// Response Wrapper Factories
// =============================================================================

/**
 * Create a paginated list response (cursor-based)
 */
export function mockCursorPaginatedResponse<T>(
  data: T[],
  overrides: { count?: number; next_cursor?: string | null } = {}
): { data: T[]; pagination: { count: number; next_cursor: string | null } } {
  return {
    data,
    pagination: {
      count: overrides.count ?? data.length,
      next_cursor: overrides.next_cursor ?? null,
    },
  };
}

/**
 * Create a paginated list response (page-based)
 */
export function mockPagePaginatedResponse<T>(
  items: T[],
  overrides: { total?: number; page?: number; per_page?: number; total_pages?: number } = {}
): { items: T[]; total: number; page: number; per_page: number; total_pages: number } {
  const total = overrides.total ?? items.length;
  const per_page = overrides.per_page ?? 10;
  return {
    items,
    total,
    page: overrides.page ?? 1,
    per_page,
    total_pages: overrides.total_pages ?? Math.ceil(total / per_page),
  };
}

/**
 * Create an items+total response (simple list)
 */
export function mockItemsResponse<T>(
  items: T[],
  overrides: { total?: number } = {}
): { items: T[]; total: number } {
  return {
    items,
    total: overrides.total ?? items.length,
  };
}

// =============================================================================
// Reset Utilities
// =============================================================================

/**
 * Reset the ID counter (useful between test files)
 */
export function resetMockIdCounter(): void {
  idCounter = 0;
}

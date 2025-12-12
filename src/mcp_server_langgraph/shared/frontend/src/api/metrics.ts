/**
 * Metrics API Client
 *
 * Frontend client for the HEART Metrics API.
 * Respects Do Not Track (DNT) browser setting.
 */

// ==============================================================================
// Types
// ==============================================================================

export interface TaskMetrics {
  tasks_started: number;
  tasks_completed: number;
  tasks_errored: number;
}

export interface EngagementMetrics {
  session_duration_ms: number;
  interaction_count: number;
  feature_usage: Record<string, number>;
}

export interface HappinessMetrics {
  nps_score?: number;
  satisfaction_score?: number;
}

export interface AdoptionMetrics {
  is_new_user: boolean;
  onboarding_steps_completed: string[];
}

export interface RetentionMetrics {
  return_visits: number;
  days_active: number;
}

export interface HeartMetricsBatch {
  session_id: string;
  app_name: 'builder' | 'playground';
  task_success?: TaskMetrics;
  engagement?: EngagementMetrics;
  happiness?: HappinessMetrics;
  adoption?: AdoptionMetrics;
  retention?: RetentionMetrics;
}

export interface MetricsReceipt {
  id: string;
  received_at: string;
  message?: string;
}

export interface FeatureEvent {
  feature_name: string;
  event_type: 'used' | 'clicked' | 'error';
  metadata?: Record<string, string | number | boolean>;
}

export interface EventReceipt {
  count: number;
  received_at: string;
}

export interface AggregateMetrics {
  period: string;
  app_name?: string;
  nps_score_avg?: number;
  satisfaction_avg?: number;
  task_success_rate?: number;
  total_tasks_started?: number;
  total_tasks_completed?: number;
  total_tasks_errored?: number;
  avg_session_duration_ms?: number;
  total_interactions?: number;
  top_features?: Record<string, number>;
  new_users_count?: number;
  onboarding_completion_rate?: number;
  avg_return_visits?: number;
  avg_days_active?: number;
}

export interface DashboardData {
  builder: Partial<AggregateMetrics>;
  playground: Partial<AggregateMetrics>;
  total_metrics_count: number;
  total_events_count: number;
  generated_at: string;
}

// ==============================================================================
// Privacy Helpers
// ==============================================================================

/**
 * Check if Do Not Track is enabled in the browser.
 */
function isDoNotTrackEnabled(): boolean {
  if (typeof navigator === 'undefined') return false;
  return navigator.doNotTrack === '1';
}

// ==============================================================================
// API Functions
// ==============================================================================

const API_BASE = '/api/v1/metrics';

/**
 * Send HEART metrics batch to the server.
 * Respects Do Not Track setting.
 */
export async function sendHeartMetrics(metrics: HeartMetricsBatch): Promise<MetricsReceipt> {
  // Respect Do Not Track
  if (isDoNotTrackEnabled()) {
    return { id: 'dnt-disabled', received_at: new Date().toISOString() };
  }

  const response = await fetch(`${API_BASE}/heart`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(metrics),
  });

  if (!response.ok) {
    throw new Error(`Failed to send metrics: ${response.status}`);
  }

  return response.json();
}

/**
 * Send feature events to the server.
 * Respects Do Not Track setting.
 */
export async function sendEvents(
  sessionId: string,
  appName: 'builder' | 'playground',
  events: FeatureEvent[]
): Promise<EventReceipt> {
  // Respect Do Not Track
  if (isDoNotTrackEnabled()) {
    return { count: 0, received_at: new Date().toISOString() };
  }

  const response = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      app_name: appName,
      events,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to send events: ${response.status}`);
  }

  return response.json();
}

/**
 * Get aggregated HEART metrics.
 */
export async function getAggregateMetrics(options?: {
  period?: string;
  app?: string;
}): Promise<AggregateMetrics> {
  const params = new URLSearchParams();
  if (options?.period) params.set('period', options.period);
  if (options?.app) params.set('app', options.app);

  const queryString = params.toString();
  const url = queryString
    ? `${API_BASE}/heart/aggregate?${queryString}`
    : `${API_BASE}/heart/aggregate`;

  const response = await fetch(url, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error(`Failed to get aggregate metrics: ${response.status}`);
  }

  return response.json();
}

/**
 * Get dashboard data for admin UI.
 */
export async function getDashboard(): Promise<DashboardData> {
  const response = await fetch(`${API_BASE}/dashboard`, {
    method: 'GET',
  });

  if (!response.ok) {
    throw new Error(`Failed to get dashboard: ${response.status}`);
  }

  return response.json();
}

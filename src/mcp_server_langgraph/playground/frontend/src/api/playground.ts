/**
 * Playground REST API Client
 *
 * REST fallback for observability data when MCP Resources
 * are not available. Communicates with the :8002 endpoint.
 */

import type {
  SessionSummary,
  SessionDetails,
  CreateSessionRequest,
  TraceInfo,
  LogEntry,
  LogLevel,
  Alert,
  MetricsSummary,
  LoginRequest,
  LoginResponse,
  AuthUser,
} from './types';
import { PlaygroundAPIError } from './types';

// =============================================================================
// API Client Configuration
// =============================================================================

export interface PlaygroundAPIConfig {
  baseUrl: string;
  authToken?: string;
  timeout?: number;
}

// =============================================================================
// API Response Types
// =============================================================================

interface APIResponse<T> {
  data: T;
  meta?: {
    total?: number;
    page?: number;
    pageSize?: number;
  };
}

interface TraceListParams {
  sessionId?: string;
  limit?: number;
  offset?: number;
}

interface LogListParams {
  sessionId?: string;
  level?: LogLevel;
  limit?: number;
  offset?: number;
  since?: string;
}

interface AlertListParams {
  acknowledged?: boolean;
  severity?: string;
  limit?: number;
}

// =============================================================================
// API Client Implementation
// =============================================================================

export class PlaygroundAPI {
  private baseUrl: string;
  private authToken: string | null;
  private timeout: number;

  constructor(config: PlaygroundAPIConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, '');
    this.authToken = config.authToken || null;
    this.timeout = config.timeout || 30000;
  }

  // ===========================================================================
  // Authentication
  // ===========================================================================

  setAuthToken(token: string | null): void {
    this.authToken = token;
  }

  async login(request: LoginRequest): Promise<LoginResponse> {
    return this.post<LoginResponse>('/auth/login', request);
  }

  async logout(): Promise<void> {
    await this.post<void>('/auth/logout', {});
  }

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    return this.post<LoginResponse>('/auth/refresh', { refreshToken });
  }

  async getCurrentUser(): Promise<AuthUser> {
    return this.get<AuthUser>('/auth/me');
  }

  // ===========================================================================
  // Session Endpoints
  // ===========================================================================

  async listSessions(): Promise<SessionSummary[]> {
    const response = await this.get<APIResponse<SessionSummary[]>>('/sessions');
    return response.data;
  }

  async getSession(sessionId: string): Promise<SessionDetails> {
    return this.get<SessionDetails>(`/sessions/${sessionId}`);
  }

  async createSession(request: CreateSessionRequest): Promise<SessionDetails> {
    return this.post<SessionDetails>('/sessions', request);
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.delete(`/sessions/${sessionId}`);
  }

  // ===========================================================================
  // Observability Endpoints
  // ===========================================================================

  async getTraces(params?: TraceListParams): Promise<TraceInfo[]> {
    const queryString = this.buildQueryString(params as Record<string, unknown>);
    const response = await this.get<APIResponse<TraceInfo[]>>(
      `/observability/traces${queryString}`
    );
    return response.data;
  }

  async getTrace(traceId: string): Promise<TraceInfo> {
    return this.get<TraceInfo>(`/observability/traces/${traceId}`);
  }

  async getLogs(params?: LogListParams): Promise<LogEntry[]> {
    const queryString = this.buildQueryString(params as Record<string, unknown>);
    const response = await this.get<APIResponse<LogEntry[]>>(
      `/observability/logs${queryString}`
    );
    return response.data;
  }

  async getMetrics(sessionId?: string): Promise<MetricsSummary> {
    const queryString = sessionId ? `?sessionId=${sessionId}` : '';
    return this.get<MetricsSummary>(`/observability/metrics${queryString}`);
  }

  async getAlerts(params?: AlertListParams): Promise<Alert[]> {
    const queryString = this.buildQueryString(params as Record<string, unknown>);
    const response = await this.get<APIResponse<Alert[]>>(
      `/observability/alerts${queryString}`
    );
    return response.data;
  }

  async acknowledgeAlert(alertId: string): Promise<Alert> {
    return this.post<Alert>(`/observability/alerts/${alertId}/acknowledge`, {});
  }

  // ===========================================================================
  // Health Check
  // ===========================================================================

  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.get<{ status: string; version: string }>('/health');
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  private getHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    if (this.authToken) {
      headers['Authorization'] = `Bearer ${this.authToken}`;
    }

    return headers;
  }

  private buildQueryString(params?: Record<string, unknown>): string {
    if (!params) return '';

    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null) {
        searchParams.append(key, String(value));
      }
    }

    const queryString = searchParams.toString();
    return queryString ? `?${queryString}` : '';
  }

  private async fetchWithTimeout(
    url: string,
    init: RequestInit
  ): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), this.timeout);

    try {
      const response = await fetch(url, {
        ...init,
        signal: controller.signal,
      });
      return response;
    } finally {
      clearTimeout(timeoutId);
    }
  }

  private async handleResponse<T>(response: Response): Promise<T> {
    if (!response.ok) {
      let errorData: { code?: string; message?: string; details?: unknown } | undefined;

      try {
        errorData = await response.json();
      } catch {
        // Response body is not JSON
      }

      throw new PlaygroundAPIError(
        errorData?.code || `HTTP_${response.status}`,
        errorData?.message || response.statusText,
        errorData?.details as Record<string, unknown> | undefined
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as unknown as T;
    }

    return response.json();
  }

  private async get<T>(path: string): Promise<T> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${path}`, {
      method: 'GET',
      headers: this.getHeaders(),
    });

    return this.handleResponse<T>(response);
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify(body),
    });

    return this.handleResponse<T>(response);
  }

  private async delete(path: string): Promise<void> {
    const response = await this.fetchWithTimeout(`${this.baseUrl}${path}`, {
      method: 'DELETE',
      headers: this.getHeaders(),
    });

    await this.handleResponse<void>(response);
  }
}

// =============================================================================
// Factory Function
// =============================================================================

export function createPlaygroundAPI(config: PlaygroundAPIConfig): PlaygroundAPI {
  return new PlaygroundAPI(config);
}

// =============================================================================
// Default Instance (for convenience)
// =============================================================================

let defaultInstance: PlaygroundAPI | null = null;

export function getPlaygroundAPI(): PlaygroundAPI {
  if (!defaultInstance) {
    defaultInstance = createPlaygroundAPI({
      baseUrl: '/api/playground',
    });
  }
  return defaultInstance;
}

export function configurePlaygroundAPI(config: PlaygroundAPIConfig): void {
  defaultInstance = createPlaygroundAPI(config);
}

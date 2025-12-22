/**
 * Tests for Metrics API Client
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  sendHeartMetrics,
  sendEvents,
  getAggregateMetrics,
  getDashboard,
  type HeartMetricsBatch,
  type FeatureEvent,
  type AggregateMetrics,
  type DashboardData,
} from './metrics';

// Mock fetch globally
const mockFetch = vi.fn();
global.fetch = mockFetch;

describe('Metrics API Client', () => {
  beforeEach(() => {
    mockFetch.mockClear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ==============================================================================
  // sendHeartMetrics Tests
  // ==============================================================================

  describe('sendHeartMetrics', () => {
    it('sends POST request to /api/v1/metrics/heart', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'receipt-123', received_at: '2024-01-01T00:00:00Z' }),
      });

      const metrics: HeartMetricsBatch = {
        session_id: 'test-session',
        app_name: 'studio',
      };

      await sendHeartMetrics(metrics);

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/heart', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(metrics),
      });
    });

    it('includes all metrics fields when provided', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ id: 'receipt-123' }),
      });

      const metrics: HeartMetricsBatch = {
        session_id: 'test-session',
        app_name: 'studio',
        task_success: {
          tasks_started: 10,
          tasks_completed: 8,
          tasks_errored: 2,
        },
        engagement: {
          session_duration_ms: 300000,
          interaction_count: 50,
          feature_usage: { code_generation: 5 },
        },
        happiness: {
          nps_score: 9,
          satisfaction_score: 4,
        },
      };

      await sendHeartMetrics(metrics);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.task_success).toEqual(metrics.task_success);
      expect(callBody.engagement).toEqual(metrics.engagement);
      expect(callBody.happiness).toEqual(metrics.happiness);
    });

    it('returns receipt on success', async () => {
      const receipt = { id: 'receipt-123', received_at: '2024-01-01T00:00:00Z', message: 'OK' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(receipt),
      });

      const result = await sendHeartMetrics({
        session_id: 'test',
        app_name: 'studio',
      });

      expect(result).toEqual(receipt);
    });

    it('throws error on failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
      });

      await expect(
        sendHeartMetrics({ session_id: 'test', app_name: 'studio' })
      ).rejects.toThrow('Failed to send metrics: 500');
    });

    it('respects Do Not Track setting', async () => {
      // Simulate DNT enabled
      Object.defineProperty(navigator, 'doNotTrack', {
        value: '1',
        configurable: true,
      });

      await sendHeartMetrics({
        session_id: 'test',
        app_name: 'studio',
      });

      // Should not call fetch when DNT is enabled
      expect(mockFetch).not.toHaveBeenCalled();

      // Cleanup
      Object.defineProperty(navigator, 'doNotTrack', {
        value: null,
        configurable: true,
      });
    });
  });

  // ==============================================================================
  // sendEvents Tests
  // ==============================================================================

  describe('sendEvents', () => {
    it('sends POST request to /api/v1/metrics/events', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ count: 2, received_at: '2024-01-01T00:00:00Z' }),
      });

      const events: FeatureEvent[] = [
        { feature_name: 'dark_mode', event_type: 'used' },
        { feature_name: 'export', event_type: 'clicked' },
      ];

      await sendEvents('test-session', 'studio', events);

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: 'test-session',
          app_name: 'studio',
          events,
        }),
      });
    });

    it('returns count on success', async () => {
      const receipt = { count: 3, received_at: '2024-01-01T00:00:00Z' };
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(receipt),
      });

      const result = await sendEvents('test', 'studio', [
        { feature_name: 'a', event_type: 'used' },
        { feature_name: 'b', event_type: 'used' },
        { feature_name: 'c', event_type: 'used' },
      ]);

      expect(result.count).toBe(3);
    });

    it('supports event metadata', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ count: 1 }),
      });

      const events: FeatureEvent[] = [
        {
          feature_name: 'error',
          event_type: 'error',
          metadata: { error_code: 500, retried: true },
        },
      ];

      await sendEvents('test', 'studio', events);

      const callBody = JSON.parse(mockFetch.mock.calls[0][1].body);
      expect(callBody.events[0].metadata).toEqual({ error_code: 500, retried: true });
    });
  });

  // ==============================================================================
  // getAggregateMetrics Tests
  // ==============================================================================

  describe('getAggregateMetrics', () => {
    it('sends GET request to /api/v1/metrics/heart/aggregate', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ period: '7d', nps_score_avg: 8.5 }),
      });

      await getAggregateMetrics();

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/heart/aggregate', {
        method: 'GET',
      });
    });

    it('includes period parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ period: '30d' }),
      });

      await getAggregateMetrics({ period: '30d' });

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/heart/aggregate?period=30d', {
        method: 'GET',
      });
    });

    it('includes app filter parameter', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ period: '7d', app_name: 'studio' }),
      });

      await getAggregateMetrics({ app: 'studio' });

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/heart/aggregate?app=studio', {
        method: 'GET',
      });
    });

    it('includes both period and app parameters', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ period: '30d', app_name: 'studio' }),
      });

      await getAggregateMetrics({ period: '30d', app: 'studio' });

      expect(mockFetch).toHaveBeenCalledWith(
        '/api/v1/metrics/heart/aggregate?period=30d&app=studio',
        { method: 'GET' }
      );
    });

    it('returns aggregate metrics', async () => {
      const aggregate: AggregateMetrics = {
        period: '7d',
        nps_score_avg: 8.5,
        task_success_rate: 0.85,
        total_tasks_started: 100,
        total_tasks_completed: 85,
        total_tasks_errored: 15,
        avg_session_duration_ms: 180000,
        total_interactions: 500,
        top_features: { code_generation: 50, dark_mode: 30 },
        new_users_count: 10,
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(aggregate),
      });

      const result = await getAggregateMetrics();
      expect(result).toEqual(aggregate);
    });
  });

  // ==============================================================================
  // getDashboard Tests
  // ==============================================================================

  describe('getDashboard', () => {
    it('sends GET request to /api/v1/metrics/dashboard', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ studio: {} }),
      });

      await getDashboard();

      expect(mockFetch).toHaveBeenCalledWith('/api/v1/metrics/dashboard', {
        method: 'GET',
      });
    });

    it('returns dashboard data', async () => {
      const dashboard: DashboardData = {
        studio: { period: '7d', nps_score_avg: 8.5 },
        total_metrics_count: 100,
        total_events_count: 500,
        generated_at: '2024-01-01T00:00:00Z',
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(dashboard),
      });

      const result = await getDashboard();
      expect(result.studio).toBeDefined();
      expect(result.total_metrics_count).toBe(100);
      expect(result.generated_at).toBeDefined();
    });
  });
});

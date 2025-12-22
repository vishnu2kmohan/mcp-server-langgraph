/**
 * Tests for AI Suggestions MSW Handlers
 *
 * TDD Phase: GREEN - Tests for HTTP fallback endpoints when WebSocket unavailable
 *
 * These handlers provide REST API alternatives for AI suggestions:
 * - POST /api/v1/ai/suggestions/request - Request new suggestions
 * - GET /api/v1/ai/suggestions - Poll for current suggestions
 * - POST /api/v1/ai/suggestions/dismiss - Dismiss a suggestion
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { server } from '../server';

import {
  aiSuggestionsHandlers,
  mockSuggestions,
  resetMockSuggestions,
  addMockSuggestion,
  type MockSuggestion,
} from './aiSuggestionsHandlers';

// =============================================================================
// Test Setup
// =============================================================================

beforeEach(() => {
  // Add our handlers to the global server
  server.use(...aiSuggestionsHandlers);
});

afterEach(() => {
  server.resetHandlers();
  resetMockSuggestions();
});

// =============================================================================
// Tests
// =============================================================================

describe('AI Suggestions MSW Handlers', () => {
  describe('GET /api/v1/ai/suggestions', () => {
    it('should return empty array when no suggestions', async () => {
      const response = await fetch('/api/v1/ai/suggestions');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toEqual({
        type: 'suggestions',
        data: [],
        timestamp: expect.any(Number),
      });
    });

    it('should return current suggestions', async () => {
      // Add a suggestion
      addMockSuggestion({
        id: 'test-1',
        type: 'tooltip',
        message: 'Test suggestion',
        priority: 'medium',
      });

      const response = await fetch('/api/v1/ai/suggestions');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.data).toHaveLength(1);
      expect(data.data[0]).toEqual(
        expect.objectContaining({
          id: 'test-1',
          type: 'tooltip',
          message: 'Test suggestion',
          priority: 'medium',
        })
      );
    });

    it('should return multiple suggestions', async () => {
      addMockSuggestion({
        id: 's1',
        type: 'tooltip',
        message: 'Tip 1',
        priority: 'low',
      });
      addMockSuggestion({
        id: 's2',
        type: 'spotlight',
        message: 'Tip 2',
        priority: 'high',
      });
      addMockSuggestion({
        id: 's3',
        type: 'banner',
        message: 'Tip 3',
        priority: 'medium',
      });

      const response = await fetch('/api/v1/ai/suggestions');
      const data = await response.json();

      expect(data.data).toHaveLength(3);
      expect(data.data.map((s: MockSuggestion) => s.id)).toEqual(['s1', 's2', 's3']);
    });
  });

  describe('POST /api/v1/ai/suggestions/request', () => {
    it('should accept context and return suggestions', async () => {
      const response = await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: {
            page: 'chat',
            action: 'typing',
            sessionId: 'test-session',
          },
        }),
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toEqual({
        type: 'suggestions',
        data: expect.any(Array),
        timestamp: expect.any(Number),
      });
    });

    it('should generate context-aware suggestions for chat page', async () => {
      const response = await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: { page: 'chat' },
        }),
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      // Should have at least one suggestion related to chat
      expect(data.data.length).toBeGreaterThanOrEqual(1);
    });

    it('should generate context-aware suggestions for workflows page', async () => {
      const response = await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          context: { page: 'workflows' },
        }),
      });

      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data.data.length).toBeGreaterThanOrEqual(1);
    });

    it('should return 400 for missing context', async () => {
      const response = await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(400);
    });
  });

  describe('POST /api/v1/ai/suggestions/dismiss', () => {
    it('should dismiss a suggestion by ID', async () => {
      // Add a suggestion first
      addMockSuggestion({
        id: 'dismiss-me',
        type: 'tooltip',
        message: 'This will be dismissed',
        priority: 'low',
      });

      // Verify it exists
      let response = await fetch('/api/v1/ai/suggestions');
      let data = await response.json();
      expect(data.data).toHaveLength(1);

      // Dismiss it
      response = await fetch('/api/v1/ai/suggestions/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'dismiss-me' }),
      });

      expect(response.status).toBe(200);

      // Verify it's gone
      response = await fetch('/api/v1/ai/suggestions');
      data = await response.json();
      expect(data.data).toHaveLength(0);
    });

    it('should return 400 for missing suggestion ID', async () => {
      const response = await fetch('/api/v1/ai/suggestions/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(400);
    });

    it('should return 404 for non-existent suggestion', async () => {
      const response = await fetch('/api/v1/ai/suggestions/dismiss', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: 'does-not-exist' }),
      });

      expect(response.status).toBe(404);
    });
  });

  describe('GET /api/v1/ai/suggestions/health', () => {
    it('should return health status', async () => {
      const response = await fetch('/api/v1/ai/suggestions/health');
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toEqual({
        status: 'healthy',
        websocket_available: false,
        fallback_active: true,
        timestamp: expect.any(Number),
      });
    });
  });

  describe('Handler State Management', () => {
    it('should reset suggestions between tests', () => {
      addMockSuggestion({
        id: 'temp',
        type: 'tooltip',
        message: 'Temp',
        priority: 'low',
      });

      expect(mockSuggestions()).toHaveLength(1);

      resetMockSuggestions();

      expect(mockSuggestions()).toHaveLength(0);
    });

    it('should generate unique IDs for context-based suggestions', async () => {
      // Request suggestions twice
      await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: { page: 'chat' } }),
      });

      await fetch('/api/v1/ai/suggestions/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context: { page: 'workflows' } }),
      });

      const response = await fetch('/api/v1/ai/suggestions');
      const data = await response.json();

      // All IDs should be unique
      const ids = data.data.map((s: MockSuggestion) => s.id);
      const uniqueIds = new Set(ids);
      expect(uniqueIds.size).toBe(ids.length);
    });
  });
});

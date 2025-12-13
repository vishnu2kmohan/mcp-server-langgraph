/**
 * RTK Query API Tests
 *
 * TDD tests for the unified API slice.
 * Tests cover:
 * - API configuration
 * - Endpoint definitions
 * - Tag types
 * - Query/mutation configurations
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api } from './index';

// Mock localStorage
const mockLocalStorage = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

describe('RTK Query API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('API Configuration', () => {
    it('should have correct reducer path', () => {
      expect(api.reducerPath).toBe('api');
    });

    it('should export reducer function', () => {
      expect(typeof api.reducer).toBe('function');
    });

    it('should export middleware', () => {
      expect(api.middleware).toBeDefined();
    });

    it('should have util methods', () => {
      expect(api.util).toBeDefined();
      expect(api.util.invalidateTags).toBeDefined();
      expect(api.util.resetApiState).toBeDefined();
    });
  });

  describe('Endpoint Definitions', () => {
    describe('Feature Flags', () => {
      it('should have getFeatureFlags endpoint', () => {
        expect(api.endpoints.getFeatureFlags).toBeDefined();
      });

      it('should be a query endpoint', () => {
        expect(api.endpoints.getFeatureFlags.select).toBeDefined();
      });
    });

    describe('Workflows', () => {
      it('should have listWorkflows endpoint', () => {
        expect(api.endpoints.listWorkflows).toBeDefined();
      });

      it('should have getWorkflow endpoint', () => {
        expect(api.endpoints.getWorkflow).toBeDefined();
      });

      it('should have createWorkflow endpoint', () => {
        expect(api.endpoints.createWorkflow).toBeDefined();
      });

      it('should have updateWorkflow endpoint', () => {
        expect(api.endpoints.updateWorkflow).toBeDefined();
      });

      it('should have deleteWorkflow endpoint', () => {
        expect(api.endpoints.deleteWorkflow).toBeDefined();
      });
    });

    describe('Sessions', () => {
      it('should have listSessions endpoint', () => {
        expect(api.endpoints.listSessions).toBeDefined();
      });

      it('should have getSession endpoint', () => {
        expect(api.endpoints.getSession).toBeDefined();
      });

      it('should have createSession endpoint', () => {
        expect(api.endpoints.createSession).toBeDefined();
      });

      it('should have deleteSession endpoint', () => {
        expect(api.endpoints.deleteSession).toBeDefined();
      });
    });

    describe('Messages', () => {
      it('should have getSessionMessages endpoint', () => {
        expect(api.endpoints.getSessionMessages).toBeDefined();
      });
    });

    describe('Chat', () => {
      it('should have sendChatMessage endpoint', () => {
        expect(api.endpoints.sendChatMessage).toBeDefined();
      });
    });

    describe('Cost', () => {
      it('should have getCostSummary endpoint', () => {
        expect(api.endpoints.getCostSummary).toBeDefined();
      });

      it('should have getCostByModel endpoint', () => {
        expect(api.endpoints.getCostByModel).toBeDefined();
      });
    });

    describe('Observability', () => {
      it('should have listTraces endpoint', () => {
        expect(api.endpoints.listTraces).toBeDefined();
      });

      it('should have getTrace endpoint', () => {
        expect(api.endpoints.getTrace).toBeDefined();
      });
    });
  });

  describe('Hooks Export', () => {
    it('should export useGetFeatureFlagsQuery hook', async () => {
      const { useGetFeatureFlagsQuery } = await import('./index');
      expect(useGetFeatureFlagsQuery).toBeDefined();
    });

    it('should export useListWorkflowsQuery hook', async () => {
      const { useListWorkflowsQuery } = await import('./index');
      expect(useListWorkflowsQuery).toBeDefined();
    });

    it('should export useGetWorkflowQuery hook', async () => {
      const { useGetWorkflowQuery } = await import('./index');
      expect(useGetWorkflowQuery).toBeDefined();
    });

    it('should export useCreateWorkflowMutation hook', async () => {
      const { useCreateWorkflowMutation } = await import('./index');
      expect(useCreateWorkflowMutation).toBeDefined();
    });

    it('should export useUpdateWorkflowMutation hook', async () => {
      const { useUpdateWorkflowMutation } = await import('./index');
      expect(useUpdateWorkflowMutation).toBeDefined();
    });

    it('should export useDeleteWorkflowMutation hook', async () => {
      const { useDeleteWorkflowMutation } = await import('./index');
      expect(useDeleteWorkflowMutation).toBeDefined();
    });

    it('should export useListSessionsQuery hook', async () => {
      const { useListSessionsQuery } = await import('./index');
      expect(useListSessionsQuery).toBeDefined();
    });

    it('should export useGetSessionQuery hook', async () => {
      const { useGetSessionQuery } = await import('./index');
      expect(useGetSessionQuery).toBeDefined();
    });

    it('should export useCreateSessionMutation hook', async () => {
      const { useCreateSessionMutation } = await import('./index');
      expect(useCreateSessionMutation).toBeDefined();
    });

    it('should export useDeleteSessionMutation hook', async () => {
      const { useDeleteSessionMutation } = await import('./index');
      expect(useDeleteSessionMutation).toBeDefined();
    });

    it('should export useGetSessionMessagesQuery hook', async () => {
      const { useGetSessionMessagesQuery } = await import('./index');
      expect(useGetSessionMessagesQuery).toBeDefined();
    });

    it('should export useSendChatMessageMutation hook', async () => {
      const { useSendChatMessageMutation } = await import('./index');
      expect(useSendChatMessageMutation).toBeDefined();
    });

    it('should export useGetCostSummaryQuery hook', async () => {
      const { useGetCostSummaryQuery } = await import('./index');
      expect(useGetCostSummaryQuery).toBeDefined();
    });

    it('should export useGetCostByModelQuery hook', async () => {
      const { useGetCostByModelQuery } = await import('./index');
      expect(useGetCostByModelQuery).toBeDefined();
    });

    it('should export useListTracesQuery hook', async () => {
      const { useListTracesQuery } = await import('./index');
      expect(useListTracesQuery).toBeDefined();
    });

    it('should export useGetTraceQuery hook', async () => {
      const { useGetTraceQuery } = await import('./index');
      expect(useGetTraceQuery).toBeDefined();
    });
  });

  describe('Reducer Integration', () => {
    it('should create valid initial state', () => {
      const initialState = api.reducer(undefined, { type: '@@INIT' });
      expect(initialState).toBeDefined();
      expect(typeof initialState).toBe('object');
    });

    it('should handle unknown actions', () => {
      const state = api.reducer(undefined, { type: 'UNKNOWN_ACTION' });
      expect(state).toBeDefined();
    });
  });

  describe('Endpoint Select Methods', () => {
    it('should have select method for getFeatureFlags', () => {
      const selector = api.endpoints.getFeatureFlags.select();
      expect(typeof selector).toBe('function');
    });

    it('should have select method for listWorkflows', () => {
      const selector = api.endpoints.listWorkflows.select({ limit: 20 });
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getWorkflow', () => {
      const selector = api.endpoints.getWorkflow.select('workflow-1');
      expect(typeof selector).toBe('function');
    });

    it('should have select method for listSessions', () => {
      const selector = api.endpoints.listSessions.select({ limit: 20 });
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getSession', () => {
      const selector = api.endpoints.getSession.select('session-1');
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getSessionMessages', () => {
      const selector = api.endpoints.getSessionMessages.select('session-1');
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getCostSummary', () => {
      const selector = api.endpoints.getCostSummary.select({ period: '30d' });
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getCostByModel', () => {
      const selector = api.endpoints.getCostByModel.select({ period: '30d' });
      expect(typeof selector).toBe('function');
    });

    it('should have select method for listTraces', () => {
      const selector = api.endpoints.listTraces.select({ limit: 50 });
      expect(typeof selector).toBe('function');
    });

    it('should have select method for getTrace', () => {
      const selector = api.endpoints.getTrace.select('trace-1');
      expect(typeof selector).toBe('function');
    });
  });

  describe('Mutation Endpoints', () => {
    it('createWorkflow should be a mutation', () => {
      expect(api.endpoints.createWorkflow.initiate).toBeDefined();
    });

    it('updateWorkflow should be a mutation', () => {
      expect(api.endpoints.updateWorkflow.initiate).toBeDefined();
    });

    it('deleteWorkflow should be a mutation', () => {
      expect(api.endpoints.deleteWorkflow.initiate).toBeDefined();
    });

    it('createSession should be a mutation', () => {
      expect(api.endpoints.createSession.initiate).toBeDefined();
    });

    it('deleteSession should be a mutation', () => {
      expect(api.endpoints.deleteSession.initiate).toBeDefined();
    });

    it('sendChatMessage should be a mutation', () => {
      expect(api.endpoints.sendChatMessage.initiate).toBeDefined();
    });
  });

  describe('Query Endpoints', () => {
    it('getFeatureFlags should be a query', () => {
      expect(api.endpoints.getFeatureFlags.initiate).toBeDefined();
      expect(api.endpoints.getFeatureFlags.select).toBeDefined();
    });

    it('listWorkflows should be a query', () => {
      expect(api.endpoints.listWorkflows.initiate).toBeDefined();
      expect(api.endpoints.listWorkflows.select).toBeDefined();
    });

    it('getWorkflow should be a query', () => {
      expect(api.endpoints.getWorkflow.initiate).toBeDefined();
      expect(api.endpoints.getWorkflow.select).toBeDefined();
    });

    it('listSessions should be a query', () => {
      expect(api.endpoints.listSessions.initiate).toBeDefined();
      expect(api.endpoints.listSessions.select).toBeDefined();
    });

    it('getSession should be a query', () => {
      expect(api.endpoints.getSession.initiate).toBeDefined();
      expect(api.endpoints.getSession.select).toBeDefined();
    });

    it('getSessionMessages should be a query', () => {
      expect(api.endpoints.getSessionMessages.initiate).toBeDefined();
      expect(api.endpoints.getSessionMessages.select).toBeDefined();
    });

    it('getCostSummary should be a query', () => {
      expect(api.endpoints.getCostSummary.initiate).toBeDefined();
      expect(api.endpoints.getCostSummary.select).toBeDefined();
    });

    it('getCostByModel should be a query', () => {
      expect(api.endpoints.getCostByModel.initiate).toBeDefined();
      expect(api.endpoints.getCostByModel.select).toBeDefined();
    });

    it('listTraces should be a query', () => {
      expect(api.endpoints.listTraces.initiate).toBeDefined();
      expect(api.endpoints.listTraces.select).toBeDefined();
    });

    it('getTrace should be a query', () => {
      expect(api.endpoints.getTrace.initiate).toBeDefined();
      expect(api.endpoints.getTrace.select).toBeDefined();
    });
  });
});

/**
 * MSW Server for Tests
 *
 * Sets up the MSW server for Node.js test environments.
 * This is the primary entry point for MSW in unit/integration tests.
 *
 * Usage in tests:
 *   import { server } from './mocks/server';
 *
 *   beforeAll(() => server.listen());
 *   afterEach(() => server.resetHandlers());
 *   afterAll(() => server.close());
 *
 * To override handlers for specific tests:
 *   server.use(
 *     http.get('/api/v1/health', () =>
 *       HttpResponse.json({ status: 'unhealthy' })
 *     )
 *   );
 */

import { setupServer } from "msw/node";
import { handlers } from "./handlers";

// Create the server with default handlers
export const server = setupServer(...handlers);

// Re-export handlers for convenience
export { handlers };

// Re-export error handler factories for test customization
export {
  createUnauthorizedHandler,
  createServerErrorHandler,
  createNetworkErrorHandler,
  createDelayedHandler,
  createMockWorkflow,
  createMockSession,
  createMockConnection,
  createMockCostSummary,
  createMockModelCost,
  mockWorkflows,
  mockSessions,
  mockConnections,
  mockModelCosts,
  mockCostHistory,
  mockHealthStatus,
  mockFeatureFlags,
} from "./handlers";

/**
 * Router Configuration Tests
 *
 * TDD tests for the studio router configuration.
 * Tests cover:
 * - Router structure and configuration
 * - Route paths
 * - Lazy loading
 * - Redirects
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { RouteObject } from 'react-router-dom';
import { router } from './index';

// Mock all lazy-loaded pages to avoid import issues
vi.mock('../pages/WorkflowsPage', () => ({
  WorkflowsPage: () => <div data-testid="workflows-page">Workflows Page</div>,
}));
vi.mock('../pages/ChatPage', () => ({
  ChatPage: () => <div data-testid="chat-page">Chat Page</div>,
}));
vi.mock('../pages/SessionsPage', () => ({
  SessionsPage: () => <div data-testid="sessions-page">Sessions Page</div>,
}));
vi.mock('../pages/MCPPage', () => ({
  MCPPage: () => <div data-testid="mcp-page">MCP Page</div>,
}));
vi.mock('../pages/ObservabilityPage', () => ({
  ObservabilityPage: () => <div data-testid="observability-page">Observability Page</div>,
}));
vi.mock('../pages/SettingsPage', () => ({
  SettingsPage: () => <div data-testid="settings-page">Settings Page</div>,
}));
vi.mock('../pages/AdminDashboardPage', () => ({
  AdminDashboardPage: () => <div data-testid="admin-dashboard-page">Admin Dashboard Page</div>,
}));

// Mock the App component
vi.mock('../App', () => ({
  App: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="app">{children}</div>
  ),
}));

describe('Router', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Router Configuration', () => {
    it('should export a router object', () => {
      expect(router).toBeDefined();
      expect(router.routes).toBeDefined();
    });

    it('should have routes array', () => {
      expect(Array.isArray(router.routes)).toBe(true);
      expect(router.routes.length).toBeGreaterThan(0);
    });
  });

  describe('Route Structure', () => {
    it('should have root path configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      expect(rootRoute).toBeDefined();
    });

    it('should have children routes under root', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      expect(rootRoute?.children).toBeDefined();
      expect(Array.isArray(rootRoute?.children)).toBe(true);
    });

    it('should have studio routes configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      expect(studioRoute).toBeDefined();
    });

    it('should have admin routes configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const adminRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'admin');
      expect(adminRoute).toBeDefined();
    });
  });

  describe('Studio Routes', () => {
    it('should have workflows route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const workflowsRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'workflows');
      expect(workflowsRoute).toBeDefined();
    });

    it('should have chat route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const chatRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'chat');
      expect(chatRoute).toBeDefined();
    });

    it('should have sessions route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const sessionsRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'sessions');
      expect(sessionsRoute).toBeDefined();
    });

    it('should have mcp route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const mcpRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'mcp');
      expect(mcpRoute).toBeDefined();
    });

    it('should have observability route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const observabilityRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'observability');
      expect(observabilityRoute).toBeDefined();
    });

    it('should have settings route under studio', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const settingsRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'settings');
      expect(settingsRoute).toBeDefined();
    });
  });

  describe('Admin Routes', () => {
    it('should have dashboard route under admin', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const adminRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'admin');
      const dashboardRoute = adminRoute?.children?.find((r: RouteObject) => r.path === 'dashboard');
      expect(dashboardRoute).toBeDefined();
    });
  });

  describe('Legacy Redirects', () => {
    it('should have build redirect configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const buildRedirect = rootRoute?.children?.find((r: RouteObject) => r.path === 'build');
      expect(buildRedirect).toBeDefined();
    });

    it('should have build/* redirect configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const buildWildcardRedirect = rootRoute?.children?.find((r: RouteObject) => r.path === 'build/*');
      expect(buildWildcardRedirect).toBeDefined();
    });

    it('should have chat legacy redirect configured', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const chatRedirect = rootRoute?.children?.find((r: RouteObject) => r.path === 'chat');
      expect(chatRedirect).toBeDefined();
    });
  });

  describe('Lazy Loading', () => {
    it('should have lazy function for workflows route', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const workflowsRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'workflows');
      expect(workflowsRoute?.lazy).toBeDefined();
      expect(typeof workflowsRoute?.lazy).toBe('function');
    });

    it('should have lazy function for chat route', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      const chatRoute = studioRoute?.children?.find((r: RouteObject) => r.path === 'chat');
      expect(chatRoute?.lazy).toBeDefined();
      expect(typeof chatRoute?.lazy).toBe('function');
    });

    it('should have lazy function for admin dashboard route', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const adminRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'admin');
      const dashboardRoute = adminRoute?.children?.find((r: RouteObject) => r.path === 'dashboard');
      expect(dashboardRoute?.lazy).toBeDefined();
      expect(typeof dashboardRoute?.lazy).toBe('function');
    });
  });

  describe('Route Count', () => {
    it('should have expected number of studio child routes', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const studioRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'studio');
      // index + workflows + chat + sessions + mcp + observability + settings + cost = 8
      expect(studioRoute?.children?.length).toBe(8);
    });

    it('should have expected number of admin child routes', () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === '/');
      const adminRoute = rootRoute?.children?.find((r: RouteObject) => r.path === 'admin');
      // index + dashboard = 2
      expect(adminRoute?.children?.length).toBe(2);
    });
  });
});

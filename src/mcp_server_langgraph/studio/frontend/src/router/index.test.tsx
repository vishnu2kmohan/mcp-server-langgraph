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

import { describe, it, expect, vi, beforeEach } from "vitest";
import { RouteObject } from "react-router";
import { router } from "./index";

// Mock all lazy-loaded pages to avoid import issues
vi.mock("../pages/ProjectsPage", () => ({
  ProjectsPage: () => <div data-testid="projects-page">Projects Page</div>,
}));
vi.mock("../pages/ProjectDetailPage", () => ({
  ProjectDetailPage: () => (
    <div data-testid="project-detail-page">Project Detail Page</div>
  ),
}));
vi.mock("../pages/WorkflowsPage", () => ({
  WorkflowsPage: () => <div data-testid="workflows-page">Workflows Page</div>,
}));
vi.mock("../pages/ChatPage", () => ({
  ChatPage: () => <div data-testid="chat-page">Chat Page</div>,
}));
// SessionsPage removed - now redirects to ChatPage
vi.mock("../pages/MCPPage", () => ({
  MCPPage: () => <div data-testid="mcp-page">MCP Page</div>,
}));
vi.mock("../pages/AgentsPage", () => ({
  AgentsPage: () => <div data-testid="agents-page">Agents Page</div>,
}));
vi.mock("../pages/VectorsPage", () => ({
  VectorsPage: () => <div data-testid="vectors-page">Vectors Page</div>,
}));
vi.mock("../pages/ObservabilityPage", () => ({
  ObservabilityPage: () => (
    <div data-testid="observability-page">Observability Page</div>
  ),
}));
vi.mock("../pages/SettingsPage", () => ({
  SettingsPage: () => <div data-testid="settings-page">Settings Page</div>,
}));
vi.mock("../pages/CostPage", () => ({
  CostPage: () => <div data-testid="cost-page">Cost Page</div>,
}));
vi.mock("../pages/AdminDashboardPage", () => ({
  AdminDashboardPage: () => (
    <div data-testid="admin-dashboard-page">Admin Dashboard Page</div>
  ),
}));
vi.mock("../pages/AuditLogPage", () => ({
  AuditLogPage: () => <div data-testid="audit-log-page">Audit Log Page</div>,
}));

// Mock the App component
vi.mock("../App", () => ({
  App: ({ children }: { children?: React.ReactNode }) => (
    <div data-testid="app">{children}</div>
  ),
}));

describe("Router", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Router Configuration", () => {
    it("should export a router object", () => {
      expect(router).toBeDefined();
      expect(router.routes).toBeDefined();
    });

    it("should have routes array", () => {
      expect(Array.isArray(router.routes)).toBe(true);
      expect(router.routes.length).toBeGreaterThan(0);
    });
  });

  describe("Route Structure", () => {
    it("should have root path configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      expect(rootRoute).toBeDefined();
    });

    it("should have children routes under root", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      expect(rootRoute?.children).toBeDefined();
      expect(Array.isArray(rootRoute?.children)).toBe(true);
    });

    it("should have studio routes configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      expect(studioRoute).toBeDefined();
    });

    it("should have admin routes configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const adminRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      expect(adminRoute).toBeDefined();
    });
  });

  describe("Studio Routes", () => {
    it("should have workflows route under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const workflowsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "workflows",
      );
      expect(workflowsRoute).toBeDefined();
    });

    it("should have chat route under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const chatRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "chat",
      );
      expect(chatRoute).toBeDefined();
    });

    it("should have sessions redirect to chat under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const sessionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "sessions",
      );
      expect(sessionsRoute).toBeDefined();
      // Sessions now redirects to chat (has element, not lazy)
      expect(sessionsRoute?.element).toBeDefined();
      expect(sessionsRoute?.lazy).toBeUndefined();
    });

    it("should have mcp route under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const mcpRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "mcp",
      );
      expect(mcpRoute).toBeDefined();
    });

    it("should have observability route under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const observabilityRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "observability",
      );
      expect(observabilityRoute).toBeDefined();
    });

    it("should have settings route under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const settingsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "settings",
      );
      expect(settingsRoute).toBeDefined();
    });
  });

  describe("Admin Routes", () => {
    it("should have dashboard route under admin", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      const dashboardRoute = adminRoute?.children?.find(
        (r: RouteObject) => r.path === "dashboard",
      );
      expect(dashboardRoute).toBeDefined();
    });
  });

  describe("Legacy Redirects", () => {
    it("should have build redirect configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const buildRedirect = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "build",
      );
      expect(buildRedirect).toBeDefined();
    });

    it("should have build/* redirect configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const buildWildcardRedirect = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "build/*",
      );
      expect(buildWildcardRedirect).toBeDefined();
    });

    it("should have chat legacy redirect configured", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const chatRedirect = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "chat",
      );
      expect(chatRedirect).toBeDefined();
    });
  });

  describe("Lazy Loading", () => {
    it("should have lazy function for workflows route (via child)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const workflowsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "workflows",
      );
      // Workflows route has children with lazy loading (unified workflows paradigm)
      expect(workflowsRoute?.children).toBeDefined();
      const indexRoute = workflowsRoute?.children?.find(
        (r: RouteObject) => r.index,
      );
      expect(indexRoute?.lazy).toBeDefined();
      expect(typeof indexRoute?.lazy).toBe("function");
    });

    it("should have lazy function for chat route", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const chatRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "chat",
      );
      expect(chatRoute?.lazy).toBeDefined();
      expect(typeof chatRoute?.lazy).toBe("function");
    });

    it("should have lazy function for admin dashboard route", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      const dashboardRoute = adminRoute?.children?.find(
        (r: RouteObject) => r.path === "dashboard",
      );
      expect(dashboardRoute?.lazy).toBeDefined();
      expect(typeof dashboardRoute?.lazy).toBe("function");
    });
  });

  describe("Route Count", () => {
    it("should have expected number of studio child routes", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      // index + projects + projects/:projectId + workflows + shared-workflows + chat + sessions + mcp + connections + observability + settings + cost + admin = 13
      expect(studioRoute?.children?.length).toBe(13);
    });

    it("should have expected number of admin child routes", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      // index + dashboard + audit-logs = 3
      expect(adminRoute?.children?.length).toBe(3);
    });
  });

  describe("Lazy Loading Execution", () => {
    it("should load projects page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const projectsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "projects",
      );
      expect(projectsRoute?.lazy).toBeDefined();

      if (projectsRoute?.lazy) {
        const result = await projectsRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load project detail page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const projectDetailRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "projects/:projectId",
      );
      expect(projectDetailRoute?.lazy).toBeDefined();

      if (projectDetailRoute?.lazy) {
        const result = await projectDetailRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load workflows page via lazy function (via child)", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const workflowsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "workflows",
      );
      // Workflows now has PersonaGuard element with lazy child
      const indexRoute = workflowsRoute?.children?.find(
        (r: RouteObject) => r.index,
      );
      expect(indexRoute?.lazy).toBeDefined();

      if (indexRoute?.lazy) {
        const result = await indexRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load chat page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const chatRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "chat",
      );
      expect(chatRoute?.lazy).toBeDefined();

      if (chatRoute?.lazy) {
        const result = await chatRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load MCP page via lazy function (via child)", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const mcpRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "mcp",
      );
      // MCP now has PersonaGuard element with lazy child
      const indexRoute = mcpRoute?.children?.find((r: RouteObject) => r.index);
      expect(indexRoute?.lazy).toBeDefined();

      if (indexRoute?.lazy) {
        const result = await indexRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load observability page via lazy function (via child)", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const observabilityRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "observability",
      );
      // Observability now has PersonaGuard element with lazy child
      const indexRoute = observabilityRoute?.children?.find(
        (r: RouteObject) => r.index,
      );
      expect(indexRoute?.lazy).toBeDefined();

      if (indexRoute?.lazy) {
        const result = await indexRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load settings page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const settingsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "settings",
      );
      expect(settingsRoute?.lazy).toBeDefined();

      if (settingsRoute?.lazy) {
        const result = await settingsRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load cost page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const costRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "cost",
      );
      expect(costRoute?.lazy).toBeDefined();

      if (costRoute?.lazy) {
        const result = await costRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load admin dashboard via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      const dashboardRoute = adminRoute?.children?.find(
        (r: RouteObject) => r.path === "dashboard",
      );
      expect(dashboardRoute?.lazy).toBeDefined();

      if (dashboardRoute?.lazy) {
        const result = await dashboardRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load audit log page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );
      const auditRoute = adminRoute?.children?.find(
        (r: RouteObject) => r.path === "audit-logs",
      );
      expect(auditRoute?.lazy).toBeDefined();

      if (auditRoute?.lazy) {
        const result = await auditRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });
  });

  describe("PersonaGuard Protection", () => {
    it("should have PersonaGuard on admin routes", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const adminRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "admin",
      );

      // Admin route should have element (PersonaGuard wrapper) not lazy
      expect(adminRoute?.element).toBeDefined();
      expect(adminRoute?.children).toBeDefined();
    });

    // Routes accessible to all personas (no PersonaGuard needed)
    it("should NOT have PersonaGuard on projects route (all personas)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const projectsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "projects",
      );

      // Projects route should have lazy (no guard needed)
      expect(projectsRoute?.lazy).toBeDefined();
      expect(projectsRoute?.element).toBeUndefined();
    });

    it("should NOT have PersonaGuard on chat route (all personas)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const chatRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "chat",
      );

      // Chat route should have lazy (no guard needed)
      expect(chatRoute?.lazy).toBeDefined();
      expect(chatRoute?.element).toBeUndefined();
    });

    it("should redirect shared-workflows to workflows (legacy redirect)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const sharedWorkflowsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "shared-workflows",
      );

      // Shared workflows is a redirect to unified workflows page
      expect(sharedWorkflowsRoute?.element).toBeDefined();
    });

    it("should NOT have PersonaGuard on cost route (all personas)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const costRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "cost",
      );

      // Cost route should have lazy (no guard needed)
      expect(costRoute?.lazy).toBeDefined();
      expect(costRoute?.element).toBeUndefined();
    });

    it("should NOT have PersonaGuard on settings route (all personas)", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const settingsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "settings",
      );

      // Settings route should have lazy (no guard needed)
      expect(settingsRoute?.lazy).toBeDefined();
      expect(settingsRoute?.element).toBeUndefined();
    });
  });

  describe("Connections Routes", () => {
    it("should have connections section under studio", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      expect(connectionsRoute).toBeDefined();
      expect(connectionsRoute?.children).toBeDefined();
    });

    it("should have mcp route under connections", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      const mcpRoute = connectionsRoute?.children?.find(
        (r: RouteObject) => r.path === "mcp",
      );
      expect(mcpRoute).toBeDefined();
      expect(mcpRoute?.lazy).toBeDefined();
    });

    it("should have agents route under connections", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      const agentsRoute = connectionsRoute?.children?.find(
        (r: RouteObject) => r.path === "agents",
      );
      expect(agentsRoute).toBeDefined();
      expect(agentsRoute?.lazy).toBeDefined();
    });

    it("should have vectors route under connections", () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      const vectorsRoute = connectionsRoute?.children?.find(
        (r: RouteObject) => r.path === "vectors",
      );
      expect(vectorsRoute).toBeDefined();
      expect(vectorsRoute?.lazy).toBeDefined();
    });

    it("should load agents page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      const agentsRoute = connectionsRoute?.children?.find(
        (r: RouteObject) => r.path === "agents",
      );

      if (agentsRoute?.lazy) {
        const result = await agentsRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });

    it("should load vectors page via lazy function", async () => {
      const rootRoute = router.routes.find((r: RouteObject) => r.path === "/");
      const studioRoute = rootRoute?.children?.find(
        (r: RouteObject) => r.path === "studio",
      );
      const connectionsRoute = studioRoute?.children?.find(
        (r: RouteObject) => r.path === "connections",
      );
      const vectorsRoute = connectionsRoute?.children?.find(
        (r: RouteObject) => r.path === "vectors",
      );

      if (vectorsRoute?.lazy) {
        const result = await vectorsRoute.lazy();
        expect(result).toHaveProperty("Component");
      }
    });
  });
});

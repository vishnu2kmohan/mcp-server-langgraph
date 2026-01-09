/* eslint-disable react-refresh/only-export-components */
import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { App } from "../App";
import { AuthGuard } from "./guards/AuthGuard";
import { PersonaGuard } from "./guards/PersonaGuard";
import { PermissionGuard } from "./guards/PermissionGuard";
import { RootRedirect } from "./guards/RootRedirect";
import { StudioShellGuard } from "./guards/StudioShellGuard";
import {
  chatLoader,
  sessionsLoader,
  complianceLoader,
  artifactsLoader,
} from "./loaders";

/**
 * Studio Router Configuration
 *
 * Routes:
 * - /studio/* - Main studio application (authenticated)
 * - /admin/* - Admin portal (admin role required)
 * - / - Redirect to /studio
 * - /build, /chat - Legacy redirects
 *
 * All page components are lazy-loaded for optimal bundle splitting.
 *
 * Note: This is a CSR (Client-Side Rendered) app, not SSR.
 * We provide a HydrateFallback to handle the initial loading state.
 */

/**
 * Loading fallback component shown during route transitions and initial load.
 * Uses the same styling as StudioShellGuard's ShellSkeleton for consistency.
 */
function RouterFallback() {
  return (
    <div
      data-testid="router-loading"
      className="flex flex-col h-screen bg-white dark:bg-gray-900 animate-pulse"
    >
      {/* TopBar skeleton */}
      <div className="h-12 bg-gray-100 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700" />
      {/* Main content skeleton */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-64 bg-gray-50 dark:bg-gray-850 border-r border-gray-200 dark:border-gray-700">
          <div className="p-4 space-y-3">
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4" />
            <div className="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2" />
          </div>
        </div>
        <div className="flex-1 bg-white dark:bg-gray-900" />
      </div>
      {/* StatusBar skeleton */}
      <div className="h-6 bg-gray-100 dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700" />
    </div>
  );
}

export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <App />,
      hydrateFallbackElement: <RouterFallback />,
      children: [
        // Root redirect - uses feature flag to choose StudioShell or legacy
        { index: true, element: <RootRedirect /> },

        // Studio routes (lazy-loaded, authentication required)
        // Uses StudioShellGuard which renders StudioShellLayout
        {
          id: "studio",
          path: "studio",
          element: (
            <AuthGuard>
              <StudioShellGuard />
            </AuthGuard>
          ),
          // Load sessions for SessionNav on shell mount
          loader: sessionsLoader,
          children: [
            // Default redirect to chat (StudioShell default)
            { index: true, element: <Navigate to="chat" replace /> },
            {
              path: "projects",
              handle: { breadcrumb: "Projects" },
              lazy: async () => {
                const { ProjectsPage } = await import("../pages/ProjectsPage");
                return { Component: ProjectsPage };
              },
            },
            {
              path: "projects/:projectId",
              handle: {
                breadcrumb: (params: { projectId: string }) =>
                  `Project: ${params.projectId.slice(0, 8)}`,
              },
              lazy: async () => {
                const { ProjectDetailPage } =
                  await import("../pages/ProjectDetailPage");
                return { Component: ProjectDetailPage };
              },
            },
            // Workflows - unified view (all personas can access)
            // Shows owned workflows (editable) + shared workflows (read-only)
            {
              path: "workflows",
              handle: { breadcrumb: "Workflows" },
              // Explicit Outlet element ensures React Router properly renders children
              element: <Outlet />,
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { WorkflowsPage } =
                      await import("../pages/WorkflowsPage");
                    return { Component: WorkflowsPage };
                  },
                },
                // Workflow builder/canvas - admin/developer only
                {
                  path: "builder",
                  handle: { breadcrumb: "Builder" },
                  element: (
                    <PersonaGuard allowedPersonas={["admin", "developer"]}>
                      <Outlet />
                    </PersonaGuard>
                  ),
                  children: [
                    {
                      index: true,
                      lazy: async () => {
                        const { WorkflowsPage } =
                          await import("../pages/WorkflowsPage");
                        return { Component: WorkflowsPage };
                      },
                    },
                  ],
                },
                // View individual workflow (readonly for users, editable for admin/dev)
                {
                  path: ":workflowId",
                  handle: {
                    breadcrumb: (params: { workflowId: string }) =>
                      `Workflow: ${params.workflowId.slice(0, 8)}`,
                  },
                  lazy: async () => {
                    const { WorkflowsPage } =
                      await import("../pages/WorkflowsPage");
                    return { Component: WorkflowsPage };
                  },
                },
              ],
            },
            // Legacy redirect: shared-workflows -> workflows
            {
              path: "shared-workflows",
              element: <Navigate to="/studio/workflows" replace />,
            },
            // Chat routes - Empty element (StudioShellLayout provides the 3-panel UI)
            // StudioShellLayout detects chat routes via isChatRoute and renders
            // SessionNav + ConversationPanel + CanvasPanel directly.
            // We use an empty fragment to satisfy React Router's leaf route requirement.
            // ChatPage is DEPRECATED - its UI is now in StudioShellLayout panels.
            {
              path: "chat",
              children: [
                {
                  index: true,
                  id: "chat-index",
                  loader: chatLoader,
                  // Empty fragment - StudioShellLayout renders the chat UI
                  element: <></>,
                },
                {
                  id: "chat-session",
                  path: ":sessionId",
                  loader: chatLoader,
                  // Empty fragment - StudioShellLayout renders the chat UI
                  element: <></>,
                },
              ],
            },
            // Sessions merged into ChatPage - redirect for backward compatibility
            {
              path: "sessions",
              element: <Navigate to="/studio/chat" replace />,
            },
            // MCP - admin/developer only
            {
              path: "mcp",
              handle: { breadcrumb: "MCP" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { MCPPage } = await import("../pages/MCPPage");
                    return { Component: MCPPage };
                  },
                },
              ],
            },
            // Connections section - admin/developer only
            {
              path: "connections",
              handle: { breadcrumb: "Connections" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ConnectionsPage } =
                      await import("../pages/ConnectionsPage");
                    return { Component: ConnectionsPage };
                  },
                },
                {
                  path: "mcp",
                  handle: { breadcrumb: "MCP" },
                  lazy: async () => {
                    const { MCPPage } = await import("../pages/MCPPage");
                    return { Component: MCPPage };
                  },
                },
                {
                  path: "agents",
                  handle: { breadcrumb: "Agents" },
                  lazy: async () => {
                    const { AgentsPage } = await import("../pages/AgentsPage");
                    return { Component: AgentsPage };
                  },
                },
                {
                  path: "vectors",
                  handle: { breadcrumb: "Vectors" },
                  lazy: async () => {
                    const { VectorsPage } =
                      await import("../pages/VectorsPage");
                    return { Component: VectorsPage };
                  },
                },
              ],
            },
            // Observability - admin/developer only
            // Supports tabs: /traces, /logs, /metrics, /alerts
            {
              path: "observability",
              handle: { breadcrumb: "Observability" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "traces",
                  handle: { breadcrumb: "Traces" },
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "logs",
                  handle: { breadcrumb: "Logs" },
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "metrics",
                  handle: { breadcrumb: "Metrics" },
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "alerts",
                  handle: { breadcrumb: "Alerts" },
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
              ],
            },
            // Agents - standalone route (ActivityBar points here)
            // Renders AgentsPage directly - admin/developer only
            {
              path: "agents",
              handle: { breadcrumb: "Agents" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { AgentsPage } = await import("../pages/AgentsPage");
                    return { Component: AgentsPage };
                  },
                },
              ],
            },
            // Traces - redirect to observability (consolidated in Sprint 7)
            {
              path: "traces",
              element: <Navigate to="/studio/observability/traces" replace />,
            },
            // Vectors - standalone route (ActivityBar points here)
            // Renders VectorsPage directly - admin/developer only
            {
              path: "vectors",
              handle: { breadcrumb: "Vectors" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { VectorsPage } =
                      await import("../pages/VectorsPage");
                    return { Component: VectorsPage };
                  },
                },
              ],
            },
            // Logs - standalone route (parity with /studio/traces)
            // Renders ObservabilityPage with logs tab - admin/developer only
            {
              path: "logs",
              handle: { breadcrumb: "Logs" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
              ],
            },
            // Metrics - standalone route (parity with /studio/traces)
            // Renders ObservabilityPage with metrics tab - admin/developer only
            {
              path: "metrics",
              handle: { breadcrumb: "Metrics" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
              ],
            },
            // Alerts - standalone route (parity with /studio/traces)
            // Renders ObservabilityPage with alerts tab - admin/developer only
            {
              path: "alerts",
              handle: { breadcrumb: "Alerts" },
              element: (
                <PersonaGuard allowedPersonas={["admin", "developer"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
              ],
            },
            {
              path: "settings",
              handle: { breadcrumb: "Settings" },
              lazy: async () => {
                const { SettingsPage } = await import("../pages/SettingsPage");
                return { Component: SettingsPage };
              },
            },
            {
              path: "cost",
              handle: { breadcrumb: "Cost" },
              lazy: async () => {
                const { CostPage } = await import("../pages/CostPage");
                return { Component: CostPage };
              },
            },
            // Artifacts - artifact browser for session artifacts and uploaded files
            {
              id: "artifacts",
              path: "artifacts",
              handle: { breadcrumb: "Artifacts" },
              loader: artifactsLoader,
              lazy: async () => {
                const { ArtifactsPage } =
                  await import("../pages/ArtifactsPage");
                return { Component: ArtifactsPage };
              },
            },
            // Compliance - requires compliance:read permission
            {
              path: "compliance",
              handle: { breadcrumb: "Compliance" },
              element: (
                <PermissionGuard
                  requiredPermissions={["compliance:read"]}
                  fallbackPath="/studio/chat"
                >
                  <Outlet />
                </PermissionGuard>
              ),
              children: [
                {
                  index: true,
                  id: "compliance-dashboard",
                  loader: complianceLoader,
                  lazy: async () => {
                    const { ConnectedComplianceDashboard } =
                      await import("../compliance/ConnectedComplianceDashboard");
                    return { Component: ConnectedComplianceDashboard };
                  },
                },
              ],
            },
            // Audit - requires audit:read permission
            {
              path: "audit",
              handle: { breadcrumb: "Audit" },
              element: (
                <PermissionGuard
                  requiredPermissions={["audit:read"]}
                  fallbackPath="/studio/chat"
                >
                  <Outlet />
                </PermissionGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { AuditLogPage } =
                      await import("../pages/AuditLogPage");
                    return { Component: AuditLogPage };
                  },
                },
              ],
            },
            // Analytics - HEART metrics dashboard (admin only)
            {
              path: "analytics",
              handle: { breadcrumb: "Analytics" },
              element: (
                <PermissionGuard
                  requiredPermissions={["admin:access"]}
                  fallbackPath="/studio/chat"
                >
                  <Outlet />
                </PermissionGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { AnalyticsDashboardPage } =
                      await import("../pages/AnalyticsDashboardPage");
                    return { Component: AnalyticsDashboardPage };
                  },
                },
              ],
            },
            // Help - full help center
            {
              path: "help",
              handle: { breadcrumb: "Help" },
              lazy: async () => {
                const { HelpPage } = await import("../pages/HelpPage");
                return { Component: HelpPage };
              },
            },
            // Skills Marketplace - admin only (install/uninstall capabilities)
            {
              path: "skills",
              handle: { breadcrumb: "Skills" },
              element: (
                <PersonaGuard allowedPersonas={["admin"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { SkillsPage } = await import("../pages/SkillsPage");
                    return { Component: SkillsPage };
                  },
                },
              ],
            },
            // Admin routes nested under /studio/admin (lazy-loaded with PersonaGuard)
            {
              path: "admin",
              handle: { breadcrumb: "Admin" },
              element: (
                <PersonaGuard allowedPersonas={["admin"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                { index: true, element: <Navigate to="dashboard" replace /> },
                {
                  path: "dashboard",
                  handle: { breadcrumb: "Dashboard" },
                  lazy: async () => {
                    const { AdminDashboardPage } =
                      await import("../pages/AdminDashboardPage");
                    return { Component: AdminDashboardPage };
                  },
                },
                {
                  path: "audit-logs",
                  handle: { breadcrumb: "Audit Logs" },
                  lazy: async () => {
                    const { AuditLogPage } =
                      await import("../pages/AuditLogPage");
                    return { Component: AuditLogPage };
                  },
                },
              ],
            },
          ],
        },

        // Legacy admin redirect (for backward compatibility)
        {
          path: "admin",
          element: <Navigate to="/studio/admin" replace />,
        },
        {
          path: "admin/*",
          element: <Navigate to="/studio/admin" replace />,
        },

        // Native Login route (no Keycloak UI redirect)
        // Uses eager error handling to prevent chunk load failures during logout race conditions
        {
          path: "login",
          lazy: async () => {
            try {
              const { LoginPage } = await import("../pages/LoginPage");
              return { Component: LoginPage };
            } catch (error) {
              // Handle chunk load failure gracefully (e.g., during logout redirect race)
              // This can happen when:
              // 1. A full-page redirect cancels the chunk request
              // 2. The chunk is missing after a deployment (hash mismatch)
              console.warn("Failed to load LoginPage chunk:", error);
              // Return a simple fallback that doesn't require any additional chunks
              return {
                Component: () => {
                  // If we're here due to a cancelled request, the page is likely
                  // navigating away anyway. Try to reload if we're still here.
                  if (typeof window !== "undefined") {
                    window.location.reload();
                  }
                  return null;
                },
              };
            }
          },
        },

        // OAuth2 callback route (outside studio for direct OAuth redirect handling)
        {
          path: "oauth2/callback",
          lazy: async () => {
            const { OAuth2CallbackPage } =
              await import("../pages/OAuth2CallbackPage");
            return { Component: OAuth2CallbackPage };
          },
        },

        // OAuth2 Authorization Code + PKCE callback (ADR-0071)
        // Receives tokens in URL fragment from /api/v1/auth/callback redirect
        {
          path: "auth/callback",
          lazy: async () => {
            const { AuthCallbackPage } =
              await import("../pages/AuthCallbackPage");
            return { Component: AuthCallbackPage };
          },
        },

        // Legacy redirects (301 permanent)
        { path: "build", element: <Navigate to="/studio/workflows" replace /> },
        {
          path: "build/*",
          element: <Navigate to="/studio/workflows" replace />,
        },
        { path: "chat", element: <Navigate to="/studio/chat" replace /> },
      ],
    },
  ],
  {
    basename: "/",
    // Note: v7_startTransition and v7_relativeSplatPath are now default in React Router v7
    // CSR-only apps don't need hydration settings - remove to use React Router v7 defaults
  },
);

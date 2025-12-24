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
  filesLoader,
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
              lazy: async () => {
                const { ProjectsPage } = await import("../pages/ProjectsPage");
                return { Component: ProjectsPage };
              },
            },
            {
              path: "projects/:projectId",
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
                  lazy: async () => {
                    const { MCPPage } = await import("../pages/MCPPage");
                    return { Component: MCPPage };
                  },
                },
                {
                  path: "agents",
                  lazy: async () => {
                    const { AgentsPage } = await import("../pages/AgentsPage");
                    return { Component: AgentsPage };
                  },
                },
                {
                  path: "vectors",
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
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "logs",
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "metrics",
                  lazy: async () => {
                    const { ObservabilityPage } =
                      await import("../pages/ObservabilityPage");
                    return { Component: ObservabilityPage };
                  },
                },
                {
                  path: "alerts",
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
            // Traces - observability traces view (ActivityBar points here)
            // Renders ObservabilityPage with traces tab - admin/developer only
            {
              path: "traces",
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
              lazy: async () => {
                const { SettingsPage } = await import("../pages/SettingsPage");
                return { Component: SettingsPage };
              },
            },
            {
              path: "cost",
              lazy: async () => {
                const { CostPage } = await import("../pages/CostPage");
                return { Component: CostPage };
              },
            },
            // Files - file browser with artifacts loader
            {
              id: "files",
              path: "files",
              loader: filesLoader,
              lazy: async () => {
                const { FilesPage } = await import("../pages/FilesPage");
                return { Component: FilesPage };
              },
            },
            // Compliance - requires compliance:read permission
            {
              path: "compliance",
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
              lazy: async () => {
                const { HelpPage } = await import("../pages/HelpPage");
                return { Component: HelpPage };
              },
            },
            // Admin routes nested under /studio/admin (lazy-loaded with PersonaGuard)
            {
              path: "admin",
              element: (
                <PersonaGuard allowedPersonas={["admin"]}>
                  <Outlet />
                </PersonaGuard>
              ),
              children: [
                { index: true, element: <Navigate to="dashboard" replace /> },
                {
                  path: "dashboard",
                  lazy: async () => {
                    const { AdminDashboardPage } =
                      await import("../pages/AdminDashboardPage");
                    return { Component: AdminDashboardPage };
                  },
                },
                {
                  path: "audit-logs",
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
        {
          path: "login",
          lazy: async () => {
            const { LoginPage } = await import("../pages/LoginPage");
            return { Component: LoginPage };
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

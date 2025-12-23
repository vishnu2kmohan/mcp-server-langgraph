import { createBrowserRouter, Navigate, Outlet } from "react-router";
import { App } from "../App";
import { AuthGuard } from "./guards/AuthGuard";
import { PersonaGuard } from "./guards/PersonaGuard";
import { PermissionGuard } from "./guards/PermissionGuard";
import { RootRedirect } from "./guards/RootRedirect";
import { StudioShellGuard } from "./guards/StudioShellGuard";
import { StudioV2Redirect } from "./guards/StudioV2Redirect";
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
 * We disable partial hydration to avoid the "No HydrateFallback" warning.
 */
export const router = createBrowserRouter(
  [
    {
      path: "/",
      element: <App />,
      children: [
        // Root redirect - uses feature flag to choose HybridShell or legacy
        { index: true, element: <RootRedirect /> },

        // Studio routes (lazy-loaded, authentication required)
        // Uses StudioShellGuard which renders HybridShellLayout
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
            // Default redirect to chat (HybridShell default)
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
            {
              path: "chat",
              children: [
                {
                  index: true,
                  lazy: async () => {
                    const { ChatPage } = await import("../pages/ChatPage");
                    return { Component: ChatPage };
                  },
                },
                // Redirect /studio/chat/:sessionId to /studio/chat?session=:sessionId
                {
                  path: ":sessionId",
                  lazy: async () => {
                    const { ChatSessionRedirect } =
                      await import("../components/Chat/ChatSessionRedirect");
                    return { Component: ChatSessionRedirect };
                  },
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

        // =================================================================
        // Hybrid Canvas Studio (Phase 2 - Parallel Route with Loaders)
        // =================================================================
        // This is a completely separate route tree from legacy /studio/*
        // Feature-flagged via canvas_hybrid_shell
        // Does NOT render MainDock or AppShell - uses HybridShellLayout
        //
        // Guard Stack:
        // 1. AuthGuard - Ensures user is authenticated
        // 2. HybridShellGuard - Checks canvas_hybrid_shell feature flag
        //    - If enabled: renders HybridShellLayout
        //    - If disabled: redirects to legacy /studio/*
        {
          id: "studio-v2",
          path: "studio/v2",
          element: (
            <AuthGuard>
              <HybridShellGuard>
                <HybridShellLayout />
              </HybridShellGuard>
            </AuthGuard>
          ),
          // Load sessions for SessionNav on shell mount
          loader: sessionsLoader,
          children: [
            // Default redirect to chat
            { index: true, element: <Navigate to="chat" replace /> },
            // Phase 2: Chat routes with loaders
            {
              path: "chat",
              children: [
                {
                  index: true,
                  id: "chat-index",
                  loader: chatLoader,
                  lazy: async () => {
                    // Placeholder - will use ChatPage until CanvasChat is ready
                    const { ChatPage } = await import("../pages/ChatPage");
                    return { Component: ChatPage };
                  },
                },
                {
                  id: "chat-session",
                  path: ":sessionId",
                  loader: chatLoader,
                  lazy: async () => {
                    const { ChatPage } = await import("../pages/ChatPage");
                    return { Component: ChatPage };
                  },
                },
              ],
            },
            // Workflows - redirect to legacy until v2 page is ready
            {
              path: "workflows",
              element: <Navigate to="/studio/workflows" replace />,
            },
            // Agents - redirect to legacy until v2 page is ready
            {
              path: "agents",
              element: <Navigate to="/studio/connections/agents" replace />,
            },
            // Observability - admin/developer only (with tab deep-links)
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
                // Tab deep-links
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
            // Traces - standalone route (redirects to observability/traces)
            {
              path: "traces",
              element: (
                <Navigate to="/studio/v2/observability/traces" replace />
              ),
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
            // Compliance - requires compliance:read permission (admin/compliance-officer)
            // Uses ConnectedComplianceDashboard which includes all framework panels
            {
              path: "compliance",
              element: (
                <PermissionGuard
                  requiredPermissions={["compliance:read"]}
                  fallbackPath="/studio/v2/chat"
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
            // Audit - requires audit:read permission (admin/auditor/compliance-officer)
            // Dedicated audit route for personas with audit access
            {
              path: "audit",
              element: (
                <PermissionGuard
                  requiredPermissions={["audit:read"]}
                  fallbackPath="/studio/v2/chat"
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
            // Admin - requires admin:access permission (fine-grained RBAC)
            {
              path: "admin",
              element: (
                <PermissionGuard
                  requiredPermissions={["admin:access"]}
                  fallbackPath="/studio/v2/chat"
                >
                  <Outlet />
                </PermissionGuard>
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
            // Analytics - HEART metrics dashboard (admin only)
            {
              path: "analytics",
              element: (
                <PermissionGuard
                  requiredPermissions={["admin:access"]}
                  fallbackPath="/studio/v2/chat"
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
            // Settings - all users
            {
              path: "settings",
              element: <Navigate to="/studio/settings" replace />,
            },
            // MCP - redirect to legacy until v2 page is ready
            {
              path: "mcp",
              element: <Navigate to="/studio/mcp" replace />,
            },
            // Cost - redirect to legacy until v2 page is ready
            {
              path: "cost",
              element: <Navigate to="/studio/cost" replace />,
            },
            // Connections - redirect to legacy until v2 page is ready
            {
              path: "connections",
              element: <Navigate to="/studio/connections" replace />,
            },
            // Help - full help center
            {
              path: "help",
              lazy: async () => {
                const { HelpPage } = await import("../pages/HelpPage");
                return { Component: HelpPage };
              },
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
    future: {
      // Disable partial hydration (not needed for CSR-only apps)
      // Prevents "No HydrateFallback element provided" warning
      v7_partialHydration: false,
    },
  },
);

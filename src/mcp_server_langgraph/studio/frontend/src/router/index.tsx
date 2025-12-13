import { createBrowserRouter, Navigate } from 'react-router-dom';
import { App } from '../App';

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
 */
export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        // Root redirect to studio
        { index: true, element: <Navigate to="/studio" replace /> },

        // Studio routes (lazy-loaded)
        {
          path: 'studio',
          children: [
            { index: true, element: <Navigate to="workflows" replace /> },
            {
              path: 'workflows',
              lazy: async () => {
                const { WorkflowsPage } = await import('../pages/WorkflowsPage');
                return { Component: WorkflowsPage };
              },
            },
            {
              path: 'chat',
              lazy: async () => {
                const { ChatPage } = await import('../pages/ChatPage');
                return { Component: ChatPage };
              },
            },
            {
              path: 'sessions',
              lazy: async () => {
                const { SessionsPage } = await import('../pages/SessionsPage');
                return { Component: SessionsPage };
              },
            },
            {
              path: 'mcp',
              lazy: async () => {
                const { MCPPage } = await import('../pages/MCPPage');
                return { Component: MCPPage };
              },
            },
            {
              path: 'observability',
              lazy: async () => {
                const { ObservabilityPage } = await import('../pages/ObservabilityPage');
                return { Component: ObservabilityPage };
              },
            },
            {
              path: 'settings',
              lazy: async () => {
                const { SettingsPage } = await import('../pages/SettingsPage');
                return { Component: SettingsPage };
              },
            },
          ],
        },

        // Admin routes (lazy-loaded with role guard)
        {
          path: 'admin',
          children: [
            { index: true, element: <Navigate to="dashboard" replace /> },
            {
              path: 'dashboard',
              lazy: async () => {
                const { AdminDashboardPage } = await import('../pages/AdminDashboardPage');
                return { Component: AdminDashboardPage };
              },
            },
          ],
        },

        // Legacy redirects (301 permanent)
        { path: 'build', element: <Navigate to="/studio/workflows" replace /> },
        { path: 'build/*', element: <Navigate to="/studio/workflows" replace /> },
        { path: 'chat', element: <Navigate to="/studio/chat" replace /> },
      ],
    },
  ],
  {
    basename: '/',
  }
);

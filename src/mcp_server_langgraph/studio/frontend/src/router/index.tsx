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
 */
export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        // Root redirect to studio
        { index: true, element: <Navigate to="/studio" replace /> },

        // Studio routes (will be lazy-loaded)
        {
          path: 'studio',
          children: [
            { index: true, element: <Navigate to="workflows" replace /> },
            {
              path: 'workflows',
              lazy: async () => {
                // Placeholder until component is created
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Workflows
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          Workflow builder coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
            {
              path: 'chat',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Chat
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          Agent chat coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
            {
              path: 'sessions',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Sessions
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          Session history coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
            {
              path: 'mcp',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          MCP Tools
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          MCP explorer coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
            {
              path: 'observability',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Observability
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          Traces and metrics coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
            {
              path: 'settings',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Settings
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          User settings coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
              },
            },
          ],
        },

        // Admin routes (will be lazy-loaded with role guard)
        {
          path: 'admin',
          children: [
            { index: true, element: <Navigate to="dashboard" replace /> },
            {
              path: 'dashboard',
              lazy: async () => {
                return {
                  Component: () => (
                    <div className="flex h-screen items-center justify-center">
                      <div className="text-center">
                        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                          Admin Dashboard
                        </h1>
                        <p className="text-gray-500 dark:text-gray-400">
                          Admin portal coming soon...
                        </p>
                      </div>
                    </div>
                  ),
                };
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

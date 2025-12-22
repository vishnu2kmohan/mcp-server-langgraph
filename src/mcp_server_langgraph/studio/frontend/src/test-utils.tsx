/**
 * Test Utilities
 *
 * Provides common test wrappers and utilities for component testing.
 * Uses React Router v7 with its default behavior.
 * Includes Redux Provider for RTK Query testing.
 * Includes TelemetryProvider for hooks that require telemetry context.
 */

import { type ReactNode } from "react";
import { createMemoryRouter, RouterProvider } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { api } from "./api";
import uiReducer from "./store/slices/uiSlice";
import personaReducer from "./store/slices/personaSlice";
import sessionReducer from "./store/slices/sessionSlice";
import projectReducer from "./store/slices/projectSlice";
import workflowReducer from "./store/slices/workflowSlice";
import artifactReducer from "./store/slices/artifactSlice";
import mcpReducer from "./store/slices/mcpSlice";
import authReducer from "./store/slices/authSlice";
import notificationReducer from "./store/slices/notificationSlice";
import observabilityReducer from "./store/slices/observabilitySlice";
import workspaceReducer from "./store/slices/workspaceSlice";
import canvasReducer from "./store/slices/canvasSlice";
import backgroundAgentReducer from "./store/slices/backgroundAgentSlice";
import aiContextReducer from "./store/slices/aiContextSlice";
import complianceReducer from "./store/slices/complianceSlice";
import helpReducer from "./store/slices/helpSlice";
import alertReducer from "./store/slices/alertSlice";
import { TelemetryProvider } from "./contexts/TelemetryContext";

/**
 * Props for TestRouter component.
 */
interface TestRouterProps {
  children: ReactNode;
  initialEntries?: string[];
}

/**
 * TestRouter - A router wrapper for tests.
 *
 * Use this for consistent router setup in tests.
 *
 * @example
 * ```tsx
 * render(
 *   <TestRouter>
 *     <MyComponent />
 *   </TestRouter>
 * );
 * ```
 */
export function TestRouter({
  children,
  initialEntries = ["/"],
}: TestRouterProps) {
  const router = createMemoryRouter(
    [
      {
        path: "*",
        element: children,
      },
    ],
    {
      initialEntries,
    },
  );

  return <RouterProvider router={router} />;
}

/**
 * Creates a memory router for custom route configurations.
 *
 * @example
 * ```tsx
 * const router = createTestRouter([
 *   { path: '/', element: <Home /> },
 *   { path: '/about', element: <About /> },
 * ]);
 * render(<RouterProvider router={router} />);
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function createTestRouter(
  routes: Parameters<typeof createMemoryRouter>[0],
  initialEntries: string[] = ["/"],
) {
  return createMemoryRouter(routes, {
    initialEntries,
  });
}

/**
 * Creates a test store with RTK Query API and all required reducers.
 * Mirrors the main store configuration for comprehensive testing.
 */
// eslint-disable-next-line react-refresh/only-export-components
export function createTestStore() {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
      ui: uiReducer,
      persona: personaReducer,
      session: sessionReducer,
      project: projectReducer,
      workflow: workflowReducer,
      artifact: artifactReducer,
      mcp: mcpReducer,
      auth: authReducer,
      notifications: notificationReducer,
      observability: observabilityReducer,
      workspace: workspaceReducer,
      canvas: canvasReducer,
      backgroundAgent: backgroundAgentReducer,
      aiContext: aiContextReducer,
      compliance: complianceReducer,
      help: helpReducer,
      alerts: alertReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

/**
 * Props for TestProvider component.
 */
interface TestProviderProps {
  children: ReactNode;
  initialEntries?: string[];
}

/**
 * TestProvider - A combined Provider wrapper for tests.
 *
 * Wraps children in Redux Provider, Router, and TelemetryProvider for comprehensive testing.
 * This ensures hooks like useSessionTelemetry work correctly in tests.
 *
 * @example
 * ```tsx
 * render(
 *   <TestProvider>
 *     <MyComponent />
 *   </TestProvider>
 * );
 * ```
 */
export function TestProvider({
  children,
  initialEntries = ["/"],
}: TestProviderProps) {
  const store = createTestStore();
  const router = createMemoryRouter(
    [
      {
        path: "*",
        element: children,
      },
    ],
    {
      initialEntries,
    },
  );

  return (
    <TelemetryProvider>
      <Provider store={store}>
        <RouterProvider router={router} />
      </Provider>
    </TelemetryProvider>
  );
}

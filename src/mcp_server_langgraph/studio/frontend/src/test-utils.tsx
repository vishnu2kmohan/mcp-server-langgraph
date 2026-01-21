/**
 * Test Utilities
 *
 * Provides common test wrappers and utilities for component testing.
 * Uses React Router v7 with its default behavior.
 * Includes Redux Provider for RTK Query testing.
 * Includes TelemetryProvider for hooks that require telemetry context.
 * Includes motion/react mock utilities for animation testing.
 */

import React, { type ReactNode } from "react";

// ============================================================================
// Motion/React Mock Utilities
// ============================================================================
//
// IMPORTANT: Due to Vitest's vi.mock() hoisting behavior, the createMotionMock()
// function cannot be directly used in vi.mock() calls like:
//   vi.mock("motion/react", () => createMotionMock())  // ERROR: hoisting issue
//
// Instead, each test file must define its own inline mock. Use MOTION_PROPS
// and filterMotionProps as the AUTHORITATIVE reference for which props to filter.
//
// Example usage in test files:
// ```tsx
// // Copy the MOTION_PROPS set and filterMotionProps function inline
// const MOTION_PROPS = new Set([...]);  // See below for complete list
// function filterMotionProps<T>(...) { ... }
//
// vi.mock("motion/react", () => ({
//   motion: {
//     div: ({ children, ...props }) => <div {...filterMotionProps(props)}>{children}</div>,
//   },
//   useReducedMotion: () => false,
//   AnimatePresence: ({ children }) => <>{children}</>,
// }));
// ```

/**
 * Motion-specific props that should not be passed to DOM elements.
 * React does not recognize props like whileHover, whileTap on DOM elements.
 *
 * Use this as the AUTHORITATIVE list when creating inline mocks.
 *
 * @see https://motion.dev/docs/react-motion-component
 */
export const MOTION_PROPS = new Set([
  "whileHover",
  "whileTap",
  "whileFocus",
  "whileDrag",
  "whileInView",
  "initial",
  "animate",
  "exit",
  "variants",
  "transition",
  "layout",
  "layoutId",
  "drag",
  "dragConstraints",
  "dragElastic",
  "dragMomentum",
  "onAnimationStart",
  "onAnimationComplete",
  "onDragStart",
  "onDragEnd",
  "onDrag",
]);

/**
 * Filter out motion-specific props to avoid React DOM warnings.
 * Use this in motion mock implementations to prevent:
 * "Warning: React does not recognize the `whileHover` prop on a DOM element."
 *
 * @example
 * ```tsx
 * vi.mock("motion/react", () => ({
 *   motion: {
 *     div: ({ children, ...props }) => <div {...filterMotionProps(props)}>{children}</div>,
 *   },
 * }));
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function filterMotionProps<T extends Record<string, unknown>>(
  props: T
): Omit<T, (typeof MOTION_PROPS extends Set<infer U> ? U : never)> {
  const filtered = { ...props };
  for (const key of Object.keys(filtered)) {
    if (MOTION_PROPS.has(key)) {
      delete filtered[key];
    }
  }
  return filtered;
}

/**
 * Creates a mock motion/react module for vi.mock().
 * Provides motion components that filter motion-specific props.
 *
 * @example
 * ```tsx
 * vi.mock("motion/react", () => createMotionMock());
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function createMotionMock() {
  return {
    motion: {
      div: ({
        children,
        ...props
      }: React.ComponentProps<"div"> & Record<string, unknown>) => (
        <div {...filterMotionProps(props)}>{children}</div>
      ),
      button: ({
        children,
        ...props
      }: React.ComponentProps<"button"> & Record<string, unknown>) => (
        // eslint-disable-next-line react/forbid-elements -- motion component mock requires raw element
        (<button {...filterMotionProps(props)}>{children}</button>)
      ),
      span: ({
        children,
        ...props
      }: React.ComponentProps<"span"> & Record<string, unknown>) => (
        <span {...filterMotionProps(props)}>{children}</span>
      ),
      ul: ({
        children,
        ...props
      }: React.ComponentProps<"ul"> & Record<string, unknown>) => (
        <ul {...filterMotionProps(props)}>{children}</ul>
      ),
      li: ({
        children,
        ...props
      }: React.ComponentProps<"li"> & Record<string, unknown>) => (
        <li {...filterMotionProps(props)}>{children}</li>
      ),
      section: ({
        children,
        ...props
      }: React.ComponentProps<"section"> & Record<string, unknown>) => (
        <section {...filterMotionProps(props)}>{children}</section>
      ),
      article: ({
        children,
        ...props
      }: React.ComponentProps<"article"> & Record<string, unknown>) => (
        <article {...filterMotionProps(props)}>{children}</article>
      ),
      aside: ({
        children,
        ...props
      }: React.ComponentProps<"aside"> & Record<string, unknown>) => (
        <aside {...filterMotionProps(props)}>{children}</aside>
      ),
      nav: ({
        children,
        ...props
      }: React.ComponentProps<"nav"> & Record<string, unknown>) => (
        <nav {...filterMotionProps(props)}>{children}</nav>
      ),
      header: ({
        children,
        ...props
      }: React.ComponentProps<"header"> & Record<string, unknown>) => (
        <header {...filterMotionProps(props)}>{children}</header>
      ),
      footer: ({
        children,
        ...props
      }: React.ComponentProps<"footer"> & Record<string, unknown>) => (
        <footer {...filterMotionProps(props)}>{children}</footer>
      ),
      form: ({
        children,
        ...props
      }: React.ComponentProps<"form"> & Record<string, unknown>) => (
        <form {...filterMotionProps(props)}>{children}</form>
      ),
      input: (props: React.ComponentProps<"input"> & Record<string, unknown>) => (
         
        (<Input {...filterMotionProps(props)} />)
      ),
      textarea: (props: React.ComponentProps<"textarea"> & Record<string, unknown>) => (
         
        (<Textarea {...filterMotionProps(props)} />)
      ),
      label: ({
        children,
        ...props
      }: React.ComponentProps<"label"> & Record<string, unknown>) => (
        <label {...filterMotionProps(props)}>{children}</label>
      ),
      a: ({
        children,
        ...props
      }: React.ComponentProps<"a"> & Record<string, unknown>) => (
        <a {...filterMotionProps(props)}>{children}</a>
      ),
      p: ({
        children,
        ...props
      }: React.ComponentProps<"p"> & Record<string, unknown>) => (
        <p {...filterMotionProps(props)}>{children}</p>
      ),
      h1: ({
        children,
        ...props
      }: React.ComponentProps<"h1"> & Record<string, unknown>) => (
        <h1 {...filterMotionProps(props)}>{children}</h1>
      ),
      h2: ({
        children,
        ...props
      }: React.ComponentProps<"h2"> & Record<string, unknown>) => (
        <h2 {...filterMotionProps(props)}>{children}</h2>
      ),
      h3: ({
        children,
        ...props
      }: React.ComponentProps<"h3"> & Record<string, unknown>) => (
        <h3 {...filterMotionProps(props)}>{children}</h3>
      ),
      svg: ({
        children,
        ...props
      }: React.SVGProps<SVGSVGElement> & Record<string, unknown>) => (
        <svg {...filterMotionProps(props)}>{children}</svg>
      ),
      path: (props: React.SVGProps<SVGPathElement> & Record<string, unknown>) => (
        <path {...filterMotionProps(props)} />
      ),
    },
    useReducedMotion: () => false,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    LayoutGroup: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
    LazyMotion: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    domAnimation: {},
    domMax: {},
  };
}

// ============================================================================
// TelemetryContext Mock Utilities
// ============================================================================
//
// IMPORTANT: Due to Vitest's vi.mock() hoisting behavior, the createTelemetryMock()
// function cannot be directly used in vi.mock() calls. Each test file must define
// its own inline mock. Use TELEMETRY_MOCK_METHODS as the AUTHORITATIVE reference.
//
// Example usage in test files:
// ```tsx
// vi.mock("../contexts/TelemetryContext", () => ({
//   useSessionTelemetry: () => ({
//     trackExecutionModeChange: vi.fn(),
//     trackBypassApproval: vi.fn(),
//     trackSessionCreation: vi.fn(),
//     trackRevalidation: vi.fn(),
//     trackSync: vi.fn(),
//     trackArtifactSave: vi.fn(),
//     trackArtifactDelete: vi.fn(),
//     trackSuggestionAction: vi.fn(),
//     trackCanvasAction: vi.fn(),
//     getMetrics: vi.fn(),
//     getHistory: vi.fn(),
//     reset: vi.fn(),
//   }),
//   TelemetryProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
// }));
// ```

/**
 * Authoritative list of TelemetryContext methods that should be mocked.
 * Use this as reference when creating inline mocks.
 *
 * @see src/contexts/TelemetryContext.tsx for actual implementation
 * @see .claude/memory/execution-mode-patterns.md gotcha #12
 */
export const TELEMETRY_MOCK_METHODS = [
  "trackExecutionModeChange",
  "trackBypassApproval",
  "trackSessionCreation",
  "trackRevalidation",
  "trackSync",
  "trackArtifactSave",
  "trackArtifactDelete",
  "trackSuggestionAction",
  "trackCanvasAction",
  "getMetrics",
  "getHistory",
  "reset",
] as const;

/**
 * Creates a mock TelemetryContext for testing.
 * Returns an object with all telemetry methods as vi.fn() mocks.
 *
 * Note: Due to Vitest hoisting, this cannot be used directly in vi.mock().
 * Use as reference for what methods to include in inline mocks.
 *
 * @example
 * ```tsx
 * // For runtime usage (not in vi.mock):
 * const telemetryMock = createTelemetryMock();
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function createTelemetryMock() {
  // Note: We use a simple object with vi.fn() here for documentation
  // In actual vi.mock(), you'll need to inline this
  return {
    useSessionTelemetry: () => ({
      trackExecutionModeChange: jest.fn?.() ?? (() => {}),
      trackBypassApproval: jest.fn?.() ?? (() => {}),
      trackSessionCreation: jest.fn?.() ?? (() => {}),
      trackRevalidation: jest.fn?.() ?? (() => {}),
      trackSync: jest.fn?.() ?? (() => {}),
      trackArtifactSave: jest.fn?.() ?? (() => {}),
      trackArtifactDelete: jest.fn?.() ?? (() => {}),
      trackSuggestionAction: jest.fn?.() ?? (() => {}),
      trackCanvasAction: jest.fn?.() ?? (() => {}),
      getMetrics: jest.fn?.() ?? (() => ({})),
      getHistory: jest.fn?.() ?? (() => []),
      reset: jest.fn?.() ?? (() => {}),
    }),
    TelemetryProvider: ({ children }: { children: React.ReactNode }) => (
      <>{children}</>
    ),
  };
}

// ============================================================================
// React Router Test Utilities
// ============================================================================
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

import { Input, Textarea } from "@/components/UI";

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

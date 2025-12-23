/**
 * Lazy MCP Components
 *
 * Code-split versions of MCP components for reduced initial bundle size.
 * These components are loaded on-demand when first rendered.
 *
 * Usage:
 * ```tsx
 * import { LazyToolInvocationDialog } from "../components/MCP/lazy";
 * import { Suspense } from "react";
 *
 * <Suspense fallback={<div>Loading...</div>}>
 *   <LazyToolInvocationDialog {...props} />
 * </Suspense>
 * ```
 *
 * Benefits:
 * - Reduces initial bundle size by ~40-80KB
 * - MCP dialogs loaded only when user opens them
 * - Faster initial page load for users not using MCP features
 */

import { lazy } from "react";

/**
 * Lazy-loaded AddConnectionDialog component.
 * Only loaded when user wants to add a new MCP connection.
 */
export const LazyAddConnectionDialog = lazy(() =>
  import("./AddConnectionDialog").then((module) => ({
    default: module.AddConnectionDialog,
  })),
);

/**
 * Lazy-loaded ToolInvocationDialog component.
 * Only loaded when user wants to invoke an MCP tool.
 */
export const LazyToolInvocationDialog = lazy(() =>
  import("./ToolInvocationDialog").then((module) => ({
    default: module.ToolInvocationDialog,
  })),
);

/**
 * Lazy-loaded ResourceViewer component.
 * Only loaded when user views MCP resources.
 */
export const LazyResourceViewer = lazy(() =>
  import("./ResourceViewer").then((module) => ({
    default: module.ResourceViewer,
  })),
);

/**
 * Lazy-loaded PromptTester component.
 * Only loaded when user tests MCP prompts.
 */
export const LazyPromptTester = lazy(() =>
  import("./PromptTester").then((module) => ({
    default: module.PromptTester,
  })),
);

/**
 * Lazy-loaded ElicitationDialog component.
 * Only loaded when MCP server requests user input.
 */
export const LazyElicitationDialog = lazy(() =>
  import("./ElicitationDialog").then((module) => ({
    default: module.ElicitationDialog,
  })),
);

// Re-export types that consumers need (types don't affect bundle size)
export type { AddConnectionDialogProps } from "./AddConnectionDialog";
export type { ToolInvocationDialogProps } from "./ToolInvocationDialog";
export type { ResourceViewerProps } from "./ResourceViewer";
export type { PromptTesterProps } from "./PromptTester";
export type { ElicitationDialogProps } from "./ElicitationDialog";

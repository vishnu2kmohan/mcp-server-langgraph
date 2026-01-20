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

// =============================================================================
// Aggregated Capabilities Components (MCP 2025-11-25)
// =============================================================================

/**
 * Lazy-loaded AggregatedCapabilitiesPanel component.
 * Only loaded when user views aggregated capabilities from external MCP servers.
 */
export const LazyAggregatedCapabilitiesPanel = lazy(() =>
  import("./AggregatedCapabilities").then((module) => ({
    default: module.AggregatedCapabilitiesPanel,
  })),
);

/**
 * Lazy-loaded MCPServerCard component.
 * Only loaded when displaying server capability summaries.
 */
export const LazyMCPServerCard = lazy(() =>
  import("./MCPServerCard").then((module) => ({
    default: module.MCPServerCard,
  })),
);

/**
 * Lazy-loaded ToolExplorer component.
 * Only loaded when browsing aggregated tools.
 */
export const LazyToolExplorer = lazy(() =>
  import("./ToolExplorer").then((module) => ({
    default: module.ToolExplorer,
  })),
);

/**
 * Lazy-loaded ResourceBrowser component.
 * Only loaded when browsing aggregated resources.
 */
export const LazyResourceBrowser = lazy(() =>
  import("./ResourceBrowser").then((module) => ({
    default: module.ResourceBrowser,
  })),
);

/**
 * Lazy-loaded PromptLibrary component.
 * Only loaded when browsing aggregated prompts.
 */
export const LazyPromptLibrary = lazy(() =>
  import("./PromptLibrary").then((module) => ({
    default: module.PromptLibrary,
  })),
);

// =============================================================================
// Inbound JSON-RPC Components (MCP 2025-11-25 Server-Initiated Requests)
// =============================================================================

/**
 * Lazy-loaded InboundElicitationModal component.
 * Only loaded when MCP server sends an elicitation/create request.
 */
export const LazyInboundElicitationModal = lazy(() =>
  import("./InboundElicitationModal").then((module) => ({
    default: module.InboundElicitationModal,
  })),
);

/**
 * Lazy-loaded InboundSamplingModal component.
 * Only loaded when MCP server sends a sampling/createMessage request.
 */
export const LazyInboundSamplingModal = lazy(() =>
  import("./InboundSamplingModal").then((module) => ({
    default: module.InboundSamplingModal,
  })),
);

// Re-export types that consumers need (types don't affect bundle size)
export type { AddConnectionDialogProps } from "./AddConnectionDialog";
export type { ToolInvocationDialogProps } from "./ToolInvocationDialog";
export type { ResourceViewerProps } from "./ResourceViewer";
export type { PromptTesterProps } from "./PromptTester";
export type { ElicitationDialogProps } from "./ElicitationDialog";
export type { AggregatedCapabilitiesPanelProps } from "./AggregatedCapabilities";
export type { MCPServerCardProps } from "./MCPServerCard";
export type { ToolExplorerProps } from "./ToolExplorer";
export type { ResourceBrowserProps } from "./ResourceBrowser";
export type { PromptLibraryProps } from "./PromptLibrary";
export type { InboundElicitationModalProps } from "./InboundElicitationModal";
export type { InboundSamplingModalProps } from "./InboundSamplingModal";

/**
 * MCP Components
 *
 * Components for MCP (Model Context Protocol) connection management.
 *
 * NOTE: Component implementations are only available via lazy exports to enable
 * code-splitting. Import lazy components from this file:
 *
 * ```tsx
 * import { LazyToolInvocationDialog } from "../components/MCP";
 * ```
 *
 * Type exports are available directly from this file.
 */

// Type-only exports (don't affect bundle size)
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

// Lazy exports (code-split, loaded on demand)
export {
  LazyAddConnectionDialog,
  LazyToolInvocationDialog,
  LazyResourceViewer,
  LazyPromptTester,
  LazyElicitationDialog,
  // Aggregated capabilities (MCP 2025-11-25)
  LazyAggregatedCapabilitiesPanel,
  LazyMCPServerCard,
  LazyToolExplorer,
  LazyResourceBrowser,
  LazyPromptLibrary,
} from "./lazy";

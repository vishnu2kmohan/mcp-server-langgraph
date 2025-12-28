/**
 * MCP Components
 *
 * Components for MCP (Model Context Protocol) connection management.
 */

// Regular exports (synchronous)
export { AddConnectionDialog } from "./AddConnectionDialog";
export { ToolInvocationDialog } from "./ToolInvocationDialog";
export { ResourceViewer } from "./ResourceViewer";
export { PromptTester } from "./PromptTester";
export { ElicitationDialog } from "./ElicitationDialog";

// Aggregated capabilities components (MCP 2025-11-25)
export { AggregatedCapabilitiesPanel } from "./AggregatedCapabilities";
export { MCPServerCard } from "./MCPServerCard";
export { ToolExplorer } from "./ToolExplorer";
export { ResourceBrowser } from "./ResourceBrowser";
export { PromptLibrary } from "./PromptLibrary";

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

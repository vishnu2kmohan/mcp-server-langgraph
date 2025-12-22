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

// Lazy exports (code-split, loaded on demand)
export {
  LazyAddConnectionDialog,
  LazyToolInvocationDialog,
  LazyResourceViewer,
  LazyPromptTester,
  LazyElicitationDialog,
} from "./lazy";

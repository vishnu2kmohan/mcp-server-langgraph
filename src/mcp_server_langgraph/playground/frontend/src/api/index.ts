/**
 * API Module Exports
 *
 * Re-exports all API types and clients for easy consumption.
 */

// Types
export * from './types';
export * from './mcp-types';

// MCP Client
export type { MCPClient, MCPClientOptions } from './mcp-client';
export { MCPClientError, createMCPClient, MCP_METHODS } from './mcp-client';

// Playground REST API
export type { PlaygroundAPIConfig } from './playground';
export {
  PlaygroundAPI,
  createPlaygroundAPI,
  getPlaygroundAPI,
  configurePlaygroundAPI,
} from './playground';

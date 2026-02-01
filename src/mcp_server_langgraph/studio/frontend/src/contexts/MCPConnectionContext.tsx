/**
 * MCPConnectionContext
 *
 * Provides a single MCP WebSocket connection to avoid duplicate connections.
 * Components that need MCP functionality should use useMCPConnection() instead
 * of calling useMCPWebSocket() directly.
 *
 * This ensures:
 * - Single WebSocket connection for the entire app
 * - Consistent connection state across all consumers
 * - Centralized handling of inbound requests (elicitation/sampling)
 *
 * @see ADR-0069 MCP 2025-11-25 Upgrade
 */

import { createContext, useContext, type ReactNode } from "react";
import {
  useMCPWebSocket,
  type UseMCPWebSocketReturn,
} from "../hooks/useMCPWebSocket";

/**
 * MCP Connection Context
 *
 * Holds the shared MCP WebSocket connection state and methods.
 */
const MCPConnectionContext = createContext<UseMCPWebSocketReturn | null>(null);

/**
 * Props for MCPConnectionProvider
 */
export interface MCPConnectionProviderProps {
  children: ReactNode;
}

/**
 * MCPConnectionProvider
 *
 * Wraps the application (or a subtree) to provide a single shared MCP connection.
 * Should be placed high in the component tree, typically in StudioShellLayout.
 *
 * @example
 * ```tsx
 * function App() {
 *   return (
 *     <MCPConnectionProvider>
 *       <MyComponent />
 *     </MCPConnectionProvider>
 *   );
 * }
 * ```
 */
export function MCPConnectionProvider({
  children,
}: MCPConnectionProviderProps) {
  // Create a single MCP WebSocket connection for the entire app
  const mcpConnection = useMCPWebSocket();

  return (
    <MCPConnectionContext.Provider value={mcpConnection}>
      {children}
    </MCPConnectionContext.Provider>
  );
}

/**
 * useMCPConnection
 *
 * Hook to access the shared MCP connection. Must be used within MCPConnectionProvider.
 *
 * @returns The shared MCP connection state and methods
 * @throws Error if used outside of MCPConnectionProvider
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { tools, callTool, sendResponse } = useMCPConnection();
 *
 *   return <div>{tools.length} tools available</div>;
 * }
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components -- Hook export alongside context provider is standard pattern
export function useMCPConnection(): UseMCPWebSocketReturn {
  const context = useContext(MCPConnectionContext);

  if (context === null) {
    throw new Error(
      "useMCPConnection must be used within MCPConnectionProvider",
    );
  }

  return context;
}

export default MCPConnectionProvider;

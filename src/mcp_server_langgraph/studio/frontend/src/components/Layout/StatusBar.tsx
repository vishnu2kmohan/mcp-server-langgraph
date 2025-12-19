/**
 * StatusBar Component
 *
 * JupyterLab-inspired status bar for Agent Studio.
 * Displays at the bottom of the AppShell and shows:
 * - Session info (name, messages, model, tokens, cost)
 * - Connection status (API health)
 * - Persona/role indicator
 */

import { useMemo } from "react";
import { useAppSelector } from "../../store/hooks";
import { selectPersona } from "../../store/slices/personaSlice";
import { selectCurrentSession } from "../../store/slices/sessionSlice";
import { useGetHealthQuery } from "../../api";
import { useConnectionHealthWebSocket } from "../../hooks/useConnectionHealthWebSocket";
import { useMCPTaskWebSocket } from "../../hooks/useMCPTaskWebSocket";

// Cost per 1K tokens by provider (simplified estimates)
const COST_PER_1K_TOKENS: Record<string, { input: number; output: number }> = {
  openai: { input: 0.01, output: 0.03 },
  anthropic: { input: 0.015, output: 0.075 },
  google: { input: 0.00025, output: 0.0005 },
  azure: { input: 0.01, output: 0.03 },
};

// =============================================================================
// Types
// =============================================================================

export interface StatusBarProps {
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Component
// =============================================================================

export function StatusBar({ className }: StatusBarProps) {
  // API Health check with polling every 30 seconds
  const {
    data: healthData,
    isLoading: isHealthLoading,
    isError: isHealthError,
  } = useGetHealthQuery(undefined, {
    pollingInterval: 30000, // Poll every 30 seconds
    refetchOnMountOrArgChange: true,
  });

  // MCP Connection Health
  const { summary: mcpSummary } = useConnectionHealthWebSocket();

  // MCP Task Status
  const { tasks } = useMCPTaskWebSocket();
  const activeTasks = useMemo(() => {
    return tasks.filter(
      (task) => task.status === "running" || task.status === "pending",
    );
  }, [tasks]);

  // Selectors
  const persona = useAppSelector(selectPersona);
  const currentSession = useAppSelector(selectCurrentSession);

  // Session info
  const sessionName = currentSession?.name;
  const messageCount = currentSession?.messages?.length ?? 0;
  const modelName = currentSession?.config?.modelName;

  // Calculate total tokens from messages
  const tokenStats = useMemo(() => {
    if (!currentSession?.messages) {
      return { prompt: 0, completion: 0, total: 0 };
    }
    return currentSession.messages.reduce(
      (acc, msg) => {
        if (msg.usage) {
          acc.prompt += msg.usage.promptTokens;
          acc.completion += msg.usage.completionTokens;
          acc.total += msg.usage.totalTokens;
        }
        return acc;
      },
      { prompt: 0, completion: 0, total: 0 },
    );
  }, [currentSession?.messages]);

  // Estimate cost
  const estimatedCost = useMemo(() => {
    if (!currentSession?.config) return 0;
    const rates =
      COST_PER_1K_TOKENS[currentSession.config.modelProvider] ??
      COST_PER_1K_TOKENS.openai;
    const inputCost = (tokenStats.prompt / 1000) * rates.input;
    const outputCost = (tokenStats.completion / 1000) * rates.output;
    return inputCost + outputCost;
  }, [currentSession?.config, tokenStats]);

  // Determine API health status text and color
  const isConnected = healthData?.status === "healthy";
  const isDegraded = healthData?.status === "degraded";
  const isUnhealthy = healthData?.status === "unhealthy";
  const isConnecting = isHealthLoading;

  const connectionStatus = isConnecting
    ? "Connecting..."
    : isHealthError
      ? "Disconnected"
      : isUnhealthy
        ? "Unhealthy"
        : isDegraded
          ? "Degraded"
          : isConnected
            ? "Connected"
            : "Disconnected";

  // Tooltip with more details about the connection status
  const connectionTooltip = isConnecting
    ? "Checking API health..."
    : isHealthError
      ? "Cannot reach the API server"
      : isUnhealthy
        ? "API responding but system has errors (check backend logs)"
        : isDegraded
          ? "API responding but some services are degraded"
          : isConnected
            ? "All systems operational"
            : "Unknown connection state";

  const connectionColor = isConnecting
    ? "text-yellow-500"
    : isHealthError
      ? "text-red-500"
      : isUnhealthy
        ? "text-red-500"
        : isDegraded
          ? "text-yellow-500"
          : isConnected
            ? "text-green-500"
            : "text-gray-400";

  return (
    <div
      data-testid="status-bar"
      className={cn(
        "h-6 flex-shrink-0",
        "border-t border-gray-200 dark:border-gray-700",
        "bg-gray-100 dark:bg-gray-800",
        "flex items-center justify-between px-3 text-xs",
        className,
      )}
    >
      {/* Left section - Session info */}
      <div className="flex items-center gap-4">
        {/* Session Group - session-related items */}
        {currentSession && (
          <div data-testid="session-group" className="flex items-center gap-3">
            {/* Session Info */}
            <div
              data-testid="session-info"
              title={`Session: ${sessionName} (${messageCount} ${messageCount === 1 ? "message" : "messages"})`}
              className="flex items-center gap-2 text-gray-600 dark:text-gray-300 cursor-help"
            >
              <span className="truncate max-w-48">{sessionName}</span>
              <span className="text-gray-400 dark:text-gray-500">·</span>
              <span className="text-gray-500 dark:text-gray-400">
                {messageCount} {messageCount === 1 ? "msg" : "msgs"}
              </span>
            </div>

            {/* Model Info */}
            {currentSession.config && modelName && (
              <div
                data-testid="model-info"
                title={`Model: ${modelName} (Provider: ${currentSession.config.modelProvider})`}
                className="flex items-center gap-1 text-gray-600 dark:text-gray-300 cursor-help"
              >
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"
                  />
                </svg>
                <span>{modelName}</span>
              </div>
            )}

            {/* Token Count */}
            {tokenStats.total > 0 && (
              <div
                data-testid="token-count"
                title={`Tokens: ${tokenStats.prompt.toLocaleString()} in + ${tokenStats.completion.toLocaleString()} out = ${tokenStats.total.toLocaleString()} total`}
                className="flex items-center gap-1 text-gray-500 dark:text-gray-400 cursor-help"
              >
                <span>{tokenStats.total.toLocaleString()} tok</span>
              </div>
            )}

            {/* Cost Estimate */}
            {estimatedCost > 0 && (
              <div
                data-testid="cost-estimate"
                title={`Estimated cost based on ${currentSession.config?.modelProvider || "default"} pricing`}
                className="flex items-center gap-1 text-green-600 dark:text-green-400 cursor-help"
              >
                <span>${estimatedCost.toFixed(2)}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Right section - Connection status and persona */}
      <div className="flex items-center gap-4">
        {/* MCP Connection Status */}
        {mcpSummary.total > 0 && (
          <div
            data-testid="mcp-status"
            title={`MCP Connections: ${mcpSummary.connected}/${mcpSummary.total} connected${mcpSummary.error > 0 ? `, ${mcpSummary.error} error(s)` : ""}${mcpSummary.auth_required > 0 ? `, ${mcpSummary.auth_required} auth required` : ""}`}
            className={cn(
              "flex items-center gap-1.5 cursor-help",
              mcpSummary.connected === mcpSummary.total && "text-green-500",
              mcpSummary.connected > 0 &&
                mcpSummary.connected < mcpSummary.total &&
                "text-yellow-500",
              mcpSummary.connected === 0 && "text-red-500",
            )}
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"
              />
            </svg>
            <span>
              {mcpSummary.connected}/{mcpSummary.total}
            </span>
          </div>
        )}

        {/* MCP Task Status */}
        {activeTasks.length > 0 && (
          <div
            data-testid="task-status"
            title={`${activeTasks.length} active task${activeTasks.length !== 1 ? "s" : ""}: ${activeTasks.filter((t) => t.status === "running").length} running, ${activeTasks.filter((t) => t.status === "pending").length} pending`}
            className="flex items-center gap-1.5 cursor-help text-blue-500"
          >
            <svg
              className="w-3.5 h-3.5 animate-spin"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <circle
                className="opacity-25"
                cx="12"
                cy="12"
                r="10"
                strokeWidth="4"
              />
              <path
                className="opacity-75"
                fill="currentColor"
                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
              />
            </svg>
            <span>{activeTasks.length}</span>
          </div>
        )}

        {/* Connection Status */}
        <div
          data-testid="connection-status"
          title={connectionTooltip}
          className={cn(
            "flex items-center gap-1.5 cursor-help",
            connectionColor,
          )}
        >
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              isConnecting && "bg-yellow-500 animate-pulse",
              isHealthError && "bg-red-500",
              isUnhealthy && "bg-red-500",
              isDegraded && "bg-yellow-500",
              isConnected && "bg-green-500",
              !isConnecting &&
                !isConnected &&
                !isDegraded &&
                !isHealthError &&
                !isUnhealthy &&
                "bg-gray-400",
            )}
          />
          <span>{connectionStatus}</span>
        </div>

        {/* Persona Indicator */}
        <div
          data-testid="persona-indicator"
          title={`Logged in as ${persona} - determines access to features`}
          className={cn(
            "flex items-center gap-1 capitalize cursor-help",
            persona === "admin" && "text-purple-600 dark:text-purple-400",
            persona === "developer" && "text-blue-600 dark:text-blue-400",
            persona === "user" && "text-gray-600 dark:text-gray-400",
          )}
        >
          <svg
            className="w-3.5 h-3.5"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"
            />
          </svg>
          <span>{persona}</span>
        </div>
      </div>
    </div>
  );
}

export default StatusBar;

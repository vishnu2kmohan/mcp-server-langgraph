/**
 * StatusBar Component
 *
 * JupyterLab-inspired status bar for Agent Studio.
 * Displays at the bottom of the AppShell and shows:
 * - Connection status (MCP server)
 * - Persona/role indicator
 * - Notification count badge
 * - Ready state
 */

import { useMemo } from "react";
import { useAppSelector } from "../../store/hooks";
import {
  selectIsConnected,
  selectIsConnecting,
} from "../../store/slices/mcpSlice";
import { selectPersona } from "../../store/slices/personaSlice";
import { selectUnreadCount } from "../../store/slices/notificationSlice";
import { selectCurrentSession } from "../../store/slices/sessionSlice";

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
  // Selectors
  const isConnected = useAppSelector(selectIsConnected);
  const isConnecting = useAppSelector(selectIsConnecting);
  const persona = useAppSelector(selectPersona);
  const unreadCount = useAppSelector(selectUnreadCount);
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

  // Determine connection status text and color
  const connectionStatus = isConnecting
    ? "Connecting..."
    : isConnected
      ? "Connected"
      : "Disconnected";

  const connectionColor = isConnecting
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
      {/* Left section */}
      <div className="flex items-center gap-4">
        {/* Connection Status */}
        <div
          data-testid="connection-status"
          className={cn("flex items-center gap-1.5", connectionColor)}
        >
          <span
            className={cn(
              "w-2 h-2 rounded-full",
              isConnecting && "bg-yellow-500 animate-pulse",
              isConnected && "bg-green-500",
              !isConnecting && !isConnected && "bg-gray-400",
            )}
          />
          <span>{connectionStatus}</span>
        </div>

        {/* Ready State */}
        <span className="text-gray-500 dark:text-gray-400">Ready</span>

        {/* Session Info */}
        {currentSession && (
          <div
            data-testid="session-info"
            className="flex items-center gap-2 text-gray-600 dark:text-gray-300"
          >
            <span className="truncate max-w-48">{sessionName}</span>
            <span className="text-gray-400 dark:text-gray-500">|</span>
            <span className="text-gray-500 dark:text-gray-400">
              {messageCount} {messageCount === 1 ? "message" : "messages"}
            </span>
          </div>
        )}

        {/* Model Info */}
        {currentSession?.config && modelName && (
          <div
            data-testid="model-info"
            className="flex items-center gap-1 text-gray-600 dark:text-gray-300"
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
        {currentSession && tokenStats.total > 0 && (
          <div
            data-testid="token-count"
            className="flex items-center gap-1 text-gray-500 dark:text-gray-400"
          >
            <span>{tokenStats.total.toLocaleString()} tokens</span>
          </div>
        )}

        {/* Cost Estimate */}
        {currentSession && estimatedCost > 0 && (
          <div
            data-testid="cost-estimate"
            className="flex items-center gap-1 text-green-600 dark:text-green-400"
          >
            <span>${estimatedCost.toFixed(2)}</span>
          </div>
        )}
      </div>

      {/* Right section */}
      <div className="flex items-center gap-4">
        {/* Notification Count Badge */}
        {unreadCount > 0 && (
          <div
            data-testid="notification-count"
            className="flex items-center gap-1 text-blue-600 dark:text-blue-400"
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
                d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
              />
            </svg>
            <span>{unreadCount}</span>
          </div>
        )}

        {/* Persona Indicator */}
        <div
          data-testid="persona-indicator"
          className={cn(
            "flex items-center gap-1 capitalize",
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

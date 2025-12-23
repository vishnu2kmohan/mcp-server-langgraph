/**
 * StatusBar Component
 *
 * Bottom status bar showing application state, connection status,
 * agent status, model info, token count, and keyboard shortcuts.
 * Extracted from HybridShellLayout for maintainability.
 *
 * Features:
 * - Status display (Ready, Loading, etc.)
 * - Connection status indicator (connected, disconnected, connecting)
 * - Agent status display
 * - Model name indicator
 * - Token count indicator
 * - User indicator
 * - Keyboard shortcut hints
 * - Feature flag toggle (dev mode)
 */
import {
  Cpu,
  Hash,
  User,
  ListTodo,
  AlertTriangle,
  Terminal,
} from "lucide-react";
import { cn } from "../utils/cn";
import { FeatureFlagToggle } from "./FeatureFlagToggle";

// =============================================================================
// Types
// =============================================================================

export type ConnectionStatus =
  | "connected"
  | "disconnected"
  | "connecting"
  | "error";

export interface StatusBarProps {
  /** Current status message (default: "Ready") */
  status?: string;
  /** Connection status for WebSocket/API */
  connectionStatus?: ConnectionStatus;
  /** Agent status message (e.g., "Thinking...") */
  agentStatus?: string;
  /** Model name (e.g., "claude-3-opus") */
  modelName?: string;
  /** Token count for current session */
  tokenCount?: number;
  /** Current user name */
  userName?: string;
  /** Error message to display (shows in red) */
  errorMessage?: string;
  /** Number of background agents (shows toggle when > 0) */
  agentCount?: number;
  /** Callback when agent queue toggle is clicked */
  onAgentQueueToggle?: () => void;
  /** Whether the agent queue panel is currently open */
  agentQueueOpen?: boolean;
  /** Number of pending agent approvals */
  pendingApprovals?: number;
  /** Callback when pending approvals indicator is clicked */
  onPendingApprovalsClick?: () => void;
  /** Whether the approvals panel is currently open */
  approvalsPanelOpen?: boolean;
  /** Whether the DevTools panel is collapsed */
  devToolsCollapsed?: boolean;
  /** Callback when DevTools toggle is clicked */
  onDevToolsToggle?: () => void;
  /** Number of problems/errors in DevTools */
  problemCount?: number;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

export function StatusBar({
  status = "Ready",
  connectionStatus,
  agentStatus,
  modelName,
  tokenCount,
  userName,
  errorMessage,
  agentCount,
  onAgentQueueToggle,
  agentQueueOpen = false,
  pendingApprovals,
  onPendingApprovalsClick,
  approvalsPanelOpen = false,
  devToolsCollapsed = true,
  onDevToolsToggle,
  problemCount,
  className,
}: StatusBarProps) {
  // Check if we're in dev mode
  const isDev = import.meta.env.DEV;

  return (
    <div
      data-testid="status-bar"
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-between px-4 py-1",
        "bg-gray-100 dark:bg-gray-900",
        "border-t border-gray-200 dark:border-gray-700",
        "text-xs text-gray-500 dark:text-gray-400",
        className,
      )}
    >
      {/* Left section: Status and connection */}
      <div className="flex items-center gap-4">
        {/* Connection indicator */}
        {connectionStatus && (
          <span
            data-testid="connection-indicator"
            role="status"
            className={cn(
              "w-2 h-2 rounded-full",
              connectionStatus === "connected" && "bg-green-500",
              connectionStatus === "disconnected" && "bg-red-500",
              connectionStatus === "connecting" && "bg-yellow-500",
              connectionStatus === "error" && "bg-red-500",
            )}
            aria-label={`Connection status: ${connectionStatus}`}
          />
        )}

        {/* Status text */}
        <span>{status}</span>

        {/* Agent status */}
        {agentStatus && (
          <span
            data-testid="agent-status"
            className="text-primary-600 dark:text-primary-400"
          >
            {agentStatus}
          </span>
        )}

        {/* Model indicator */}
        {modelName && (
          <span
            data-testid="model-indicator"
            className="flex items-center gap-1"
          >
            <Cpu size={12} aria-hidden="true" />
            <span>{modelName}</span>
          </span>
        )}

        {/* Token count */}
        {tokenCount !== undefined && (
          <span data-testid="token-count" className="flex items-center gap-1">
            <Hash size={12} aria-hidden="true" />
            <span>{tokenCount.toLocaleString()} tokens</span>
          </span>
        )}

        {/* User indicator */}
        {userName && (
          <span
            data-testid="user-indicator"
            className="flex items-center gap-1"
          >
            <User size={12} aria-hidden="true" />
            <span>{userName}</span>
          </span>
        )}

        {/* Error message */}
        {errorMessage && (
          <span
            data-testid="error-message"
            className="text-red-500 dark:text-red-400"
            role="alert"
          >
            {errorMessage}
          </span>
        )}

        {/* Dev-mode shell toggle */}
        <FeatureFlagToggle isDev={isDev} />

        {/* Agent queue toggle button */}
        {agentCount !== undefined && agentCount > 0 && onAgentQueueToggle && (
          <button
            data-testid="agent-queue-toggle"
            type="button"
            onClick={onAgentQueueToggle}
            aria-label={`Toggle agent task queue (${agentCount} agents)`}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded",
              "hover:bg-gray-200 dark:hover:bg-gray-700",
              "transition-colors",
              agentQueueOpen && "bg-primary-100 dark:bg-primary-900/30",
            )}
          >
            <ListTodo size={12} aria-hidden="true" />
            <span className="font-medium">{agentCount}</span>
          </button>
        )}

        {/* Pending approvals indicator */}
        {pendingApprovals !== undefined &&
          pendingApprovals > 0 &&
          onPendingApprovalsClick && (
            <button
              data-testid="pending-approvals-indicator"
              type="button"
              onClick={onPendingApprovalsClick}
              aria-label={`View ${pendingApprovals} pending agent approval${pendingApprovals === 1 ? "" : "s"}`}
              className={cn(
                "flex items-center gap-1 px-2 py-0.5 rounded",
                "transition-colors",
                approvalsPanelOpen
                  ? "bg-amber-200 dark:bg-amber-800/50"
                  : "bg-amber-100 dark:bg-amber-900/30",
                "hover:bg-amber-200 dark:hover:bg-amber-800/50",
              )}
            >
              <AlertTriangle
                size={12}
                className="text-amber-600 dark:text-amber-400"
                aria-hidden="true"
              />
              <span className="font-medium text-amber-700 dark:text-amber-300">
                {pendingApprovals} pending
              </span>
            </button>
          )}

        {/* DevTools toggle button */}
        {onDevToolsToggle && (
          <button
            data-testid="devtools-toggle"
            type="button"
            onClick={onDevToolsToggle}
            aria-label={devToolsCollapsed ? "Open DevTools" : "Close DevTools"}
            aria-pressed={!devToolsCollapsed}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded",
              "hover:bg-gray-200 dark:hover:bg-gray-700",
              "transition-colors",
              !devToolsCollapsed && "bg-primary-100 dark:bg-primary-900/30",
            )}
          >
            <Terminal size={12} aria-hidden="true" />
            {problemCount !== undefined && problemCount > 0 && (
              <span
                data-testid="devtools-problem-count"
                className="min-w-[1rem] h-4 px-1 text-xs font-medium text-white bg-red-500 rounded-full flex items-center justify-center"
              >
                {problemCount > 99 ? "99+" : problemCount}
              </span>
            )}
          </button>
        )}
      </div>

      {/* Right section: Keyboard shortcuts */}
      <div className="flex items-center gap-4">
        <span className="hidden sm:inline">⌘K Command Palette</span>
        <span className="hidden sm:inline">⌘/ Toggle Canvas</span>
        <span className="hidden sm:inline">⌘⇧I DevTools</span>
      </div>
    </div>
  );
}

/**
 * StatusBar Component
 *
 * Bottom status bar showing application state, connection status,
 * agent status, model info, token count, and keyboard shortcuts.
 * Extracted from StudioShellLayout for maintainability.
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
import { useRef, useEffect } from "react";
import {
  Cpu,
  Hash,
  ListTodo,
  AlertTriangle,
  Terminal,
  Database,
} from "lucide-react";
import { useReducedMotion } from "motion/react";
import { cn } from "../utils/cn";
import { FeatureFlagToggle } from "./FeatureFlagToggle";
import type { ConnectionStatus } from "../types/connection";
import type {
  ModelProvider,
  TokenBreakdown,
  CostBreakdown,
} from "../types/session";
import type { KBStatusValue, KBContextStats } from "../types/api";

import { Button, Badge } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export interface StatusBarProps {
  /**
   * Override status message (optional).
   * If not provided, status is derived from context:
   * - agentStatus takes priority if present
   * - Otherwise derived from connectionStatus + activity
   * @deprecated Prefer letting StatusBar derive context automatically
   */
  status?: string;
  /** Connection status for WebSocket/API */
  connectionStatus?: ConnectionStatus;
  /** Number of reconnection attempts (for showing reconnection progress) */
  reconnectAttempts?: number;
  /** Agent status message (e.g., "Thinking...") - takes priority over derived status */
  agentStatus?: string;
  /** Model name (e.g., "claude-3-opus") */
  modelName?: string;
  /** Model provider for icon display */
  modelProvider?: ModelProvider;
  /** Token count for current session */
  tokenCount?: number;
  /** Token breakdown (input/output) for enhanced display */
  tokenBreakdown?: TokenBreakdown;
  /** Cost breakdown for estimated cost display */
  costBreakdown?: CostBreakdown;
  /**
   * Current user name
   * @deprecated User info is displayed in the top-bar - this is redundant
   */
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
  /** Knowledge Base status (ready, misconfigured, unavailable) */
  kbStatus?: KBStatusValue;
  /** Knowledge Base status message (e.g., configuration guidance) */
  kbStatusMessage?: string;
  /** Knowledge Base context stats (refs count, token usage) */
  kbContextStats?: KBContextStats;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Format cost for display
 */
function formatCost(costUsd: number): string {
  if (costUsd < 0.01) {
    return `$${costUsd.toFixed(4)}`;
  }
  return `$${costUsd.toFixed(2)}`;
}

/**
 * Build token breakdown tooltip content
 */
function buildTokenTooltip(
  tokenCount: number,
  tokenBreakdown?: TokenBreakdown,
  costBreakdown?: CostBreakdown,
): string {
  const lines: string[] = [];

  if (tokenBreakdown) {
    lines.push(`Input: ${tokenBreakdown.promptTokens.toLocaleString()} tokens`);
    lines.push(
      `Output: ${tokenBreakdown.completionTokens.toLocaleString()} tokens`,
    );
    lines.push(`Total: ${tokenBreakdown.totalTokens.toLocaleString()} tokens`);
  } else {
    lines.push(`Session tokens: ${tokenCount.toLocaleString()}`);
  }

  if (costBreakdown) {
    lines.push(`Estimated cost: ${formatCost(costBreakdown.estimatedCostUsd)}`);

    if (costBreakdown.byModel) {
      lines.push("");
      lines.push("By model:");
      for (const [model, data] of Object.entries(costBreakdown.byModel)) {
        lines.push(
          `  ${model}: ${data.tokens.toLocaleString()} tokens (${formatCost(data.cost)})`,
        );
      }
    }
  }

  return lines.join("\n");
}

/**
 * Get provider-specific color class
 * Uses step 11 for high-contrast text per Radix design system
 */
function getProviderColorClass(provider: ModelProvider): string {
  switch (provider) {
    case "openai":
      return "text-success-11";
    case "anthropic":
      return "text-grafana-11";
    case "google":
      return "text-primary-11";
    case "azure":
      return "text-primary-11";
    default:
      return "";
  }
}

/**
 * Derive contextual status based on current activity.
 * Priority order:
 * 1. agentStatus (if provided) - e.g., "Thinking...", "Analyzing..."
 * 2. Activity-based status (agents running, approvals pending)
 * 3. Connection-derived status
 * 4. "Idle" as fallback
 */
function deriveContextualStatus(
  connectionStatus?: ConnectionStatus,
  agentStatus?: string,
  agentCount?: number,
  pendingApprovals?: number,
): string {
  // Priority 1: Agent status takes precedence
  if (agentStatus) {
    return agentStatus;
  }

  // Priority 2: Activity-based status
  const activities: string[] = [];

  if (agentCount && agentCount > 0) {
    activities.push(
      `${agentCount} agent${agentCount === 1 ? "" : "s"} running`,
    );
  }

  if (pendingApprovals && pendingApprovals > 0) {
    activities.push(
      `${pendingApprovals} approval${pendingApprovals === 1 ? "" : "s"} needed`,
    );
  }

  if (activities.length > 0) {
    return activities.join(" · ");
  }

  // Priority 3: Connection-derived status
  switch (connectionStatus) {
    case "connected":
      return "Connected";
    case "connecting":
      return "Connecting...";
    case "disconnected":
      return "Disconnected";
    case "error":
      return "Connection Error";
    default:
      // Priority 4: Fallback
      return "Idle";
  }
}

/**
 * Get KB status indicator color class
 */
function getKBStatusValueColor(status: KBStatusValue): string {
  switch (status) {
    case "ready":
      return "bg-success-9";
    case "misconfigured":
      return "bg-warning-9";
    case "unavailable":
      return "bg-neutral-4";
  }
}

/**
 * Build KB tooltip message
 */
function buildKBTooltip(
  status: KBStatusValue,
  statusMessage?: string,
  contextStats?: KBContextStats,
): string {
  const lines: string[] = [];

  // Status line
  switch (status) {
    case "ready":
      lines.push("Knowledge Base: Ready");
      break;
    case "misconfigured":
      lines.push("Knowledge Base: Misconfigured");
      break;
    case "unavailable":
      lines.push("Knowledge Base: Unavailable");
      break;
  }

  // Add custom message if provided
  if (statusMessage) {
    lines.push(statusMessage);
  }

  // Add context stats if provided
  if (contextStats) {
    const usagePercent = Math.round(
      (contextStats.tokensUsed / contextStats.tokenBudget) * 100,
    );
    lines.push(
      `Context: ${contextStats.refsCount} refs, ${contextStats.tokensUsed.toLocaleString()}/${contextStats.tokenBudget.toLocaleString()} tokens (${usagePercent}%)`,
    );
  }

  return lines.join("\n");
}

export function StatusBar({
  status,
  connectionStatus,
  reconnectAttempts,
  agentStatus,
  modelName,
  modelProvider,
  tokenCount,
  tokenBreakdown,
  costBreakdown,
  userName: _userName, // Deprecated - ignored, user info is in top-bar
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
  kbStatus,
  kbStatusMessage,
  kbContextStats,
  className,
}: StatusBarProps) {
  // WCAG 2.2 AA: Respect user's reduced motion preference
  const prefersReducedMotion = useReducedMotion();

  // Ref for dynamic height tracking
  const statusBarRef = useRef<HTMLDivElement>(null);

  // Update CSS variable with actual height for overlay positioning
  useEffect(() => {
    if (!statusBarRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        document.documentElement.style.setProperty(
          "--statusbar-height",
          `${entry.contentRect.height}px`,
        );
      }
    });
    observer.observe(statusBarRef.current);
    return () => observer.disconnect();
  }, []);

  // Check if we're in dev mode
  const isDev = import.meta.env.DEV;

  // Derive contextual status from activity (ignore deprecated static status prop)
  const displayStatus =
    status ??
    deriveContextualStatus(
      connectionStatus,
      agentStatus,
      agentCount,
      pendingApprovals,
    );

  return (
    <div
      ref={statusBarRef}
      data-testid="status-bar"
      role="status"
      aria-live="polite"
      className={cn(
        "flex items-center justify-between px-4 py-1",
        "bg-neutral-2",
        "border-t border-neutral-5",
        "text-xs text-neutral-11",
        className,
      )}
    >
      {/* Left section: Status and connection */}
      <div className="flex items-center gap-4 flex-wrap min-w-0">
        {/* Connection indicator */}
        {connectionStatus && (
          <span
            data-testid="connection-indicator"
            role="status"
            title={`Connection: ${connectionStatus}`}
            className={cn(
              "w-2 h-2 rounded-full cursor-help",
              connectionStatus === "connected" && "bg-success-9",
              connectionStatus === "disconnected" && "bg-error-9",
              connectionStatus === "connecting" && "bg-warning-9",
              connectionStatus === "error" && "bg-error-9",
            )}
            aria-label={`Connection status: ${connectionStatus}`}
          />
        )}

        {/* Reconnection indicator - shows when reconnecting with attempt count */}
        {connectionStatus === "connecting" &&
          reconnectAttempts !== undefined &&
          reconnectAttempts > 0 && (
            <span
              data-testid="reconnecting-indicator"
              role="status"
              aria-label={`Reconnecting, attempt ${reconnectAttempts}`}
              className={cn(
                "flex items-center gap-1 text-warning-11",
                !prefersReducedMotion && "animate-pulse",
              )}
            >
              <span>Reconnecting ({reconnectAttempts})...</span>
            </span>
          )}

        {/* Status text - context-aware, derived from activity */}
        <span data-testid="status-text">{displayStatus}</span>

        {/* Model indicator with provider color */}
        {modelName && (
          <span
            data-testid="model-indicator"
            title={`Model: ${modelName}${modelProvider ? ` (${modelProvider})` : ""}`}
            className={cn(
              "flex items-center gap-1 cursor-help",
              modelProvider && getProviderColorClass(modelProvider),
            )}
          >
            <Cpu size={12} aria-hidden="true" />
            <span>{modelName}</span>
          </span>
        )}

        {/* Token count with breakdown and cost tooltip */}
        {tokenCount !== undefined && (
          <span
            data-testid="token-count"
            title={buildTokenTooltip(tokenCount, tokenBreakdown, costBreakdown)}
            className="flex items-center gap-1 cursor-help"
          >
            <Hash size={12} aria-hidden="true" />
            <span>
              {tokenCount.toLocaleString()} tokens
              {costBreakdown && (
                <span className="ml-1 text-neutral-11">
                  ({formatCost(costBreakdown.estimatedCostUsd)})
                </span>
              )}
            </span>
          </span>
        )}

        {/* User indicator REMOVED - redundant with top-bar (userName prop deprecated) */}

        {/* Knowledge Base status indicator */}
        {kbStatus && (
          <span
            role="status"
            aria-label={`Knowledge Base status: ${kbStatus}`}
            title={buildKBTooltip(kbStatus, kbStatusMessage, kbContextStats)}
            className="flex items-center gap-1.5 cursor-help"
          >
            <span
              data-testid="kb-status-indicator"
              className={cn(
                "w-2 h-2 rounded-full",
                getKBStatusValueColor(kbStatus),
              )}
            />
            <Database
              size={12}
              aria-hidden="true"
              className="text-neutral-11"
            />
            <span>KB</span>
            {kbContextStats && (
              <span
                data-testid="kb-context-stats"
                title={`Context usage: ${Math.round((kbContextStats.tokensUsed / kbContextStats.tokenBudget) * 100)}%`}
                className="text-neutral-11"
              >
                {kbContextStats.refsCount} refs ·{" "}
                {kbContextStats.tokensUsed.toLocaleString()}
              </span>
            )}
          </span>
        )}

        {/* Error message */}
        {errorMessage && (
          <span
            data-testid="error-message"
            className="text-error-11"
            role="alert"
          >
            {errorMessage}
          </span>
        )}

        {/* Dev-mode shell toggle */}
        <FeatureFlagToggle isDev={isDev} />

        {/* Agent queue toggle button */}
        {agentCount !== undefined && agentCount > 0 && onAgentQueueToggle && (
          <Button
            variant="ghost"
            data-testid="agent-queue-toggle"
            type="button"
            onClick={onAgentQueueToggle}
            title={`Toggle agent task queue (${agentCount} background agents)`}
            aria-label={`Toggle agent task queue (${agentCount} agents)`}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded",
              "hover:bg-neutral-3",
              !prefersReducedMotion && "transition-colors",
              agentQueueOpen && "bg-primary-3 bg-primary-4",
            )}>
            <ListTodo size={12} aria-hidden="true" />
            <span className="font-medium">{agentCount}</span>
          </Button>
        )}

        {/* Pending approvals indicator */}
        {pendingApprovals !== undefined &&
          pendingApprovals > 0 &&
          onPendingApprovalsClick && (
            <Button
              variant="ghost"
              data-testid="pending-approvals-indicator"
              type="button"
              onClick={onPendingApprovalsClick}
              title={`${pendingApprovals} pending agent approval${pendingApprovals === 1 ? "" : "s"} - click to review`}
              aria-label={`View ${pendingApprovals} pending agent approval${pendingApprovals === 1 ? "" : "s"}`}
              className={cn(
                "flex items-center gap-1 px-2 py-0.5 rounded",
                !prefersReducedMotion && "transition-colors",
                approvalsPanelOpen
                  ? "bg-warning-6 dark:bg-warning-a6"
                  : "bg-warning-3 dark:bg-warning-a4",
                "hover:bg-warning-6 dark:hover:bg-warning-a6",
              )}>
              <AlertTriangle
                size={12}
                className="text-warning-11"
                aria-hidden="true"
              />
              <span className="font-medium text-warning-11">
                {pendingApprovals} pending
              </span>
            </Button>
          )}

        {/* DevTools toggle button */}
        {onDevToolsToggle && (
          <Button
            variant="ghost"
            data-testid="devtools-toggle"
            type="button"
            onClick={onDevToolsToggle}
            title={`DevTools: ${devToolsCollapsed ? "Open" : "Close"} (⌘⇧I)`}
            aria-label={devToolsCollapsed ? "Open DevTools" : "Close DevTools"}
            aria-pressed={!devToolsCollapsed}
            className={cn(
              "flex items-center gap-1 px-2 py-0.5 rounded",
              "hover:bg-neutral-3",
              !prefersReducedMotion && "transition-colors",
              !devToolsCollapsed && "bg-primary-3 bg-primary-4",
            )}>
            <Terminal size={12} aria-hidden="true" />
            {problemCount !== undefined && problemCount > 0 && (
              <Badge
                data-testid="devtools-problem-count"
                variant="error"
                size="sm"
                pill
                className="min-w-4 h-4 px-1 flex items-center justify-center"
              >
                {problemCount > 99 ? "99+" : problemCount}
              </Badge>
            )}
          </Button>
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

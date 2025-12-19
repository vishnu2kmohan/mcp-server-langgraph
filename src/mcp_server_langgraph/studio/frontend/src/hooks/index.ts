/**
 * Hooks Index
 *
 * Central export for all custom React hooks in the application.
 * Organized by category for easy discovery and import.
 */

// =============================================================================
// WebSocket Hooks (Real-time Communication)
// =============================================================================

export {
  useRealtimeSync,
  type UseRealtimeSyncOptions,
  type UseRealtimeSyncReturn,
} from "./useRealtimeSync";

export { useMCPWebSocket } from "./useMCPWebSocket";

export {
  useMCPTaskWebSocket,
  type MCPTask,
  type MCPTaskStatus,
  type UseMCPTaskWebSocketOptions,
  type UseMCPTaskWebSocketReturn,
} from "./useMCPTaskWebSocket";

export {
  useAuditWebSocket,
  type AuditEvent,
  type AuditFilter,
  type UseAuditWebSocketOptions,
  type UseAuditWebSocketReturn,
} from "./useAuditWebSocket";

export {
  useConnectionHealthWebSocket,
  type ConnectionHealth,
  type ConnectionStatus,
  type ConnectionSummary,
  type UseConnectionHealthWebSocketOptions,
  type UseConnectionHealthWebSocketReturn,
} from "./useConnectionHealthWebSocket";

export { useNotificationWebSocket } from "./useNotificationWebSocket";

export { useTraceWebSocket } from "./useTraceWebSocket";

// =============================================================================
// Connection Hooks
// =============================================================================

export { useMCPConnection } from "./useMCPConnection";

export { useConnectionHealth } from "./useConnectionHealth";

// =============================================================================
// Chat Hooks
// =============================================================================

export { useStreamingChat } from "./useStreamingChat";

export { useAutoSessionTitle } from "./useAutoSessionTitle";

export { useSessionAutoName } from "./useSessionAutoName";

// =============================================================================
// UI/UX Hooks
// =============================================================================

export { useDebounce } from "./useDebounce";

export { useKeyboardShortcuts } from "./useKeyboardShortcuts";

export { useTheme } from "./useTheme";

export { useOnboarding } from "./useOnboarding";

export { useFileUpload } from "./useFileUpload";

export { useVoiceInput } from "./useVoiceInput";

// =============================================================================
// PWA Hooks (Progressive Web App)
// =============================================================================

export { useOffline } from "./useOffline";

export { usePWAUpdate } from "./usePWAUpdate";

export { usePushNotifications } from "./usePushNotifications";

export { useBackgroundSync } from "./useBackgroundSync";

// =============================================================================
// Feature Hooks
// =============================================================================

export { useTierLimits } from "./useTierLimits";

export { useHeartMetricsTracker } from "./useHeartMetricsTracker";

export { useTraceToReactFlow } from "./useTraceToReactFlow";

export { useWorkflowExecution } from "./useWorkflowExecution";

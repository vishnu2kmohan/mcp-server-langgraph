/**
 * Toast ID Constants
 *
 * Centralized toast IDs for deduplication and consistency.
 * Using unique IDs prevents duplicate toasts when the same event fires multiple times.
 *
 * @see https://sonner.emilkowal.ski/toast#prevent-duplicate-toasts
 */

// =============================================================================
// Connection Health Toasts
// =============================================================================

/**
 * Generate a connection-specific toast ID for status updates.
 * Each connection gets its own ID to allow parallel status updates.
 */
export function getConnectionToastId(connectionName: string): string {
  return `conn-${connectionName}`;
}

/** Generic connection error toast ID */
export const TOAST_ID_CONNECTION_ERROR = "conn-error";

// =============================================================================
// Cost Tracking Toasts
// =============================================================================

/** Budget warning toast ID (prevents duplicate warnings) */
export const TOAST_ID_BUDGET_WARNING = "budget-warning";

// =============================================================================
// Session Management Toasts
// =============================================================================

/** Session deleted toast ID */
export const TOAST_ID_SESSION_DELETED = "session-deleted";

/** Session created toast ID */
export const TOAST_ID_SESSION_CREATED = "session-created";

/** Session renamed toast ID */
export const TOAST_ID_SESSION_RENAMED = "session-renamed";

// =============================================================================
// Model/Config Toasts
// =============================================================================

/** Failed to load models toast ID */
export const TOAST_ID_MODELS_LOAD_FAILED = "models-load-failed";

// =============================================================================
// Application State Toasts
// =============================================================================

/** Application update required toast ID */
export const TOAST_ID_APP_UPDATE_REQUIRED = "app-update-required";

/** Chat error toast ID */
export const TOAST_ID_CHAT_ERROR = "chat-error";

/** Export error/success toast ID */
export const TOAST_ID_EXPORT = "export";

/** Voice input error toast ID */
export const TOAST_ID_VOICE_ERROR = "voice-error";

/** File upload error toast ID */
export const TOAST_ID_FILE_ERROR = "file-error";

/** URL fetch error toast ID */
export const TOAST_ID_URL_FETCH_ERROR = "url-fetch-error";

/** Rating error toast ID */
export const TOAST_ID_RATING_ERROR = "rating-error";

// =============================================================================
// Feedback Toasts
// =============================================================================

/** Response feedback toast ID */
export const TOAST_ID_FEEDBACK = "feedback";

/** Session suggestion toast ID (create new session prompt) */
export const TOAST_ID_SESSION_SUGGEST = "session-suggest";

// =============================================================================
// Conversation Action Toasts
// =============================================================================

/** Conversation cleared toast ID */
export const TOAST_ID_CONVERSATION_CLEAR = "conversation-clear";

/** Copy to clipboard toast ID */
export const TOAST_ID_COPY = "copy";

/** Session refreshed toast ID */
export const TOAST_ID_SESSION_REFRESH = "session-refresh";

/** Hallucination report toast ID */
export const TOAST_ID_HALLUCINATION_REPORT = "hallucination-report";

/** Goal tracking toast ID */
export const TOAST_ID_GOAL = "goal";

// =============================================================================
// Alert Toasts
// =============================================================================

/** Critical alert toast ID generator */
export function getCriticalAlertToastId(alertId: string): string {
  return `alert-critical-${alertId}`;
}

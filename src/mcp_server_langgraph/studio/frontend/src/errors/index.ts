/**
 * Error Classification System
 *
 * A comprehensive error taxonomy and classification system for
 * consistent error handling across the application.
 *
 * Features:
 * - Typed error categories (network, auth, validation, server, etc.)
 * - Error classification from various sources (fetch, axios, websocket)
 * - Contextual recovery suggestions
 * - User-friendly error messages
 * - Recovery action recommendations
 */

// Error Types
export {
  type ErrorCategory,
  type ErrorCode,
  type ClassifiedError,
  type CreateClassifiedErrorOptions,
  ERROR_CATEGORIES,
  ERROR_CODES,
  isRecoverable,
  getErrorCategory,
  createClassifiedError,
  isNetworkError,
  isAuthError,
  isValidationError,
  isServerError,
  isRateLimitError,
} from "./ErrorTypes";

// Error Classifier
export {
  type ErrorClassificationOptions,
  classifyError,
  classifyFetchError,
  classifyAxiosError,
  classifyWebSocketError,
} from "./ErrorClassifier";

// Error Suggestions
export {
  type SuggestionContext,
  type RecoveryActionType,
  type RecoveryAction,
  getSuggestions,
  getUserMessage,
  getRecoveryActions,
} from "./ErrorSuggestions";

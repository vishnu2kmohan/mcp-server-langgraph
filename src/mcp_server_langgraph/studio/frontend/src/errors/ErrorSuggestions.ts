/**
 * ErrorSuggestions
 *
 * Provides contextual recovery suggestions based on error classification.
 * Suggestions are tailored to:
 * - Error category
 * - User persona
 * - Current context (page, action)
 * - Error-specific details (retryAfter, field, etc.)
 */

import { type ClassifiedError, type ErrorCategory } from "./ErrorTypes";

/**
 * Context for generating suggestions
 */
export interface SuggestionContext {
  /** Current page path */
  currentPage?: string;
  /** Last user action */
  lastAction?: string;
  /** User persona */
  persona?: string;
  /** Is on corporate network */
  isCorporateNetwork?: boolean;
  /** Has SSO enabled */
  hasSSOEnabled?: boolean;
  /** Has status page */
  hasStatusPage?: boolean;
  /** User has hit rate limits frequently */
  frequentRateLimits?: boolean;
}

/**
 * Recovery action type
 */
export type RecoveryActionType =
  | "retry"
  | "login"
  | "dismiss"
  | "report"
  | "wait"
  | "refresh"
  | "contact";

/**
 * Recovery action
 */
export interface RecoveryAction {
  /** Action type */
  type: RecoveryActionType;
  /** Display label */
  label: string;
  /** Optional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Base suggestions by error category
 */
const BASE_SUGGESTIONS: Record<ErrorCategory, string[]> = {
  network: [
    "Check your internet connection",
    "Try again in a few moments",
    "Refresh the page",
  ],
  authentication: [
    "Log in again",
    "Your session may have expired",
    "Clear browser cookies and try again",
  ],
  authorization: [
    "You don't have permission to perform this action",
    "Contact your administrator for access",
    "Check if you're using the correct account",
  ],
  validation: [
    "Check your input for errors",
    "Review the required fields",
    "Ensure all values are in the correct format",
  ],
  server: [
    "Try again in a few minutes",
    "Our servers are experiencing issues",
    "If the problem persists, contact support",
  ],
  client: [
    "Try refreshing the page",
    "Check if the resource still exists",
    "Clear your browser cache",
  ],
  timeout: [
    "The request took too long. Please retry.",
    "Try again with a smaller request",
    "Check your connection speed",
  ],
  quota: [
    "You've reached the rate limit. Please wait.",
    "Try again in a moment",
    "Consider reducing request frequency",
  ],
  unknown: [
    "Try refreshing the page",
    "If the problem persists, contact support",
    "Clear browser cache and try again",
  ],
};

/**
 * User-friendly messages by error category
 */
const USER_MESSAGES: Record<ErrorCategory, string> = {
  network:
    "We're having trouble connecting. Please check your internet connection.",
  authentication: "Your session has expired. Please log in again.",
  authorization: "You don't have permission to access this resource.",
  validation: "Please check your input and try again.",
  server:
    "We're experiencing a temporary problem. Please try again in a few minutes.",
  client: "Something went wrong. Please try again.",
  timeout: "The request took too long. Please try again.",
  quota: "You've made too many requests. Please wait a moment and try again.",
  unknown: "Something unexpected happened. Please try again or contact support.",
};

/**
 * Format milliseconds to human-readable duration
 */
function formatDuration(ms: number): string {
  const seconds = Math.ceil(ms / 1000);
  if (seconds <= 90) {
    return `${seconds} seconds`;
  }
  const minutes = Math.ceil(seconds / 60);
  return `${minutes} minute${minutes > 1 ? "s" : ""}`;
}

/**
 * Get suggestions for an error
 */
export function getSuggestions(
  error: ClassifiedError,
  context: SuggestionContext = {}
): string[] {
  const suggestions: string[] = [];
  const base = BASE_SUGGESTIONS[error.category] ?? BASE_SUGGESTIONS.unknown;

  // Start with base suggestions
  suggestions.push(...base);

  // Add context-specific suggestions
  switch (error.category) {
    case "network":
      if (context.isCorporateNetwork) {
        suggestions.push("Check your VPN connection");
      }
      break;

    case "authentication":
      if (context.hasSSOEnabled) {
        suggestions.push("Try logging in via SSO");
      }
      break;

    case "server":
      if (context.hasStatusPage) {
        suggestions.push("Check our status page for updates");
      }
      if (context.persona === "admin") {
        suggestions.push("Check the application logs for more details");
        suggestions.push("Review the trace ID in monitoring tools");
      }
      break;

    case "timeout":
      if (error.context?.operation) {
        suggestions.push("Try with a smaller batch or simpler request");
      }
      break;

    case "quota":
      if (error.retryAfter) {
        const duration = formatDuration(error.retryAfter);
        suggestions.unshift(`Wait ${duration} before trying again`);
      }
      if (context.frequentRateLimits) {
        suggestions.push("Consider upgrading your plan for higher limits");
      }
      break;

    case "validation":
      if (error.context?.field) {
        const field = String(error.context.field);
        suggestions.unshift(`Check the ${field} field for errors`);
      }
      break;
  }

  // Add page-specific suggestions
  if (context.currentPage?.includes("/workflow")) {
    if (error.category === "server" || error.category === "timeout") {
      suggestions.push("Try saving your workflow before retrying");
    }
  }

  // Filter out technical jargon for non-admin personas
  if (context.persona === "bob") {
    return suggestions.filter(
      (s) =>
        !s.toLowerCase().includes("trace") &&
        !s.toLowerCase().includes("debug") &&
        !s.toLowerCase().includes("logs")
    );
  }

  return suggestions;
}

/**
 * Get user-friendly message for an error
 */
export function getUserMessage(error: ClassifiedError): string {
  // Use custom user message if provided
  if (error.userMessage) {
    return error.userMessage;
  }

  return USER_MESSAGES[error.category] ?? USER_MESSAGES.unknown;
}

/**
 * Get recovery actions for an error
 */
export function getRecoveryActions(error: ClassifiedError): RecoveryAction[] {
  const actions: RecoveryAction[] = [];

  // Primary action based on category
  switch (error.category) {
    case "network":
    case "server":
    case "timeout":
      actions.push({ type: "retry", label: "Try Again" });
      break;

    case "authentication":
      actions.push({ type: "login", label: "Log In" });
      break;

    case "quota":
      if (error.retryAfter) {
        actions.push({
          type: "wait",
          label: `Wait ${formatDuration(error.retryAfter)}`,
          metadata: { waitTime: error.retryAfter },
        });
      }
      actions.push({ type: "retry", label: "Try Again" });
      break;

    case "client":
      actions.push({ type: "refresh", label: "Refresh Page" });
      break;
  }

  // Report action for server errors
  if (error.category === "server" || error.category === "unknown") {
    actions.push({ type: "report", label: "Report Issue" });
  }

  // Always add dismiss action last
  actions.push({ type: "dismiss", label: "Dismiss" });

  return actions;
}

export default {
  getSuggestions,
  getUserMessage,
  getRecoveryActions,
};

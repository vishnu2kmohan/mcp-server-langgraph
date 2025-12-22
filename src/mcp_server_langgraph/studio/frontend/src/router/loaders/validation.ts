/**
 * Loader Validation
 *
 * Runtime validation for loader data responses.
 * Provides type-safe validation using type guards.
 *
 * Note: This can be upgraded to Zod for more powerful validation
 * while maintaining the same API surface.
 *
 * Usage:
 * ```tsx
 * const result = validateSession(response);
 * if (result.success) {
 *   const session = result.data;
 * } else {
 *   console.error(result.errors);
 * }
 * ```
 */

import { devLogger } from "../../utils/devLogger";

const logger = devLogger.withPrefix("[validation]");

// =============================================================================
// Types
// =============================================================================

export interface ValidationError {
  field: string;
  message: string;
  value?: unknown;
}

export type ValidationResult<T> =
  | { success: true; data: T; warnings?: string[] }
  | { success: false; errors: ValidationError[] };

/** API Session format */
interface APISession {
  id: string;
  name?: string;
  status?: string;
  created_at: string;
  updated_at: string;
  config?: Record<string, unknown>;
}

/** API Message format */
interface APIMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

/** Sessions API response */
interface SessionsResponse {
  items: APISession[];
}

/** Messages API response */
interface MessagesResponse {
  items: APIMessage[];
}

// =============================================================================
// Validation Helpers
// =============================================================================

function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isArray(value: unknown): value is unknown[] {
  return Array.isArray(value);
}

function isString(value: unknown): value is string {
  return typeof value === "string";
}

// =============================================================================
// Session Validation
// =============================================================================

/**
 * Validate a session object from the API
 */
export function validateSession(value: unknown): ValidationResult<APISession> {
  const errors: ValidationError[] = [];

  if (value === null || value === undefined) {
    return {
      success: false,
      errors: [{ field: "root", message: "Value is null or undefined" }],
    };
  }

  if (!isObject(value)) {
    return {
      success: false,
      errors: [{ field: "root", message: `Expected object, got ${typeof value}` }],
    };
  }

  // Required: id (string)
  if (!isString(value.id)) {
    errors.push({
      field: "id",
      message: "Missing or invalid 'id' field",
      value: value.id,
    });
  }

  // Required: created_at (string)
  if (!isString(value.created_at)) {
    errors.push({
      field: "created_at",
      message: "Missing or invalid 'created_at' field",
      value: value.created_at,
    });
  }

  // Required: updated_at (string)
  if (!isString(value.updated_at)) {
    errors.push({
      field: "updated_at",
      message: "Missing or invalid 'updated_at' field",
      value: value.updated_at,
    });
  }

  // Optional: name (string)
  if (value.name !== undefined && !isString(value.name)) {
    errors.push({
      field: "name",
      message: "Invalid 'name' field (expected string)",
      value: value.name,
    });
  }

  // Optional: status (string)
  if (value.status !== undefined && !isString(value.status)) {
    errors.push({
      field: "status",
      message: "Invalid 'status' field (expected string)",
      value: value.status,
    });
  }

  if (errors.length > 0) {
    logger.warn("Session validation failed", { errors, value });
    return { success: false, errors };
  }

  return {
    success: true,
    data: value as unknown as APISession,
  };
}

// =============================================================================
// Message Validation
// =============================================================================

const VALID_ROLES = ["user", "assistant", "system"];

/**
 * Validate a message object from the API
 */
export function validateMessage(value: unknown): ValidationResult<APIMessage> {
  const errors: ValidationError[] = [];

  if (!isObject(value)) {
    return {
      success: false,
      errors: [{ field: "root", message: "Expected object" }],
    };
  }

  // Required: id (string)
  if (!isString(value.id)) {
    errors.push({
      field: "id",
      message: "Missing or invalid 'id' field",
      value: value.id,
    });
  }

  // Required: role (user | assistant | system)
  if (!isString(value.role) || !VALID_ROLES.includes(value.role)) {
    errors.push({
      field: "role",
      message: `Invalid 'role' field (expected one of: ${VALID_ROLES.join(", ")})`,
      value: value.role,
    });
  }

  // Required: content (string)
  if (!isString(value.content)) {
    errors.push({
      field: "content",
      message: "Missing or invalid 'content' field",
      value: value.content,
    });
  }

  // Required: created_at (string)
  if (!isString(value.created_at)) {
    errors.push({
      field: "created_at",
      message: "Missing or invalid 'created_at' field",
      value: value.created_at,
    });
  }

  if (errors.length > 0) {
    return { success: false, errors };
  }

  return {
    success: true,
    data: value as unknown as APIMessage,
  };
}

/**
 * Validate an array of messages, returning valid ones with warnings
 */
export function validateMessages(
  value: unknown,
): ValidationResult<APIMessage[]> {
  if (!isArray(value)) {
    return {
      success: false,
      errors: [{ field: "root", message: "Expected array" }],
    };
  }

  const validMessages: APIMessage[] = [];
  const warnings: string[] = [];

  for (let i = 0; i < value.length; i++) {
    const result = validateMessage(value[i]);
    if (result.success) {
      validMessages.push(result.data);
    } else {
      warnings.push(`Message at index ${i} is invalid: ${result.errors[0]?.message}`);
    }
  }

  return {
    success: true,
    data: validMessages,
    warnings: warnings.length > 0 ? warnings : undefined,
  };
}

// =============================================================================
// Response Validation
// =============================================================================

/**
 * Validate sessions API response
 */
export function validateSessionsResponse(
  value: unknown,
): ValidationResult<SessionsResponse> {
  if (!isObject(value)) {
    return {
      success: false,
      errors: [{ field: "root", message: "Expected object" }],
    };
  }

  if (!isArray(value.items)) {
    return {
      success: false,
      errors: [{ field: "items", message: "Missing or invalid 'items' array" }],
    };
  }

  const validSessions: APISession[] = [];
  const warnings: string[] = [];

  for (let i = 0; i < value.items.length; i++) {
    const result = validateSession(value.items[i]);
    if (result.success) {
      validSessions.push(result.data);
    } else {
      warnings.push(`Session at index ${i} is invalid`);
    }
  }

  return {
    success: true,
    data: { items: validSessions },
    warnings: warnings.length > 0 ? warnings : undefined,
  };
}

/**
 * Validate messages API response
 */
export function validateMessagesResponse(
  value: unknown,
): ValidationResult<MessagesResponse> {
  if (!isObject(value)) {
    return {
      success: false,
      errors: [{ field: "root", message: "Expected object" }],
    };
  }

  if (!isArray(value.items)) {
    return {
      success: false,
      errors: [{ field: "items", message: "Missing or invalid 'items' array" }],
    };
  }

  const messagesResult = validateMessages(value.items);
  if (!messagesResult.success) {
    return messagesResult as ValidationResult<MessagesResponse>;
  }

  return {
    success: true,
    data: { items: messagesResult.data },
    warnings: messagesResult.warnings,
  };
}

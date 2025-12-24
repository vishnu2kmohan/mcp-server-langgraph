/**
 * API Transforms
 *
 * Type-safe transformations between API (snake_case) and client (camelCase) formats.
 * Provides type guards and validation functions to ensure data integrity.
 *
 * Usage:
 * ```tsx
 * import { isApiSession, transformApiSessionToClient } from "../utils/apiTransforms";
 *
 * if (isApiSession(response.data)) {
 *   const clientSession = transformApiSessionToClient(response.data, []);
 * }
 * ```
 */
import type {
  ClientSession,
  SessionConfig,
  ChatMessage,
} from "../types/session";
import { devLogger } from "./devLogger";

const logger = devLogger.withPrefix("[apiTransforms]");

// =============================================================================
// Types
// =============================================================================

/**
 * API Session format (snake_case from backend)
 */
export interface ApiSession {
  id: string;
  name?: string;
  status?: string;
  created_at: string;
  updated_at: string;
  config?: ApiSessionConfig;
  organization_id?: string;
}

/**
 * API Session config format (snake_case from backend)
 */
export interface ApiSessionConfig {
  model?: string;
  modelName?: string;
  model_provider?: string;
  modelProvider?: string;
  temperature?: number;
  max_tokens?: number;
  maxTokens?: number;
  system_prompt?: string;
  systemPrompt?: string;
  [key: string]: unknown;
}

/**
 * Source citation from API (snake_case from backend)
 */
export interface ApiSourceCitation {
  title: string;
  url?: string | null;
  snippet?: string | null;
}

/**
 * API Message format (snake_case from backend)
 * Matches the generated MessageResponse schema
 */
export interface ApiMessage {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string | null;
  sources?: ApiSourceCitation[] | null;
  thinking_content?: string | null;
  thinking_tokens?: number | null;
  model_name?: string | null;
}

/**
 * Validation result type
 */
export type ValidationResult<T> =
  | { success: true; data: T }
  | { success: false; error: string };

// =============================================================================
// Constants
// =============================================================================

/**
 * Default session config
 */
export const DEFAULT_SESSION_CONFIG: SessionConfig = {
  modelName: "gpt-4",
  modelProvider: "openai",
  temperature: 0.7,
  maxTokens: 4096,
};

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Type guard to check if a value is a valid ApiSession
 */
export function isApiSession(value: unknown): value is ApiSession {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const obj = value as Record<string, unknown>;

  // Required fields
  if (typeof obj.id !== "string") {
    return false;
  }

  if (typeof obj.created_at !== "string") {
    return false;
  }

  if (typeof obj.updated_at !== "string") {
    return false;
  }

  // Optional fields type checks
  if (obj.name !== undefined && typeof obj.name !== "string") {
    return false;
  }

  if (obj.status !== undefined && typeof obj.status !== "string") {
    return false;
  }

  if (
    obj.organization_id !== undefined &&
    typeof obj.organization_id !== "string"
  ) {
    return false;
  }

  return true;
}

/**
 * Validate API session and return typed result
 */
export function validateApiSession(
  value: unknown,
): ValidationResult<ApiSession> {
  if (isApiSession(value)) {
    return { success: true, data: value };
  }

  let error = "Invalid API session:";
  if (value === null || value === undefined) {
    error = "Value is null or undefined";
  } else if (typeof value !== "object") {
    error = `Expected object, got ${typeof value}`;
  } else {
    const obj = value as Record<string, unknown>;
    if (typeof obj.id !== "string") {
      error = "Missing or invalid 'id' field";
    } else if (typeof obj.created_at !== "string") {
      error = "Missing or invalid 'created_at' field";
    } else if (typeof obj.updated_at !== "string") {
      error = "Missing or invalid 'updated_at' field";
    }
  }

  return { success: false, error };
}

// =============================================================================
// Transform Functions
// =============================================================================

/**
 * Transform API config to client config format
 */
export function transformApiConfig(
  apiConfig: ApiSessionConfig | undefined,
): Partial<SessionConfig> {
  if (!apiConfig) return {};

  const config: Partial<SessionConfig> = {};

  // Map 'model' to 'modelName'
  if (typeof apiConfig.model === "string") {
    config.modelName = apiConfig.model;
  } else if (typeof apiConfig.modelName === "string") {
    config.modelName = apiConfig.modelName;
  }

  // Map 'model_provider' or 'modelProvider'
  if (typeof apiConfig.model_provider === "string") {
    config.modelProvider =
      apiConfig.model_provider as SessionConfig["modelProvider"];
  } else if (typeof apiConfig.modelProvider === "string") {
    config.modelProvider =
      apiConfig.modelProvider as SessionConfig["modelProvider"];
  }

  // Map 'max_tokens' to 'maxTokens'
  if (typeof apiConfig.max_tokens === "number") {
    config.maxTokens = apiConfig.max_tokens;
  } else if (typeof apiConfig.maxTokens === "number") {
    config.maxTokens = apiConfig.maxTokens;
  }

  // Temperature (same name in both)
  if (typeof apiConfig.temperature === "number") {
    config.temperature = apiConfig.temperature;
  }

  // System prompt
  if (typeof apiConfig.system_prompt === "string") {
    config.systemPrompt = apiConfig.system_prompt;
  } else if (typeof apiConfig.systemPrompt === "string") {
    config.systemPrompt = apiConfig.systemPrompt;
  }

  return config;
}

/**
 * Transform API session (snake_case) to ClientSession (camelCase)
 */
export function transformApiSessionToClient(
  apiSession: ApiSession,
  messages: ChatMessage[],
): ClientSession {
  const apiConfig = transformApiConfig(apiSession.config);

  return {
    id: apiSession.id,
    name: apiSession.name || "Untitled",
    config: {
      ...DEFAULT_SESSION_CONFIG,
      ...apiConfig,
    },
    messages,
    createdAt: new Date(apiSession.created_at).getTime(),
    updatedAt: new Date(apiSession.updated_at).getTime(),
    organizationId: apiSession.organization_id,
  };
}

/**
 * Safely transform an unknown value to ClientSession
 * Returns null if validation fails
 */
export function safeTransformToClientSession(
  value: unknown,
  messages: ChatMessage[],
): ClientSession | null {
  const validation = validateApiSession(value);
  if (!validation.success) {
    logger.warn("Invalid API session:", validation.error);
    return null;
  }
  return transformApiSessionToClient(validation.data, messages);
}

// =============================================================================
// Message Type Guards and Transforms
// =============================================================================

/**
 * Type guard to check if a value is a valid ApiMessage
 */
export function isApiMessage(value: unknown): value is ApiMessage {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const obj = value as Record<string, unknown>;

  // Required fields
  if (typeof obj.message_id !== "string") {
    return false;
  }

  if (typeof obj.role !== "string") {
    return false;
  }

  if (typeof obj.content !== "string") {
    return false;
  }

  return true;
}

/**
 * Client-side source citation format (camelCase)
 */
export interface Source {
  title: string;
  url?: string;
  snippet?: string;
}

/**
 * Client-side message format (camelCase)
 */
export interface ClientMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  sources?: Source[];
  thinkingContent?: string;
  thinkingTokens?: number;
  modelName?: string;
}

/**
 * Transform API message (snake_case) to client message (camelCase)
 */
export function transformApiMessageToClient(
  apiMessage: ApiMessage,
): ClientMessage {
  return {
    id: apiMessage.message_id,
    role: apiMessage.role,
    content: apiMessage.content,
    timestamp: apiMessage.timestamp
      ? new Date(apiMessage.timestamp).getTime()
      : 0,
    sources: apiMessage.sources
      ? apiMessage.sources.map((s) => ({
          title: s.title,
          url: s.url ?? undefined,
          snippet: s.snippet ?? undefined,
        }))
      : undefined,
    thinkingContent: apiMessage.thinking_content ?? undefined,
    thinkingTokens: apiMessage.thinking_tokens ?? undefined,
    modelName: apiMessage.model_name ?? undefined,
  };
}

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
import {
  DEFAULT_SESSION_CONFIG,
  type ClientSession,
  type SessionConfig,
  type ChatMessage,
} from "../types/session";
import { devLogger } from "./devLogger";

const logger = devLogger.withPrefix("[apiTransforms]");

// =============================================================================
// Types
// =============================================================================

/**
 * API Session format (snake_case from backend)
 * Also accepts camelCase variants for loader compatibility (ADR-0091 Phase 6)
 */
export interface ApiSession {
  id: string;
  name?: string;
  status?: string;
  // Accept both snake_case (backend API) and camelCase (loader output)
  created_at?: string;
  updated_at?: string;
  createdAt?: string;
  updatedAt?: string;
  config?: ApiSessionConfig;
  organization_id?: string;
  organizationId?: string;
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

// DEFAULT_SESSION_CONFIG is imported from types/session.ts (Single Source of Truth)
// Re-export for backwards compatibility with existing imports from this module
export { DEFAULT_SESSION_CONFIG };

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Type guard to check if a value is a valid ApiSession
 * ADR-0091 Phase 6: Accepts both snake_case (API) and camelCase (loader) formats
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

  // Accept either snake_case (created_at) or camelCase (createdAt)
  const hasCreatedAt =
    typeof obj.created_at === "string" || typeof obj.createdAt === "string";
  if (!hasCreatedAt) {
    return false;
  }

  // Accept either snake_case (updated_at) or camelCase (updatedAt)
  const hasUpdatedAt =
    typeof obj.updated_at === "string" || typeof obj.updatedAt === "string";
  if (!hasUpdatedAt) {
    return false;
  }

  // Optional fields type checks
  if (obj.name !== undefined && typeof obj.name !== "string") {
    return false;
  }

  if (obj.status !== undefined && typeof obj.status !== "string") {
    return false;
  }

  // Accept either snake_case or camelCase for organization_id
  if (
    obj.organization_id !== undefined &&
    typeof obj.organization_id !== "string"
  ) {
    return false;
  }

  if (
    obj.organizationId !== undefined &&
    typeof obj.organizationId !== "string"
  ) {
    return false;
  }

  return true;
}

/**
 * Validate API session and return typed result
 * ADR-0091 Phase 6: Accepts both snake_case and camelCase formats
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
    } else if (
      typeof obj.created_at !== "string" &&
      typeof obj.createdAt !== "string"
    ) {
      error = "Missing or invalid 'created_at' field";
    } else if (
      typeof obj.updated_at !== "string" &&
      typeof obj.updatedAt !== "string"
    ) {
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
 * Transform API session (snake_case or camelCase) to ClientSession (camelCase)
 * ADR-0091 Phase 6: Handles both formats from API and loader
 */
export function transformApiSessionToClient(
  apiSession: ApiSession,
  messages: ChatMessage[],
): ClientSession {
  const apiConfig = transformApiConfig(apiSession.config);

  // Support both snake_case (API) and camelCase (loader) timestamp formats
  const createdAtStr = apiSession.created_at ?? apiSession.createdAt ?? "";
  const updatedAtStr = apiSession.updated_at ?? apiSession.updatedAt ?? "";

  // Support both snake_case and camelCase organization_id
  const orgId = apiSession.organization_id ?? apiSession.organizationId;

  return {
    id: apiSession.id,
    name: apiSession.name || "Untitled",
    config: {
      ...DEFAULT_SESSION_CONFIG,
      ...apiConfig,
    },
    messages,
    createdAt: new Date(createdAtStr).getTime(),
    updatedAt: new Date(updatedAtStr).getTime(),
    organizationId: orgId,
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

// =============================================================================
// Artifact Type Guards and Transforms
// =============================================================================

import type { CanvasArtifact } from "../types/artifacts";

/**
 * API Artifact format (snake_case from backend)
 */
export interface ApiArtifact {
  id: string;
  type: string;
  title?: string;
  name?: string;
  description?: string;
  session_id: string;
  version: number;
  content: string;
  content_type: string;
  created_at: string;
  updated_at: string;
  edit_metadata?: {
    edited_by?: string;
    ai_confidence?: number;
    language?: string;
  };
  metadata?: Record<string, unknown>;
}

/**
 * Type guard to check if a value is a valid ApiArtifact
 */
export function isApiArtifact(value: unknown): value is ApiArtifact {
  if (value === null || value === undefined) {
    return false;
  }

  if (typeof value !== "object" || Array.isArray(value)) {
    return false;
  }

  const obj = value as Record<string, unknown>;

  // Required fields
  if (typeof obj.id !== "string") return false;
  if (typeof obj.content !== "string") return false;

  return true;
}

/**
 * Transform API artifact (snake_case) to client artifact (camelCase)
 * Handles both snake_case API responses and camelCase (pass-through)
 */
export function transformApiArtifactToClient(
  apiArtifact: ApiArtifact | Record<string, unknown>,
): CanvasArtifact {
  const artifact = apiArtifact as Record<string, unknown>;

  // Support both snake_case (API) and camelCase (already transformed)
  const sessionId =
    (artifact.session_id as string) ?? (artifact.sessionId as string) ?? "";
  const contentType =
    (artifact.content_type as string) ??
    (artifact.contentType as string) ??
    "code";
  const createdAt =
    (artifact.created_at as string) ?? (artifact.createdAt as string) ?? "";
  const updatedAt =
    (artifact.updated_at as string) ?? (artifact.updatedAt as string) ?? "";

  // Transform edit_metadata
  const editMeta =
    (artifact.edit_metadata as Record<string, unknown>) ??
    (artifact.editMetadata as Record<string, unknown>);
  const editMetadata = editMeta
    ? {
        editedBy: ((editMeta.edited_by as string) ??
          (editMeta.editedBy as string) ??
          "user") as "user" | "ai-suggestion" | "ai-generation",
        aiConfidence:
          (editMeta.ai_confidence as number) ??
          (editMeta.aiConfidence as number),
        language: (editMeta.language as string) ?? undefined,
      }
    : undefined;

  return {
    id: artifact.id as string,
    type: (artifact.type as CanvasArtifact["type"]) ?? "code",
    title: artifact.title as string | undefined,
    name: artifact.name as string | undefined,
    description: artifact.description as string | undefined,
    sessionId,
    version: (artifact.version as number) ?? 1,
    content: (artifact.content as string) ?? "",
    contentType: contentType as CanvasArtifact["contentType"],
    createdAt,
    updatedAt,
    editMetadata,
    metadata: artifact.metadata as Record<string, unknown> | undefined,
  };
}

/**
 * Transform array of API artifacts to client artifacts
 */
export function transformApiArtifactsToClient(
  apiArtifacts: unknown[],
): CanvasArtifact[] {
  return apiArtifacts
    .filter(isApiArtifact)
    .map((artifact) => transformApiArtifactToClient(artifact));
}

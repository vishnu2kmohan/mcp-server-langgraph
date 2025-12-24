/**
 * Canvas Loaders - Phase 2
 *
 * React Router loaders for StudioShell routes.
 * Loaders fetch data BEFORE rendering, preventing waterfall requests.
 *
 * Pattern: fetch-before-render (vs useEffect fetch-on-render)
 *
 * Usage in router:
 * {
 *   path: "chat/:sessionId",
 *   loader: chatLoader,
 *   element: <ChatPage />,
 * }
 */

import type { LoaderFunctionArgs } from "react-router";
import type { Session, ChatMessage } from "../../types";
import type { CanvasArtifact, ArtifactVersion } from "../../types/artifacts";
import { getAuthToken } from "../../utils/storage";
import {
  validateSession,
  validateMessages,
  validateSessionsResponse,
} from "./validation";
import { devLogger } from "../../utils/devLogger";
import {
  transformApiMessageToClient,
  isApiMessage,
  type ApiMessage,
} from "../../utils/apiTransforms";

const logger = devLogger.withPrefix("[canvasLoaders]");

// =============================================================================
// Types
// =============================================================================

export interface SessionsLoaderData {
  sessions: Session[];
  error?: string;
}

export interface ChatLoaderData {
  sessionId: string | null;
  session?: Session;
  messages: ChatMessage[];
  artifacts: CanvasArtifact[];
  error?: string;
}

export interface ArtifactLoaderData {
  artifact: CanvasArtifact | null;
  versions: ArtifactVersion[];
  error?: string;
}

// =============================================================================
// API Helpers
// =============================================================================

const API_BASE = "/api/v1";

/**
 * Get auth headers for API requests.
 * Uses centralized storage utility for consistent token access.
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  const token = getAuthToken();
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  return headers;
}

/**
 * Fetch JSON with auth headers.
 * Handles both authenticated and unauthenticated scenarios gracefully.
 */
async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url, {
      headers: getAuthHeaders(),
      credentials: "include", // Forward-auth (Keycloak SSO) support
    });
    if (!response.ok) {
      return null;
    }
    return response.json();
  } catch {
    return null;
  }
}

// =============================================================================
// Loaders
// =============================================================================

/**
 * Load list of sessions for the SessionNav panel
 */
export async function sessionsLoader(
  _args: LoaderFunctionArgs,
): Promise<SessionsLoaderData> {
  const result = await fetchJson<unknown>(`${API_BASE}/sessions?limit=50`);

  if (!result) {
    return {
      sessions: [],
      error: "Failed to load sessions",
    };
  }

  // Validate sessions response
  const validation = validateSessionsResponse(result);
  if (!validation.success) {
    logger.warn("Sessions validation failed", validation.errors);
    return {
      sessions: [],
      error: "Invalid sessions response",
    };
  }

  if (validation.warnings) {
    logger.warn("Sessions validation warnings", validation.warnings);
  }

  // Use validated API data directly (Session type uses snake_case)
  // Config is optional and may be a partial object from the API
  // Backend uses CursorPaginatedResponse format with 'data' field
  const sessions: Session[] = validation.data.data.map((apiSession) => ({
    id: apiSession.id,
    name: apiSession.name || "Untitled",
    status: (apiSession.status as Session["status"]) || "active",
    created_at: apiSession.created_at,
    updated_at: apiSession.updated_at,
    config: apiSession.config as Session["config"],
  }));

  return { sessions };
}

// API message types and transforms are now imported from apiTransforms.ts
// which uses generated types from the OpenAPI spec

/**
 * Load chat data for a session
 * Parallel-fetches session details, messages, and artifacts
 */
export async function chatLoader({
  params,
}: LoaderFunctionArgs): Promise<ChatLoaderData> {
  const { sessionId } = params;

  if (!sessionId) {
    return {
      sessionId: null,
      messages: [],
      artifacts: [],
    };
  }

  // Parallel fetch session, messages, and artifacts
  // Note: Messages endpoint returns a plain array, not { items: [...] }
  // Artifacts endpoint returns { items: [...], cursor, hasMore }
  const [sessionResult, messagesResult, artifactsResult] = await Promise.all([
    fetchJson<unknown>(`${API_BASE}/sessions/${sessionId}`),
    fetchJson<unknown[]>(`${API_BASE}/sessions/${sessionId}/messages`),
    fetchJson<{ items: CanvasArtifact[] }>(
      `${API_BASE}/artifacts?session_id=${sessionId}&limit=100`,
    ),
  ]);

  // Validate session response - keep API format (snake_case)
  // useSessionSync will transform to client format (camelCase) via apiTransforms
  let validatedSession: Session | undefined;
  if (sessionResult) {
    const sessionValidation = validateSession(sessionResult);
    if (sessionValidation.success) {
      // Use validated API data directly (Session type uses snake_case)
      // Config is optional and may be a partial object from the API
      validatedSession = {
        id: sessionValidation.data.id,
        name: sessionValidation.data.name || "Untitled",
        status:
          (sessionValidation.data.status as Session["status"]) || "active",
        created_at: sessionValidation.data.created_at,
        updated_at: sessionValidation.data.updated_at,
        config: sessionValidation.data.config as Session["config"],
      };
    } else {
      logger.warn("Session validation failed", sessionValidation.errors);
    }
  }

  // Validate messages response
  // Backend returns a plain array, not { items: [...] }
  // Uses generated ApiMessage type and transformApiMessageToClient from apiTransforms
  let messages: ChatMessage[] = [];
  if (Array.isArray(messagesResult)) {
    const messagesValidation = validateMessages(messagesResult);
    if (messagesValidation.success) {
      // Transform validated API messages to client format
      messages = messagesValidation.data
        .filter(isApiMessage)
        .map((msg) => transformApiMessageToClient(msg as ApiMessage));
      if (messagesValidation.warnings) {
        logger.warn("Message validation warnings", messagesValidation.warnings);
      }
    } else {
      logger.warn("Messages validation failed", messagesValidation.errors);
    }
  }

  return {
    sessionId,
    session: validatedSession,
    messages,
    artifacts: artifactsResult?.items ?? [],
    error: !validatedSession ? "Session not found" : undefined,
  };
}

/**
 * Load a specific artifact with version history
 */
export async function artifactLoader({
  params,
}: LoaderFunctionArgs): Promise<ArtifactLoaderData> {
  const { artifactId } = params;

  if (!artifactId) {
    return {
      artifact: null,
      versions: [],
    };
  }

  // Parallel fetch artifact and versions
  const [artifactResult, versionsResult] = await Promise.all([
    fetchJson<CanvasArtifact>(`${API_BASE}/artifacts/${artifactId}`),
    fetchJson<ArtifactVersion[]>(
      `${API_BASE}/artifacts/${artifactId}/versions`,
    ),
  ]);

  return {
    artifact: artifactResult,
    versions: versionsResult ?? [],
    error: !artifactResult ? "Artifact not found" : undefined,
  };
}

// =============================================================================
// Compliance Loader (Persona-specific: admin, compliance-officer)
// =============================================================================

export interface ComplianceLoaderData {
  summary: ComplianceSummary | null;
  error?: string;
}

interface ComplianceSummary {
  soc2: FrameworkSummary;
  hipaa: FrameworkSummary;
  gdpr: FrameworkSummary;
  fedramp: FrameworkSummary;
}

interface FrameworkSummary {
  percentage: number;
  status: "compliant" | "partial" | "non-compliant";
  compliant_count?: number;
  total_count?: number;
  pending_actions?: number;
}

/**
 * Load compliance summary for compliance dashboard
 * Used by compliance-officer and admin personas
 */
export async function complianceLoader(
  _args: LoaderFunctionArgs,
): Promise<ComplianceLoaderData> {
  const result = await fetchJson<ComplianceSummary>(
    `${API_BASE}/compliance/reports/summary`,
  );

  if (!result) {
    return {
      summary: null,
      error: "Failed to load compliance summary",
    };
  }

  return {
    summary: result,
  };
}

// =============================================================================
// Files/Artifacts Loader (for FilesPage)
// =============================================================================

export interface FilesLoaderData {
  artifacts: CanvasArtifact[];
  total: number;
  error?: string;
}

/**
 * Load all artifacts across sessions for the FilesPage
 * This provides a unified view of all file-like artifacts
 */
export async function filesLoader(
  _args: LoaderFunctionArgs,
): Promise<FilesLoaderData> {
  const result = await fetchJson<{
    items: CanvasArtifact[];
    total?: number;
    hasMore?: boolean;
  }>(`${API_BASE}/artifacts?limit=100`);

  if (!result) {
    return {
      artifacts: [],
      total: 0,
      error: "Failed to load files",
    };
  }

  return {
    artifacts: result.items ?? [],
    total: result.total ?? result.items?.length ?? 0,
  };
}

// =============================================================================
// Loader Index Export
// =============================================================================

export const canvasLoaders = {
  sessions: sessionsLoader,
  chat: chatLoader,
  artifact: artifactLoader,
  compliance: complianceLoader,
  files: filesLoader,
};

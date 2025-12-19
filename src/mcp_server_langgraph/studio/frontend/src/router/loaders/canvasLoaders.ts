/**
 * Canvas Loaders - Phase 2
 *
 * React Router loaders for HybridShell routes.
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
import type { Session } from "../../types";
import type { CanvasArtifact, ArtifactVersion } from "../../types/artifacts";

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

async function fetchJson<T>(url: string): Promise<T | null> {
  try {
    const response = await fetch(url);
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
  const result = await fetchJson<{ items: Session[] }>(
    `${API_BASE}/sessions?limit=50`,
  );

  if (!result) {
    return {
      sessions: [],
      error: "Failed to load sessions",
    };
  }

  return {
    sessions: result.items,
  };
}

/**
 * Load chat data for a session
 * Parallel-fetches session details and artifacts
 */
export async function chatLoader({
  params,
}: LoaderFunctionArgs): Promise<ChatLoaderData> {
  const { sessionId } = params;

  if (!sessionId) {
    return {
      sessionId: null,
      artifacts: [],
    };
  }

  // Parallel fetch session and artifacts
  const [sessionResult, artifactsResult] = await Promise.all([
    fetchJson<Session>(`${API_BASE}/sessions/${sessionId}`),
    fetchJson<{ items: CanvasArtifact[] }>(
      `${API_BASE}/artifacts?session_id=${sessionId}&limit=100`,
    ),
  ]);

  return {
    sessionId,
    session: sessionResult ?? undefined,
    artifacts: artifactsResult?.items ?? [],
    error: !sessionResult ? "Session not found" : undefined,
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
// Loader Index Export
// =============================================================================

export const canvasLoaders = {
  sessions: sessionsLoader,
  chat: chatLoader,
  artifact: artifactLoader,
};

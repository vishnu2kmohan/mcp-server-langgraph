/**
 * useArtifactExtraction Hook
 *
 * Extracts artifacts from streaming chat content and persists them to the API.
 * Used to connect chat streaming to the canvas panel.
 *
 * Features:
 * - Parses streaming content for code blocks (mermaid, chart, code, etc.)
 * - Transforms Artifact to CreateArtifactRequest format
 * - POSTs to /api/v1/artifacts
 * - Triggers revalidation so canvas sees new artifacts
 * - Deduplicates via content hash to prevent duplicate extractions
 */
import { useCallback, useRef, useState } from "react";
import { useRevalidator } from "react-router";
import { parseArtifacts } from "../utils/artifactParser";
import type {
  Artifact,
  CanvasArtifact,
  CodeArtifact,
  ExecutableArtifact,
} from "../types/artifacts";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export interface UseArtifactExtractionOptions {
  /** Session ID to associate artifacts with */
  sessionId: string;
  /** Callback when artifacts are extracted and saved */
  onArtifactsExtracted?: (count: number) => void;
  /** Callback when saving state changes */
  onSavingChange?: (isSaving: boolean) => void;
  /** Maximum number of retry attempts for failed saves (default: 0) */
  maxRetries?: number;
  /** Base delay in ms for retry backoff (default: 100) */
  retryDelayMs?: number;
  /** Callback on each retry attempt */
  onRetry?: (attempt: number, error: Error) => void;
}

export interface UseArtifactExtractionResult {
  /** Extract artifacts from content and save to API */
  extractAndSaveArtifacts: (content: string) => Promise<number>;
  /** Reset extraction state (clear deduplication cache) */
  resetExtraction: () => void;
  /** Whether artifacts are currently being saved */
  isSaving: boolean;
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * DJB2 hash for robust deduplication (handles Unicode)
 */
function hashString(str: string): string {
  let hash = 5381;
  for (let i = 0; i < str.length; i++) {
    hash = (hash << 5) + hash + str.charCodeAt(i);
    hash = hash & hash; // Convert to 32bit integer
  }
  return hash.toString();
}

/**
 * Map ArtifactType to VALID CanvasArtifact["contentType"] only:
 * Valid types: "code" | "markdown" | "json" | "jsx" | "mermaid" | "html"
 */
function mapArtifactTypeToContentType(
  type: string,
): CanvasArtifact["contentType"] {
  const mapping: Record<string, CanvasArtifact["contentType"]> = {
    code: "code",
    mermaid: "mermaid",
    json: "json",
    chart: "json", // Charts stored as JSON config
    table: "json", // Tables stored as JSON data
    svg: "html", // SVG is valid HTML
    executable: "jsx",
    text: "markdown",
    mdx: "markdown",
    image: "markdown", // Image URLs in markdown
    audio: "markdown",
    video: "markdown",
  };
  return mapping[type] ?? "code";
}

/**
 * Type guard: Check if artifact is a CodeArtifact
 */
function isCodeArtifact(artifact: Artifact): artifact is CodeArtifact {
  return artifact.type === "code";
}

/**
 * Type guard: Check if artifact is an ExecutableArtifact
 */
function isExecutableArtifact(
  artifact: Artifact,
): artifact is ExecutableArtifact {
  return artifact.type === "executable";
}

/**
 * Extract language from artifact config using type-safe narrowing.
 * Only CodeArtifact and ExecutableArtifact have language in their config.
 */
function extractLanguage(artifact: Artifact): string | undefined {
  if (isCodeArtifact(artifact)) {
    return artifact.config.language;
  }
  if (isExecutableArtifact(artifact)) {
    return artifact.config.language;
  }
  return undefined;
}

/**
 * API request payload for creating an artifact.
 * Uses snake_case to match backend ArtifactCreateRequest schema.
 */
interface ApiCreateArtifactRequest {
  type: string;
  content: string;
  content_type: CanvasArtifact["contentType"];
  session_id: string;
  title?: string;
  edit_metadata?: {
    edited_by: "user" | "ai-suggestion" | "ai-generation";
    language?: string;
    ai_confidence?: number;
  };
}

/**
 * Transform Artifact (parser output) to API request payload
 */
function toCreateArtifactRequest(
  artifact: Artifact,
  sessionId: string,
): ApiCreateArtifactRequest {
  // CRITICAL: Serialize non-string data (Charts, Tables, JSON objects)
  let content: string;
  if (typeof artifact.data === "string") {
    content = artifact.data;
  } else {
    content = JSON.stringify(artifact.data, null, 2);
  }

  // Extract language using type-safe helper
  const language = extractLanguage(artifact);
  const contentType = mapArtifactTypeToContentType(artifact.type);

  // Build API request with snake_case keys
  const request: ApiCreateArtifactRequest = {
    type: contentType, // Use content type as artifact type
    content,
    content_type: contentType,
    session_id: sessionId,
    title: artifact.title,
  };

  // Add edit metadata with language if available
  if (language) {
    request.edit_metadata = {
      edited_by: "ai-generation",
      language,
    };
  }

  return request;
}

/**
 * Get auth headers following canvasLoaders.ts pattern
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
 * Sleep for a given number of milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// =============================================================================
// Hook
// =============================================================================

export function useArtifactExtraction(
  options: UseArtifactExtractionOptions,
): UseArtifactExtractionResult {
  const {
    sessionId,
    onArtifactsExtracted,
    onSavingChange,
    maxRetries = 0,
    retryDelayMs = 100,
    onRetry,
  } = options;

  // useRevalidator must be called unconditionally (rules of hooks)
  // This hook requires a Data Router context - error is appropriate if missing
  const revalidator = useRevalidator();

  // Track extracted content hashes to prevent duplicates
  const extractedHashesRef = useRef<Set<string>>(new Set());

  // Loading state
  const [isSaving, setIsSaving] = useState(false);

  const extractAndSaveArtifacts = useCallback(
    async (content: string): Promise<number> => {
      // Validate sessionId
      if (!sessionId || sessionId === "default-session" || sessionId === "") {
        console.warn(
          "useArtifactExtraction: Invalid sessionId, skipping extraction",
        );
        return 0;
      }

      const segments = parseArtifacts(content);

      // Filter to only new artifacts that need saving
      const artifactsToSave: Array<{
        request: ApiCreateArtifactRequest;
        hash: string;
      }> = [];

      for (const segment of segments) {
        if (segment.type === "artifact" && segment.artifact) {
          // Robust deduplication using full content hash
          const contentStr =
            typeof segment.artifact.data === "string"
              ? segment.artifact.data
              : JSON.stringify(segment.artifact.data);
          const hash = hashString(contentStr);

          if (extractedHashesRef.current.has(hash)) continue;
          extractedHashesRef.current.add(hash);

          const request = toCreateArtifactRequest(segment.artifact, sessionId);
          artifactsToSave.push({ request, hash });
        }
      }

      // If no artifacts to save, return early
      if (artifactsToSave.length === 0) {
        return 0;
      }

      // Set saving state
      setIsSaving(true);
      onSavingChange?.(true);

      let createdCount = 0;

      try {
        for (const { request } of artifactsToSave) {
          let lastError: Error | null = null;
          let success = false;

          // Retry loop with exponential backoff
          for (let attempt = 0; attempt <= maxRetries; attempt++) {
            try {
              const response = await fetch("/api/v1/artifacts", {
                method: "POST",
                headers: getAuthHeaders(),
                credentials: "include", // Keycloak SSO support
                body: JSON.stringify(request),
              });
              if (response.ok) {
                createdCount++;
                success = true;
                break;
              }
            } catch (error) {
              lastError =
                error instanceof Error ? error : new Error(String(error));
              console.error("Failed to save artifact:", error);

              // If we have more retries, wait with exponential backoff
              if (attempt < maxRetries) {
                onRetry?.(attempt + 1, lastError);
                const delay = retryDelayMs * Math.pow(2, attempt);
                await sleep(delay);
              }
            }
          }

          // If all retries failed, log the final error
          if (!success && lastError) {
            console.error(
              "Failed to save artifact after all retries:",
              lastError,
            );
          }
        }

        if (createdCount > 0) {
          onArtifactsExtracted?.(createdCount);
          revalidator.revalidate(); // Canvas sees new artifacts via loader refresh
        }
        return createdCount;
      } finally {
        setIsSaving(false);
        onSavingChange?.(false);
      }
    },
    [
      sessionId,
      revalidator,
      onArtifactsExtracted,
      onSavingChange,
      maxRetries,
      retryDelayMs,
      onRetry,
    ],
  );

  const resetExtraction = useCallback(() => {
    extractedHashesRef.current.clear();
  }, []);

  return { extractAndSaveArtifacts, resetExtraction, isSaving };
}

export default useArtifactExtraction;

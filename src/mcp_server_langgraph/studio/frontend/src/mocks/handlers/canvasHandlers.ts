/**
 * Canvas Handlers - Phase 2
 *
 * MSW handlers for Canvas API endpoints.
 * These define the API contracts for artifact management in the Studio Canvas.
 *
 * Endpoints:
 * - GET /api/v1/artifacts - List artifacts for a session
 * - GET /api/v1/artifacts/:id - Get a specific artifact
 * - POST /api/v1/artifacts - Create a new artifact
 * - PUT /api/v1/artifacts/:id - Update an artifact
 * - DELETE /api/v1/artifacts/:id - Delete an artifact
 * - GET /api/v1/artifacts/:id/versions - Get version history
 * - POST /api/v1/artifacts/:id/fork - Fork an artifact
 * - POST /api/v1/artifacts/search - Semantic search
 * - GET /api/v1/artifacts/:id/similar - Find similar artifacts
 */

import { http, HttpResponse, delay } from "msw";
import type {
  CanvasArtifact,
  ArtifactVersion,
  CreateArtifactResponse,
  UpdateArtifactResponse,
  ForkArtifactResponse,
  ListArtifactsResponse,
} from "../../types/artifacts";

// =============================================================================
// Mock Data Factories
// =============================================================================

/**
 * Create a mock canvas artifact with optional overrides
 */
export const createMockCanvasArtifact = (
  overrides: Partial<CanvasArtifact> = {},
): CanvasArtifact => ({
  id: `art-${crypto.randomUUID().slice(0, 8)}`,
  type: "code",
  sessionId: `session-${crypto.randomUUID().slice(0, 8)}`,
  version: 1,
  content: `// Generated code\nconsole.log("Hello, Canvas!");`,
  contentType: "code",
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
  title: "Untitled Artifact",
  editMetadata: {
    editedBy: "user",
    language: "javascript",
  },
  ...overrides,
});

/**
 * Create a mock artifact version with optional overrides
 */
export const createMockArtifactVersion = (
  overrides: Partial<ArtifactVersion> = {},
): ArtifactVersion => ({
  id: `ver-${crypto.randomUUID().slice(0, 8)}`,
  artifactId: `art-${crypto.randomUUID().slice(0, 8)}`,
  version: 1,
  content: `// Version content\nconsole.log("Hello!");`,
  contentType: "code",
  createdBy: "user-123",
  createdAt: new Date().toISOString(),
  metadata: {
    editType: "user",
  },
  ...overrides,
});

// =============================================================================
// Default Mock Data
// =============================================================================

/**
 * Pre-defined mock artifacts for testing
 */
export const mockCanvasArtifacts: CanvasArtifact[] = [
  createMockCanvasArtifact({
    id: "art-1",
    sessionId: "session-1",
    title: "Main Component",
    contentType: "code",
    content: `import React from 'react';

export function MainComponent() {
  return (
    <div className="container">
      <h1>Hello, Canvas!</h1>
    </div>
  );
}`,
    editMetadata: {
      editedBy: "user",
      language: "typescript",
    },
  }),
  createMockCanvasArtifact({
    id: "art-2",
    sessionId: "session-1",
    title: "README",
    contentType: "markdown",
    content: `# Project README

## Overview
This is a sample project demonstrating the Canvas feature.

## Features
- Multi-modal artifacts
- Version control
- AI-assisted editing
`,
    editMetadata: {
      editedBy: "ai-generation",
      aiConfidence: 0.95,
    },
  }),
  createMockCanvasArtifact({
    id: "art-3",
    sessionId: "session-1",
    title: "Config",
    contentType: "json",
    content: JSON.stringify(
      {
        name: "canvas-app",
        version: "1.0.0",
        features: {
          darkMode: true,
          aiSuggestions: true,
        },
      },
      null,
      2,
    ),
  }),
  createMockCanvasArtifact({
    id: "art-4",
    sessionId: "session-2",
    title: "Workflow Diagram",
    contentType: "mermaid",
    content: `graph TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
`,
  }),
];

/**
 * Mock version history for artifacts
 */
const mockArtifactVersions: Record<string, ArtifactVersion[]> = {
  "art-1": [
    createMockArtifactVersion({
      id: "ver-1-1",
      artifactId: "art-1",
      version: 1,
      content: "// Initial version",
      createdAt: new Date(Date.now() - 3600000).toISOString(),
    }),
    createMockArtifactVersion({
      id: "ver-1-2",
      artifactId: "art-1",
      version: 2,
      content: "// Updated version",
      createdAt: new Date(Date.now() - 1800000).toISOString(),
      parentVersion: 1,
    }),
  ],
  "art-2": [
    createMockArtifactVersion({
      id: "ver-2-1",
      artifactId: "art-2",
      version: 1,
      contentType: "markdown",
      content: "# Initial README",
    }),
  ],
};

// =============================================================================
// MSW Request Handlers
// =============================================================================

/**
 * Semantic search result type
 */
interface SemanticSearchResult {
  artifact_id: string;
  score: number;
  title: string | null;
}

export const canvasHandlers = [
  /**
   * POST /api/v1/artifacts/search - Semantic search across artifacts
   * MUST be defined before GET /api/v1/artifacts/:id to avoid path conflicts
   */
  http.post("/api/v1/artifacts/search", async ({ request }) => {
    await delay(50);
    const body = (await request.json()) as { query: string; limit?: number };
    const { query, limit = 10 } = body;

    // Validate query is not empty
    if (!query || query.trim() === "") {
      return HttpResponse.json(
        { detail: "Query parameter is required" },
        { status: 400 },
      );
    }

    // Simple mock search: filter artifacts by content/title matching query
    const matchingArtifacts = mockCanvasArtifacts.filter(
      (a) =>
        a.content.toLowerCase().includes(query.toLowerCase()) ||
        (a.title && a.title.toLowerCase().includes(query.toLowerCase())),
    );

    // Create search results with mock scores
    const results: SemanticSearchResult[] = matchingArtifacts
      .slice(0, limit)
      .map((a, index) => ({
        artifact_id: a.id,
        score: 0.95 - index * 0.1, // Decreasing scores for mock
        title: a.title || null,
      }));

    return HttpResponse.json({ results });
  }),

  /**
   * GET /api/v1/artifacts - List artifacts for a session
   */
  http.get("/api/v1/artifacts", async ({ request }) => {
    await delay(50);
    const url = new URL(request.url);
    const sessionId = url.searchParams.get("session_id");
    const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
    const cursor = url.searchParams.get("cursor");

    let filtered = mockCanvasArtifacts;
    if (sessionId) {
      filtered = filtered.filter((a) => a.sessionId === sessionId);
    }

    // Simple cursor-based pagination (cursor is index)
    let startIndex = 0;
    if (cursor) {
      startIndex = parseInt(cursor, 10);
    }

    const items = filtered.slice(startIndex, startIndex + limit);
    const hasMore = startIndex + limit < filtered.length;
    const nextCursor = hasMore ? String(startIndex + limit) : null;

    const response: ListArtifactsResponse = {
      items,
      cursor: nextCursor,
      hasMore,
    };

    return HttpResponse.json(response);
  }),

  /**
   * GET /api/v1/artifacts/:id - Get a specific artifact
   */
  http.get("/api/v1/artifacts/:id", async ({ params }) => {
    await delay(50);
    const artifact = mockCanvasArtifacts.find((a) => a.id === params.id);

    if (!artifact) {
      return HttpResponse.json(
        { detail: "Artifact not found" },
        { status: 404 },
      );
    }

    return HttpResponse.json(artifact);
  }),

  /**
   * POST /api/v1/artifacts - Create a new artifact
   */
  http.post("/api/v1/artifacts", async ({ request }) => {
    await delay(100);
    // Consume request body (validation in real implementation)
    await request.json();

    const response: CreateArtifactResponse = {
      id: `art-${crypto.randomUUID().slice(0, 8)}`,
      version: 1,
      createdAt: new Date().toISOString(),
    };

    return HttpResponse.json(response, { status: 201 });
  }),

  /**
   * PUT /api/v1/artifacts/:id - Update an artifact
   */
  http.put("/api/v1/artifacts/:id", async ({ params, request }) => {
    await delay(50);
    const artifact = mockCanvasArtifacts.find((a) => a.id === params.id);

    if (!artifact) {
      return HttpResponse.json(
        { detail: "Artifact not found" },
        { status: 404 },
      );
    }

    // Consume request body (validation in real implementation)
    await request.json();

    const response: UpdateArtifactResponse = {
      id: artifact.id,
      version: artifact.version + 1,
      updatedAt: new Date().toISOString(),
    };

    return HttpResponse.json(response);
  }),

  /**
   * DELETE /api/v1/artifacts/:id - Delete an artifact
   */
  http.delete("/api/v1/artifacts/:id", async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),

  /**
   * GET /api/v1/artifacts/:id/versions - Get version history
   */
  http.get("/api/v1/artifacts/:id/versions", async ({ params }) => {
    await delay(50);
    const artifactId = params.id as string;
    const artifact = mockCanvasArtifacts.find((a) => a.id === artifactId);

    if (!artifact) {
      return HttpResponse.json(
        { detail: "Artifact not found" },
        { status: 404 },
      );
    }

    const versions = mockArtifactVersions[artifactId] || [
      createMockArtifactVersion({
        artifactId,
        version: 1,
        content: artifact.content,
        contentType: artifact.contentType,
      }),
    ];

    return HttpResponse.json(versions);
  }),

  /**
   * POST /api/v1/artifacts/:id/fork - Fork an artifact
   */
  http.post("/api/v1/artifacts/:id/fork", async ({ params, request }) => {
    await delay(100);
    const artifactId = params.id as string;
    const artifact = mockCanvasArtifacts.find((a) => a.id === artifactId);

    if (!artifact) {
      return HttpResponse.json(
        { detail: "Artifact not found" },
        { status: 404 },
      );
    }

    // Consume request body (validation in real implementation)
    await request.json();

    const response: ForkArtifactResponse = {
      id: `art-${crypto.randomUUID().slice(0, 8)}`,
      parentId: artifactId,
      version: 1,
    };

    return HttpResponse.json(response, { status: 201 });
  }),

  /**
   * GET /api/v1/artifacts/:id/similar - Find similar artifacts
   */
  http.get("/api/v1/artifacts/:id/similar", async ({ params, request }) => {
    await delay(50);
    const artifactId = params.id as string;
    const artifact = mockCanvasArtifacts.find((a) => a.id === artifactId);

    if (!artifact) {
      return HttpResponse.json(
        { detail: "Artifact not found" },
        { status: 404 },
      );
    }

    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") ?? "5", 10);

    // Find similar artifacts (same content type, different ID)
    const similarArtifacts = mockCanvasArtifacts.filter(
      (a) => a.id !== artifactId && a.contentType === artifact.contentType,
    );

    // Create similarity results with mock scores
    const results: SemanticSearchResult[] = similarArtifacts
      .slice(0, limit)
      .map((a, index) => ({
        artifact_id: a.id,
        score: 0.85 - index * 0.1, // Decreasing scores for mock
        title: a.title || null,
      }));

    return HttpResponse.json({ results });
  }),
];

// =============================================================================
// Error Handler Factories
// =============================================================================

/**
 * Create a handler that returns artifact not found
 */
export const createArtifactNotFoundHandler = (path: string) =>
  http.get(path, () =>
    HttpResponse.json({ detail: "Artifact not found" }, { status: 404 }),
  );

/**
 * Create a handler that returns a rate limit error
 */
export const createRateLimitHandler = (
  path: string,
  method: "get" | "post" | "put" | "delete" = "get",
) =>
  http[method](path, () =>
    HttpResponse.json(
      { detail: "Rate limit exceeded. Please try again later." },
      { status: 429 },
    ),
  );

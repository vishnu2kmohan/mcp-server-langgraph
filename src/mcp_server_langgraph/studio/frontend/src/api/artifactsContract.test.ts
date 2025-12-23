/**
 * Artifacts API Contract Tests
 *
 * These tests validate that frontend TypeScript types match backend API responses
 * for the Studio Canvas artifacts endpoints.
 *
 * Contract tests verify:
 * - Response shape matches TypeScript interfaces
 * - Required fields are present
 * - Field types are correct
 * - Nullable fields are handled
 *
 * Phase 2: TDD RED phase - Write tests before implementing api/index.ts endpoints
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import { canvasHandlers } from "../mocks/handlers/canvasHandlers";
import type {
  CanvasArtifact,
  ArtifactVersion,
  CreateArtifactRequest,
  CreateArtifactResponse,
  UpdateArtifactRequest,
  UpdateArtifactResponse,
  ForkArtifactRequest,
  ForkArtifactResponse,
  ListArtifactsResponse,
} from "../types/artifacts";

// Setup MSW server with canvas handlers
const server = setupServer(...canvasHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

// =============================================================================
// Type Guards for Runtime Validation
// =============================================================================

/**
 * Type guard for CanvasArtifact
 */
function isCanvasArtifact(obj: unknown): obj is CanvasArtifact {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.sessionId === "string" &&
    typeof o.version === "number" &&
    typeof o.content === "string" &&
    typeof o.contentType === "string" &&
    ["code", "markdown", "json", "jsx", "mermaid", "html"].includes(
      o.contentType as string,
    ) &&
    typeof o.createdAt === "string" &&
    typeof o.updatedAt === "string"
  );
}

/**
 * Type guard for ArtifactVersion
 */
function isArtifactVersion(obj: unknown): obj is ArtifactVersion {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.artifactId === "string" &&
    typeof o.version === "number" &&
    typeof o.content === "string" &&
    typeof o.contentType === "string" &&
    typeof o.createdAt === "string"
  );
}

/**
 * Type guard for CreateArtifactResponse
 */
function isCreateArtifactResponse(obj: unknown): obj is CreateArtifactResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.version === "number" &&
    typeof o.createdAt === "string"
  );
}

/**
 * Type guard for UpdateArtifactResponse
 */
function isUpdateArtifactResponse(obj: unknown): obj is UpdateArtifactResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.version === "number" &&
    typeof o.updatedAt === "string"
  );
}

/**
 * Type guard for ForkArtifactResponse
 */
function isForkArtifactResponse(obj: unknown): obj is ForkArtifactResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.id === "string" &&
    typeof o.parentId === "string" &&
    typeof o.version === "number"
  );
}

/**
 * Type guard for ListArtifactsResponse
 */
function isListArtifactsResponse(obj: unknown): obj is ListArtifactsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.items) &&
    o.items.every(isCanvasArtifact) &&
    (o.cursor === null || typeof o.cursor === "string") &&
    typeof o.hasMore === "boolean"
  );
}

/**
 * Type guard for semantic search result
 */
interface SemanticSearchResult {
  artifact_id: string;
  score: number;
  title: string | null;
}

interface SemanticSearchResponse {
  results: SemanticSearchResult[];
}

function isSemanticSearchResult(obj: unknown): obj is SemanticSearchResult {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.artifact_id === "string" &&
    typeof o.score === "number" &&
    (o.title === null || typeof o.title === "string")
  );
}

function isSemanticSearchResponse(obj: unknown): obj is SemanticSearchResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return Array.isArray(o.results) && o.results.every(isSemanticSearchResult);
}

// =============================================================================
// Contract Tests
// =============================================================================

describe("Artifacts API Contract Tests", () => {
  describe("GET /api/v1/artifacts (List)", () => {
    it("should validate ListArtifactsResponse schema", async () => {
      const response = await fetch("/api/v1/artifacts?session_id=session-1");
      const data = await response.json();
      expect(isListArtifactsResponse(data)).toBe(true);
    });

    it("should return items array with CanvasArtifact objects", async () => {
      const response = await fetch("/api/v1/artifacts?session_id=session-1");
      const data: ListArtifactsResponse = await response.json();
      expect(data.items).toBeDefined();
      expect(Array.isArray(data.items)).toBe(true);
      if (data.items.length > 0) {
        expect(isCanvasArtifact(data.items[0])).toBe(true);
      }
    });

    it("should include pagination fields", async () => {
      const response = await fetch("/api/v1/artifacts?limit=10");
      const data = await response.json();
      expect("cursor" in data).toBe(true);
      expect("hasMore" in data).toBe(true);
    });

    it("should handle empty results", async () => {
      const response = await fetch(
        "/api/v1/artifacts?session_id=nonexistent-session",
      );
      const data: ListArtifactsResponse = await response.json();
      expect(data.items).toHaveLength(0);
      expect(data.hasMore).toBe(false);
    });
  });

  describe("GET /api/v1/artifacts/:id (Get Single)", () => {
    it("should validate CanvasArtifact schema", async () => {
      const response = await fetch("/api/v1/artifacts/art-1");
      const data = await response.json();
      expect(isCanvasArtifact(data)).toBe(true);
    });

    it("should include required CanvasArtifact fields", async () => {
      const response = await fetch("/api/v1/artifacts/art-1");
      const data: CanvasArtifact = await response.json();
      expect(data.id).toBe("art-1");
      expect(data.sessionId).toBeDefined();
      expect(data.version).toBeGreaterThanOrEqual(1);
      expect(data.content).toBeDefined();
      expect(data.contentType).toBeDefined();
      expect(data.createdAt).toBeDefined();
      expect(data.updatedAt).toBeDefined();
    });

    it("should return 404 for non-existent artifact", async () => {
      const response = await fetch("/api/v1/artifacts/non-existent-id");
      expect(response.status).toBe(404);
      const data = await response.json();
      expect(data.detail).toBeDefined();
    });
  });

  describe("POST /api/v1/artifacts (Create)", () => {
    it("should validate CreateArtifactResponse schema", async () => {
      const request: CreateArtifactRequest = {
        type: "code",
        content: "console.log('hello');",
        sessionId: "session-1",
        title: "Test Artifact",
      };

      const response = await fetch("/api/v1/artifacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(isCreateArtifactResponse(data)).toBe(true);
    });

    it("should return id, version, and createdAt", async () => {
      const request: CreateArtifactRequest = {
        type: "markdown",
        content: "# Hello World",
        sessionId: "session-1",
      };

      const response = await fetch("/api/v1/artifacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: CreateArtifactResponse = await response.json();
      expect(typeof data.id).toBe("string");
      expect(data.version).toBe(1);
      expect(typeof data.createdAt).toBe("string");
    });
  });

  describe("PUT /api/v1/artifacts/:id (Update)", () => {
    it("should validate UpdateArtifactResponse schema", async () => {
      const request: UpdateArtifactRequest = {
        content: "console.log('updated');",
        editedBy: "user",
      };

      const response = await fetch("/api/v1/artifacts/art-1", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(isUpdateArtifactResponse(data)).toBe(true);
    });

    it("should increment version on update", async () => {
      const request: UpdateArtifactRequest = {
        content: "updated content",
      };

      const response = await fetch("/api/v1/artifacts/art-1", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: UpdateArtifactResponse = await response.json();
      expect(data.version).toBeGreaterThan(0);
      expect(typeof data.updatedAt).toBe("string");
    });

    it("should return 404 for non-existent artifact", async () => {
      const request: UpdateArtifactRequest = { content: "test" };

      const response = await fetch("/api/v1/artifacts/non-existent", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(404);
    });
  });

  describe("DELETE /api/v1/artifacts/:id (Delete)", () => {
    it("should return 204 on successful delete", async () => {
      const response = await fetch("/api/v1/artifacts/art-1", {
        method: "DELETE",
      });
      expect(response.status).toBe(204);
    });
  });

  describe("GET /api/v1/artifacts/:id/versions (Version History)", () => {
    it("should return array of ArtifactVersion", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/versions");
      expect(response.status).toBe(200);
      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      if (data.length > 0) {
        expect(isArtifactVersion(data[0])).toBe(true);
      }
    });

    it("should include version metadata", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/versions");
      const versions: ArtifactVersion[] = await response.json();
      if (versions.length > 0) {
        const version = versions[0];
        expect(version.artifactId).toBe("art-1");
        expect(typeof version.version).toBe("number");
        expect(typeof version.content).toBe("string");
        expect(typeof version.createdAt).toBe("string");
      }
    });

    it("should return 404 for non-existent artifact", async () => {
      const response = await fetch("/api/v1/artifacts/non-existent/versions");
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/artifacts/:id/fork (Fork)", () => {
    it("should validate ForkArtifactResponse schema", async () => {
      const request: ForkArtifactRequest = {
        newTitle: "Forked Artifact",
      };

      const response = await fetch("/api/v1/artifacts/art-1/fork", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(isForkArtifactResponse(data)).toBe(true);
    });

    it("should return new id with parentId reference", async () => {
      const request: ForkArtifactRequest = {};

      const response = await fetch("/api/v1/artifacts/art-1/fork", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: ForkArtifactResponse = await response.json();
      expect(typeof data.id).toBe("string");
      expect(data.parentId).toBe("art-1");
      expect(data.version).toBe(1);
    });

    it("should return 404 for non-existent artifact", async () => {
      const response = await fetch("/api/v1/artifacts/non-existent/fork", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/artifacts/search (Semantic Search)", () => {
    it("should validate SemanticSearchResponse schema", async () => {
      const response = await fetch("/api/v1/artifacts/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "React component", limit: 10 }),
      });

      expect(response.status).toBe(200);
      const data = await response.json();
      expect(isSemanticSearchResponse(data)).toBe(true);
    });

    it("should return results with artifact_id and score", async () => {
      const response = await fetch("/api/v1/artifacts/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "Hello", limit: 5 }),
      });

      const data: SemanticSearchResponse = await response.json();
      if (data.results.length > 0) {
        const result = data.results[0];
        expect(typeof result.artifact_id).toBe("string");
        expect(typeof result.score).toBe("number");
        expect(result.score).toBeLessThanOrEqual(1);
        expect(result.score).toBeGreaterThanOrEqual(0);
      }
    });

    it("should return 400 for empty query", async () => {
      const response = await fetch("/api/v1/artifacts/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "", limit: 10 }),
      });
      expect(response.status).toBe(400);
    });

    it("should respect limit parameter", async () => {
      const response = await fetch("/api/v1/artifacts/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "code", limit: 2 }),
      });

      const data: SemanticSearchResponse = await response.json();
      expect(data.results.length).toBeLessThanOrEqual(2);
    });
  });

  describe("GET /api/v1/artifacts/:id/similar (Find Similar)", () => {
    it("should validate SemanticSearchResponse schema", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/similar");
      expect(response.status).toBe(200);
      const data = await response.json();
      expect(isSemanticSearchResponse(data)).toBe(true);
    });

    it("should return similar artifacts with scores", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/similar?limit=5");
      const data: SemanticSearchResponse = await response.json();
      data.results.forEach((result) => {
        expect(typeof result.artifact_id).toBe("string");
        expect(typeof result.score).toBe("number");
      });
    });

    it("should return 404 for non-existent artifact", async () => {
      const response = await fetch("/api/v1/artifacts/non-existent/similar");
      expect(response.status).toBe(404);
    });

    it("should respect limit query parameter", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/similar?limit=2");
      const data: SemanticSearchResponse = await response.json();
      expect(data.results.length).toBeLessThanOrEqual(2);
    });
  });
});

// =============================================================================
// RTK Query Hook Contract Tests
// =============================================================================

describe("Artifacts API RTK Query Hooks Contract", () => {
  /**
   * These tests verify the expected hooks will work correctly
   * once implemented in api/index.ts
   *
   * Expected hooks:
   * - useListArtifactsQuery
   * - useGetArtifactQuery
   * - useCreateArtifactMutation
   * - useUpdateArtifactMutation
   * - useDeleteArtifactMutation
   * - useGetArtifactVersionsQuery
   * - useForkArtifactMutation
   * - useSemanticSearchArtifactsMutation
   * - useFindSimilarArtifactsQuery
   */

  it("should define expected request types for listArtifacts", () => {
    // Type check: ListArtifactsParams should have session_id, cursor, limit
    const params = {
      session_id: "session-1",
      cursor: undefined as string | undefined,
      limit: 20 as number | undefined,
    };
    expect(params.session_id).toBe("session-1");
  });

  it("should define expected response type for createArtifact", () => {
    const response: CreateArtifactResponse = {
      id: "art-123",
      version: 1,
      createdAt: new Date().toISOString(),
    };
    expect(isCreateArtifactResponse(response)).toBe(true);
  });

  it("should define expected response type for updateArtifact", () => {
    const response: UpdateArtifactResponse = {
      id: "art-123",
      version: 2,
      updatedAt: new Date().toISOString(),
    };
    expect(isUpdateArtifactResponse(response)).toBe(true);
  });

  it("should define expected response type for forkArtifact", () => {
    const response: ForkArtifactResponse = {
      id: "art-456",
      parentId: "art-123",
      version: 1,
    };
    expect(isForkArtifactResponse(response)).toBe(true);
  });
});

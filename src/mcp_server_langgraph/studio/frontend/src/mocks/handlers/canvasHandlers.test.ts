/**
 * Canvas Handlers Tests
 *
 * Tests for MSW handlers that mock the Canvas API endpoints.
 * Phase 2: Contract-First development - define API contracts via MSW.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import {
  canvasHandlers,
  createMockCanvasArtifact,
  createMockArtifactVersion,
  mockCanvasArtifacts,
} from "./canvasHandlers";
import type {
  CanvasArtifact,
  CreateArtifactRequest,
  ListArtifactsResponse,
  UpdateArtifactRequest,
  ForkArtifactRequest,
  ArtifactVersion,
} from "../../types/artifacts";

// Setup MSW server with canvas handlers
const server = setupServer(...canvasHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("canvasHandlers", () => {
  describe("Mock Data Factories", () => {
    it("creates a mock canvas artifact with defaults", () => {
      const artifact = createMockCanvasArtifact();

      expect(artifact.id).toBeDefined();
      expect(artifact.sessionId).toBeDefined();
      expect(artifact.version).toBe(1);
      expect(artifact.contentType).toBe("code");
      expect(artifact.content).toBeDefined();
      expect(artifact.createdAt).toBeDefined();
      expect(artifact.updatedAt).toBeDefined();
    });

    it("creates a mock canvas artifact with overrides", () => {
      const artifact = createMockCanvasArtifact({
        id: "custom-id",
        title: "Custom Title",
        contentType: "markdown",
        version: 3,
      });

      expect(artifact.id).toBe("custom-id");
      expect(artifact.title).toBe("Custom Title");
      expect(artifact.contentType).toBe("markdown");
      expect(artifact.version).toBe(3);
    });

    it("creates a mock artifact version", () => {
      const version = createMockArtifactVersion({
        artifactId: "art-123",
        version: 2,
      });

      expect(version.id).toBeDefined();
      expect(version.artifactId).toBe("art-123");
      expect(version.version).toBe(2);
      expect(version.content).toBeDefined();
      expect(version.createdAt).toBeDefined();
    });
  });

  describe("GET /api/v1/artifacts", () => {
    it("returns a list of artifacts for a session", async () => {
      const response = await fetch(
        "/api/v1/artifacts?session_id=session-1&limit=10",
      );
      expect(response.status).toBe(200);

      const data: ListArtifactsResponse = await response.json();
      expect(data.items).toBeDefined();
      expect(Array.isArray(data.items)).toBe(true);
      expect(data.cursor).toBeDefined();
      expect(typeof data.hasMore).toBe("boolean");
    });

    it("filters artifacts by session_id", async () => {
      const response = await fetch(
        "/api/v1/artifacts?session_id=session-1&limit=10",
      );
      const data: ListArtifactsResponse = await response.json();

      data.items.forEach((artifact) => {
        expect(artifact.sessionId).toBe("session-1");
      });
    });

    it("returns empty list for unknown session", async () => {
      const response = await fetch(
        "/api/v1/artifacts?session_id=unknown-session&limit=10",
      );
      const data: ListArtifactsResponse = await response.json();

      expect(data.items).toHaveLength(0);
      expect(data.hasMore).toBe(false);
    });
  });

  describe("GET /api/v1/artifacts/:id", () => {
    it("returns a specific artifact by id", async () => {
      const response = await fetch("/api/v1/artifacts/art-1");
      expect(response.status).toBe(200);

      const artifact: CanvasArtifact = await response.json();
      expect(artifact.id).toBe("art-1");
      expect(artifact.sessionId).toBeDefined();
      expect(artifact.content).toBeDefined();
    });

    it("returns 404 for unknown artifact", async () => {
      const response = await fetch("/api/v1/artifacts/unknown-id");
      expect(response.status).toBe(404);

      const error = await response.json();
      expect(error.detail).toBe("Artifact not found");
    });
  });

  describe("POST /api/v1/artifacts", () => {
    it("creates a new artifact", async () => {
      const request: CreateArtifactRequest = {
        type: "code",
        content: "console.log('hello');",
        sessionId: "session-1",
        title: "New Code Artifact",
        language: "javascript",
      };

      const response = await fetch("/api/v1/artifacts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(201);

      const data = await response.json();
      expect(data.id).toBeDefined();
      expect(data.version).toBe(1);
      expect(data.createdAt).toBeDefined();
    });
  });

  describe("PUT /api/v1/artifacts/:id", () => {
    it("updates an existing artifact", async () => {
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
      expect(data.id).toBe("art-1");
      expect(data.version).toBeGreaterThan(0);
      expect(data.updatedAt).toBeDefined();
    });

    it("returns 404 for unknown artifact", async () => {
      const request: UpdateArtifactRequest = {
        content: "new content",
      };

      const response = await fetch("/api/v1/artifacts/unknown-id", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.status).toBe(404);
    });
  });

  describe("DELETE /api/v1/artifacts/:id", () => {
    it("deletes an artifact", async () => {
      const response = await fetch("/api/v1/artifacts/art-1", {
        method: "DELETE",
      });

      expect(response.status).toBe(204);
    });
  });

  describe("GET /api/v1/artifacts/:id/versions", () => {
    it("returns version history for an artifact", async () => {
      const response = await fetch("/api/v1/artifacts/art-1/versions");
      expect(response.status).toBe(200);

      const versions: ArtifactVersion[] = await response.json();
      expect(Array.isArray(versions)).toBe(true);
      versions.forEach((v) => {
        expect(v.artifactId).toBe("art-1");
        expect(v.version).toBeDefined();
        expect(v.content).toBeDefined();
      });
    });

    it("returns 404 for unknown artifact", async () => {
      const response = await fetch("/api/v1/artifacts/unknown-id/versions");
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/artifacts/:id/fork", () => {
    it("forks an artifact", async () => {
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
      expect(data.id).toBeDefined();
      expect(data.parentId).toBe("art-1");
      expect(data.version).toBe(1);
    });

    it("returns 404 for unknown artifact", async () => {
      const response = await fetch("/api/v1/artifacts/unknown-id/fork", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(404);
    });
  });

  describe("Mock Data", () => {
    it("has pre-defined mock artifacts", () => {
      expect(mockCanvasArtifacts.length).toBeGreaterThan(0);
      mockCanvasArtifacts.forEach((artifact) => {
        expect(artifact.id).toBeDefined();
        expect(artifact.sessionId).toBeDefined();
        expect(artifact.content).toBeDefined();
      });
    });
  });
});

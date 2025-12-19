/**
 * Canvas Loaders Tests
 *
 * Tests for React Router loaders used in HybridShell routes.
 * Phase 2: Contract-First - loaders fetch data before rendering.
 */
import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import { http, HttpResponse } from "msw";
import { canvasHandlers } from "../../mocks/handlers/canvasHandlers";
import {
  chatLoader,
  sessionsLoader,
  artifactLoader,
  type ChatLoaderData,
  type SessionsLoaderData,
  type ArtifactLoaderData,
} from "./canvasLoaders";

// Setup MSW server with canvas handlers
const server = setupServer(...canvasHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "bypass" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

// Mock loader function args
const createLoaderArgs = (
  params: Record<string, string | undefined> = {},
  request?: Request,
) => ({
  params,
  request: request ?? new Request("http://localhost:3000/studio/v2/chat"),
  context: {},
});

describe("canvasLoaders", () => {
  describe("sessionsLoader", () => {
    it("loads a list of sessions", async () => {
      const data = (await sessionsLoader(
        createLoaderArgs(),
      )) as SessionsLoaderData;

      expect(data.sessions).toBeDefined();
      expect(Array.isArray(data.sessions)).toBe(true);
    });

    it("returns an error object on failure", async () => {
      // Mock a server error
      server.use(
        http.get("/api/v1/sessions", () => {
          return HttpResponse.json(
            { detail: "Internal error" },
            { status: 500 },
          );
        }),
      );

      const data = (await sessionsLoader(
        createLoaderArgs(),
      )) as SessionsLoaderData;

      // Should handle error gracefully
      expect(data.sessions).toBeDefined();
    });
  });

  describe("chatLoader", () => {
    it("loads session data when sessionId is provided", async () => {
      const data = (await chatLoader(
        createLoaderArgs({ sessionId: "session-1" }),
      )) as ChatLoaderData;

      expect(data.sessionId).toBe("session-1");
      expect(data.artifacts).toBeDefined();
      expect(Array.isArray(data.artifacts)).toBe(true);
    });

    it("returns empty artifacts when no sessionId", async () => {
      const data = (await chatLoader(createLoaderArgs({}))) as ChatLoaderData;

      expect(data.sessionId).toBeNull();
      expect(data.artifacts).toEqual([]);
    });

    it("loads artifacts for the session", async () => {
      const data = (await chatLoader(
        createLoaderArgs({ sessionId: "session-1" }),
      )) as ChatLoaderData;

      // Should filter artifacts by session
      data.artifacts.forEach((artifact) => {
        expect(artifact.sessionId).toBe("session-1");
      });
    });
  });

  describe("artifactLoader", () => {
    it("loads a specific artifact by id", async () => {
      const data = (await artifactLoader(
        createLoaderArgs({ artifactId: "art-1" }),
      )) as ArtifactLoaderData;

      expect(data.artifact).toBeDefined();
      expect(data.artifact?.id).toBe("art-1");
    });

    it("loads version history for the artifact", async () => {
      const data = (await artifactLoader(
        createLoaderArgs({ artifactId: "art-1" }),
      )) as ArtifactLoaderData;

      expect(data.versions).toBeDefined();
      expect(Array.isArray(data.versions)).toBe(true);
    });

    it("returns null artifact when not found", async () => {
      const data = (await artifactLoader(
        createLoaderArgs({ artifactId: "unknown-id" }),
      )) as ArtifactLoaderData;

      expect(data.artifact).toBeNull();
      expect(data.error).toBeDefined();
    });

    it("returns null when no artifactId provided", async () => {
      const data = (await artifactLoader(
        createLoaderArgs({}),
      )) as ArtifactLoaderData;

      expect(data.artifact).toBeNull();
      expect(data.versions).toEqual([]);
    });
  });
});

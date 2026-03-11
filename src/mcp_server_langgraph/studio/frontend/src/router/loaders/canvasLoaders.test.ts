/**
 * Canvas Loaders Tests
 *
 * TDD tests for React Router loaders that fetch data before rendering.
 * Tests cover sessionsLoader, chatLoader, and artifactLoader.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { LoaderFunctionArgs } from "react-router";
import {
  sessionsLoader,
  chatLoader,
  artifactLoader,
  complianceLoader,
  artifactsLoader,
  canvasLoaders,
} from "./canvasLoaders";

// Mock storage utility
vi.mock("../../utils/storage", async () => {
  const actual = await vi.importActual("../../utils/storage");
  return {
    ...actual,
    getAuthToken: vi.fn(() => "mock-token"),
  };
});
// =============================================================================
// Test Setup
// =============================================================================

const mockFetch = vi.fn();

function createLoaderArgs(
  params: Record<string, string> = {},
): LoaderFunctionArgs {
  return {
    params,
    request: new Request("http://localhost/test"),
    context: undefined,
  };
}

describe("canvasLoaders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===========================================================================
  // sessionsLoader
  // ===========================================================================

  describe("sessionsLoader", () => {
    // =========================================================================
    // v8 Phase 4: Status Filter from URL Search Params
    // =========================================================================

    it("should pass status=active from URL search params to API", async () => {
      // GIVEN: Request with ?status=active in URL
      const mockApiSessions = [
        {
          id: "session-1",
          name: "Active Session",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          status: "active",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockApiSessions }),
      });

      const args: LoaderFunctionArgs = {
        params: {},
        request: new Request("http://localhost/studio?status=active"),
        context: undefined,
      };

      // WHEN: sessionsLoader is called
      const result = await sessionsLoader(args);

      // THEN: Should include status=active in API call
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions?limit=50&status=active",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
          }),
        }),
      );
      expect(result.sessions).toHaveLength(1);
      expect(result.sessions[0].status).toBe("active");
    });

    it("should pass status=archived from URL search params to API", async () => {
      // GIVEN: Request with ?status=archived in URL
      const mockApiSessions = [
        {
          id: "session-2",
          name: "Archived Session",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
          status: "archived",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockApiSessions }),
      });

      const args: LoaderFunctionArgs = {
        params: {},
        request: new Request("http://localhost/studio?status=archived"),
        context: undefined,
      };

      // WHEN: sessionsLoader is called
      const result = await sessionsLoader(args);

      // THEN: Should include status=archived in API call
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions?limit=50&status=archived",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
          }),
        }),
      );
      expect(result.sessions).toHaveLength(1);
      expect(result.sessions[0].status).toBe("archived");
    });

    it("should default to status=active when no status param in URL", async () => {
      // GIVEN: Request with no status param
      const mockApiSessions = [
        {
          id: "session-1",
          name: "Session 1",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockApiSessions }),
      });

      const args: LoaderFunctionArgs = {
        params: {},
        request: new Request("http://localhost/studio"), // No ?status=
        context: undefined,
      };

      // WHEN: sessionsLoader is called
      await sessionsLoader(args);

      // THEN: Should default to status=active
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions?limit=50&status=active",
        expect.any(Object),
      );
    });

    // =========================================================================
    // Existing tests
    // =========================================================================

    it("should return list of sessions on success", async () => {
      const mockApiSessions = [
        {
          id: "session-1",
          name: "Session 1",
          created_at: "2024-01-01T00:00:00Z",
          updated_at: "2024-01-01T00:00:00Z",
        },
        {
          id: "session-2",
          name: "Session 2",
          created_at: "2024-01-02T00:00:00Z",
          updated_at: "2024-01-02T00:00:00Z",
        },
      ];

      // Backend uses CursorPaginatedResponse format with 'data' field
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ data: mockApiSessions }),
      });

      const result = await sessionsLoader(createLoaderArgs());

      expect(result.sessions).toHaveLength(2);
      expect(result.sessions[0].id).toBe("session-1");
      expect(result.sessions[0].name).toBe("Session 1");
      // Session is transformed to camelCase per ADR-0091
      expect(result.sessions[0].createdAt).toBe("2024-01-01T00:00:00Z");
      expect(result.error).toBeUndefined();
      // v8 Phase 4: Now includes status=active by default
      expect(mockFetch).toHaveBeenCalledWith(
        "/api/v1/sessions?limit=50&status=active",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
          }),
        }),
      );
    });

    it("should return error when fetch fails", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const result = await sessionsLoader(createLoaderArgs());

      expect(result.sessions).toEqual([]);
      expect(result.error).toBe("Failed to load sessions");
    });

    it("should return error when network fails", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await sessionsLoader(createLoaderArgs());

      expect(result.sessions).toEqual([]);
      expect(result.error).toBe("Failed to load sessions");
    });
  });

  // ===========================================================================
  // chatLoader
  // ===========================================================================

  describe("chatLoader", () => {
    it("should return empty data when no sessionId provided", async () => {
      const result = await chatLoader(createLoaderArgs());

      expect(result.sessionId).toBeNull();
      expect(result.messages).toEqual([]);
      expect(result.artifacts).toEqual([]);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should fetch session, messages, and artifacts in parallel", async () => {
      const mockApiSession = {
        id: "session-1",
        name: "Test Session",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };
      // Backend uses message_id and timestamp (not id and created_at)
      // Messages endpoint returns plain array (not { items: [...] })
      const mockMessages = [
        {
          message_id: "msg-1",
          role: "user",
          content: "Hello",
          timestamp: "2024-01-01T00:00:00Z",
        },
        {
          message_id: "msg-2",
          role: "assistant",
          content: "Hi!",
          timestamp: "2024-01-01T00:01:00Z",
        },
      ];
      const mockArtifacts = [
        { id: "artifact-1", type: "code", content: "console.log('hello')" },
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiSession),
        })
        .mockResolvedValueOnce({
          ok: true,
          // Messages endpoint returns plain array
          json: () => Promise.resolve(mockMessages),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ items: mockArtifacts }),
        });

      const result = await chatLoader(
        createLoaderArgs({ sessionId: "session-1" }),
      );

      expect(result.sessionId).toBe("session-1");
      expect(result.session?.id).toBe("session-1");
      expect(result.session?.name).toBe("Test Session");
      expect(result.messages).toHaveLength(2);
      expect(result.messages[0].id).toBe("msg-1");
      expect(result.messages[0].content).toBe("Hello");
      // Artifacts are transformed - check core properties
      expect(result.artifacts).toHaveLength(1);
      expect(result.artifacts[0]).toMatchObject({
        id: "artifact-1",
        type: "code",
        content: "console.log('hello')",
      });
    });

    it("should transform message timestamps", async () => {
      const mockApiSession = {
        id: "s1",
        name: "Test",
        created_at: "2024-06-15T10:00:00Z",
        updated_at: "2024-06-15T10:00:00Z",
      };
      // Backend uses message_id and timestamp
      const mockMessages = [
        {
          message_id: "msg-1",
          role: "user",
          content: "Test",
          timestamp: "2024-06-15T10:30:00Z",
        },
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiSession),
        })
        .mockResolvedValueOnce({
          ok: true,
          // Messages endpoint returns plain array
          json: () => Promise.resolve(mockMessages),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ items: [] }),
        });

      const result = await chatLoader(createLoaderArgs({ sessionId: "s1" }));

      expect(result.messages[0].timestamp).toBe(
        new Date("2024-06-15T10:30:00Z").getTime(),
      );
    });

    it("should return error when session not found", async () => {
      mockFetch
        .mockResolvedValueOnce({ ok: false }) // Session not found
        .mockResolvedValueOnce({
          ok: true,
          // Messages endpoint returns plain array
          json: () => Promise.resolve([]),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ items: [] }),
        });

      const result = await chatLoader(
        createLoaderArgs({ sessionId: "invalid" }),
      );

      expect(result.session).toBeUndefined();
      expect(result.error).toBe("Session not found");
    });

    it("should handle partial failures gracefully", async () => {
      const mockApiSession = {
        id: "s1",
        name: "Test",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiSession),
        })
        .mockResolvedValueOnce({ ok: false }) // Messages fail
        .mockResolvedValueOnce({ ok: false }); // Artifacts fail

      const result = await chatLoader(createLoaderArgs({ sessionId: "s1" }));

      expect(result.session?.id).toBe("s1");
      expect(result.messages).toEqual([]);
      expect(result.artifacts).toEqual([]);
      expect(result.error).toBeUndefined();
    });

    it("should handle session validation failure gracefully", async () => {
      // Session missing required fields (id, created_at, updated_at) causes validation failure
      const invalidSession = { name: "No ID Session" };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(invalidSession),
        })
        .mockResolvedValueOnce({
          ok: true,
          // Messages endpoint returns plain array
          json: () => Promise.resolve([]),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ items: [] }),
        });

      const result = await chatLoader(createLoaderArgs({ sessionId: "s1" }));

      // Session should be undefined due to validation failure
      expect(result.session).toBeUndefined();
      expect(result.messages).toEqual([]);
    });

    it("should handle message validation failure gracefully", async () => {
      const mockApiSession = {
        id: "s1",
        name: "Test",
        created_at: "2024-01-01T00:00:00Z",
        updated_at: "2024-01-01T00:00:00Z",
      };
      // Messages missing required fields (message_id, role, timestamp)
      const invalidMessages = [
        { content: "No message_id or role" }, // Missing message_id, role, timestamp
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockApiSession),
        })
        .mockResolvedValueOnce({
          ok: true,
          // Messages endpoint returns plain array
          json: () => Promise.resolve(invalidMessages),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ items: [] }),
        });

      const result = await chatLoader(createLoaderArgs({ sessionId: "s1" }));

      expect(result.session?.id).toBe("s1");
      // Messages should be empty due to validation failure
      expect(result.messages).toEqual([]);
    });
  });

  // ===========================================================================
  // artifactLoader
  // ===========================================================================

  describe("artifactLoader", () => {
    it("should return null when no artifactId provided", async () => {
      const result = await artifactLoader(createLoaderArgs());

      expect(result.artifact).toBeNull();
      expect(result.versions).toEqual([]);
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it("should fetch artifact and versions in parallel", async () => {
      const mockArtifact = {
        id: "artifact-1",
        type: "code",
        content: 'console.log("test")',
        version: 3,
      };
      const mockVersions = [
        { version: 1, content: "v1" },
        { version: 2, content: "v2" },
        { version: 3, content: 'console.log("test")' },
      ];

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockArtifact),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockVersions),
        });

      const result = await artifactLoader(
        createLoaderArgs({ artifactId: "artifact-1" }),
      );

      // Artifact is transformed - check core properties
      expect(result.artifact).toMatchObject({
        id: "artifact-1",
        type: "code",
        content: 'console.log("test")',
        version: 3,
      });
      expect(result.versions).toEqual(mockVersions);
      expect(result.error).toBeUndefined();
    });

    it("should return error when artifact not found", async () => {
      mockFetch
        .mockResolvedValueOnce({ ok: false })
        .mockResolvedValueOnce({ ok: true, json: () => Promise.resolve([]) });

      const result = await artifactLoader(
        createLoaderArgs({ artifactId: "invalid" }),
      );

      expect(result.artifact).toBeNull();
      expect(result.error).toBe("Artifact not found");
    });

    it("should handle version fetch failure gracefully", async () => {
      const mockArtifact = { id: "a1", type: "code", content: "test" };

      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockArtifact),
        })
        .mockResolvedValueOnce({ ok: false }); // Versions fail

      const result = await artifactLoader(
        createLoaderArgs({ artifactId: "a1" }),
      );

      // Artifact is transformed - check core properties
      expect(result.artifact).toMatchObject({
        id: "a1",
        type: "code",
        content: "test",
      });
      expect(result.versions).toEqual([]);
    });
  });

  // ===========================================================================
  // canvasLoaders export
  // ===========================================================================

  // ===========================================================================
  // complianceLoader
  // ===========================================================================

  describe("complianceLoader", () => {
    it("should fetch compliance summary on success", async () => {
      const mockSummary = {
        soc2: { percentage: 94, status: "compliant" },
        hipaa: { percentage: 100, status: "compliant" },
        gdpr: { percentage: 87, status: "partial" },
        fedramp: { percentage: 92, status: "compliant" },
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockSummary),
      });

      const result = await complianceLoader(createLoaderArgs());

      expect(result.summary).toEqual(mockSummary);
      expect(result.error).toBeUndefined();
      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/compliance/reports/summary"),
        expect.any(Object),
      );
    });

    it("should handle failure gracefully", async () => {
      mockFetch.mockResolvedValueOnce({ ok: false });

      const result = await complianceLoader(createLoaderArgs());

      expect(result.summary).toBeNull();
      expect(result.error).toBe("Failed to load compliance summary");
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await complianceLoader(createLoaderArgs());

      expect(result.summary).toBeNull();
      expect(result.error).toBe("Failed to load compliance summary");
    });
  });

  describe("canvasLoaders export", () => {
    it("should export all loaders", () => {
      expect(canvasLoaders.sessions).toBe(sessionsLoader);
      expect(canvasLoaders.chat).toBe(chatLoader);
      expect(canvasLoaders.artifact).toBe(artifactLoader);
      expect(canvasLoaders.compliance).toBe(complianceLoader);
      expect(canvasLoaders.artifacts).toBe(artifactsLoader);
    });
  });

  describe("artifactsLoader (files)", () => {
    it("should load artifacts successfully", async () => {
      const mockArtifacts = [
        {
          id: "artifact-1",
          type: "code" as const,
          content: "console.log('hello');",
          sessionId: "session-1",
          version: 1,
          createdAt: "2025-01-15T10:00:00Z",
          updatedAt: "2025-01-15T10:00:00Z",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: mockArtifacts, total: 1 }),
      });

      const result = await artifactsLoader(createLoaderArgs());

      expect(result.artifacts).toHaveLength(1);
      expect(result.total).toBe(1);
      expect(result.error).toBeUndefined();
    });

    it("should return empty array on API failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: () => Promise.resolve({ detail: "Server error" }),
      });

      const result = await artifactsLoader(createLoaderArgs());

      expect(result.artifacts).toEqual([]);
      expect(result.total).toBe(0);
      expect(result.error).toBe("Failed to load artifacts");
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const result = await artifactsLoader(createLoaderArgs());

      expect(result.artifacts).toEqual([]);
      expect(result.total).toBe(0);
      expect(result.error).toBe("Failed to load artifacts");
    });

    it("should use items length when total not provided", async () => {
      const mockArtifacts = [
        {
          id: "artifact-1",
          type: "code" as const,
          content: "code1",
          sessionId: "session-1",
          version: 1,
          createdAt: "2025-01-15T10:00:00Z",
          updatedAt: "2025-01-15T10:00:00Z",
        },
        {
          id: "artifact-2",
          type: "code" as const,
          content: "code2",
          sessionId: "session-1",
          version: 1,
          createdAt: "2025-01-15T10:00:00Z",
          updatedAt: "2025-01-15T10:00:00Z",
        },
      ];

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: mockArtifacts }), // no total
      });

      const result = await artifactsLoader(createLoaderArgs());

      expect(result.artifacts).toHaveLength(2);
      expect(result.total).toBe(2); // Uses items.length as fallback
    });
  });

  // ===========================================================================
  // Auth headers
  // ===========================================================================

  describe("Authentication", () => {
    it("should include auth token in requests", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ items: [] }),
      });

      await sessionsLoader(createLoaderArgs());

      expect(mockFetch).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-token",
            "Content-Type": "application/json",
          }),
          credentials: "include",
        }),
      );
    });
  });
});

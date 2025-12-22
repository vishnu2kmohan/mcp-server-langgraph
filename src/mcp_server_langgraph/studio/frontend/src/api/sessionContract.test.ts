/**
 * Session API Contract Tests
 *
 * Verifies API schema matches backend for session management.
 * Reference: src/mcp_server_langgraph/api/v1/router.py (session endpoints)
 *
 * Uses raw fetch() to validate API contract without RTK Query transformation.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

// =============================================================================
// MSW Handler Factory for Sessions
// =============================================================================

/**
 * Create default handlers for session endpoints.
 * Uses server.use() to add handlers to the global MSW server.
 *
 * NOTE: Static paths MUST come before parameterized paths to avoid conflicts.
 * Order: /sessions/generate-title BEFORE /sessions/:id
 */
function setupSessionHandlers() {
  server.use(
    // NOTE: Static paths MUST come before parameterized paths to avoid conflicts
    // POST /api/v1/sessions/generate-title - Generate session title
    http.post("/api/v1/sessions/generate-title", async ({ request }) => {
      const body = (await request.json()) as { messages: Array<{ role: string; content: string }> };
      return HttpResponse.json({
        title:
          body.messages.length > 0
            ? `Session: ${body.messages[0].content.substring(0, 30)}...`
            : "New Session",
      });
    }),

    // GET /api/v1/sessions - List sessions with pagination
    http.get("/api/v1/sessions", ({ request }) => {
      const url = new URL(request.url);
      const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
      const cursor = url.searchParams.get("cursor");
      const search = url.searchParams.get("search");

      let sessions = [
        {
          id: "session-001",
          name: "Research Session",
          workflow_id: "wf-123",
          user_id: "user-001",
          status: "active",
          created_at: "2024-01-15T10:00:00Z",
          updated_at: "2024-01-15T12:30:00Z",
          config: {
            model: "gpt-4",
            temperature: 0.7,
            max_tokens: 4096,
          },
        },
        {
          id: "session-002",
          name: "Code Review Session",
          workflow_id: null,
          user_id: "user-001",
          status: "active",
          created_at: "2024-01-14T09:00:00Z",
          updated_at: "2024-01-14T15:00:00Z",
          config: {
            model: "gpt-4-turbo",
            temperature: 0.3,
            max_tokens: 8192,
          },
        },
        {
          id: "session-003",
          name: "Archived Session",
          workflow_id: null,
          user_id: "user-001",
          status: "archived",
          created_at: "2024-01-10T08:00:00Z",
          updated_at: "2024-01-12T16:00:00Z",
          config: null,
        },
      ];

      // Filter by search
      if (search) {
        sessions = sessions.filter((s) =>
          s.name.toLowerCase().includes(search.toLowerCase())
        );
      }

      // Simulate cursor pagination
      let startIndex = 0;
      if (cursor) {
        startIndex = sessions.findIndex((s) => s.id === cursor);
        if (startIndex === -1) startIndex = 0;
        else startIndex += 1;
      }

      const items = sessions.slice(startIndex, startIndex + limit);
      const nextCursor = items.length === limit ? items[items.length - 1].id : null;

      return HttpResponse.json({
        items,
        next_cursor: nextCursor,
        total: sessions.length,
      });
    }),

    // GET /api/v1/sessions/:id - Get single session
    http.get("/api/v1/sessions/:id", ({ params }) => {
      const id = params.id as string;
      if (id === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return HttpResponse.json({
        id,
        name: "Research Session",
        workflow_id: "wf-123",
        user_id: "user-001",
        status: "active",
        created_at: "2024-01-15T10:00:00Z",
        updated_at: "2024-01-15T12:30:00Z",
        config: {
          model: "gpt-4",
          temperature: 0.7,
          max_tokens: 4096,
        },
      });
    }),

    // POST /api/v1/sessions - Create new session
    http.post("/api/v1/sessions", async ({ request }) => {
      const body = (await request.json()) as { name?: string; workflow_id?: string };
      return HttpResponse.json({
        id: "session-new-001",
        name: body.name || "New Session",
        workflow_id: body.workflow_id || null,
        user_id: "user-001",
        status: "active",
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
        config: {
          model: "gpt-4",
          temperature: 0.7,
          max_tokens: 4096,
        },
      });
    }),

    // DELETE /api/v1/sessions/:id - Delete session
    http.delete("/api/v1/sessions/:id", ({ params }) => {
      const id = params.id as string;
      if (id === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return new HttpResponse(null, { status: 204 });
    }),

    // PUT /api/v1/sessions/:id/config - Update session configuration
    http.put("/api/v1/sessions/:id/config", async ({ params, request }) => {
      const id = params.id as string;
      const body = (await request.json()) as {
        model?: string;
        temperature?: number;
        max_tokens?: number;
      };
      return HttpResponse.json({
        id,
        name: "Research Session",
        workflow_id: "wf-123",
        user_id: "user-001",
        status: "active",
        created_at: "2024-01-15T10:00:00Z",
        updated_at: new Date().toISOString(),
        config: {
          model: body.model || "gpt-4",
          temperature: body.temperature ?? 0.7,
          max_tokens: body.max_tokens ?? 4096,
        },
      });
    }),

    // GET /api/v1/sessions/:id/messages - Get session messages
    http.get("/api/v1/sessions/:id/messages", ({ params }) => {
      const sessionId = params.id as string;
      if (sessionId === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return HttpResponse.json([
        {
          message_id: "msg-001",
          role: "user",
          content: "Hello, I need help with a research task.",
          timestamp: "2024-01-15T10:00:00Z",
          metadata: {},
        },
        {
          message_id: "msg-002",
          role: "assistant",
          content: "I'd be happy to help with your research. What topic are you exploring?",
          timestamp: "2024-01-15T10:00:05Z",
          metadata: { model: "gpt-4" },
          sources: [
            {
              id: "src-001",
              title: "Research Guide",
              url: "https://example.com/guide",
              content: "Research methodology overview...",
            },
          ],
        },
      ]);
    }),

    // POST /api/v1/sessions/:id/export - Export session
    http.post("/api/v1/sessions/:id/export", async ({ params, request }) => {
      const sessionId = params.id as string;
      const body = (await request.json()) as {
        format: "markdown" | "json" | "html";
        include_metadata?: boolean;
      };

      // Return blob-like response based on format
      if (body.format === "json") {
        return HttpResponse.json({
          session_id: sessionId,
          exported_at: new Date().toISOString(),
          format: "json",
          messages: [
            { role: "user", content: "Hello" },
            { role: "assistant", content: "Hi there!" },
          ],
        });
      }

      // For markdown and html, return as blob
      const content =
        body.format === "markdown"
          ? `# Session Export\n\n**User:** Hello\n\n**Assistant:** Hi there!`
          : `<html><body><h1>Session Export</h1><p>User: Hello</p><p>Assistant: Hi there!</p></body></html>`;

      return new HttpResponse(content, {
        headers: {
          "Content-Type":
            body.format === "markdown" ? "text/markdown" : "text/html",
          "Content-Disposition": `attachment; filename="session-${sessionId}.${body.format === "markdown" ? "md" : "html"}"`,
        },
      });
    }),

    // POST /api/v1/sessions/:id/bootstrap-workflow - Bootstrap workflow from session
    http.post("/api/v1/sessions/:id/bootstrap-workflow", async ({ params }) => {
      const sessionId = params.id as string;
      return HttpResponse.json({
        workflow_id: `wf-from-${sessionId}`,
        name: `Workflow from Session ${sessionId}`,
        node_count: 3,
        edge_count: 2,
        created_at: new Date().toISOString(),
      });
    })
  );
}

// Set up handlers before each test, reset after
beforeEach(() => {
  setupSessionHandlers();
});

afterEach(() => {
  server.resetHandlers();
});

// =============================================================================
// Schema Type Definitions (matching backend Pydantic models)
// =============================================================================

interface ApiSessionConfig {
  model: string;
  temperature: number;
  max_tokens: number;
}

interface Session {
  id: string;
  name: string;
  workflow_id: string | null;
  user_id: string;
  status: "active" | "archived" | "deleted";
  created_at: string;
  updated_at: string;
  config: ApiSessionConfig | null;
}

interface SessionListResponse {
  items: Session[];
  next_cursor: string | null;
  total: number;
}

interface Message {
  message_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: string;
  metadata?: Record<string, unknown>;
  sources?: Array<{
    id: string;
    title: string;
    url: string;
    content?: string;
  }>;
}

// =============================================================================
// Contract Tests
// =============================================================================

describe("Session API Contract", () => {
  describe("GET /api/v1/sessions", () => {
    it("should return paginated session list", async () => {
      const response = await fetch("/api/v1/sessions?limit=10");
      expect(response.ok).toBe(true);

      const data: SessionListResponse = await response.json();

      // Validate PaginatedResponse schema
      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("next_cursor");
      expect(data).toHaveProperty("total");
      expect(Array.isArray(data.items)).toBe(true);
    });

    it("should validate Session schema in list response", async () => {
      const response = await fetch("/api/v1/sessions");
      const data: SessionListResponse = await response.json();

      expect(data.items.length).toBeGreaterThan(0);
      const session = data.items[0];

      // Validate Session schema
      expect(typeof session.id).toBe("string");
      expect(typeof session.name).toBe("string");
      expect(["active", "archived", "deleted"]).toContain(session.status);
      expect(typeof session.created_at).toBe("string");
      expect(typeof session.updated_at).toBe("string");
    });

    it("should support search filtering", async () => {
      const response = await fetch("/api/v1/sessions?search=Research");
      expect(response.ok).toBe(true);

      const data: SessionListResponse = await response.json();
      expect(data.items.some((s) => s.name.includes("Research"))).toBe(true);
    });

    it("should support cursor pagination", async () => {
      const response = await fetch("/api/v1/sessions?limit=1");
      const data: SessionListResponse = await response.json();

      // With limit=1, should have next cursor
      expect(data.items).toHaveLength(1);
      expect(data.next_cursor).not.toBeNull();
    });
  });

  describe("GET /api/v1/sessions/:id", () => {
    it("should return single session with all fields", async () => {
      const response = await fetch("/api/v1/sessions/session-001");
      expect(response.ok).toBe(true);

      const session: Session = await response.json();

      expect(session.id).toBe("session-001");
      expect(typeof session.name).toBe("string");
      expect(["active", "archived", "deleted"]).toContain(session.status);
      expect(typeof session.created_at).toBe("string");
      expect(typeof session.updated_at).toBe("string");
    });

    it("should include optional config when present", async () => {
      const response = await fetch("/api/v1/sessions/session-001");
      const session: Session = await response.json();

      expect(session.config).toBeDefined();
      if (session.config) {
        expect(typeof session.config.model).toBe("string");
        expect(typeof session.config.temperature).toBe("number");
        expect(typeof session.config.max_tokens).toBe("number");
      }
    });

    it("should return 404 for non-existent session", async () => {
      const response = await fetch("/api/v1/sessions/not-found");
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/sessions", () => {
    it("should create new session with name", async () => {
      const response = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "My New Session",
          workflow_id: "wf-123",
        }),
      });

      expect(response.ok).toBe(true);
      const session: Session = await response.json();

      expect(typeof session.id).toBe("string");
      expect(session.name).toBe("My New Session");
      expect(session.status).toBe("active");
    });

    it("should create session without name (uses default)", async () => {
      const response = await fetch("/api/v1/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      expect(response.ok).toBe(true);
      const session: Session = await response.json();

      expect(session.name).toBe("New Session");
    });
  });

  describe("DELETE /api/v1/sessions/:id", () => {
    it("should delete session and return 204", async () => {
      const response = await fetch("/api/v1/sessions/session-001", {
        method: "DELETE",
      });

      expect(response.status).toBe(204);
    });

    it("should return 404 for non-existent session", async () => {
      const response = await fetch("/api/v1/sessions/not-found", {
        method: "DELETE",
      });

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/sessions/generate-title", () => {
    it("should generate title from messages", async () => {
      const response = await fetch("/api/v1/sessions/generate-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            { role: "user", content: "Help me understand machine learning algorithms" },
          ],
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(typeof data.title).toBe("string");
      expect(data.title.length).toBeGreaterThan(0);
    });

    it("should generate default title for empty messages", async () => {
      const response = await fetch("/api/v1/sessions/generate-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: [] }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.title).toBe("New Session");
    });
  });

  describe("PUT /api/v1/sessions/:id/config", () => {
    it("should update session configuration", async () => {
      const response = await fetch("/api/v1/sessions/session-001/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "gpt-4-turbo",
          temperature: 0.5,
          max_tokens: 8192,
        }),
      });

      expect(response.ok).toBe(true);
      const session: Session = await response.json();

      expect(session.config?.model).toBe("gpt-4-turbo");
      expect(session.config?.temperature).toBe(0.5);
      expect(session.config?.max_tokens).toBe(8192);
    });

    it("should allow partial config updates", async () => {
      const response = await fetch("/api/v1/sessions/session-001/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          temperature: 0.9,
        }),
      });

      expect(response.ok).toBe(true);
      const session: Session = await response.json();

      expect(session.config?.temperature).toBe(0.9);
      // Other fields should retain defaults
      expect(session.config?.model).toBe("gpt-4");
    });
  });

  describe("GET /api/v1/sessions/:id/messages", () => {
    it("should return array of messages", async () => {
      const response = await fetch("/api/v1/sessions/session-001/messages");
      expect(response.ok).toBe(true);

      const messages: Message[] = await response.json();

      expect(Array.isArray(messages)).toBe(true);
      expect(messages.length).toBeGreaterThan(0);
    });

    it("should validate Message schema", async () => {
      const response = await fetch("/api/v1/sessions/session-001/messages");
      const messages: Message[] = await response.json();

      const message = messages[0];
      expect(typeof message.message_id).toBe("string");
      expect(["user", "assistant", "system"]).toContain(message.role);
      expect(typeof message.content).toBe("string");
      expect(typeof message.timestamp).toBe("string");
    });

    it("should include sources for assistant messages when available", async () => {
      const response = await fetch("/api/v1/sessions/session-001/messages");
      const messages: Message[] = await response.json();

      const assistantMessage = messages.find((m) => m.role === "assistant");
      expect(assistantMessage?.sources).toBeDefined();
      if (assistantMessage?.sources) {
        expect(assistantMessage.sources.length).toBeGreaterThan(0);
        const source = assistantMessage.sources[0];
        expect(typeof source.id).toBe("string");
        expect(typeof source.title).toBe("string");
        expect(typeof source.url).toBe("string");
      }
    });

    it("should return 404 for non-existent session", async () => {
      const response = await fetch("/api/v1/sessions/not-found/messages");
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/sessions/:id/export", () => {
    it("should export session as JSON", async () => {
      const response = await fetch("/api/v1/sessions/session-001/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          format: "json",
          include_metadata: true,
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.session_id).toBe("session-001");
      expect(data.format).toBe("json");
      expect(Array.isArray(data.messages)).toBe(true);
    });

    it("should export session as markdown", async () => {
      const response = await fetch("/api/v1/sessions/session-001/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          format: "markdown",
        }),
      });

      expect(response.ok).toBe(true);
      expect(response.headers.get("Content-Type")).toContain("text/markdown");

      const content = await response.text();
      expect(content).toContain("# Session Export");
    });

    it("should export session as HTML", async () => {
      const response = await fetch("/api/v1/sessions/session-001/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          format: "html",
        }),
      });

      expect(response.ok).toBe(true);
      expect(response.headers.get("Content-Type")).toContain("text/html");

      const content = await response.text();
      expect(content).toContain("<html>");
    });
  });

  describe("POST /api/v1/sessions/:id/bootstrap-workflow", () => {
    it("should create workflow from session", async () => {
      const response = await fetch(
        "/api/v1/sessions/session-001/bootstrap-workflow",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(typeof data.workflow_id).toBe("string");
      expect(typeof data.name).toBe("string");
      expect(typeof data.node_count).toBe("number");
      expect(typeof data.edge_count).toBe("number");
    });
  });
});

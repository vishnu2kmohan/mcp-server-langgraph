/**
 * Connection API Contract Tests
 *
 * Verifies API schema matches backend for MCP connection management.
 * Reference: src/mcp_server_langgraph/api/v1/router.py (connection endpoints)
 *
 * Uses raw fetch() to validate API contract without RTK Query transformation.
 *
 * NOTE: Static paths MUST come before parameterized paths to avoid MSW conflicts.
 * Order: /connections/audit/logs BEFORE /connections/:id
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

// =============================================================================
// MSW Handler Factory for Connections
// =============================================================================

/**
 * Create default handlers for connection endpoints.
 * Uses server.use() to add handlers to the global MSW server.
 *
 * CRITICAL: Static paths MUST come before parameterized paths to avoid conflicts.
 * Example: /connections/audit/logs BEFORE /connections/:id
 */
function setupConnectionHandlers() {
  server.use(
    // NOTE: Static paths MUST come before parameterized paths to avoid conflicts
    // Order: bulk operations, audit, templates, then :id handlers

    // ===========================================================================
    // Bulk Operations (static paths first)
    // ===========================================================================

    // POST /api/v1/connections/bulk/delete - Bulk delete connections
    http.post("/api/v1/connections/bulk/delete", async ({ request }) => {
      const body = (await request.json()) as { connection_ids: string[] };
      const failedIds = body.connection_ids.filter((id) => id === "conn-fail");
      return HttpResponse.json({
        deleted_count: body.connection_ids.length - failedIds.length,
        failed_ids: failedIds,
      });
    }),

    // POST /api/v1/connections/bulk/test - Bulk test connections
    http.post("/api/v1/connections/bulk/test", async ({ request }) => {
      const body = (await request.json()) as { connection_ids: string[] };
      const results = body.connection_ids.map((id) => ({
        connection_id: id,
        success: id !== "conn-fail",
        server_name: id !== "conn-fail" ? "Test Server" : null,
        server_version: id !== "conn-fail" ? "1.0.0" : null,
        tool_count: id !== "conn-fail" ? 5 : 0,
        error: id === "conn-fail" ? "Connection timeout" : null,
      }));
      return HttpResponse.json({
        results,
        not_found: [],
      });
    }),

    // POST /api/v1/connections/bulk/status - Bulk update connection status
    http.post("/api/v1/connections/bulk/status", async ({ request }) => {
      const body = (await request.json()) as {
        connection_ids: string[];
        status: string;
      };
      return HttpResponse.json({
        updated_count: body.connection_ids.length,
        failed_ids: [],
      });
    }),

    // ===========================================================================
    // Connection Audit (static paths before :id)
    // ===========================================================================

    // POST /api/v1/connections/audit/log - Log audit event
    http.post("/api/v1/connections/audit/log", async ({ request }) => {
      const body = (await request.json()) as {
        connection_id: string;
        action: string;
        details?: Record<string, unknown>;
      };
      return HttpResponse.json({
        id: "audit-001",
        connection_id: body.connection_id,
        action: body.action,
        details: body.details || {},
        created_at: new Date().toISOString(),
      });
    }),

    // GET /api/v1/connections/audit/logs - Query audit logs
    http.get("/api/v1/connections/audit/logs", ({ request }) => {
      const url = new URL(request.url);
      const limit = parseInt(url.searchParams.get("limit") ?? "50", 10);

      return HttpResponse.json({
        logs: [
          {
            id: "audit-001",
            connection_id: "conn-001",
            action: "test",
            actor: "user@example.com",
            details: { result: "success" },
            created_at: "2024-01-15T10:00:00Z",
          },
          {
            id: "audit-002",
            connection_id: "conn-001",
            action: "update",
            actor: "admin@example.com",
            details: {
              field: "name",
              old_value: "Old Name",
              new_value: "New Name",
            },
            created_at: "2024-01-15T09:00:00Z",
          },
        ].slice(0, limit),
        total: 2,
        offset: 0,
      });
    }),

    // DELETE /api/v1/connections/audit/retention - Delete old audit logs
    http.delete("/api/v1/connections/audit/retention", ({ request }) => {
      const url = new URL(request.url);
      const days = parseInt(url.searchParams.get("days") ?? "30", 10);
      return HttpResponse.json({
        deleted_count: days > 60 ? 100 : 20,
      });
    }),

    // GET /api/v1/connections/audit/export - Export audit logs
    http.get("/api/v1/connections/audit/export", () => {
      const csvContent = `id,connection_id,action,actor,created_at
audit-001,conn-001,test,user@example.com,2024-01-15T10:00:00Z
audit-002,conn-001,update,admin@example.com,2024-01-15T09:00:00Z`;

      return new HttpResponse(csvContent, {
        headers: {
          "Content-Type": "text/csv",
          "Content-Disposition": "attachment; filename=audit-export.csv",
        },
      });
    }),

    // ===========================================================================
    // Connection Templates
    // ===========================================================================

    // GET /api/v1/connection-templates/categories - List template categories
    http.get("/api/v1/connection-templates/categories", () => {
      return HttpResponse.json({
        categories: [
          {
            id: "ai",
            name: "AI & ML",
            description: "AI and machine learning tools",
          },
          {
            id: "data",
            name: "Data",
            description: "Data sources and databases",
          },
          {
            id: "productivity",
            name: "Productivity",
            description: "Productivity tools",
          },
        ],
      });
    }),

    // GET /api/v1/connection-templates - List templates
    http.get("/api/v1/connection-templates", ({ request }) => {
      const url = new URL(request.url);
      const category = url.searchParams.get("category");

      let templates = [
        {
          id: "tmpl-openai",
          name: "OpenAI",
          description: "Connect to OpenAI API",
          category: "ai",
          auth_type: "api_key",
          icon_url: "https://example.com/openai.svg",
        },
        {
          id: "tmpl-postgres",
          name: "PostgreSQL",
          description: "Connect to PostgreSQL database",
          category: "data",
          auth_type: "api_key",
          icon_url: "https://example.com/postgres.svg",
        },
      ];

      if (category) {
        templates = templates.filter((t) => t.category === category);
      }

      return HttpResponse.json({
        templates,
        total: templates.length,
      });
    }),

    // GET /api/v1/connection-templates/:id - Get template details
    http.get("/api/v1/connection-templates/:id", ({ params }) => {
      const templateId = params.id as string;
      if (templateId === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return HttpResponse.json({
        id: templateId,
        name: templateId === "tmpl-openai" ? "OpenAI" : "Unknown Template",
        description: "Template description",
        category: "ai",
        auth_type: "api_key",
        url_template: "https://api.openai.com/v1",
        required_env_vars: ["OPENAI_API_KEY"],
        optional_env_vars: ["OPENAI_ORG_ID"],
        setup_instructions: "1. Get API key\n2. Create connection",
      });
    }),

    // POST /api/v1/connection-templates/:id/apply - Apply template
    http.post(
      "/api/v1/connection-templates/:id/apply",
      async ({ params, request }) => {
        const templateId = params.id as string;
        const body = (await request.json()) as {
          name?: string;
          env_vars?: Record<string, string>;
        };
        return HttpResponse.json({
          connection: {
            name: body.name || `Connection from ${templateId}`,
            description: "Created from template",
            status: "disconnected",
          },
        });
      },
    ),

    // ===========================================================================
    // Connection CRUD (parameterized paths last)
    // ===========================================================================

    // GET /api/v1/connections - List connections
    http.get("/api/v1/connections", ({ request }) => {
      const url = new URL(request.url);
      const status = url.searchParams.get("status");
      const search = url.searchParams.get("search");
      const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);

      let connections = [
        {
          id: "conn-001",
          name: "OpenAI Connection",
          url: "https://api.openai.com/v1",
          transport: "streamable_http",
          auth_type: "api_key",
          status: "connected",
          server_name: "OpenAI MCP Server",
          tool_count: 5,
          resource_count: 0,
          prompt_count: 3,
          last_connected_at: "2024-01-15T10:00:00Z",
          created_at: "2024-01-10T08:00:00Z",
        },
        {
          id: "conn-002",
          name: "Local Server",
          url: "stdio://local-server",
          transport: "stdio",
          auth_type: "none",
          status: "disconnected",
          server_name: null,
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
          last_connected_at: null,
          created_at: "2024-01-12T09:00:00Z",
        },
        {
          id: "conn-003",
          name: "Error Connection",
          url: "https://error.example.com",
          transport: "streamable_http",
          auth_type: "oauth2",
          status: "error",
          server_name: null,
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
          last_connected_at: null,
          created_at: "2024-01-14T11:00:00Z",
        },
      ];

      // Filter by status
      if (status) {
        connections = connections.filter((c) => c.status === status);
      }

      // Filter by search
      if (search) {
        connections = connections.filter((c) =>
          c.name.toLowerCase().includes(search.toLowerCase()),
        );
      }

      const items = connections.slice(0, limit);

      return HttpResponse.json({
        items,
        total: connections.length,
        cursor:
          items.length < connections.length ? items[items.length - 1].id : null,
      });
    }),

    // GET /api/v1/connections/:id - Get single connection
    http.get("/api/v1/connections/:id", ({ params }) => {
      const id = params.id as string;
      if (id === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return HttpResponse.json({
        id,
        name: "OpenAI Connection",
        description: "Production OpenAI API connection",
        url: "https://api.openai.com/v1",
        transport: "streamable_http",
        auth_type: "api_key",
        oauth2_config: null,
        command: null,
        args: null,
        env: null,
        status: "connected",
        last_error: null,
        last_connected_at: "2024-01-15T10:00:00Z",
        server_name: "OpenAI MCP Server",
        server_version: "1.0.0",
        server_capabilities: { tools: true, resources: false, prompts: true },
        tool_count: 5,
        resource_count: 0,
        prompt_count: 3,
        owner_id: "user-001",
        organization_id: "org-001",
        project_id: null,
        created_at: "2024-01-10T08:00:00Z",
        updated_at: "2024-01-15T10:00:00Z",
      });
    }),

    // POST /api/v1/connections - Create connection
    http.post("/api/v1/connections", async ({ request }) => {
      const body = (await request.json()) as {
        name: string;
        description?: string;
        url: string;
        transport?: string;
        auth_type?: string;
        api_key?: string;
      };
      return HttpResponse.json({
        id: "conn-new-001",
        name: body.name,
        description: body.description || null,
        url: body.url,
        transport: body.transport || "streamable_http",
        auth_type: body.auth_type || "none",
        oauth2_config: null,
        command: null,
        args: null,
        env: null,
        status: "disconnected",
        last_error: null,
        last_connected_at: null,
        server_name: null,
        server_version: null,
        server_capabilities: null,
        tool_count: 0,
        resource_count: 0,
        prompt_count: 0,
        owner_id: "user-001",
        organization_id: null,
        project_id: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      });
    }),

    // PUT /api/v1/connections/:id - Update connection
    http.put("/api/v1/connections/:id", async ({ params, request }) => {
      const id = params.id as string;
      const body = (await request.json()) as {
        name?: string;
        description?: string;
        url?: string;
      };
      return HttpResponse.json({
        id,
        name: body.name || "OpenAI Connection",
        description: body.description ?? "Production OpenAI API connection",
        url: body.url || "https://api.openai.com/v1",
        transport: "streamable_http",
        auth_type: "api_key",
        oauth2_config: null,
        command: null,
        args: null,
        env: null,
        status: "connected",
        last_error: null,
        last_connected_at: "2024-01-15T10:00:00Z",
        server_name: "OpenAI MCP Server",
        server_version: "1.0.0",
        server_capabilities: { tools: true, resources: false, prompts: true },
        tool_count: 5,
        resource_count: 0,
        prompt_count: 3,
        owner_id: "user-001",
        organization_id: "org-001",
        project_id: null,
        created_at: "2024-01-10T08:00:00Z",
        updated_at: new Date().toISOString(),
      });
    }),

    // DELETE /api/v1/connections/:id - Delete connection
    http.delete("/api/v1/connections/:id", ({ params }) => {
      const id = params.id as string;
      if (id === "not-found") {
        return new HttpResponse(null, { status: 404 });
      }
      return new HttpResponse(null, { status: 204 });
    }),

    // POST /api/v1/connections/:id/test - Test connection
    http.post("/api/v1/connections/:id/test", ({ params }) => {
      const id = params.id as string;
      if (id === "conn-fail") {
        return HttpResponse.json({
          success: false,
          server_name: null,
          server_version: null,
          tool_count: 0,
          resource_count: 0,
          prompt_count: 0,
          error: "Connection timeout: server did not respond",
        });
      }
      return HttpResponse.json({
        success: true,
        server_name: "OpenAI MCP Server",
        server_version: "1.0.0",
        tool_count: 5,
        resource_count: 0,
        prompt_count: 3,
        error: null,
      });
    }),

    // POST /api/v1/connections/:id/oauth/start - Start OAuth2 flow
    http.post("/api/v1/connections/:id/oauth/start", ({ params }) => {
      const id = params.id as string;
      return HttpResponse.json({
        authorization_url: `https://oauth.example.com/authorize?client_id=xxx&redirect_uri=xxx&state=${id}`,
        state: `oauth-state-${id}`,
      });
    }),

    // GET /api/v1/connections/:id/audit - Get connection-specific audit log
    http.get("/api/v1/connections/:id/audit", ({ params, request }) => {
      const connectionId = params.id as string;
      const url = new URL(request.url);
      const limit = parseInt(url.searchParams.get("limit") ?? "50", 10);

      return HttpResponse.json({
        logs: [
          {
            id: "audit-001",
            connection_id: connectionId,
            action: "test",
            actor: "user@example.com",
            details: { result: "success" },
            created_at: "2024-01-15T10:00:00Z",
          },
        ].slice(0, limit),
        total: 1,
        offset: 0,
      });
    }),
  );
}

// Set up handlers before each test, reset after
beforeEach(() => {
  setupConnectionHandlers();
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

// Import types from connection module (avoid duplication)
import type {
  MCPConnection,
  ConnectionListResponse,
  MCPConnectionTestResult,
  OAuth2StartResponse,
} from "../types/connection";

// =============================================================================
// Contract Tests
// =============================================================================

describe("Connection API Contract", () => {
  describe("GET /api/v1/connections", () => {
    it("should return paginated connection list", async () => {
      const response = await fetch("/api/v1/connections?limit=10");
      expect(response.ok).toBe(true);

      const data: ConnectionListResponse = await response.json();

      // Validate ConnectionListResponse schema
      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("total");
      expect(data).toHaveProperty("cursor");
      expect(Array.isArray(data.items)).toBe(true);
    });

    it("should validate MCPConnectionSummary schema", async () => {
      const response = await fetch("/api/v1/connections");
      const data: ConnectionListResponse = await response.json();

      expect(data.items.length).toBeGreaterThan(0);
      const conn = data.items[0];

      // Required fields
      expect(typeof conn.id).toBe("string");
      expect(typeof conn.name).toBe("string");
      expect(typeof conn.url).toBe("string");
      expect(["streamable_http", "stdio"]).toContain(conn.transport);
      expect(["none", "api_key", "oauth2"]).toContain(conn.auth_type);
      expect([
        "disconnected",
        "connecting",
        "connected",
        "error",
        "auth_required",
      ]).toContain(conn.status);
      expect(typeof conn.tool_count).toBe("number");
      expect(typeof conn.resource_count).toBe("number");
      expect(typeof conn.prompt_count).toBe("number");
    });

    it("should support status filtering", async () => {
      const response = await fetch("/api/v1/connections?status=connected");
      expect(response.ok).toBe(true);

      const data: ConnectionListResponse = await response.json();
      expect(data.items.every((c) => c.status === "connected")).toBe(true);
    });

    it("should support search filtering", async () => {
      const response = await fetch("/api/v1/connections?search=OpenAI");
      expect(response.ok).toBe(true);

      const data: ConnectionListResponse = await response.json();
      expect(data.items.some((c) => c.name.includes("OpenAI"))).toBe(true);
    });
  });

  describe("GET /api/v1/connections/:id", () => {
    it("should return full MCPConnection details", async () => {
      const response = await fetch("/api/v1/connections/conn-001");
      expect(response.ok).toBe(true);

      const conn: MCPConnection = await response.json();

      // Validate additional fields not in summary
      expect(conn.id).toBe("conn-001");
      expect(typeof conn.owner_id).toBe("string");
      expect(typeof conn.updated_at).toBe("string");
      expect(conn.server_capabilities).toBeDefined();
    });

    it("should return 404 for non-existent connection", async () => {
      const response = await fetch("/api/v1/connections/not-found");
      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/connections", () => {
    it("should create new connection with required fields", async () => {
      const response = await fetch("/api/v1/connections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "My New Connection",
          url: "https://api.example.com/mcp",
        }),
      });

      expect(response.ok).toBe(true);
      const conn: MCPConnection = await response.json();

      expect(typeof conn.id).toBe("string");
      expect(conn.name).toBe("My New Connection");
      expect(conn.url).toBe("https://api.example.com/mcp");
      expect(conn.status).toBe("disconnected");
    });

    it("should create connection with optional fields", async () => {
      const response = await fetch("/api/v1/connections", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Secure Connection",
          url: "https://secure.example.com/mcp",
          description: "A secure MCP connection",
          auth_type: "api_key",
          api_key: "secret-key",
        }),
      });

      expect(response.ok).toBe(true);
      const conn: MCPConnection = await response.json();

      expect(conn.auth_type).toBe("api_key");
    });
  });

  describe("PUT /api/v1/connections/:id", () => {
    it("should update connection", async () => {
      const response = await fetch("/api/v1/connections/conn-001", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Updated Connection Name",
          description: "Updated description",
        }),
      });

      expect(response.ok).toBe(true);
      const conn: MCPConnection = await response.json();

      expect(conn.name).toBe("Updated Connection Name");
      expect(conn.description).toBe("Updated description");
    });
  });

  describe("DELETE /api/v1/connections/:id", () => {
    it("should delete connection and return 204", async () => {
      const response = await fetch("/api/v1/connections/conn-001", {
        method: "DELETE",
      });

      expect(response.status).toBe(204);
    });

    it("should return 404 for non-existent connection", async () => {
      const response = await fetch("/api/v1/connections/not-found", {
        method: "DELETE",
      });

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/connections/:id/test", () => {
    it("should return successful test result", async () => {
      const response = await fetch("/api/v1/connections/conn-001/test", {
        method: "POST",
      });

      expect(response.ok).toBe(true);
      const result: MCPConnectionTestResult = await response.json();

      expect(result.success).toBe(true);
      expect(typeof result.server_name).toBe("string");
      expect(typeof result.server_version).toBe("string");
      expect(typeof result.tool_count).toBe("number");
      expect(result.error).toBeNull();
    });

    it("should return failed test result with error", async () => {
      const response = await fetch("/api/v1/connections/conn-fail/test", {
        method: "POST",
      });

      expect(response.ok).toBe(true);
      const result: MCPConnectionTestResult = await response.json();

      expect(result.success).toBe(false);
      expect(typeof result.error).toBe("string");
    });
  });

  describe("POST /api/v1/connections/:id/oauth/start", () => {
    it("should return OAuth2 authorization URL", async () => {
      const response = await fetch("/api/v1/connections/conn-001/oauth/start", {
        method: "POST",
      });

      expect(response.ok).toBe(true);
      const result: OAuth2StartResponse = await response.json();

      expect(typeof result.authorization_url).toBe("string");
      expect(result.authorization_url).toContain("authorize");
      expect(typeof result.state).toBe("string");
    });
  });

  describe("Bulk Operations", () => {
    describe("POST /api/v1/connections/bulk/delete", () => {
      it("should delete multiple connections", async () => {
        const response = await fetch("/api/v1/connections/bulk/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connection_ids: ["conn-001", "conn-002"],
          }),
        });

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(typeof data.deleted_count).toBe("number");
        expect(Array.isArray(data.failed_ids)).toBe(true);
      });

      it("should report failed deletions", async () => {
        const response = await fetch("/api/v1/connections/bulk/delete", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connection_ids: ["conn-001", "conn-fail"],
          }),
        });

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(data.deleted_count).toBe(1);
        expect(data.failed_ids).toContain("conn-fail");
      });
    });

    describe("POST /api/v1/connections/bulk/test", () => {
      it("should test multiple connections", async () => {
        const response = await fetch("/api/v1/connections/bulk/test", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connection_ids: ["conn-001", "conn-002"],
          }),
        });

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(Array.isArray(data.results)).toBe(true);
        expect(data.results.length).toBe(2);

        const result = data.results[0];
        expect(typeof result.connection_id).toBe("string");
        expect(typeof result.success).toBe("boolean");
      });
    });

    describe("POST /api/v1/connections/bulk/status", () => {
      it("should update status for multiple connections", async () => {
        const response = await fetch("/api/v1/connections/bulk/status", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            connection_ids: ["conn-001", "conn-002"],
            status: "disconnected",
          }),
        });

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(typeof data.updated_count).toBe("number");
        expect(Array.isArray(data.failed_ids)).toBe(true);
      });
    });
  });

  describe("Connection Audit", () => {
    describe("GET /api/v1/connections/audit/logs", () => {
      it("should return audit logs", async () => {
        const response = await fetch("/api/v1/connections/audit/logs");
        expect(response.ok).toBe(true);

        const data = await response.json();

        expect(Array.isArray(data.logs)).toBe(true);
        expect(typeof data.total).toBe("number");
        expect(typeof data.offset).toBe("number");
      });

      it("should validate audit log schema", async () => {
        const response = await fetch("/api/v1/connections/audit/logs");
        const data = await response.json();

        expect(data.logs.length).toBeGreaterThan(0);
        const log = data.logs[0];

        expect(typeof log.id).toBe("string");
        expect(typeof log.connection_id).toBe("string");
        expect(typeof log.action).toBe("string");
        expect(typeof log.actor).toBe("string");
        expect(typeof log.created_at).toBe("string");
      });
    });

    describe("GET /api/v1/connections/:id/audit", () => {
      it("should return connection-specific audit log", async () => {
        const response = await fetch("/api/v1/connections/conn-001/audit");
        expect(response.ok).toBe(true);

        const data = await response.json();

        expect(Array.isArray(data.logs)).toBe(true);
        // All logs should be for the requested connection
        expect(
          data.logs.every(
            (log: { connection_id: string }) =>
              log.connection_id === "conn-001",
          ),
        ).toBe(true);
      });
    });

    describe("DELETE /api/v1/connections/audit/retention", () => {
      it("should delete old audit logs", async () => {
        const response = await fetch(
          "/api/v1/connections/audit/retention?days=90",
          {
            method: "DELETE",
          },
        );

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(typeof data.deleted_count).toBe("number");
      });
    });

    describe("GET /api/v1/connections/audit/export", () => {
      it("should export audit logs as CSV", async () => {
        const response = await fetch("/api/v1/connections/audit/export");
        expect(response.ok).toBe(true);

        expect(response.headers.get("Content-Type")).toContain("text/csv");
        const content = await response.text();
        expect(content).toContain("id,connection_id,action");
      });
    });
  });

  describe("Connection Templates", () => {
    describe("GET /api/v1/connection-templates/categories", () => {
      it("should return template categories", async () => {
        const response = await fetch("/api/v1/connection-templates/categories");
        expect(response.ok).toBe(true);

        const data = await response.json();

        expect(Array.isArray(data.categories)).toBe(true);
        expect(data.categories.length).toBeGreaterThan(0);

        const category = data.categories[0];
        expect(typeof category.id).toBe("string");
        expect(typeof category.name).toBe("string");
      });
    });

    describe("GET /api/v1/connection-templates", () => {
      it("should return list of templates", async () => {
        const response = await fetch("/api/v1/connection-templates");
        expect(response.ok).toBe(true);

        const data = await response.json();

        expect(Array.isArray(data.templates)).toBe(true);
        expect(typeof data.total).toBe("number");
      });

      it("should filter templates by category", async () => {
        const response = await fetch(
          "/api/v1/connection-templates?category=ai",
        );
        expect(response.ok).toBe(true);

        const data = await response.json();
        expect(
          data.templates.every(
            (t: { category: string }) => t.category === "ai",
          ),
        ).toBe(true);
      });
    });

    describe("GET /api/v1/connection-templates/:id", () => {
      it("should return template details", async () => {
        const response = await fetch(
          "/api/v1/connection-templates/tmpl-openai",
        );
        expect(response.ok).toBe(true);

        const data = await response.json();

        expect(data.id).toBe("tmpl-openai");
        expect(typeof data.name).toBe("string");
        expect(Array.isArray(data.required_env_vars)).toBe(true);
        expect(typeof data.setup_instructions).toBe("string");
      });

      it("should return 404 for non-existent template", async () => {
        const response = await fetch("/api/v1/connection-templates/not-found");
        expect(response.status).toBe(404);
      });
    });

    describe("POST /api/v1/connection-templates/:id/apply", () => {
      it("should create connection from template", async () => {
        const response = await fetch(
          "/api/v1/connection-templates/tmpl-openai/apply",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              name: "My OpenAI Connection",
              env_vars: { OPENAI_API_KEY: "sk-xxx" },
            }),
          },
        );

        expect(response.ok).toBe(true);
        const data = await response.json();

        expect(data.connection).toBeDefined();
        expect(data.connection.name).toBe("My OpenAI Connection");
      });
    });
  });
});

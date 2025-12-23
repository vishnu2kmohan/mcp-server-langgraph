/**
 * Workflow API Contract Tests
 *
 * Verifies API schema matches backend for workflow CRUD operations.
 * Reference: src/mcp_server_langgraph/api/v1/workflows.py
 *
 * Uses raw fetch() to validate API contract without RTK Query transformation.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../mocks/server";

// =============================================================================
// MSW Handler Factory for Workflow Endpoints
// =============================================================================

/**
 * Create default handlers for workflow endpoints.
 * Uses server.use() to add handlers to the global MSW server.
 */
function setupWorkflowHandlers() {
  server.use(
    // NOTE: Static paths MUST come before parameterized paths to avoid conflicts
    // GET /api/v1/workflows/shared-with-me - Get workflows shared with user
    http.get("/api/v1/workflows/shared-with-me", () => {
      return HttpResponse.json([
        {
          id: "wf-shared-001",
          name: "Shared Workflow",
          description: "A workflow shared by another user",
          node_count: 3,
          edge_count: 2,
          created_at: "2024-01-10T08:00:00Z",
          updated_at: "2024-01-12T14:00:00Z",
        },
      ]);
    }),

    // GET /api/v1/workflows - List workflows with pagination
    http.get("/api/v1/workflows", ({ request }) => {
      const url = new URL(request.url);
      const search = url.searchParams.get("search");
      const limit = parseInt(url.searchParams.get("limit") ?? "20", 10);
      const cursor = url.searchParams.get("cursor");

      const items = [
        {
          id: "wf-001",
          name: "Data Pipeline",
          description: "ETL workflow for data processing",
          node_count: 5,
          edge_count: 4,
          created_at: "2024-01-15T10:00:00Z",
          updated_at: "2024-01-15T10:00:00Z",
        },
        {
          id: "wf-002",
          name: "Chat Assistant",
          description: "Conversational AI workflow",
          node_count: 3,
          edge_count: 2,
          created_at: "2024-01-14T09:00:00Z",
          updated_at: "2024-01-15T11:00:00Z",
        },
      ];

      // Filter by search if provided
      const filtered = search
        ? items.filter((w) =>
            w.name.toLowerCase().includes(search.toLowerCase()),
          )
        : items;

      return HttpResponse.json({
        items: filtered.slice(0, limit),
        next_cursor: cursor ? null : "cursor-next",
        has_more: !cursor,
      });
    }),

    // GET /api/v1/workflows/:id - Get single workflow
    http.get("/api/v1/workflows/:id", ({ params }) => {
      const { id } = params;

      if (id === "wf-not-found") {
        return HttpResponse.json(
          { detail: "Workflow not found" },
          { status: 404 },
        );
      }

      return HttpResponse.json({
        id: id as string,
        name: "Test Workflow",
        description: "A test workflow",
        nodes: [
          { id: "node-1", type: "start", position: { x: 0, y: 0 }, data: {} },
          { id: "node-2", type: "llm", position: { x: 100, y: 0 }, data: {} },
        ],
        edges: [{ id: "edge-1", source: "node-1", target: "node-2" }],
        user_id: "user-123",
        created_at: "2024-01-15T10:00:00Z",
        updated_at: "2024-01-15T10:00:00Z",
      });
    }),

    // POST /api/v1/workflows - Create workflow
    http.post("/api/v1/workflows", async ({ request }) => {
      const body = (await request.json()) as {
        name: string;
        description?: string;
        nodes?: unknown[];
        edges?: unknown[];
      };

      return HttpResponse.json(
        {
          id: "wf-new-001",
          name: body.name,
          description: body.description ?? "",
          nodes: body.nodes ?? [],
          edges: body.edges ?? [],
          user_id: "user-123",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        { status: 201 },
      );
    }),

    // PUT /api/v1/workflows/:id - Update workflow
    http.put("/api/v1/workflows/:id", async ({ params, request }) => {
      const { id } = params;
      const body = (await request.json()) as {
        name?: string;
        description?: string;
        nodes?: unknown[];
        edges?: unknown[];
      };

      return HttpResponse.json({
        id: id as string,
        name: body.name ?? "Updated Workflow",
        description: body.description ?? "",
        nodes: body.nodes ?? [],
        edges: body.edges ?? [],
        user_id: "user-123",
        created_at: "2024-01-15T10:00:00Z",
        updated_at: new Date().toISOString(),
      });
    }),

    // DELETE /api/v1/workflows/:id - Delete workflow
    http.delete("/api/v1/workflows/:id", () => {
      return new HttpResponse(null, { status: 204 });
    }),

    // GET /api/v1/workflows/:id/shares - Get workflow shares
    http.get("/api/v1/workflows/:id/shares", () => {
      return HttpResponse.json({
        shares: [
          { user_id: "user-1", email: "alice@example.com", permission: "edit" },
          { user_id: "user-2", email: "bob@example.com", permission: "view" },
        ],
        is_public: false,
        share_link: null,
      });
    }),

    // POST /api/v1/workflows/:id/shares - Add workflow share
    http.post("/api/v1/workflows/:id/shares", async ({ request }) => {
      const body = (await request.json()) as {
        email: string;
        permission: string;
      };

      return HttpResponse.json({
        user_id: "user-new",
        email: body.email,
        permission: body.permission,
      });
    }),

    // DELETE /api/v1/workflows/:id/shares/:userId - Remove workflow share
    http.delete("/api/v1/workflows/:id/shares/:userId", () => {
      return new HttpResponse(null, { status: 204 });
    }),

    // PUT /api/v1/workflows/:id/public - Update workflow public status
    http.put("/api/v1/workflows/:id/public", async ({ request }) => {
      const body = (await request.json()) as { is_public: boolean };

      return HttpResponse.json({
        is_public: body.is_public,
        share_link: body.is_public ? "https://example.com/share/wf-001" : null,
      });
    }),
  );
}

// Set up handlers before each test, reset after
beforeEach(() => {
  setupWorkflowHandlers();
});

afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

// =============================================================================
// Schema Type Definitions (matching backend Pydantic models)
// =============================================================================

interface WorkflowSummary {
  id: string;
  name: string;
  description: string;
  node_count: number;
  edge_count: number;
  created_at: string;
  updated_at: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  nodes: Array<Record<string, unknown>>;
  edges: Array<Record<string, unknown>>;
  user_id?: string;
  created_at: string;
  updated_at: string;
}

interface PaginatedWorkflowsResponse {
  items: WorkflowSummary[];
  next_cursor: string | null;
  has_more: boolean;
}

interface WorkflowShare {
  user_id: string;
  email: string;
  permission: "view" | "edit" | "execute";
}

interface WorkflowSharesResponse {
  shares: WorkflowShare[];
  is_public: boolean;
  share_link: string | null;
}

// =============================================================================
// Contract Tests
// =============================================================================

describe("Workflow API Contract", () => {
  describe("GET /api/v1/workflows", () => {
    it("should return PaginatedWorkflowsResponse schema", async () => {
      const response = await fetch("/api/v1/workflows");
      expect(response.ok).toBe(true);

      const data: PaginatedWorkflowsResponse = await response.json();

      // Validate response structure
      expect(data).toHaveProperty("items");
      expect(data).toHaveProperty("next_cursor");
      expect(data).toHaveProperty("has_more");
      expect(Array.isArray(data.items)).toBe(true);
    });

    it("should return WorkflowSummary objects with required fields", async () => {
      const response = await fetch("/api/v1/workflows");
      const data: PaginatedWorkflowsResponse = await response.json();

      expect(data.items.length).toBeGreaterThan(0);

      const workflow = data.items[0];
      expect(typeof workflow.id).toBe("string");
      expect(typeof workflow.name).toBe("string");
      expect(typeof workflow.description).toBe("string");
      expect(typeof workflow.node_count).toBe("number");
      expect(typeof workflow.edge_count).toBe("number");
      expect(typeof workflow.created_at).toBe("string");
      expect(typeof workflow.updated_at).toBe("string");
    });

    it("should support search parameter", async () => {
      const response = await fetch("/api/v1/workflows?search=Pipeline");
      expect(response.ok).toBe(true);

      const data: PaginatedWorkflowsResponse = await response.json();
      expect(data.items.length).toBe(1);
      expect(data.items[0].name).toBe("Data Pipeline");
    });

    it("should support limit parameter", async () => {
      const response = await fetch("/api/v1/workflows?limit=1");
      expect(response.ok).toBe(true);

      const data: PaginatedWorkflowsResponse = await response.json();
      expect(data.items.length).toBeLessThanOrEqual(1);
    });

    it("should support cursor pagination", async () => {
      const response = await fetch("/api/v1/workflows?cursor=cursor-prev");
      expect(response.ok).toBe(true);

      const data: PaginatedWorkflowsResponse = await response.json();
      expect(data.next_cursor).toBeNull();
      expect(data.has_more).toBe(false);
    });
  });

  describe("GET /api/v1/workflows/:id", () => {
    it("should return Workflow schema with full details", async () => {
      const response = await fetch("/api/v1/workflows/wf-001");
      expect(response.ok).toBe(true);

      const data: Workflow = await response.json();

      // Validate full workflow structure
      expect(typeof data.id).toBe("string");
      expect(typeof data.name).toBe("string");
      expect(typeof data.description).toBe("string");
      expect(Array.isArray(data.nodes)).toBe(true);
      expect(Array.isArray(data.edges)).toBe(true);
      expect(typeof data.created_at).toBe("string");
      expect(typeof data.updated_at).toBe("string");
    });

    it("should include nodes with proper structure", async () => {
      const response = await fetch("/api/v1/workflows/wf-001");
      const data: Workflow = await response.json();

      expect(data.nodes.length).toBeGreaterThan(0);
      const node = data.nodes[0];
      expect(node).toHaveProperty("id");
      expect(node).toHaveProperty("type");
      expect(node).toHaveProperty("position");
    });

    it("should include edges with proper structure", async () => {
      const response = await fetch("/api/v1/workflows/wf-001");
      const data: Workflow = await response.json();

      expect(data.edges.length).toBeGreaterThan(0);
      const edge = data.edges[0];
      expect(edge).toHaveProperty("id");
      expect(edge).toHaveProperty("source");
      expect(edge).toHaveProperty("target");
    });

    it("should return 404 for non-existent workflow", async () => {
      const response = await fetch("/api/v1/workflows/wf-not-found");
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("detail");
    });
  });

  describe("POST /api/v1/workflows", () => {
    it("should create workflow and return Workflow schema", async () => {
      const response = await fetch("/api/v1/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "New Workflow",
          description: "A brand new workflow",
        }),
      });

      expect(response.status).toBe(201);
      const data: Workflow = await response.json();

      expect(data.id).toBeDefined();
      expect(data.name).toBe("New Workflow");
      expect(data.description).toBe("A brand new workflow");
      expect(Array.isArray(data.nodes)).toBe(true);
      expect(Array.isArray(data.edges)).toBe(true);
    });

    it("should accept nodes and edges in create request", async () => {
      const response = await fetch("/api/v1/workflows", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Workflow with Nodes",
          nodes: [{ id: "n1", type: "start" }],
          edges: [{ id: "e1", source: "n1", target: "n2" }],
        }),
      });

      expect(response.status).toBe(201);
      const data: Workflow = await response.json();
      expect(data.nodes.length).toBe(1);
      expect(data.edges.length).toBe(1);
    });
  });

  describe("PUT /api/v1/workflows/:id", () => {
    it("should update workflow and return updated Workflow", async () => {
      const response = await fetch("/api/v1/workflows/wf-001", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "Updated Workflow Name",
          description: "Updated description",
        }),
      });

      expect(response.ok).toBe(true);
      const data: Workflow = await response.json();

      expect(data.id).toBe("wf-001");
      expect(data.name).toBe("Updated Workflow Name");
    });
  });

  describe("DELETE /api/v1/workflows/:id", () => {
    it("should delete workflow and return 204", async () => {
      const response = await fetch("/api/v1/workflows/wf-001", {
        method: "DELETE",
      });

      expect(response.status).toBe(204);
    });
  });

  describe("GET /api/v1/workflows/:id/shares", () => {
    it("should return WorkflowSharesResponse schema", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/shares");
      expect(response.ok).toBe(true);

      const data: WorkflowSharesResponse = await response.json();

      expect(data).toHaveProperty("shares");
      expect(data).toHaveProperty("is_public");
      expect(data).toHaveProperty("share_link");
      expect(Array.isArray(data.shares)).toBe(true);
    });

    it("should return WorkflowShare objects with required fields", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/shares");
      const data: WorkflowSharesResponse = await response.json();

      expect(data.shares.length).toBeGreaterThan(0);
      const share = data.shares[0];
      expect(typeof share.user_id).toBe("string");
      expect(typeof share.email).toBe("string");
      expect(["view", "edit", "execute"]).toContain(share.permission);
    });
  });

  describe("POST /api/v1/workflows/:id/shares", () => {
    it("should add share and return WorkflowShare", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/shares", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: "newuser@example.com",
          permission: "edit",
        }),
      });

      expect(response.ok).toBe(true);
      const data: WorkflowShare = await response.json();

      expect(data.email).toBe("newuser@example.com");
      expect(data.permission).toBe("edit");
    });
  });

  describe("DELETE /api/v1/workflows/:id/shares/:userId", () => {
    it("should remove share and return 204", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/shares/user-1", {
        method: "DELETE",
      });

      expect(response.status).toBe(204);
    });
  });

  describe("PUT /api/v1/workflows/:id/public", () => {
    it("should update public status and return share link when public", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/public", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_public: true }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.is_public).toBe(true);
      expect(typeof data.share_link).toBe("string");
    });

    it("should clear share link when made private", async () => {
      const response = await fetch("/api/v1/workflows/wf-001/public", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ is_public: false }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data.is_public).toBe(false);
      expect(data.share_link).toBeNull();
    });
  });

  describe("GET /api/v1/workflows/shared-with-me", () => {
    it("should return array of WorkflowSummary", async () => {
      const response = await fetch("/api/v1/workflows/shared-with-me");
      expect(response.ok).toBe(true);

      const data: WorkflowSummary[] = await response.json();

      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);

      const workflow = data[0];
      expect(typeof workflow.id).toBe("string");
      expect(typeof workflow.name).toBe("string");
      expect(typeof workflow.node_count).toBe("number");
    });
  });
});

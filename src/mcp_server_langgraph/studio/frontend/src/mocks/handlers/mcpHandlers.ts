/**
 * MCP Handlers
 *
 * MSW handlers for MCP (Model Context Protocol) endpoints.
 *
 * Endpoints covered:
 * - GET /api/v1/mcp/resources - List resources
 * - GET /api/v1/mcp/resources/content - Read resource content
 * - GET /api/v1/mcp/tools - List tools
 * - POST /api/v1/mcp/tools/call - Invoke tool
 * - POST /api/v1/mcp/sampling - Request sampling
 * - POST /api/v1/mcp/elicitation - Request elicitation
 * - GET /api/v1/mcp/prompts - List prompts
 * - POST /api/v1/mcp/prompts/get - Get prompt with arguments
 * - GET /api/v1/mcp/tasks - List tasks
 * - GET /api/v1/mcp/tasks/:id - Get task by ID
 * - POST /api/v1/mcp/tasks/:id/cancel - Cancel task
 */

import { http, HttpResponse } from "msw";

// =============================================================================
// Types
// =============================================================================

export interface MCPResource {
  uri: string;
  name: string;
  mimeType: string;
  description?: string;
}

export interface MCPTool {
  name: string;
  description: string;
  inputSchema: Record<string, unknown>;
}

export interface MCPPrompt {
  name: string;
  description: string;
  arguments?: Array<{
    name: string;
    description?: string;
    required?: boolean;
  }>;
}

export interface MCPTask {
  id: string;
  status: "pending" | "running" | "completed" | "cancelled" | "failed";
  createdAt: string;
  updatedAt?: string;
  result?: unknown;
  error?: string;
}

// =============================================================================
// Mock Data Factories
// =============================================================================

export const createMockResource = (
  overrides: Partial<MCPResource> = {}
): MCPResource => ({
  uri: "file:///project/README.md",
  name: "README.md",
  mimeType: "text/markdown",
  description: "Project README file",
  ...overrides,
});

export const createMockTool = (
  overrides: Partial<MCPTool> = {}
): MCPTool => ({
  name: "read_file",
  description: "Read contents of a file",
  inputSchema: {
    type: "object",
    properties: {
      path: { type: "string", description: "File path to read" },
    },
    required: ["path"],
  },
  ...overrides,
});

export const createMockPrompt = (
  overrides: Partial<MCPPrompt> = {}
): MCPPrompt => ({
  name: "summarize",
  description: "Summarize the given text",
  arguments: [
    { name: "text", description: "Text to summarize", required: true },
    { name: "maxLength", description: "Maximum summary length", required: false },
  ],
  ...overrides,
});

export const createMockTask = (
  overrides: Partial<MCPTask> = {}
): MCPTask => ({
  id: "task-1",
  status: "running",
  createdAt: new Date().toISOString(),
  ...overrides,
});

// =============================================================================
// Default Mock Data
// =============================================================================

export const MOCK_RESOURCES: MCPResource[] = [
  createMockResource({
    uri: "file:///project/README.md",
    name: "README.md",
    mimeType: "text/markdown",
  }),
  createMockResource({
    uri: "file:///project/src/index.ts",
    name: "index.ts",
    mimeType: "text/typescript",
  }),
  createMockResource({
    uri: "file:///project/package.json",
    name: "package.json",
    mimeType: "application/json",
  }),
];

export const MOCK_TOOLS: MCPTool[] = [
  createMockTool({
    name: "read_file",
    description: "Read contents of a file",
    inputSchema: {
      type: "object",
      properties: { path: { type: "string" } },
      required: ["path"],
    },
  }),
  createMockTool({
    name: "write_file",
    description: "Write contents to a file",
    inputSchema: {
      type: "object",
      properties: {
        path: { type: "string" },
        content: { type: "string" },
      },
      required: ["path", "content"],
    },
  }),
  createMockTool({
    name: "execute_command",
    description: "Execute a shell command",
    inputSchema: {
      type: "object",
      properties: { command: { type: "string" } },
      required: ["command"],
    },
  }),
];

export const MOCK_PROMPTS: MCPPrompt[] = [
  createMockPrompt({
    name: "summarize",
    description: "Summarize the given text",
    arguments: [
      { name: "text", description: "Text to summarize", required: true },
    ],
  }),
  createMockPrompt({
    name: "translate",
    description: "Translate text to another language",
    arguments: [
      { name: "text", description: "Text to translate", required: true },
      { name: "targetLanguage", description: "Target language", required: true },
    ],
  }),
];

const MOCK_TASKS: MCPTask[] = [
  createMockTask({ id: "task-1", status: "running" }),
  createMockTask({ id: "task-2", status: "completed" }),
  createMockTask({ id: "task-3", status: "pending" }),
];

// Resource content mapping
const RESOURCE_CONTENT: Record<string, { text: string; mimeType: string }> = {
  "file:///project/README.md": {
    text: "# Project README\n\nThis is the project readme file.",
    mimeType: "text/markdown",
  },
  "file:///project/src/index.ts": {
    text: 'export const main = () => console.log("Hello, World!");',
    mimeType: "text/typescript",
  },
  "file:///project/package.json": {
    text: '{"name": "project", "version": "1.0.0"}',
    mimeType: "application/json",
  },
};

// =============================================================================
// Error Scenario Factory Types
// =============================================================================

type HttpMethod = "get" | "post" | "put" | "patch" | "delete";

// =============================================================================
// Error Scenario Factories
// =============================================================================

/**
 * Creates an error handler for testing error scenarios.
 *
 * @param method - HTTP method (get, post, etc.)
 * @param path - API endpoint path
 * @param status - HTTP status code
 * @param message - Error message
 * @param details - Optional error details
 * @returns MSW handler that returns the error
 *
 * @example
 * ```ts
 * server.use(createErrorHandler("get", "/api/v1/mcp/resources", 500, "Server error"));
 * ```
 */
export function createErrorHandler(
  method: HttpMethod,
  path: string,
  status: number,
  message: string,
  details?: Record<string, unknown>
) {
  const handler = http[method](path, () => {
    const body: { error: string; details?: Record<string, unknown> } = {
      error: message,
    };
    if (details) {
      body.details = details;
    }
    return HttpResponse.json(body, { status });
  });
  return handler;
}

/**
 * Creates a handler that simulates network failure.
 *
 * @param method - HTTP method
 * @param path - API endpoint path
 * @returns MSW handler that throws network error
 *
 * @example
 * ```ts
 * server.use(createNetworkErrorHandler("get", "/api/v1/mcp/resources"));
 * ```
 */
export function createNetworkErrorHandler(method: HttpMethod, path: string) {
  return http[method](path, () => {
    return HttpResponse.error();
  });
}

/**
 * Creates a handler with delayed response for testing loading states.
 *
 * @param method - HTTP method
 * @param path - API endpoint path
 * @param delayMs - Delay in milliseconds
 * @param response - Response data to return
 * @returns MSW handler with delayed response
 *
 * @example
 * ```ts
 * server.use(createDelayedHandler("get", "/api/v1/mcp/tasks", 1000, { tasks: [] }));
 * ```
 */
export function createDelayedHandler(
  method: HttpMethod,
  path: string,
  delayMs: number,
  response: unknown
) {
  return http[method](path, async () => {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
    return HttpResponse.json(response);
  });
}

// =============================================================================
// Handlers
// =============================================================================

export const mcpHandlers = [
  // GET /api/v1/mcp/resources - List resources
  http.get("/api/v1/mcp/resources", () => {
    return HttpResponse.json({
      resources: MOCK_RESOURCES,
    });
  }),

  // GET /api/v1/mcp/resources/content - Read resource content
  http.get("/api/v1/mcp/resources/content", ({ request }) => {
    const url = new URL(request.url);
    const uri = url.searchParams.get("uri");

    if (!uri) {
      return HttpResponse.json(
        { error: "Missing uri parameter" },
        { status: 400 }
      );
    }

    const decodedUri = decodeURIComponent(uri);
    const content = RESOURCE_CONTENT[decodedUri];

    if (!content) {
      return HttpResponse.json(
        { error: "Resource not found" },
        { status: 404 }
      );
    }

    return HttpResponse.json({
      contents: [
        {
          uri: decodedUri,
          text: content.text,
          mimeType: content.mimeType,
        },
      ],
    });
  }),

  // GET /api/v1/mcp/tools - List tools
  http.get("/api/v1/mcp/tools", () => {
    return HttpResponse.json({
      tools: MOCK_TOOLS,
    });
  }),

  // POST /api/v1/mcp/tools/call - Invoke tool
  http.post("/api/v1/mcp/tools/call", async ({ request }) => {
    const body = (await request.json()) as { name: string; arguments: Record<string, unknown> };
    const { name } = body;

    // Check if tool exists
    const tool = MOCK_TOOLS.find((t) => t.name === name);
    if (!tool) {
      return HttpResponse.json(
        { error: `Tool '${name}' not found` },
        { status: 404 }
      );
    }

    // Return mock result
    return HttpResponse.json({
      content: [
        {
          type: "text",
          text: `Tool '${name}' executed successfully`,
        },
      ],
      isError: false,
    });
  }),

  // POST /api/v1/mcp/sampling - Request sampling
  http.post("/api/v1/mcp/sampling", async ({ request }) => {
    const body = (await request.json()) as {
      messages: Array<{ role: string; content: unknown }>;
      maxTokens: number;
      modelPreferences?: { hints?: Array<{ name: string }> };
    };

    const modelHint = body.modelPreferences?.hints?.[0]?.name;

    return HttpResponse.json({
      role: "assistant",
      content: {
        type: "text",
        text: "This is a mock sampling response.",
      },
      model: modelHint || "mock-model",
      stopReason: "end_turn",
    });
  }),

  // POST /api/v1/mcp/elicitation - Request elicitation
  http.post("/api/v1/mcp/elicitation", async () => {
    // Simulate user accepting the elicitation
    return HttpResponse.json({
      action: "accept",
      content: {
        name: "John Doe",
        email: "john@example.com",
      },
    });
  }),

  // GET /api/v1/mcp/prompts - List prompts
  http.get("/api/v1/mcp/prompts", () => {
    return HttpResponse.json({
      prompts: MOCK_PROMPTS,
    });
  }),

  // POST /api/v1/mcp/prompts/get - Get prompt with arguments
  http.post("/api/v1/mcp/prompts/get", async ({ request }) => {
    const body = (await request.json()) as { name: string; arguments: Record<string, unknown> };
    const { name, arguments: args } = body;

    // Check if prompt exists
    const prompt = MOCK_PROMPTS.find((p) => p.name === name);
    if (!prompt) {
      return HttpResponse.json(
        { error: `Prompt '${name}' not found` },
        { status: 404 }
      );
    }

    // Generate prompt messages based on the prompt template
    return HttpResponse.json({
      description: prompt.description,
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text: `${prompt.description}: ${JSON.stringify(args)}`,
          },
        },
      ],
    });
  }),

  // GET /api/v1/mcp/tasks - List tasks
  http.get("/api/v1/mcp/tasks", () => {
    return HttpResponse.json({
      tasks: MOCK_TASKS,
    });
  }),

  // GET /api/v1/mcp/tasks/:id - Get task by ID
  http.get("/api/v1/mcp/tasks/:id", ({ params }) => {
    const { id } = params;
    const task = MOCK_TASKS.find((t) => t.id === id);

    if (!task) {
      return HttpResponse.json(
        { error: `Task '${id}' not found` },
        { status: 404 }
      );
    }

    return HttpResponse.json(task);
  }),

  // POST /api/v1/mcp/tasks/:id/cancel - Cancel task
  http.post("/api/v1/mcp/tasks/:id/cancel", ({ params }) => {
    const { id } = params;
    const task = MOCK_TASKS.find((t) => t.id === id);

    if (!task) {
      return HttpResponse.json(
        { error: `Task '${id}' not found` },
        { status: 404 }
      );
    }

    // Return the task with cancelled status
    return HttpResponse.json({
      ...task,
      status: "cancelled",
      updatedAt: new Date().toISOString(),
    });
  }),
];

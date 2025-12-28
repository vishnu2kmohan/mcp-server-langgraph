/**
 * AggregatedCapabilities Component Tests
 *
 * TDD tests for MCP aggregated capabilities components:
 * - AggregatedCapabilitiesPanel - Main panel showing all capabilities
 * - MCPServerCard - Server capability summary card
 * - ToolExplorer - Browse and invoke aggregated tools
 * - ResourceBrowser - Browse aggregated resources
 * - PromptLibrary - Browse and test aggregated prompts
 *
 * These components support the MCP Protocol 2025-11-25 capability aggregation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  cleanup,
  waitFor,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

// Mock the RTK Query hooks
const mockAggregatedTools = {
  tools: [
    {
      qualified_name: "github:create_issue",
      server_name: "github",
      name: "create_issue",
      description: "Create a GitHub issue",
      input_schema: {
        type: "object",
        properties: { title: { type: "string" } },
      },
    },
    {
      qualified_name: "github:list_repos",
      server_name: "github",
      name: "list_repos",
      description: "List GitHub repositories",
      input_schema: { type: "object", properties: {} },
    },
    {
      qualified_name: "slack:send_message",
      server_name: "slack",
      name: "send_message",
      description: "Send a Slack message",
      input_schema: {
        type: "object",
        properties: { channel: { type: "string" } },
      },
    },
  ],
  total_count: 3,
};

const mockAggregatedResources = {
  resources: [
    {
      qualified_name: "github:repo://owner/repo",
      server_name: "github",
      uri: "repo://owner/repo",
      name: "Repository",
      description: "GitHub repository resource",
      mime_type: "application/json",
    },
    {
      qualified_name: "config:config://settings",
      server_name: "config",
      uri: "config://settings",
      name: "Settings",
      description: "Application settings",
      mime_type: "application/json",
    },
  ],
  total_count: 2,
};

const mockAggregatedPrompts = {
  prompts: [
    {
      qualified_name: "assistant:code_review",
      server_name: "assistant",
      name: "code_review",
      description: "Review code for issues",
      arguments: [
        { name: "code", required: true, description: "Code to review" },
        { name: "language", required: false, description: "Language" },
      ],
    },
    {
      qualified_name: "assistant:summarize",
      server_name: "assistant",
      name: "summarize",
      description: "Summarize content",
      arguments: [],
    },
  ],
  total_count: 2,
};

const mockServers = {
  servers: [
    {
      server_name: "github",
      tool_count: 2,
      resource_count: 1,
      prompt_count: 0,
    },
    { server_name: "slack", tool_count: 1, resource_count: 0, prompt_count: 0 },
    {
      server_name: "config",
      tool_count: 0,
      resource_count: 1,
      prompt_count: 0,
    },
    {
      server_name: "assistant",
      tool_count: 0,
      resource_count: 0,
      prompt_count: 2,
    },
  ],
  total_servers: 4,
  total_tools: 3,
  total_resources: 2,
  total_prompts: 2,
};

// Mock the API with filter support
// API hooks accept serverName?: string (not an object)
vi.mock("../../api", () => ({
  useListAggregatedToolsQuery: vi.fn((serverName?: string) => {
    const tools = serverName
      ? mockAggregatedTools.tools.filter((t) => t.server_name === serverName)
      : mockAggregatedTools.tools;
    return {
      data: { tools, total_count: tools.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
  }),
  useListAggregatedResourcesQuery: vi.fn((serverName?: string) => {
    const resources = serverName
      ? mockAggregatedResources.resources.filter(
          (r) => r.server_name === serverName,
        )
      : mockAggregatedResources.resources;
    return {
      data: { resources, total_count: resources.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
  }),
  useListAggregatedPromptsQuery: vi.fn((serverName?: string) => {
    const prompts = serverName
      ? mockAggregatedPrompts.prompts.filter(
          (p) => p.server_name === serverName,
        )
      : mockAggregatedPrompts.prompts;
    return {
      data: { prompts, total_count: prompts.length },
      isLoading: false,
      error: null,
      refetch: vi.fn(),
    };
  }),
  useListAggregatedServersQuery: vi.fn(() => ({
    data: mockServers,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useGetServerCapabilitiesQuery: vi.fn(() => ({
    data: {
      server_name: "github",
      tool_count: 2,
      resource_count: 1,
      prompt_count: 0,
    },
    isLoading: false,
    error: null,
  })),
}));

// Mock the useMCPAggregatedUpdates hook to avoid Redux auth dependencies
vi.mock("../../hooks", async () => {
  const actual = await vi.importActual("../../hooks");
  return {
    ...actual,
    useMCPAggregatedUpdates: vi.fn(() => ({
      status: "connected",
      lastToolsUpdate: null,
      lastResourcesUpdate: null,
      lastPromptsUpdate: null,
      disconnect: vi.fn(),
      reconnect: vi.fn(),
    })),
  };
});

import {
  _useListAggregatedToolsQuery,
  _useListAggregatedResourcesQuery,
  _useListAggregatedPromptsQuery,
  useListAggregatedServersQuery,
} from "../../api";

// Mock persona slice
const mockPersonaSlice = {
  name: "persona",
  initialState: {
    persona: "developer" as const,
    subPersona: "alice-builder",
    visibleModules: ["mcp", "connections", "chat"],
  },
  reducers: {},
};

// Create mock store
function createMockStore() {
  return configureStore({
    reducer: {
      persona: () => mockPersonaSlice.initialState,
    },
  });
}

// Import components after mocking
import { AggregatedCapabilitiesPanel } from "./AggregatedCapabilities";
import { MCPServerCard } from "./MCPServerCard";
import { ToolExplorer } from "./ToolExplorer";
import { ResourceBrowser } from "./ResourceBrowser";
import { PromptLibrary } from "./PromptLibrary";

describe("AggregatedCapabilitiesPanel", () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  afterEach(() => {
    cleanup();
  });

  describe("Component Structure", () => {
    it("should render panel title", () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      expect(screen.getByText(/aggregated capabilities/i)).toBeInTheDocument();
    });

    it("should show total capability counts", () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      // Should show totals from mockServers
      expect(screen.getByText(/3 tools/i)).toBeInTheDocument();
      expect(screen.getByText(/2 resources/i)).toBeInTheDocument();
      expect(screen.getByText(/2 prompts/i)).toBeInTheDocument();
    });

    it("should show server count", () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      expect(screen.getByText(/4 servers/i)).toBeInTheDocument();
    });

    it("should have tabs for Tools, Resources, Prompts, Servers", () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      expect(screen.getByRole("tab", { name: /tools/i })).toBeInTheDocument();
      expect(
        screen.getByRole("tab", { name: /resources/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /prompts/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /servers/i })).toBeInTheDocument();
    });
  });

  describe("Tab Navigation", () => {
    it("should switch to Resources tab when clicked", async () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      const resourcesTab = screen.getByRole("tab", { name: /resources/i });
      fireEvent.click(resourcesTab);
      await waitFor(() => {
        // Use getAllByText since the URI appears in both qualified_name and uri fields
        const matches = screen.getAllByText(/repo:\/\/owner\/repo/i);
        expect(matches.length).toBeGreaterThan(0);
      });
    });

    it("should switch to Prompts tab when clicked", async () => {
      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      const promptsTab = screen.getByRole("tab", { name: /prompts/i });
      fireEvent.click(promptsTab);
      await waitFor(() => {
        expect(screen.getByText(/code_review/i)).toBeInTheDocument();
      });
    });
  });

  describe("Loading States", () => {
    it("should show loading spinner when fetching data", () => {
      vi.mocked(useListAggregatedServersQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      } as unknown);

      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      expect(screen.getByTestId("loading-spinner")).toBeInTheDocument();
    });
  });

  describe("Error States", () => {
    it("should show error message when API fails", () => {
      vi.mocked(useListAggregatedServersQuery).mockReturnValueOnce({
        data: undefined,
        isLoading: false,
        error: { message: "Failed to fetch" },
        refetch: vi.fn(),
      } as unknown);

      render(
        <Provider store={store}>
          <AggregatedCapabilitiesPanel />
        </Provider>,
      );
      expect(screen.getByText(/failed to load/i)).toBeInTheDocument();
    });
  });
});

describe("MCPServerCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  const defaultProps = {
    serverName: "github",
    toolCount: 5,
    resourceCount: 3,
    promptCount: 2,
    onSelect: vi.fn(),
  };

  it("should render server name", () => {
    render(<MCPServerCard {...defaultProps} />);
    expect(screen.getByText("github")).toBeInTheDocument();
  });

  it("should show tool count with icon", () => {
    render(<MCPServerCard {...defaultProps} />);
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByTestId("tool-icon")).toBeInTheDocument();
  });

  it("should show resource count with icon", () => {
    render(<MCPServerCard {...defaultProps} />);
    expect(screen.getByText("3")).toBeInTheDocument();
    expect(screen.getByTestId("resource-icon")).toBeInTheDocument();
  });

  it("should show prompt count with icon", () => {
    render(<MCPServerCard {...defaultProps} />);
    expect(screen.getByText("2")).toBeInTheDocument();
    expect(screen.getByTestId("prompt-icon")).toBeInTheDocument();
  });

  it("should call onSelect when clicked", () => {
    render(<MCPServerCard {...defaultProps} />);
    fireEvent.click(screen.getByRole("button"));
    expect(defaultProps.onSelect).toHaveBeenCalledWith("github");
  });

  it("should show zero counts gracefully", () => {
    render(
      <MCPServerCard
        serverName="empty-server"
        toolCount={0}
        resourceCount={0}
        promptCount={0}
        onSelect={vi.fn()}
      />,
    );
    expect(screen.getAllByText("0")).toHaveLength(3);
  });
});

describe("ToolExplorer", () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render tool list", () => {
    render(
      <Provider store={store}>
        <ToolExplorer />
      </Provider>,
    );
    expect(screen.getByText("github:create_issue")).toBeInTheDocument();
    expect(screen.getByText("github:list_repos")).toBeInTheDocument();
    expect(screen.getByText("slack:send_message")).toBeInTheDocument();
  });

  it("should show tool descriptions", () => {
    render(
      <Provider store={store}>
        <ToolExplorer />
      </Provider>,
    );
    expect(screen.getByText("Create a GitHub issue")).toBeInTheDocument();
  });

  it("should show server badge for each tool", () => {
    render(
      <Provider store={store}>
        <ToolExplorer />
      </Provider>,
    );
    const githubBadges = screen.getAllByText("github");
    expect(githubBadges.length).toBeGreaterThanOrEqual(2);
  });

  it("should filter tools by search term", async () => {
    render(
      <Provider store={store}>
        <ToolExplorer />
      </Provider>,
    );
    const searchInput = screen.getByPlaceholderText(/search tools/i);
    fireEvent.change(searchInput, { target: { value: "slack" } });
    await waitFor(() => {
      expect(screen.queryByText("github:create_issue")).not.toBeInTheDocument();
      expect(screen.getByText("slack:send_message")).toBeInTheDocument();
    });
  });

  it("should filter tools by server", async () => {
    render(
      <Provider store={store}>
        <ToolExplorer serverFilter="github" />
      </Provider>,
    );
    expect(screen.getByText("github:create_issue")).toBeInTheDocument();
    expect(screen.queryByText("slack:send_message")).not.toBeInTheDocument();
  });

  it("should show invoke button for each tool", () => {
    render(
      <Provider store={store}>
        <ToolExplorer />
      </Provider>,
    );
    const invokeButtons = screen.getAllByRole("button", { name: /invoke/i });
    expect(invokeButtons.length).toBe(3);
  });
});

describe("ResourceBrowser", () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render resource list", () => {
    render(
      <Provider store={store}>
        <ResourceBrowser />
      </Provider>,
    );
    expect(screen.getByText("github:repo://owner/repo")).toBeInTheDocument();
    expect(screen.getByText("config:config://settings")).toBeInTheDocument();
  });

  it("should show resource URIs", () => {
    render(
      <Provider store={store}>
        <ResourceBrowser />
      </Provider>,
    );
    // Use getAllByText since the URI appears in both qualified_name and uri fields
    const matches = screen.getAllByText(/repo:\/\/owner\/repo/);
    expect(matches.length).toBeGreaterThan(0);
  });

  it("should show MIME types", () => {
    render(
      <Provider store={store}>
        <ResourceBrowser />
      </Provider>,
    );
    const mimeTypes = screen.getAllByText("application/json");
    expect(mimeTypes.length).toBe(2);
  });

  it("should show view button for each resource", () => {
    render(
      <Provider store={store}>
        <ResourceBrowser />
      </Provider>,
    );
    const viewButtons = screen.getAllByRole("button", { name: /view/i });
    expect(viewButtons.length).toBe(2);
  });

  it("should filter resources by search term", async () => {
    render(
      <Provider store={store}>
        <ResourceBrowser />
      </Provider>,
    );
    const searchInput = screen.getByPlaceholderText(/search resources/i);
    fireEvent.change(searchInput, { target: { value: "settings" } });
    await waitFor(() => {
      expect(
        screen.queryByText("github:repo://owner/repo"),
      ).not.toBeInTheDocument();
      expect(screen.getByText("config:config://settings")).toBeInTheDocument();
    });
  });
});

describe("PromptLibrary", () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render prompt list", () => {
    render(
      <Provider store={store}>
        <PromptLibrary />
      </Provider>,
    );
    expect(screen.getByText("assistant:code_review")).toBeInTheDocument();
    expect(screen.getByText("assistant:summarize")).toBeInTheDocument();
  });

  it("should show prompt descriptions", () => {
    render(
      <Provider store={store}>
        <PromptLibrary />
      </Provider>,
    );
    expect(screen.getByText("Review code for issues")).toBeInTheDocument();
    expect(screen.getByText("Summarize content")).toBeInTheDocument();
  });

  it("should show argument count", () => {
    render(
      <Provider store={store}>
        <PromptLibrary />
      </Provider>,
    );
    expect(screen.getByText(/2 arguments/i)).toBeInTheDocument();
    expect(screen.getByText(/0 arguments/i)).toBeInTheDocument();
  });

  it("should show test button for each prompt", () => {
    render(
      <Provider store={store}>
        <PromptLibrary />
      </Provider>,
    );
    const testButtons = screen.getAllByRole("button", { name: /test/i });
    expect(testButtons.length).toBe(2);
  });

  it("should expand prompt to show arguments", async () => {
    render(
      <Provider store={store}>
        <PromptLibrary />
      </Provider>,
    );
    const expandButton = screen.getAllByRole("button", { name: /expand/i })[0];
    fireEvent.click(expandButton);
    await waitFor(() => {
      expect(screen.getByText("code")).toBeInTheDocument();
      expect(screen.getByText("language")).toBeInTheDocument();
    });
  });
});

describe("Persona Access Control", () => {
  afterEach(() => {
    cleanup();
  });

  it("should show admin-only actions for admin persona", () => {
    const adminStore = configureStore({
      reducer: {
        persona: () => ({
          persona: "admin",
          subPersona: "admin",
          visibleModules: ["mcp", "connections", "admin"],
        }),
      },
    });

    render(
      <Provider store={adminStore}>
        <AggregatedCapabilitiesPanel />
      </Provider>,
    );

    // Admin should see refresh all button
    expect(
      screen.getByRole("button", { name: /refresh all/i }),
    ).toBeInTheDocument();
  });

  it("should hide admin actions for bob persona", () => {
    const bobStore = configureStore({
      reducer: {
        persona: () => ({
          persona: "user",
          subPersona: "bob",
          visibleModules: ["chat", "projects"],
        }),
      },
    });

    render(
      <Provider store={bobStore}>
        <AggregatedCapabilitiesPanel showAdminActions={false} />
      </Provider>,
    );

    // Bob should not see refresh all button
    expect(
      screen.queryByRole("button", { name: /refresh all/i }),
    ).not.toBeInTheDocument();
  });

  it("should show invoke actions for alice-builder", () => {
    const aliceStore = configureStore({
      reducer: {
        persona: () => ({
          persona: "developer",
          subPersona: "alice-builder",
          visibleModules: ["mcp", "connections", "chat", "workflows"],
        }),
      },
    });

    render(
      <Provider store={aliceStore}>
        <ToolExplorer />
      </Provider>,
    );

    // Alice should see invoke buttons
    expect(screen.getAllByRole("button", { name: /invoke/i })).toHaveLength(3);
  });
});

describe("Real-time WebSocket Status", () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createMockStore();
  });

  afterEach(() => {
    cleanup();
  });

  it("should show Live indicator when WebSocket is connected", () => {
    render(
      <Provider store={store}>
        <AggregatedCapabilitiesPanel />
      </Provider>,
    );

    // Should show "Live" text when connected
    expect(screen.getByText("Live")).toBeInTheDocument();
  });

  it("should have real-time updates status title", () => {
    render(
      <Provider store={store}>
        <AggregatedCapabilitiesPanel />
      </Provider>,
    );

    // Should have a title indicating real-time updates status
    expect(
      screen.getByTitle("Real-time updates: connected"),
    ).toBeInTheDocument();
  });
});

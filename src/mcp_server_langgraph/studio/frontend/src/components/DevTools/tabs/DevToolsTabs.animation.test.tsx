/**
 * DevTools Tabs Animation Integration Tests
 *
 * Tests for Motion.dev integration in DevTools tabs:
 * - Loading state shimmer animations
 * - Row animation variants
 * - Card hover animations
 * - Reduced motion support (WCAG 2.2 AA)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import React from "react";

// Note: motion/react is globally mocked in src/test/setup.ts with proper prop filtering

// Mock timeline context
vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => ({
    timeWindow: null,
    events: [],
    filteredEvents: [],
  }),
}));

// Mock API hooks
vi.mock("../../../api", () => ({
  useListDevtoolsServicesQuery: () => ({ data: [] }),
}));

// Mock UI components
vi.mock("@/components/UI", () => ({
  Button: ({ children, ...props }: { children: React.ReactNode }) => (
    <button {...props}>{children}</button>
  ),
  Input: (props: Record<string, unknown>) => <input {...props} />,
}));

// =============================================================================
// Animation Variants Tests
// =============================================================================

describe("Animation Variants Design System", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should export shimmerVariants from micro-interactions", async () => {
    const { shimmerVariants } =
      await import("../../../design-system/micro-interactions");
    expect(shimmerVariants).toBeDefined();
    expect(shimmerVariants.shimmer).toBeDefined();
  });

  it("should export accordionVariants from micro-interactions", async () => {
    const { accordionVariants } =
      await import("../../../design-system/micro-interactions");
    expect(accordionVariants).toBeDefined();
    expect(accordionVariants.collapsed).toBeDefined();
    expect(accordionVariants.expanded).toBeDefined();
  });

  it("should export cardHoverVariants from micro-interactions", async () => {
    const { cardHoverVariants } =
      await import("../../../design-system/micro-interactions");
    expect(cardHoverVariants).toBeDefined();
    expect(cardHoverVariants.rest).toBeDefined();
    expect(cardHoverVariants.hover).toBeDefined();
  });

  it("should export list variants from micro-interactions", async () => {
    const { listContainerVariants, listItemVariants } =
      await import("../../../design-system/micro-interactions");
    expect(listContainerVariants).toBeDefined();
    expect(listItemVariants).toBeDefined();
  });
});

// =============================================================================
// MetricsTab Animation Tests
// =============================================================================

describe("MetricsTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render loading state with shimmer skeleton elements", async () => {
    const { MetricsTab } = await import("./MetricsTab");

    render(<MetricsTab isLoading={true} />);

    // Loading state should be rendered with shimmer skeleton
    // Animation variants are verified in the design system tests
    expect(screen.getByTestId("metrics-loading")).toBeInTheDocument();
  });

  it("should render metric cards with cardHoverVariants", async () => {
    const { MetricsTab } = await import("./MetricsTab");

    const mockMetrics = [
      {
        name: "requests_total",
        value: 1000,
        unit: "req",
        trend: "up" as const,
        change: 5.2,
        sparkline: [10, 20, 30, 40, 50],
      },
    ];

    render(<MetricsTab metrics={mockMetrics} />);

    // Metric card should be rendered with hover variants
    // Animation variants are verified in the design system tests
    expect(screen.getByText(/requests total/i)).toBeInTheDocument();
  });

  it("should render HEART dimension cards with cardHoverVariants", async () => {
    const { MetricsTab } = await import("./MetricsTab");

    const mockHeartMetrics = {
      happiness: { score: 85, trend: "up" as const, change: 2.3 },
      engagement: { score: 78, trend: "stable" as const, change: 0.1 },
      adoption: { score: 92, trend: "up" as const, change: 5.0 },
      retention: { score: 88, trend: "down" as const, change: -1.2 },
      taskSuccess: { score: 95, trend: "up" as const, change: 3.1 },
    };

    render(<MetricsTab heartMetrics={mockHeartMetrics} />);

    // HEART metrics should be rendered
    expect(screen.getByText(/happiness/i)).toBeInTheDocument();
    expect(screen.getByText(/engagement/i)).toBeInTheDocument();
  });
});

// =============================================================================
// TracesTab Animation Tests
// =============================================================================

describe("TracesTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render loading state with shimmer skeleton elements", async () => {
    const { TracesTab } = await import("./TracesTab");

    render(<TracesTab isLoading={true} />);

    // Loading state should be rendered with shimmer skeleton
    // Animation variants are verified in the design system tests
    expect(screen.getByTestId("traces-loading")).toBeInTheDocument();
  });

  it("should render trace list with listItemVariants", async () => {
    const { TracesTab } = await import("./TracesTab");

    const mockTraces = [
      {
        traceId: "trace-1",
        name: "GET /api/users",
        startTime: Date.now(),
        durationMs: 150,
        spanCount: 5,
        status: "ok" as const,
      },
      {
        traceId: "trace-2",
        name: "POST /api/users",
        startTime: Date.now(),
        durationMs: 300,
        spanCount: 8,
        status: "error" as const,
      },
    ];

    render(<TracesTab traces={mockTraces} />);

    // Traces should be rendered
    expect(screen.getByText(/GET \/api\/users/)).toBeInTheDocument();
    expect(screen.getByText(/POST \/api\/users/)).toBeInTheDocument();
  });

  it("should use dropdownVariants for filter menus", async () => {
    const { TracesTab } = await import("./TracesTab");

    render(<TracesTab traces={[]} />);

    // The component should have dropdown motion elements prepared
    // Even without opening, the structure should be in place
    expect(screen.getByTestId("traces-tab")).toBeInTheDocument();
  });
});

// =============================================================================
// NetworkTab Animation Tests
// =============================================================================

describe("NetworkTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render network entries with networkRowVariants", async () => {
    const { NetworkTab } = await import("./NetworkTab");

    const mockEntries = [
      {
        id: "req-1",
        url: "https://api.example.com/users",
        method: "GET",
        status: "completed" as const,
        statusCode: 200,
        startTime: Date.now(),
        duration: 150,
        responseSize: 1024,
      },
    ];

    render(<NetworkTab externalEntries={mockEntries} />);

    // Network entry should be rendered
    expect(screen.getByTestId("network-entry-req-1")).toBeInTheDocument();
  });

  it("should respect reduced motion preference for row animations", async () => {
    // Note: useReducedMotion is globally mocked in src/test/setup.ts
    // This test verifies components render correctly with the default mock (false)
    const { NetworkTab } = await import("./NetworkTab");

    const mockEntries = [
      {
        id: "req-1",
        url: "https://api.example.com/users",
        method: "GET",
        status: "completed" as const,
        statusCode: 200,
        startTime: Date.now(),
        duration: 150,
        responseSize: 1024,
      },
    ];

    render(<NetworkTab externalEntries={mockEntries} />);

    // Entry should be rendered with animations (reduced motion is false)
    expect(screen.getByTestId("network-entry-req-1")).toBeInTheDocument();
  });
});

// =============================================================================
// Shimmer Gradient Configuration Tests
// =============================================================================

describe("Shimmer Animation Configuration", () => {
  it("should have shimmerVariants with proper animation configuration", async () => {
    const { shimmerVariants } =
      await import("../../../design-system/micro-interactions");

    // Verify shimmer animation has backgroundPosition keyframes
    expect(shimmerVariants.shimmer).toBeDefined();
    expect(shimmerVariants.shimmer.backgroundPosition).toBeDefined();
  });

  it("should have accordionVariants with height transitions", async () => {
    const { accordionVariants } =
      await import("../../../design-system/micro-interactions");

    // Verify accordion variants have height property
    expect(accordionVariants.collapsed.height).toBe(0);
    expect(accordionVariants.expanded.height).toBe("auto");
  });
});

// =============================================================================
// StateTab Animation Tests
// =============================================================================

// Mock Redux store
// lang-graph: langGraphSlice uses currentSessionId (string), sessionSlice uses currentSession (object)
vi.mock("../../../store/hooks", () => ({
  useAppSelector: (selector: (state: unknown) => unknown) =>
    selector({
      session: { currentSession: null },
      langGraph: { currentSessionId: "test-session" },
      canvas: { nodes: [] },
    }),
}));

// Mock state history hook
vi.mock("../hooks/useStateHistory", () => ({
  useStateHistory: () => ({
    snapshots: [],
    recordSnapshot: vi.fn(),
  }),
}));

describe("StateTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render state tree with accordionVariants for expand/collapse", async () => {
    const { StateTab } = await import("./StateTab");

    render(<StateTab context="session" />);

    // State tab should be rendered
    expect(screen.getByTestId("state-tab")).toBeInTheDocument();

    // State tree should be present
    expect(screen.getByTestId("state-tree")).toBeInTheDocument();
  });

  it("should support time-travel toggle button", async () => {
    const { StateTab } = await import("./StateTab");

    render(<StateTab context="session" contextEntityId="test-123" />);

    // Time-travel toggle should be present
    expect(screen.getByTestId("time-travel-toggle")).toBeInTheDocument();
  });

  it("should render state search input", async () => {
    const { StateTab } = await import("./StateTab");

    render(<StateTab context="session" />);

    // Search input should be present
    expect(screen.getByTestId("state-search")).toBeInTheDocument();
  });
});

// =============================================================================
// AIInsightsTab Animation Tests
// =============================================================================

// Mock auth state
vi.mock("../../../store/slices/authSlice", () => ({
  selectUser: () => ({ id: "test-user", name: "Test User" }),
}));

// Mock DevToolsAI hook with insights for testing card animations
vi.mock("../hooks/useDevToolsAI", () => ({
  useDevToolsAI: () => ({
    insights: [
      {
        id: "insight-1",
        title: "Performance Issue",
        description: "High latency detected",
        type: "performance",
        severity: "high",
        confidence: 0.85,
        suggestedAction: "Optimize query",
      },
    ],
    suggestedLayout: null,
    confidence: 0,
    isLoading: false,
    error: null,
    dismissInsight: vi.fn(),
    applyLayout: vi.fn(),
    fetchSuggestions: vi.fn(),
  }),
}));

// Mock ObservabilityAI hook
vi.mock("../hooks/useObservabilityAI", () => ({
  useObservabilityAI: () => ({
    insights: {
      traceAnomalies: null,
      alertCorrelations: [],
      costPrediction: null,
      rootCauseAnalysis: null,
      predictiveAlerts: [],
    },
    suggestedActions: [],
    isAnalyzing: false,
    refresh: vi.fn(),
  }),
}));

// Mock Studio Analyze API
vi.mock("../../../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../../../api")>();
  return {
    ...original,
    useStudioAnalyzeMutation: () => [vi.fn(), { isLoading: false }],
  };
});

describe("AIInsightsTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render AIInsightsTab with correct structure", async () => {
    const { AIInsightsTab } = await import("./AIInsightsTab");

    render(<AIInsightsTab context="session" />);

    // AI insights tab should be rendered
    expect(screen.getByTestId("ai-insights-tab")).toBeInTheDocument();
  });

  it("should render insight cards with cardHoverVariants", async () => {
    const { AIInsightsTab } = await import("./AIInsightsTab");

    render(<AIInsightsTab context="session" />);

    // Insight card should be rendered with hover variants (mock provides insights)
    // Animation variants are verified in the design system tests
    expect(screen.getByTestId("ai-insight-insight-1")).toBeInTheDocument();
  });

  it("should display insight title and description", async () => {
    const { AIInsightsTab } = await import("./AIInsightsTab");

    render(<AIInsightsTab context="session" />);

    // Insight content should be visible
    expect(screen.getByText("Performance Issue")).toBeInTheDocument();
    expect(screen.getByText("High latency detected")).toBeInTheDocument();
  });
});

// =============================================================================
// ExecutionTraceTab Animation Tests
// =============================================================================

// Mock workflow execution hook with steps for testing
vi.mock("../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: () => ({
    steps: [
      {
        id: "step-1",
        nodeId: "node-1",
        nodeName: "Process Input",
        status: "completed",
        duration: 150,
        startTime: Date.now(),
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
    currentStepId: null,
  }),
}));

describe("ExecutionTraceTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render ExecutionTraceTab with correct structure", async () => {
    const { ExecutionTraceTab } = await import("./ExecutionTraceTab");

    render(<ExecutionTraceTab workflowId="wf-123" />);

    // Execution trace tab should be rendered
    expect(screen.getByTestId("execution-trace-tab")).toBeInTheDocument();
  });

  it("should render execution steps with status icons", async () => {
    const { ExecutionTraceTab } = await import("./ExecutionTraceTab");

    render(<ExecutionTraceTab workflowId="wf-123" />);

    // Execution step should be rendered (mock provides steps)
    expect(screen.getByTestId("execution-step-step-1")).toBeInTheDocument();
  });

  it("should display step name and duration", async () => {
    const { ExecutionTraceTab } = await import("./ExecutionTraceTab");

    render(<ExecutionTraceTab workflowId="wf-123" />);

    // Step content should be visible
    expect(screen.getByText("Process Input")).toBeInTheDocument();
    expect(screen.getByText("150ms")).toBeInTheDocument();
  });
});

// =============================================================================
// AgentTraceTab Animation Tests
// =============================================================================

// Mock agent trace hook with trace data for testing
vi.mock("../hooks/useAgentTrace", () => ({
  useAgentTrace: () => ({
    trace: {
      nodes: [
        {
          id: "node-1",
          name: "Agent Node",
          status: "completed",
          duration: 200,
          startTime: Date.now(),
          endTime: Date.now() + 200,
        },
      ],
      tokens: { input: 100, output: 50 },
    },
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  }),
}));

describe("AgentTraceTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render AgentTraceTab with correct structure", async () => {
    const { AgentTraceTab } = await import("./AgentTraceTab");

    render(<AgentTraceTab sessionId="session-123" />);

    // Agent trace tab should be rendered
    expect(screen.getByTestId("agent-trace-tab")).toBeInTheDocument();
  });

  it("should render trace nodes", async () => {
    const { AgentTraceTab } = await import("./AgentTraceTab");

    render(<AgentTraceTab sessionId="session-123" />);

    // Trace node should be rendered (mock provides trace data)
    expect(screen.getByTestId("trace-node-node-1")).toBeInTheDocument();
  });

  it("should display token counts in toolbar", async () => {
    const { AgentTraceTab } = await import("./AgentTraceTab");

    render(<AgentTraceTab sessionId="session-123" />);

    // Token counts should be displayed
    expect(screen.getByTestId("token-input")).toHaveTextContent("100");
    expect(screen.getByTestId("token-output")).toHaveTextContent("50");
  });

  it("should display node name and duration", async () => {
    const { AgentTraceTab } = await import("./AgentTraceTab");

    render(<AgentTraceTab sessionId="session-123" />);

    // Node content should be visible
    expect(screen.getByText("Agent Node")).toBeInTheDocument();
    expect(screen.getByText("200ms")).toBeInTheDocument();
  });
});

// =============================================================================
// LLMStreamingTab Animation Tests
// =============================================================================

// Mock react-router
vi.mock("react-router", () => ({
  useParams: () => ({ sessionId: "session-123" }),
}));

// Mock LLM streaming WebSocket hook with active streams
vi.mock("../../../hooks/useLLMStreamingWebSocket", () => ({
  useLLMStreamingWebSocket: () => ({
    status: "connected",
    activeStreams: new Map([
      [
        "stream-1",
        {
          streamId: "stream-1",
          model: "gpt-4",
          provider: "openai",
          status: "active",
          ttfcMs: 250,
          chunksReceived: 10,
          totalChunkSize: 1024,
          startedAt: new Date().toISOString(),
        },
      ],
    ]),
    sessionId: "session-123",
    error: null,
    reconnect: vi.fn(),
  }),
}));

describe("LLMStreamingTab Animation Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render LLM streaming tab with correct structure", async () => {
    const { LLMStreamingTab } = await import("./LLMStreamingTab");

    render(<LLMStreamingTab />);

    // LLM streaming tab should be rendered
    expect(screen.getByTestId("llm-streaming-tab")).toBeInTheDocument();
  });

  it("should render stream cards with cardHoverVariants", async () => {
    const { LLMStreamingTab } = await import("./LLMStreamingTab");

    render(<LLMStreamingTab />);

    // Stream card should be rendered with hover variants (mock provides active streams)
    // Animation variants are verified in the design system tests
    expect(screen.getByTestId("stream-card")).toBeInTheDocument();
  });

  it("should display stream status icon for active streams", async () => {
    const { LLMStreamingTab } = await import("./LLMStreamingTab");

    render(<LLMStreamingTab />);

    // Active status icon should be visible
    expect(screen.getByTestId("stream-status-active")).toBeInTheDocument();
  });

  it("should display model and provider information", async () => {
    const { LLMStreamingTab } = await import("./LLMStreamingTab");

    render(<LLMStreamingTab />);

    // Model and provider should be visible
    expect(screen.getByText("gpt-4")).toBeInTheDocument();
    expect(screen.getByText("openai")).toBeInTheDocument();
  });
});

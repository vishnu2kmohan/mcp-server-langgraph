/**
 * Chat Types Test Suite
 *
 * TDD tests for chat message and LangGraph visualization types.
 * These types are extracted from ChatMessages.tsx for reusability.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import type {
  Source,
  Message,
  LangGraphNodeType,
  LangGraphNodeStatus,
  LangGraphNode,
  LangGraphEdge,
  AgentExecutionTrace,
} from "./chat";

describe("Chat Types", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Source interface", () => {
    it("should accept valid source with title and url", () => {
      const source: Source = {
        title: "Example Source",
        url: "https://example.com",
      };
      expect(source.title).toBe("Example Source");
      expect(source.url).toBe("https://example.com");
    });
  });

  describe("Message interface", () => {
    it("should accept minimal user message", () => {
      const message: Message = {
        id: "msg-1",
        role: "user",
        content: "Hello, world!",
        timestamp: Date.now(),
      };
      expect(message.role).toBe("user");
      expect(message.content).toBe("Hello, world!");
    });

    it("should accept assistant message with all optional fields", () => {
      const message: Message = {
        id: "msg-2",
        role: "assistant",
        content: "Here is my response.",
        timestamp: Date.now(),
        sources: [{ title: "Source 1", url: "https://source1.com" }],
        confidence: 0.95,
        isReported: false,
        thinkingContent: "Let me think about this...",
        thinkingTokens: 150,
        modelName: "claude-opus-4-5-20251101",
      };
      expect(message.role).toBe("assistant");
      expect(message.confidence).toBe(0.95);
      expect(message.sources).toHaveLength(1);
      expect(message.thinkingContent).toBeDefined();
    });

    it("should accept system message", () => {
      const message: Message = {
        id: "msg-3",
        role: "system",
        content: "You are a helpful assistant.",
        timestamp: Date.now(),
      };
      expect(message.role).toBe("system");
    });
  });

  describe("LangGraphNodeType", () => {
    it("should accept all valid node types", () => {
      const types: LangGraphNodeType[] = [
        "start",
        "end",
        "tool",
        "conditional",
        "agent",
        "default",
      ];
      expect(types).toHaveLength(6);
    });
  });

  describe("LangGraphNodeStatus", () => {
    it("should accept all valid statuses", () => {
      const statuses: LangGraphNodeStatus[] = [
        "pending",
        "running",
        "completed",
        "error",
        "skipped",
      ];
      expect(statuses).toHaveLength(5);
    });
  });

  describe("LangGraphNode interface", () => {
    it("should accept minimal node", () => {
      const node: LangGraphNode = {
        id: "node-1",
        name: "Start Node",
        type: "start",
        status: "completed",
      };
      expect(node.type).toBe("start");
      expect(node.status).toBe("completed");
    });

    it("should accept node with optional fields", () => {
      const node: LangGraphNode = {
        id: "node-2",
        name: "Tool Node",
        type: "tool",
        status: "completed",
        duration: 250,
        output: "Tool output result",
      };
      expect(node.duration).toBe(250);
      expect(node.output).toBe("Tool output result");
    });

    it("should accept node with timing properties for time-travel debugging", () => {
      const now = Date.now();
      const node: LangGraphNode = {
        id: "node-3",
        name: "Agent Node",
        type: "agent",
        status: "completed",
        startTime: now - 1000,
        endTime: now,
        duration: 1000,
        output: "Agent completed",
      };
      expect(node.startTime).toBe(now - 1000);
      expect(node.endTime).toBe(now);
      expect(node.duration).toBe(1000);
    });

    it("should allow startTime without endTime (for running nodes)", () => {
      const node: LangGraphNode = {
        id: "node-4",
        name: "Running Node",
        type: "tool",
        status: "running",
        startTime: Date.now(),
      };
      expect(node.startTime).toBeDefined();
      expect(node.endTime).toBeUndefined();
    });
  });

  describe("LangGraphEdge interface", () => {
    it("should accept edge without condition", () => {
      const edge: LangGraphEdge = {
        from: "node-1",
        to: "node-2",
      };
      expect(edge.from).toBe("node-1");
      expect(edge.to).toBe("node-2");
    });

    it("should accept conditional edge", () => {
      const edge: LangGraphEdge = {
        from: "node-1",
        to: "node-3",
        condition: "is_valid",
      };
      expect(edge.condition).toBe("is_valid");
    });
  });

  describe("AgentExecutionTrace interface", () => {
    it("should accept empty trace", () => {
      const trace: AgentExecutionTrace = {};
      expect(trace).toBeDefined();
    });

    it("should accept full trace with all fields", () => {
      const trace: AgentExecutionTrace = {
        rawOutput: "Agent execution log...",
        steps: [
          { name: "step1", status: "completed", duration: 100 },
          { name: "step2", status: "running" },
        ],
        tokens: { input: 500, output: 200 },
        nodes: [
          { id: "n1", name: "Start", type: "start", status: "completed" },
          { id: "n2", name: "Agent", type: "agent", status: "running" },
        ],
        edges: [{ from: "n1", to: "n2" }],
        currentNode: "n2",
      };
      expect(trace.steps).toHaveLength(2);
      expect(trace.nodes).toHaveLength(2);
      expect(trace.tokens?.input).toBe(500);
      expect(trace.currentNode).toBe("n2");
    });

    it("should accept trace with timing properties for time-travel debugging", () => {
      const now = Date.now();
      const trace: AgentExecutionTrace = {
        startTime: now - 5000,
        endTime: now,
        nodes: [
          {
            id: "n1",
            name: "Start",
            type: "start",
            status: "completed",
            startTime: now - 5000,
            endTime: now - 4000,
            duration: 1000,
          },
          {
            id: "n2",
            name: "Agent",
            type: "agent",
            status: "completed",
            startTime: now - 4000,
            endTime: now,
            duration: 4000,
          },
        ],
        edges: [{ from: "n1", to: "n2" }],
      };
      expect(trace.startTime).toBe(now - 5000);
      expect(trace.endTime).toBe(now);
      expect(trace.nodes?.[0].startTime).toBe(now - 5000);
      expect(trace.nodes?.[1].endTime).toBe(now);
    });

    it("should allow trace with only startTime (for running traces)", () => {
      const now = Date.now();
      const trace: AgentExecutionTrace = {
        startTime: now - 1000,
        nodes: [
          {
            id: "n1",
            name: "Running Agent",
            type: "agent",
            status: "running",
            startTime: now - 1000,
          },
        ],
      };
      expect(trace.startTime).toBeDefined();
      expect(trace.endTime).toBeUndefined();
    });
  });
});

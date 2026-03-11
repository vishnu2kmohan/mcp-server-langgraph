/**
 * NodeInspector Tests
 *
 * TDD tests for the node configuration panel.
 * Tests cover:
 * - Visibility based on node selection
 * - Displaying node properties
 * - Editing node label
 * - Editing node-specific config
 * - Closing inspector
 * - AI Config Assistant integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { NodeInspector } from "./NodeInspector";
import workflowReducer, {
  initialWorkflowState,
} from "../../store/slices/workflowSlice";
import type { WorkflowSliceState } from "../../store/slices/workflowSlice";
import type { WorkflowNode } from "../../types/workflow";

// Mock RTK Query hooks for AI Config Assistant
const mockGetNodeConfigHelp = vi.fn().mockReturnValue({
  unwrap: () =>
    Promise.resolve({
      answer: "You should use 'gpt-4o' for high-quality responses.",
      suggested_config: { model: "gpt-4o", temperature: 0.7 },
      examples: ["Example usage here"],
    }),
});

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useGetNodeConfigHelpMutation: vi.fn(() => [
      mockGetNodeConfigHelp,
      { isLoading: false },
    ]),
  };
});
// Import the mocked function for test manipulation
import { useGetNodeConfigHelpMutation } from "../../api";
const mockUseGetNodeConfigHelpMutation = vi.mocked(
  useGetNodeConfigHelpMutation,
);

// Create a test store with custom workflow state
const createTestStore = (workflowState: Partial<WorkflowSliceState> = {}) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: { ...initialWorkflowState, ...workflowState },
    },
  });
};

// Helper to render with store
const renderWithStore = (
  component: React.ReactNode,
  workflowState: Partial<WorkflowSliceState> = {},
) => {
  const store = createTestStore(workflowState);
  return {
    store,
    ...render(<Provider store={store}>{component}</Provider>),
  };
};

// Mock nodes for testing
const mockLLMNode: WorkflowNode = {
  id: "node-llm-1",
  type: "default",
  position: { x: 100, y: 100 },
  data: {
    label: "LLM Node",
    nodeType: "llm",
    config: { model: "gpt-4o" },
    description: "An LLM node for processing",
  },
};

const mockToolNode: WorkflowNode = {
  id: "node-tool-1",
  type: "default",
  position: { x: 200, y: 100 },
  data: {
    label: "Tool Node",
    nodeType: "tool",
    config: { toolName: "search_web" },
  },
};

const mockStartNode: WorkflowNode = {
  id: "node-start-1",
  type: "default",
  position: { x: 0, y: 100 },
  data: {
    label: "Start",
    nodeType: "start",
    config: {},
  },
};

describe("NodeInspector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockGetNodeConfigHelp.mockReset();
    mockGetNodeConfigHelp.mockReturnValue({
      unwrap: () =>
        Promise.resolve({
          answer: "You should use 'gpt-4o' for high-quality responses.",
          suggested_config: { model: "gpt-4o", temperature: 0.7 },
          examples: ["Example usage here"],
        }),
    });
    mockUseGetNodeConfigHelpMutation.mockImplementation(() => [
      mockGetNodeConfigHelp,
      { isLoading: false },
    ]);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Visibility", () => {
    it("should not render when no node is selected", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: [],
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });

    it("should not render when multiple nodes are selected", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode, mockToolNode],
        selectedNodeIds: ["node-llm-1", "node-tool-1"],
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });

    it("should render when exactly one node is selected", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Node Inspector")).toBeInTheDocument();
    });
  });

  describe("Node Properties Display", () => {
    it("should display node type", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("llm")).toBeInTheDocument();
    });

    it("should display node label", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByDisplayValue("LLM Node")).toBeInTheDocument();
    });

    it("should display Type label", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Type")).toBeInTheDocument();
    });

    it("should display Label label", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Label")).toBeInTheDocument();
    });

    it("should display description field", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Description (optional)")).toBeInTheDocument();
    });

    it("should display node description value", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(
        screen.getByDisplayValue("An LLM node for processing"),
      ).toBeInTheDocument();
    });
  });

  describe("LLM Node Configuration", () => {
    it("should display model selector for LLM nodes", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Model")).toBeInTheDocument();
    });

    it("should display current model value", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      const select = screen.getByRole("combobox");
      expect(select).toHaveValue("gpt-4o");
    });

    it("should have model options", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Gemini 2.5 Flash")).toBeInTheDocument();
      expect(screen.getByText("Gemini 2.5 Pro")).toBeInTheDocument();
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
      expect(screen.getByText("Claude Opus 4.5")).toBeInTheDocument();
    });

    it("should update model in store when changed", () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.change(screen.getByRole("combobox"), {
        target: { value: "claude-opus-4.5" },
      });

      const state = store.getState().workflow;
      const updatedNode = state.nodes.find((n) => n.id === "node-llm-1");
      expect(updatedNode?.data.config.model).toBe("claude-opus-4.5");
    });

    it("should not show model selector for non-LLM nodes", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockStartNode],
        selectedNodeIds: ["node-start-1"],
      });

      expect(screen.queryByText("Model")).not.toBeInTheDocument();
    });
  });

  describe("Tool Node Configuration", () => {
    it("should display tool name field for tool nodes", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockToolNode],
        selectedNodeIds: ["node-tool-1"],
      });

      expect(screen.getByText("Tool Name")).toBeInTheDocument();
    });

    it("should display current tool name value", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockToolNode],
        selectedNodeIds: ["node-tool-1"],
      });

      expect(screen.getByDisplayValue("search_web")).toBeInTheDocument();
    });

    it("should show placeholder for tool name input", () => {
      const nodeWithoutToolName: WorkflowNode = {
        ...mockToolNode,
        data: { ...mockToolNode.data, config: {} },
      };

      renderWithStore(<NodeInspector />, {
        nodes: [nodeWithoutToolName],
        selectedNodeIds: ["node-tool-1"],
      });

      expect(
        screen.getByPlaceholderText("e.g., search_web, read_file"),
      ).toBeInTheDocument();
    });

    it("should update tool name in store when changed", () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockToolNode],
        selectedNodeIds: ["node-tool-1"],
      });

      fireEvent.change(screen.getByDisplayValue("search_web"), {
        target: { value: "read_file" },
      });

      const state = store.getState().workflow;
      const updatedNode = state.nodes.find((n) => n.id === "node-tool-1");
      expect(updatedNode?.data.config.toolName).toBe("read_file");
    });

    it("should not show tool name field for non-tool nodes", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.queryByText("Tool Name")).not.toBeInTheDocument();
    });
  });

  describe("Editing Node Label", () => {
    it("should update label in store when changed", () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.change(screen.getByDisplayValue("LLM Node"), {
        target: { value: "Updated Label" },
      });

      const state = store.getState().workflow;
      const updatedNode = state.nodes.find((n) => n.id === "node-llm-1");
      expect(updatedNode?.data.label).toBe("Updated Label");
    });
  });

  describe("Editing Description", () => {
    it("should update description in store when changed", () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      const textarea = screen.getByDisplayValue("An LLM node for processing");
      fireEvent.change(textarea, {
        target: { value: "Updated description" },
      });

      const state = store.getState().workflow;
      const updatedNode = state.nodes.find((n) => n.id === "node-llm-1");
      expect(updatedNode?.data.description).toBe("Updated description");
    });

    it("should allow empty description", () => {
      const nodeWithoutDescription: WorkflowNode = {
        ...mockStartNode,
        data: { ...mockStartNode.data, description: undefined },
      };

      renderWithStore(<NodeInspector />, {
        nodes: [nodeWithoutDescription],
        selectedNodeIds: ["node-start-1"],
      });

      // Should have an empty textarea
      const textareas = document.querySelectorAll("textarea");
      expect(textareas.length).toBeGreaterThan(0);
    });
  });

  describe("Close Inspector", () => {
    it("should have close button", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      const closeButton = document.querySelector("button");
      expect(closeButton).toBeInTheDocument();
    });

    it("should clear selection when close button is clicked", () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      // Find close button (first button in the component)
      const closeButton = document.querySelector("button");
      if (closeButton) {
        fireEvent.click(closeButton);
      }

      const state = store.getState().workflow;
      expect(state.selectedNodeIds).toEqual([]);
    });
  });

  describe("Different Node Types", () => {
    it("should render for start node", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockStartNode],
        selectedNodeIds: ["node-start-1"],
      });

      expect(screen.getByText("Node Inspector")).toBeInTheDocument();
      expect(screen.getByText("start")).toBeInTheDocument();
    });

    it("should render for tool node", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockToolNode],
        selectedNodeIds: ["node-tool-1"],
      });

      expect(screen.getByText("Node Inspector")).toBeInTheDocument();
      expect(screen.getByText("tool")).toBeInTheDocument();
    });

    it("should render for llm node", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByText("Node Inspector")).toBeInTheDocument();
      expect(screen.getByText("llm")).toBeInTheDocument();
    });
  });

  describe("Edge Cases", () => {
    it("should handle node not found gracefully", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [],
        selectedNodeIds: ["non-existent-node"],
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });

    it("should handle empty nodes array", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [],
        selectedNodeIds: [],
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });

    it("should handle undefined selectedNodeIds", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        // @ts-expect-error - testing undefined case
        selectedNodeIds: undefined,
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });

    it("should handle undefined nodes", () => {
      renderWithStore(<NodeInspector />, {
        // @ts-expect-error - testing undefined case
        nodes: undefined,
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.queryByText("Node Inspector")).not.toBeInTheDocument();
    });
  });

  describe("AI Config Assistant", () => {
    it("should have Ask AI button", () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      expect(screen.getByTestId("ask-ai-button")).toBeInTheDocument();
      expect(screen.getByText("Ask AI")).toBeInTheDocument();
    });

    it("should toggle AI chat panel when Ask AI is clicked", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      // Panel should not be visible initially
      expect(screen.queryByTestId("ai-chat-panel")).not.toBeInTheDocument();

      // Click Ask AI
      fireEvent.click(screen.getByTestId("ask-ai-button"));

      // Panel should be visible
      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });
    });

    it("should have question input in AI chat panel", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/ask about this node/i),
        ).toBeInTheDocument();
      });
    });

    it("should have send button in AI chat panel", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("send-ai-question")).toBeInTheDocument();
      });
    });

    it("should call API when question is submitted", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      // Type a question
      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, {
        target: { value: "What model should I use?" },
      });

      // Submit
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(mockGetNodeConfigHelp).toHaveBeenCalledWith({
          node_type: "llm",
          node_config: { model: "gpt-4o" },
          question: "What model should I use?",
        });
      });
    });

    it("should display AI response", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, {
        target: { value: "What model should I use?" },
      });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(
          screen.getByText(
            /You should use 'gpt-4o' for high-quality responses/,
          ),
        ).toBeInTheDocument();
      });
    });

    it("should show loading state while waiting for response", async () => {
      // Set loading state
      mockUseGetNodeConfigHelpMutation.mockImplementation(() => [
        mockGetNodeConfigHelp,
        { isLoading: true },
      ]);

      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-loading")).toBeInTheDocument();
      });
    });

    it("should show error message when API fails", async () => {
      mockGetNodeConfigHelp.mockReturnValue({
        unwrap: () => Promise.reject(new Error("API Error")),
      });

      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, { target: { value: "Test question" } });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-error")).toBeInTheDocument();
      });
    });

    it("should show Apply Config button when suggested config is provided", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, {
        target: { value: "What model should I use?" },
      });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(
          screen.getByTestId("apply-suggested-config"),
        ).toBeInTheDocument();
        expect(screen.getByText("Apply Suggested Config")).toBeInTheDocument();
      });
    });

    it("should apply suggested config to node when Apply is clicked", async () => {
      const { store } = renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, {
        target: { value: "What model should I use?" },
      });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(
          screen.getByTestId("apply-suggested-config"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("apply-suggested-config"));

      // Check that the node config was updated
      await waitFor(() => {
        const state = store.getState().workflow;
        const updatedNode = state.nodes.find((n) => n.id === "node-llm-1");
        expect(updatedNode?.data.config.temperature).toBe(0.7);
      });
    });

    it("should close AI panel when close button is clicked", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("close-ai-panel"));

      await waitFor(() => {
        expect(screen.queryByTestId("ai-chat-panel")).not.toBeInTheDocument();
      });
    });

    it("should clear previous response when new question is submitted", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      // First question
      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, { target: { value: "First question" } });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(screen.getByText(/You should use 'gpt-4o'/)).toBeInTheDocument();
      });

      // Change mock for second question
      mockGetNodeConfigHelp.mockReturnValue({
        unwrap: () =>
          Promise.resolve({
            answer: "Second answer",
            suggested_config: null,
            examples: [],
          }),
      });

      // Second question
      fireEvent.change(input, { target: { value: "Second question" } });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(screen.getByText(/Second answer/)).toBeInTheDocument();
      });
    });

    it("should show examples if provided in response", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/ask about this node/i);
      fireEvent.change(input, { target: { value: "Show me examples" } });
      fireEvent.click(screen.getByTestId("send-ai-question"));

      await waitFor(() => {
        expect(screen.getByText(/Example usage here/)).toBeInTheDocument();
      });
    });

    it("should disable send button when question is empty", async () => {
      renderWithStore(<NodeInspector />, {
        nodes: [mockLLMNode],
        selectedNodeIds: ["node-llm-1"],
      });

      fireEvent.click(screen.getByTestId("ask-ai-button"));

      await waitFor(() => {
        expect(screen.getByTestId("ai-chat-panel")).toBeInTheDocument();
      });

      const sendButton = screen.getByTestId("send-ai-question");
      expect(sendButton).toBeDisabled();
    });
  });
});

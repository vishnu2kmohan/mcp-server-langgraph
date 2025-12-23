/**
 * ChatProperties Tests
 *
 * TDD tests for the chat properties panel including model selection.
 */

import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ChatProperties } from "./ChatProperties";
import type { TabState } from "../../../store/slices/workspaceSlice";
import type { ClientSession } from "../../../types/session";
import type { MCPTool } from "../../../types/mcp";

// Mock the API hooks
const mockUpdateSessionConfig = vi.fn();
vi.mock("../../../api", () => ({
  useUpdateSessionConfigMutation: () => [
    mockUpdateSessionConfig,
    { isLoading: false, error: null },
  ],
}));

// =============================================================================
// Test Data
// =============================================================================

const mockTab: TabState = {
  id: "chat-1",
  type: "chat",
  title: "Test Chat",
  entityId: "session-123",
  isDirty: false,
  isLoading: false,
};

const mockSession: ClientSession = {
  id: "session-123",
  name: "Test Session",
  config: {
    modelProvider: "openai",
    modelName: "gpt-4o-mini",
    temperature: 0.7,
    maxTokens: 1000,
  },
  messages: [],
  createdAt: Date.now(),
  updatedAt: Date.now(),
};

const mockTools: MCPTool[] = [
  { name: "test-tool", description: "A test tool" },
];

// Simple mock store for tests
function createMockStore() {
  return configureStore({
    reducer: {
      api: (state = {}) => state,
    },
  });
}

// =============================================================================
// Tests
// =============================================================================

describe("ChatProperties", () => {
  const mockIsSectionExpanded = vi.fn(() => true);
  const mockOnToggleSection = vi.fn();

  afterEach(() => {
    cleanup();
  });

  beforeEach(() => {
    vi.clearAllMocks();
    mockIsSectionExpanded.mockReturnValue(true);
  });

  describe("Model Display", () => {
    it("displays the current model name", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      expect(screen.getByText("gpt-4o-mini")).toBeInTheDocument();
    });

    it("displays the model provider", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      expect(screen.getByText("openai")).toBeInTheDocument();
    });

    it("displays temperature and max tokens", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      expect(screen.getByText("0.7")).toBeInTheDocument();
      expect(screen.getByText("1,000")).toBeInTheDocument();
    });
  });

  describe("Model Selection", () => {
    it("has an edit button for model name", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-model-button");
      expect(editButton).toBeInTheDocument();
    });

    it("shows model input when edit button is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-model-button");
      fireEvent.click(editButton);

      await waitFor(() => {
        expect(screen.getByTestId("model-input")).toBeInTheDocument();
      });
    });

    it("updates model when save is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      // Click edit
      const editButton = screen.getByTestId("edit-model-button");
      fireEvent.click(editButton);

      // Change model name
      const input = screen.getByTestId("model-input");
      fireEvent.change(input, { target: { value: "claude-3-sonnet" } });

      // Click save
      const saveButton = screen.getByTestId("save-model-button");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateSessionConfig).toHaveBeenCalledWith({
          session_id: "session-123",
          model: "claude-3-sonnet",
        });
      });
    });

    it("cancels edit when cancel button is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      // Click edit
      const editButton = screen.getByTestId("edit-model-button");
      fireEvent.click(editButton);

      // Change model name
      const input = screen.getByTestId("model-input");
      fireEvent.change(input, { target: { value: "claude-3-sonnet" } });

      // Click cancel
      const cancelButton = screen.getByTestId("cancel-model-button");
      fireEvent.click(cancelButton);

      await waitFor(() => {
        expect(screen.queryByTestId("model-input")).not.toBeInTheDocument();
      });

      // Original value should still be displayed
      expect(screen.getByText("gpt-4o-mini")).toBeInTheDocument();
    });
  });

  describe("Temperature Editing", () => {
    it("has an edit button for temperature", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-temperature-button");
      expect(editButton).toBeInTheDocument();
    });

    it("shows temperature input when edit button is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-temperature-button");
      fireEvent.click(editButton);

      await waitFor(() => {
        expect(screen.getByTestId("temperature-input")).toBeInTheDocument();
      });
    });

    it("updates temperature when save is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      // Click edit
      const editButton = screen.getByTestId("edit-temperature-button");
      fireEvent.click(editButton);

      // Change temperature
      const input = screen.getByTestId("temperature-input");
      fireEvent.change(input, { target: { value: "0.9" } });

      // Click save
      const saveButton = screen.getByTestId("save-temperature-button");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateSessionConfig).toHaveBeenCalledWith({
          session_id: "session-123",
          temperature: 0.9,
        });
      });
    });
  });

  describe("Max Tokens Editing", () => {
    it("has an edit button for max tokens", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-max-tokens-button");
      expect(editButton).toBeInTheDocument();
    });

    it("shows max tokens input when edit button is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-max-tokens-button");
      fireEvent.click(editButton);

      await waitFor(() => {
        expect(screen.getByTestId("max-tokens-input")).toBeInTheDocument();
      });
    });

    it("updates max tokens when save is clicked", async () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={mockSession}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      // Click edit
      const editButton = screen.getByTestId("edit-max-tokens-button");
      fireEvent.click(editButton);

      // Change max tokens
      const input = screen.getByTestId("max-tokens-input");
      fireEvent.change(input, { target: { value: "2000" } });

      // Click save
      const saveButton = screen.getByTestId("save-max-tokens-button");
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(mockUpdateSessionConfig).toHaveBeenCalledWith({
          session_id: "session-123",
          max_tokens: 2000,
        });
      });
    });
  });

  describe("No Session", () => {
    it("shows default values when session is null", () => {
      render(
        <Provider store={createMockStore()}>
          <ChatProperties
            tab={mockTab}
            session={null}
            tools={mockTools}
            isSectionExpanded={mockIsSectionExpanded}
            onToggleSection={mockOnToggleSection}
          />
        </Provider>,
      );

      expect(screen.getByText("Not configured")).toBeInTheDocument();
      expect(screen.getByText("Default")).toBeInTheDocument();
    });
  });
});

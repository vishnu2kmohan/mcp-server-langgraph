/**
 * useSlashCommands Hook Tests
 *
 * TDD tests for the hook that converts workflow templates
 * into slash commands for the chat input.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

// Mock the API
const mockTemplates = [
  {
    id: "template-1",
    name: "Simple Chatbot",
    description: "A basic chatbot workflow",
    category: "chat",
    tags: ["beginner", "chatbot"],
  },
  {
    id: "template-2",
    name: "RAG Pipeline",
    description: "Retrieval-Augmented Generation workflow",
    category: "retrieval",
    tags: ["advanced", "rag"],
  },
  {
    id: "template-3",
    name: "Multi-Agent System",
    description: "Coordinated multi-agent workflow",
    category: "agents",
    tags: ["advanced", "agents"],
  },
];

vi.mock("../api", () => ({
  useGetWorkflowTemplatesQuery: vi.fn(() => ({
    data: mockTemplates,
    isLoading: false,
    error: null,
  })),
  api: {
    reducerPath: "api",
    reducer: (state = {}) => state,
    middleware: (getDefault: () => unknown[]) => getDefault(),
  },
}));

// Import after mock
import { useSlashCommands } from "./useSlashCommands";

// Create wrapper with store
const createWrapper = () => {
  const store = configureStore({
    reducer: {
      api: (state = {}) => state,
    },
  });

  const Wrapper = ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );

  return Wrapper;
};

describe("useSlashCommands", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("template to command conversion", () => {
    it("should convert workflow templates to slash commands", async () => {
      const { result } = renderHook(() => useSlashCommands(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.commands.length).toBeGreaterThan(0);
      });

      // Check first command
      const firstCommand = result.current.commands.find(
        (c) => c.name === "chatbot",
      );
      expect(firstCommand).toBeDefined();
      expect(firstCommand?.description).toBe("A basic chatbot workflow");
    });

    it("should convert template name to lowercase command name", async () => {
      const { result } = renderHook(() => useSlashCommands(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.commands.length).toBeGreaterThan(0);
      });

      // Multi-word template names should be converted to lowercase slug
      const ragCommand = result.current.commands.find((c) =>
        c.name.includes("rag"),
      );
      expect(ragCommand).toBeDefined();
      expect(ragCommand?.name).not.toContain(" ");
    });

    it("should include default built-in commands", async () => {
      const { result } = renderHook(() => useSlashCommands(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.commands.length).toBeGreaterThan(0);
      });

      // Should include built-in commands like /help, /clear
      const helpCommand = result.current.commands.find(
        (c) => c.name === "help",
      );
      expect(helpCommand).toBeDefined();
      expect(helpCommand?.icon).toBe("help");

      const clearCommand = result.current.commands.find(
        (c) => c.name === "clear",
      );
      expect(clearCommand).toBeDefined();
      expect(clearCommand?.icon).toBe("trash");
    });
  });

  describe("loading states", () => {
    it("should return built-in commands while templates are loading", async () => {
      // When templates are loading, the hook should still return built-in commands
      const { result } = renderHook(() => useSlashCommands(), {
        wrapper: createWrapper(),
      });

      // Built-in commands should always be available
      const helpCommand = result.current.commands.find(
        (c) => c.name === "help",
      );
      expect(helpCommand).toBeDefined();

      // isLoading reflects template fetch state (mocked as false)
      // In real usage, this would be true initially
      expect(typeof result.current.isLoading).toBe("boolean");
    });
  });

  describe("command handler", () => {
    it("should provide onSelect handler for template commands", async () => {
      const onTemplateSelect = vi.fn();

      const { result } = renderHook(
        () => useSlashCommands({ onTemplateSelect }),
        {
          wrapper: createWrapper(),
        },
      );

      await waitFor(() => {
        expect(result.current.commands.length).toBeGreaterThan(0);
      });

      // Find a template command (not a built-in)
      const templateCommand = result.current.commands.find(
        (c) => c.name === "chatbot",
      );
      expect(templateCommand).toBeDefined();

      // Simulate selecting the command
      result.current.handleSelect(templateCommand!);

      // Template callback should be called with template ID
      expect(onTemplateSelect).toHaveBeenCalledWith(
        expect.objectContaining({
          templateId: "template-1",
        }),
      );
    });
  });
});

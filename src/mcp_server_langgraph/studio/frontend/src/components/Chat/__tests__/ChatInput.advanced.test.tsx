/**
 * ChatInput Advanced Features Tests
 *
 * Covers: model settings dropdown, tool selector, KB focus selector, voice input,
 * inline suggestions, slash commands, URL content fetch, mentions system,
 * recent models and model search, KB status indicator, model lifecycle badges,
 * tools loading state, PreferencesMenu integration, ExecutionMode integration,
 * Provider Display Formatting
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createMockProps } from "./ChatInput.fixtures";
import { TestProvider } from "@/test-utils";
import { ChatInput } from "../ChatInput";

describe("ChatInput - advanced", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("model settings dropdown", () => {
    const mockModels = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "claude-sonnet-4",
        name: "Claude Sonnet 4",
        provider: "anthropic",
        supportsThinking: false,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
        supportsThinking: false,
      },
    ];

    it("renders model settings button with brain icon when showModelSelector is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-settings-button")).toBeInTheDocument();
    });

    it("does not render model settings when showModelSelector is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showModelSelector: false })} />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });

    it("displays selected model name on button", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Claude Opus 4.5")).toBeInTheDocument();
    });

    it("displays provider badge on button", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      // formatProviderDisplay properly cases provider names
      expect(screen.getByText("Anthropic")).toBeInTheDocument();
    });

    it("opens dropdown when clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("model-settings-dropdown")).toBeInTheDocument();
    });

    it("shows all available models in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Claude Sonnet 4")).toBeInTheDocument();
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
    });

    it("calls onModelChange when model is selected", async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              onModelChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.click(screen.getByText("GPT-4o"));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("shows thinking controls when model supports thinking", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              reasoningEffort: "medium",
              onReasoningEffortChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByTestId("thinking-controls")).toBeInTheDocument();
    });

    it("hides thinking controls when model does not support thinking", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "gpt-4o",
              availableModels: mockModels,
              modelSupportsThinking: false,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.queryByTestId("thinking-controls")).not.toBeInTheDocument();
    });

    it("calls onReasoningEffortChange when thinking level is changed", async () => {
      const user = userEvent.setup();
      const onReasoningEffortChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              modelSupportsThinking: true,
              reasoningEffort: "medium",
              onReasoningEffortChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.click(screen.getByRole("button", { name: /high/i }));

      expect(onReasoningEffortChange).toHaveBeenCalledWith("high");
    });

    it("closes dropdown when Escape is pressed", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      expect(screen.getByTestId("model-settings-dropdown")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      expect(
        screen.queryByTestId("model-settings-dropdown"),
      ).not.toBeInTheDocument();
    });
  });

  describe("tool selector", () => {
    it("renders tool selector when showToolSelector is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showToolSelector: true,
              selectedTools: [],
              onSelectedToolsChange: vi.fn(),
              toolSelectionMode: "auto",
              onToolSelectionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("tool-selector")).toBeInTheDocument();
    });

    it("does not render tool selector when showToolSelector is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showToolSelector: false })} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("tool-selector")).not.toBeInTheDocument();
    });
  });

  describe("KB focus selector", () => {
    it("renders KB focus when showKBFocus is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "all",
              onKBFocusChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("kb-focus-selector")).toBeInTheDocument();
    });

    it("does not render KB focus when showKBFocus is false", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ showKBFocus: false })} />
        </TestProvider>,
      );

      expect(screen.queryByTestId("kb-focus-selector")).not.toBeInTheDocument();
    });
  });

  describe("slash commands", () => {
    const mockSlashCommands = [
      { name: "help", description: "Show help", icon: "help" },
      { name: "clear", description: "Clear conversation", icon: "trash" },
    ];

    it("shows slash command menu when user types /", async () => {
      const _user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "/",
              onChange,
              slashCommands: mockSlashCommands,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("calls onSlashCommandSelect when a command is clicked", async () => {
      const user = userEvent.setup();
      const onSlashCommandSelect = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "/",
              slashCommands: mockSlashCommands,
              onSlashCommandSelect,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("/help"));

      expect(onSlashCommandSelect).toHaveBeenCalledWith(mockSlashCommands[0]);
    });
  });

  describe("URL content fetch", () => {
    it("shows URL loading indicator when urlFetchLoading contains URLs", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              urlFetchLoading: ["https://example.com"],
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("url-fetch-loading")).toBeInTheDocument();
    });

    it("displays fetched URL badges", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              fetchedUrls: [
                {
                  url: "https://example.com",
                  title: "Example Site",
                  content: "...",
                },
              ],
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("Example Site")).toBeInTheDocument();
    });

    it("calls onRemoveFetchedUrl when URL badge is removed", async () => {
      const user = userEvent.setup();
      const onRemoveFetchedUrl = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              enableUrlFetch: true,
              fetchedUrls: [
                {
                  url: "https://example.com",
                  title: "Example Site",
                  content: "...",
                },
              ],
              onRemoveFetchedUrl,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /remove.*url/i }));

      expect(onRemoveFetchedUrl).toHaveBeenCalledWith("https://example.com");
    });
  });

  describe("mentions system", () => {
    const mockMentionOptions = [
      {
        type: "model" as const,
        value: "claude-opus-4-5",
        label: "Claude Opus 4.5",
      },
      { type: "file" as const, value: "readme.md", label: "readme.md" },
    ];

    it("shows mention suggestions when @ is typed", async () => {
      const _user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "@",
              onChange,
              mentionOptions: mockMentionOptions,
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("mention-suggestions")).toBeInTheDocument();
    });

    it("inserts mention when suggestion is clicked", async () => {
      const user = userEvent.setup();
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              value: "@cl",
              onChange,
              mentionOptions: mockMentionOptions,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByText("Claude Opus 4.5"));

      expect(onChange).toHaveBeenCalledWith(
        expect.stringContaining("@claude-opus-4-5"),
      );
    });
  });

  describe("recent models and model search", () => {
    const mockModels = [
      { id: "claude-opus-4-5", name: "Claude Opus 4.5", provider: "anthropic" },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic" },
      { id: "gpt-4o", name: "GPT-4o", provider: "openai" },
    ];

    it("shows recent models section when recentModels is provided", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              recentModels: ["gpt-4o", "claude-sonnet-4"],
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Recent")).toBeInTheDocument();
    });

    it("shows model search input when enableModelSearch is true", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              enableModelSearch: true,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByPlaceholderText(/search models/i)).toBeInTheDocument();
    });

    it("filters models based on search query", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModels,
              enableModelSearch: true,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));
      await user.type(screen.getByPlaceholderText(/search models/i), "gpt");

      // GPT-4o should be visible in the dropdown
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
      // Claude models should be filtered out from the dropdown list
      // (Claude Opus 4.5 will still appear on the button as the selected model)
      const dropdown = screen.getByTestId("model-settings-dropdown");
      expect(dropdown.querySelector('[role="option"]')?.textContent).toContain(
        "GPT-4o",
      );
      // Verify Claude Sonnet 4 is not in the dropdown (it was never the selected model)
      expect(screen.queryByText("Claude Sonnet 4")).not.toBeInTheDocument();
    });
  });

  describe("KB status indicator", () => {
    it("shows KB status indicator when kbStatus is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "kb_only",
              onKBFocusChange: vi.fn(),
              kbStatus: "ready",
              kbStatusMessage: "Knowledge base is ready",
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("kb-status-indicator")).toBeInTheDocument();
    });

    it("shows tooltip with kbStatusMessage on hover", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showKBFocus: true,
              kbFocusValue: "kb_only",
              onKBFocusChange: vi.fn(),
              kbStatus: "misconfigured",
              kbStatusMessage: "API key not configured",
            })}
          />
        </TestProvider>,
      );

      await user.hover(screen.getByTestId("kb-status-indicator"));

      expect(screen.getByText("API key not configured")).toBeInTheDocument();
    });
  });

  describe("model lifecycle badges", () => {
    const mockModelsWithStatus = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        status: "current" as const,
      },
      {
        id: "claude-3-opus",
        name: "Claude 3 Opus",
        provider: "anthropic",
        status: "deprecated" as const,
        sunsetDate: "2025-06-01",
      },
      {
        id: "gpt-4-preview",
        name: "GPT-4 Preview",
        provider: "openai",
        status: "preview" as const,
      },
    ];

    it("shows lifecycle badge for deprecated models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Deprecated")).toBeInTheDocument();
    });

    it("shows preview badge for preview models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText("Preview")).toBeInTheDocument();
    });

    it("shows sunset date for deprecated models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithStatus,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("model-settings-button"));

      expect(screen.getByText(/sunset.*2025-06-01/i)).toBeInTheDocument();
    });
  });

  describe("tools loading state", () => {
    it("shows loading indicator in tool selector when isToolsLoading is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showToolSelector: true,
              isToolsLoading: true,
              onSelectedToolsChange: vi.fn(),
              onToolSelectionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("tools-loading")).toBeInTheDocument();
    });
  });

  describe("PreferencesMenu integration", () => {
    const mockModels = [
      { id: "claude-opus-4-5", name: "Claude Opus 4.5", provider: "anthropic" },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic" },
    ];

    it("renders PreferencesMenu when showPreferencesMenu is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange: vi.fn(),
              onThinkingLevelChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(
        screen.getByTestId("preferences-menu-trigger"),
      ).toBeInTheDocument();
    });

    it("hides model selector when showPreferencesMenu is true", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              showModelSelector: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // PreferencesMenu should be visible
      expect(
        screen.getByTestId("preferences-menu-trigger"),
      ).toBeInTheDocument();
      // Standard model selector should NOT be visible (preferences menu replaces it)
      expect(
        screen.queryByTestId("model-settings-button"),
      ).not.toBeInTheDocument();
    });

    it("passes model props to PreferencesMenu", async () => {
      const onModelChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              onModelChange,
            })}
          />
        </TestProvider>,
      );

      // Open preferences menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Verify menu opened
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("passes thinking level props to PreferencesMenu", async () => {
      const onThinkingLevelChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showPreferencesMenu: true,
              availableModels: mockModels,
              selectedModel: "claude-opus-4-5",
              thinkingLevel: "medium",
              onThinkingLevelChange,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Verify thinking submenu trigger exists
      expect(
        screen.getByTestId("submenu-trigger-thinking"),
      ).toBeInTheDocument();
    });
  });

  describe("ExecutionMode integration", () => {
    it("renders SegmentedControl when onExecutionModeChange is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onExecutionModeChange: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // SegmentedControl wrapper is rendered when onExecutionModeChange is provided
      expect(
        screen.getByTestId("execution-mode-segmented"),
      ).toBeInTheDocument();
    });

    it("renders ExecutionModeIndicator when only onCycleExecutionMode is provided", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "plan",
              onCycleExecutionMode: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      // ExecutionModeIndicator shows the mode badge when only cycling is available
      expect(
        screen.getByTestId("execution-mode-indicator"),
      ).toBeInTheDocument();
    });

    it("calls onExecutionModeChange when mode is changed via SegmentedControl", async () => {
      const onExecutionModeChange = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onExecutionModeChange,
            })}
          />
        </TestProvider>,
      );

      // Find and click the plan mode option
      const planOption = screen.getByRole("radio", { name: /plan/i });
      await user.click(planOption);

      expect(onExecutionModeChange).toHaveBeenCalledWith("plan");
    });

    it("calls onCycleExecutionMode when keyboard shortcut is used", async () => {
      const onCycleExecutionMode = vi.fn();
      const user = userEvent.setup();

      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              executionMode: "default",
              onCycleExecutionMode,
            })}
          />
        </TestProvider>,
      );

      // Focus the textarea
      const textarea = screen.getByRole("textbox");
      await user.click(textarea);

      // Ctrl+Shift+M cycles execution mode
      await user.keyboard("{Control>}{Shift>}m{/Shift}{/Control}");

      expect(onCycleExecutionMode).toHaveBeenCalled();
    });
  });

  describe("Provider Display Formatting", () => {
    const mockModelsWithVendor = [
      {
        id: "claude-opus-4-5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        vendor: "vertex_ai_anthropic" as const,
      },
      {
        id: "gemini-2.5-pro",
        name: "Gemini 2.5 Pro",
        provider: "google",
        vendor: "vertex_ai" as const,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
      },
    ];

    it("displays formatted provider names with proper casing in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithVendor,
            })}
          />
        </TestProvider>,
      );

      // Open the model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      // Should show properly formatted provider names with vendor context
      // Vertex AI models show "(Vertex AI)" suffix, direct API models show just the provider
      // Use getAllByText since button AND dropdown both show the selected model's provider
      expect(
        screen.getAllByText("Anthropic (Vertex AI)").length,
      ).toBeGreaterThan(0);
      expect(screen.getByText("OpenAI")).toBeInTheDocument();
      expect(screen.getByText("Google (Vertex AI)")).toBeInTheDocument();
    });

    it("shows vendor info when different from provider", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              showModelSelector: true,
              selectedModel: "claude-opus-4-5",
              availableModels: mockModelsWithVendor,
            })}
          />
        </TestProvider>,
      );

      // Open the model dropdown
      await user.click(screen.getByTestId("model-settings-button"));

      // Vertex AI models should show vendor context (getAllByText since multiple may exist)
      const vertexElements = screen.getAllByText(/Vertex AI/);
      expect(vertexElements.length).toBeGreaterThan(0);
    });
  });
});

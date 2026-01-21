/**
 * HeaderModelSelector Tests
 *
 * TDD tests for the unified header-based model selector that combines
 * model selection and thinking level into a single compact control.
 *
 * Based on user research:
 * - Header-Based pattern (ChatGPT/Gemini style)
 * - Combined selector: "Claude Opus (High)"
 * - Set-and-forget usage pattern
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { HeaderModelSelector, type ModelOption } from "./HeaderModelSelector";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";

// Mock the useNativeCapabilities hook
vi.mock("@/hooks", () => ({
  useNativeCapabilities: vi.fn(),
}));

import { useNativeCapabilities } from "@/hooks";
const mockUseNativeCapabilities = useNativeCapabilities as ReturnType<typeof vi.fn>;

// =============================================================================
// Test Data
// =============================================================================

const mockModels: ModelOption[] = [
  {
    id: "claude-opus-4.5",
    name: "Claude Opus 4.5",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "claude-sonnet-4",
    name: "Claude Sonnet 4",
    provider: "anthropic",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gpt-4o",
    name: "GPT-4o",
    provider: "openai",
    supportsThinking: false,
    supportsVision: true,
    supportsTools: true,
    status: "current",
  },
  {
    id: "gemini-2.5-pro",
    name: "Gemini 2.5 Pro",
    provider: "google",
    supportsThinking: true,
    supportsVision: true,
    supportsTools: true,
    status: "preview",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("HeaderModelSelector", () => {
  const defaultProps = {
    selectedModel: "claude-opus-4.5",
    availableModels: mockModels,
    onModelChange: vi.fn(),
    thinkingLevel: "medium" as ReasoningEffortLevel,
    onThinkingLevelChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock: no native tools available
    mockUseNativeCapabilities.mockReturnValue({
      capabilities: [],
      nativeProvider: null,
      masterEnabled: false,
      isLoading: false,
      isError: false,
      error: undefined,
      refetch: vi.fn(),
      supportsWebSearch: false,
      supportsCodeExecution: false,
      hasNativeTools: false,
      isToolAvailable: () => false,
      getCapability: () => undefined,
    });
  });

  describe("Rendering", () => {
    it("renders the combined selector pill", () => {
      render(<HeaderModelSelector {...defaultProps} />);

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toBeInTheDocument();
    });

    it("displays model name and thinking level in pill", () => {
      render(<HeaderModelSelector {...defaultProps} />);

      // Should show combined format: "Claude Opus 4.5 (Medium)"
      expect(screen.getByText(/Claude Opus 4.5/)).toBeInTheDocument();
      expect(screen.getByText(/Medium/i)).toBeInTheDocument();
    });

    it("hides thinking level for models that don't support it", () => {
      render(
        <HeaderModelSelector {...defaultProps} selectedModel="gpt-4o" />
      );

      // Should show only model name, no thinking level
      expect(screen.getByText(/GPT-4o/)).toBeInTheDocument();
      expect(screen.queryByText(/Medium/i)).not.toBeInTheDocument();
    });

    it("shows loading state when models are loading", () => {
      render(<HeaderModelSelector {...defaultProps} isLoading />);

      expect(screen.getByTestId("model-loading-spinner")).toBeInTheDocument();
    });

    it("can be disabled", () => {
      render(<HeaderModelSelector {...defaultProps} disabled />);

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveAttribute("disabled");
    });
  });

  describe("Dropdown Behavior", () => {
    it("opens dropdown on click", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      const pill = screen.getByTestId("header-model-selector");
      await user.click(pill);

      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();
    });

    it("closes dropdown on outside click", async () => {
      const user = userEvent.setup();
      render(
        <div>
          <HeaderModelSelector {...defaultProps} />
          <button data-testid="outside-button">Outside</button>
        </div>
      );

      // Open dropdown
      await user.click(screen.getByTestId("header-model-selector"));
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();

      // Click outside
      await user.click(screen.getByTestId("outside-button"));
      await waitFor(() => {
        expect(screen.queryByTestId("model-dropdown")).not.toBeInTheDocument();
      });
    });

    it("closes dropdown on Escape key", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      await waitFor(() => {
        expect(screen.queryByTestId("model-dropdown")).not.toBeInTheDocument();
      });
    });
  });

  describe("Model Selection", () => {
    it("displays all available models in dropdown", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      mockModels.forEach((model) => {
        expect(within(dropdown).getByText(model.name)).toBeInTheDocument();
      });
    });

    it("shows checkmark next to selected model", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      // Find the selected model option
      const selectedOption = screen.getByRole("option", {
        name: /Claude Opus 4.5/,
      });
      expect(
        within(selectedOption).getByTestId("model-selected-check")
      ).toBeInTheDocument();
    });

    it("calls onModelChange when a model is selected", async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();
      render(
        <HeaderModelSelector {...defaultProps} onModelChange={onModelChange} />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("closes dropdown after model selection", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      await waitFor(() => {
        expect(screen.queryByTestId("model-dropdown")).not.toBeInTheDocument();
      });
    });

    it("shows thinking badge for models that support thinking", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      // Models with thinking support should have a brain icon
      const opusOption = screen.getByRole("option", { name: /Claude Opus 4.5/ });
      expect(within(opusOption).getByTestId("thinking-badge")).toBeInTheDocument();

      // GPT-4o doesn't support thinking
      const gptOption = screen.getByRole("option", { name: /GPT-4o/ });
      expect(within(gptOption).queryByTestId("thinking-badge")).not.toBeInTheDocument();
    });
  });

  describe("Thinking Level Selection", () => {
    it("shows thinking level section in dropdown for thinking-capable models", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("thinking-level-section")).toBeInTheDocument();
    });

    it("hides thinking level section for non-thinking models", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector {...defaultProps} selectedModel="gpt-4o" />
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.queryByTestId("thinking-level-section")).not.toBeInTheDocument();
    });

    it("displays all thinking levels (Low, Medium, High)", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByRole("radio", { name: /Low/i })).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: /Medium/i })).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: /High/i })).toBeInTheDocument();
    });

    it("highlights current thinking level", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} thinkingLevel="high" />);

      await user.click(screen.getByTestId("header-model-selector"));

      const highRadio = screen.getByRole("radio", { name: /High/i });
      expect(highRadio).toBeChecked();
    });

    it("calls onThinkingLevelChange when level is changed", async () => {
      const user = userEvent.setup();
      const onThinkingLevelChange = vi.fn();
      render(
        <HeaderModelSelector
          {...defaultProps}
          onThinkingLevelChange={onThinkingLevelChange}
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("radio", { name: /High/i }));

      expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
    });

    it("keeps dropdown open after changing thinking level", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("radio", { name: /High/i }));

      // Dropdown should remain open for further adjustments
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("supports arrow key navigation in model list", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));
      await user.keyboard("{ArrowDown}");

      // First model should be focused
      const firstOption = screen.getAllByRole("option")[0];
      expect(firstOption).toHaveFocus();
    });

    it("selects model on Enter key", async () => {
      const user = userEvent.setup();
      const onModelChange = vi.fn();
      render(
        <HeaderModelSelector {...defaultProps} onModelChange={onModelChange} />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.keyboard("{ArrowDown}");
      await user.keyboard("{ArrowDown}"); // Move to second model
      await user.keyboard("{Enter}");

      expect(onModelChange).toHaveBeenCalledWith("claude-sonnet-4");
    });
  });

  describe("Accessibility", () => {
    it("has proper ARIA attributes", () => {
      render(<HeaderModelSelector {...defaultProps} />);

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveAttribute("aria-haspopup", "listbox");
      expect(pill).toHaveAttribute("aria-expanded", "false");
    });

    it("sets aria-expanded when dropdown opens", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      const pill = screen.getByTestId("header-model-selector");
      await user.click(pill);

      expect(pill).toHaveAttribute("aria-expanded", "true");
    });

    it("has accessible label", () => {
      render(<HeaderModelSelector {...defaultProps} />);

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Claude Opus 4.5")
      );
    });

    it("dropdown has proper role", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      const dropdown = screen.getByTestId("model-dropdown");
      expect(dropdown).toHaveAttribute("role", "listbox");
    });

    it("model options have proper role", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      const options = screen.getAllByRole("option");
      expect(options.length).toBe(mockModels.length);
    });
  });

  describe("Status Badges", () => {
    it("shows preview badge for preview models", async () => {
      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      const geminiOption = screen.getByRole("option", { name: /Gemini 2.5 Pro/ });
      expect(within(geminiOption).getByText("Preview")).toBeInTheDocument();
    });
  });

  describe("Compact Mode", () => {
    it("renders compact version when compact prop is true", () => {
      render(<HeaderModelSelector {...defaultProps} compact />);

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveClass("compact");
    });

    it("shows abbreviated model name in compact mode", () => {
      render(<HeaderModelSelector {...defaultProps} compact />);

      // Should show abbreviated like "Opus 4.5" instead of "Claude Opus 4.5"
      expect(screen.getByText(/Opus/)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Native Tools Section Tests (v7)
  // ===========================================================================

  describe("Native Tools Section", () => {
    it("shows native tools section when native tools are available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "web_search_20250305", enabled: true },
          { toolName: "code_execution", supported: true, providerType: "code_execution_20250825", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: true,
        hasNativeTools: true,
        isToolAvailable: (name: string) => name === "web_search" || name === "code_execution",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-tools-section")).toBeInTheDocument();
    });

    it("hides native tools section when no native tools available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [],
        nativeProvider: null,
        masterEnabled: false,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: false,
        supportsCodeExecution: false,
        hasNativeTools: false,
        isToolAvailable: () => false,
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.queryByTestId("native-tools-section")).not.toBeInTheDocument();
    });

    it("hides native tools section when master switch is disabled", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "web_search_20250305", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: false, // Master switch off
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: false,
        hasNativeTools: true, // Has tools but master is off
        isToolAvailable: () => false,
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      // Should not show because masterEnabled is false
      expect(screen.queryByTestId("native-tools-section")).not.toBeInTheDocument();
    });

    it("shows web search badge when web search is available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "web_search_20250305", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: false,
        hasNativeTools: true,
        isToolAvailable: (name: string) => name === "web_search",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(screen.getByText("Web Search")).toBeInTheDocument();
    });

    it("shows code execution badge when code execution is available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "code_execution", supported: true, providerType: "code_execution_20250825", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: false,
        supportsCodeExecution: true,
        hasNativeTools: true,
        isToolAvailable: (name: string) => name === "code_execution",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-code-execution-badge")).toBeInTheDocument();
      expect(screen.getByText("Code Execution")).toBeInTheDocument();
    });

    it("shows both badges when both capabilities are available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "web_search_20250305", enabled: true },
          { toolName: "code_execution", supported: true, providerType: "code_execution_20250825", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: true,
        hasNativeTools: true,
        isToolAvailable: () => true,
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(screen.getByTestId("native-code-execution-badge")).toBeInTheDocument();
    });

    it("shows provider name in native tools section", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "web_search_20250305", enabled: true },
        ],
        nativeProvider: "anthropic",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: false,
        hasNativeTools: true,
        isToolAvailable: () => true,
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(<HeaderModelSelector {...defaultProps} />);

      await user.click(screen.getByTestId("header-model-selector"));

      // Should show provider name in the native tools section
      const nativeSection = screen.getByTestId("native-tools-section");
      expect(within(nativeSection).getByText(/anthropic/i)).toBeInTheDocument();
    });

    it("shows Google provider for Gemini models", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "googleSearch", enabled: true },
        ],
        nativeProvider: "google",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: false,
        hasNativeTools: true,
        isToolAvailable: (name: string) => name === "web_search",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(
        <HeaderModelSelector {...defaultProps} selectedModel="gemini-2.5-pro" />
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const nativeSection = screen.getByTestId("native-tools-section");
      expect(nativeSection).toBeInTheDocument();
      expect(within(nativeSection).getByText(/google/i)).toBeInTheDocument();
    });

    it("does not show code execution badge for Google models", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          { toolName: "web_search", supported: true, providerType: "googleSearch", enabled: true },
          { toolName: "code_execution", supported: false, providerType: null, enabled: false },
        ],
        nativeProvider: "google",
        masterEnabled: true,
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
        supportsWebSearch: true,
        supportsCodeExecution: false, // Google doesn't support code execution
        hasNativeTools: true,
        isToolAvailable: (name: string) => name === "web_search",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(
        <HeaderModelSelector {...defaultProps} selectedModel="gemini-2.5-pro" />
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(screen.queryByTestId("native-code-execution-badge")).not.toBeInTheDocument();
    });
  });

  // Issue 4: Model Selector Search functionality tests
  describe("Model Search", () => {
    const manyModels: ModelOption[] = [
      { id: "claude-opus-4.5", name: "Claude Opus 4.5", provider: "anthropic", supportsThinking: true },
      { id: "claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic", supportsThinking: true },
      { id: "claude-haiku-3.5", name: "Claude Haiku 3.5", provider: "anthropic", supportsThinking: false },
      { id: "gpt-4o", name: "GPT-4o", provider: "openai", supportsThinking: false },
      { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", supportsThinking: false },
      { id: "gemini-2.5-pro", name: "Gemini 2.5 Pro", provider: "google", supportsThinking: true },
      { id: "gemini-2.5-flash", name: "Gemini 2.5 Flash", provider: "google", supportsThinking: true },
    ];

    it("shows search input when enableSearch prop is true and many models", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("model-search-input")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/search models/i)).toBeInTheDocument();
    });

    it("filters models based on search query", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "claude");

      // Should only show Claude models in dropdown
      expect(within(dropdown).getByText("Claude Opus 4.5")).toBeInTheDocument();
      expect(within(dropdown).getByText("Claude Sonnet 4")).toBeInTheDocument();
      expect(within(dropdown).getByText("Claude Haiku 3.5")).toBeInTheDocument();

      // Should not show other models in dropdown
      expect(within(dropdown).queryByText("GPT-4o")).not.toBeInTheDocument();
      expect(within(dropdown).queryByText("Gemini 2.5 Pro")).not.toBeInTheDocument();
    });

    it("filters by provider name", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "google");

      // Should show Google models in dropdown
      expect(within(dropdown).getByText("Gemini 2.5 Pro")).toBeInTheDocument();
      expect(within(dropdown).getByText("Gemini 2.5 Flash")).toBeInTheDocument();

      // Should not show other models in dropdown
      expect(within(dropdown).queryByText("Claude Opus 4.5")).not.toBeInTheDocument();
      expect(within(dropdown).queryByText("GPT-4o")).not.toBeInTheDocument();
    });

    it("shows no results message when search has no matches", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.type(screen.getByTestId("model-search-input"), "xyz123");

      expect(screen.getByText(/no models found/i)).toBeInTheDocument();
    });

    it("clears search on dropdown close", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.type(screen.getByTestId("model-search-input"), "claude");
      await user.keyboard("{Escape}");

      // Reopen dropdown
      await user.click(screen.getByTestId("header-model-selector"));

      // Search should be cleared
      expect(screen.getByTestId("model-search-input")).toHaveValue("");
      // All models should be visible
      expect(screen.getByText("GPT-4o")).toBeInTheDocument();
    });

    it("does not show search when enableSearch is false", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch={false}
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.queryByTestId("model-search-input")).not.toBeInTheDocument();
    });

    it("is case-insensitive", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={manyModels}
          enableSearch
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "CLAUDE");

      // Should find Claude models despite uppercase search (in dropdown)
      expect(within(dropdown).getByText("Claude Opus 4.5")).toBeInTheDocument();
    });
  });

  // Issue 5: Vendor field display tests for Google vs Vertex AI distinction
  describe("Vendor Display", () => {
    const modelsWithVendor: ModelOption[] = [
      {
        id: "gemini-2.5-flash",
        name: "Gemini 2.5 Flash",
        provider: "google",
        vendor: "vertex_ai", // Vertex AI, not native Google
      },
      {
        id: "claude-opus-vertex",
        name: "Claude Opus (Vertex)",
        provider: "anthropic",
        vendor: "vertex_ai_anthropic", // Anthropic via Vertex AI
      },
      {
        id: "gpt-4o-azure",
        name: "GPT-4o (Azure)",
        provider: "openai",
        vendor: "azure", // OpenAI via Azure
      },
      {
        id: "claude-opus-native",
        name: "Claude Opus (Native)",
        provider: "anthropic",
        // No vendor = native API
      },
    ];

    it("shows 'Google (Vertex AI)' for Vertex AI Google models", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={modelsWithVendor}
          selectedModel="gemini-2.5-flash"
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(within(dropdown).getByText("Google (Vertex AI)")).toBeInTheDocument();
    });

    it("shows 'Anthropic (Vertex AI)' for Anthropic via Vertex AI", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={modelsWithVendor}
          selectedModel="claude-opus-vertex"
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(within(dropdown).getByText("Anthropic (Vertex AI)")).toBeInTheDocument();
    });

    it("shows 'OpenAI (Azure)' for Azure OpenAI models", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={modelsWithVendor}
          selectedModel="gpt-4o-azure"
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(within(dropdown).getByText("OpenAI (Azure)")).toBeInTheDocument();
    });

    it("shows capitalized provider name when no vendor is specified", async () => {
      const user = userEvent.setup();
      render(
        <HeaderModelSelector
          {...defaultProps}
          availableModels={modelsWithVendor}
          selectedModel="claude-opus-native"
        />
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      // Should show "Anthropic" (capitalized) without vendor suffix
      expect(within(dropdown).getByText("Anthropic")).toBeInTheDocument();
    });
  });
});

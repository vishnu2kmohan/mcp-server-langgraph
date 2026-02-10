/**
 * HeaderModelSelector Feature Tests
 *
 * Covers: Keyboard Navigation, Accessibility, Compact Mode,
 * Native Tools Section, Model Search
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  mockModels,
  defaultProps,
  defaultNativeCapabilitiesMock,
} from "./HeaderModelSelector.fixtures";
import { TestProvider } from "@/test-utils";

// Mock BEFORE component import
vi.mock("@/hooks", () => ({
  useNativeCapabilities: vi.fn(),
}));

import { HeaderModelSelector, type ModelOption } from "../HeaderModelSelector";
import { useNativeCapabilities } from "@/hooks";
const mockUseNativeCapabilities = useNativeCapabilities as ReturnType<
  typeof vi.fn
>;

// =============================================================================
// Tests
// =============================================================================

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("HeaderModelSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Default mock: no native tools available
    mockUseNativeCapabilities.mockReturnValue(defaultNativeCapabilitiesMock);
  });

  describe("Keyboard Navigation", () => {
    it("supports arrow key navigation in model list", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

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
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            onModelChange={onModelChange}
          />
        </TestProvider>,
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      // The dropdown contains a dialog (settings + model list), not just a listbox
      expect(pill).toHaveAttribute("aria-haspopup", "dialog");
      expect(pill).toHaveAttribute("aria-expanded", "false");
    });

    it("sets aria-expanded when dropdown opens", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      await user.click(pill);

      expect(pill).toHaveAttribute("aria-expanded", "true");
    });

    it("has accessible label", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveAttribute(
        "aria-label",
        expect.stringContaining("Claude Opus 4.5"),
      );
    });

    it("dropdown has proper role", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const dropdown = screen.getByTestId("model-dropdown");
      // Container is a dialog (contains thinking level section, search, etc.)
      expect(dropdown).toHaveAttribute("role", "dialog");
      // Models are inside a nested listbox
      expect(dropdown.querySelector('[role="listbox"]')).toBeInTheDocument();
    });

    it("model options have proper role", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const options = screen.getAllByRole("option");
      expect(options.length).toBe(mockModels.length);
    });
  });

  describe("Compact Mode", () => {
    it("renders compact version when compact prop is true", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} compact />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveClass("compact");
    });

    it("shows abbreviated model name in compact mode", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} compact />
        </TestProvider>,
      );

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
          {
            toolName: "web_search",
            supported: true,
            providerType: "web_search_20250305",
            enabled: true,
          },
          {
            toolName: "code_execution",
            supported: true,
            providerType: "code_execution_20250825",
            enabled: true,
          },
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
        isToolAvailable: (name: string) =>
          name === "web_search" || name === "code_execution",
        getCapability: () => undefined,
      });

      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(
        screen.queryByTestId("native-tools-section"),
      ).not.toBeInTheDocument();
    });

    it("hides native tools section when master switch is disabled", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "web_search_20250305",
            enabled: true,
          },
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      // Should not show because masterEnabled is false
      expect(
        screen.queryByTestId("native-tools-section"),
      ).not.toBeInTheDocument();
    });

    it("shows web search badge when web search is available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "web_search_20250305",
            enabled: true,
          },
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(screen.getByText("Web Search")).toBeInTheDocument();
    });

    it("shows code execution badge when code execution is available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "code_execution",
            supported: true,
            providerType: "code_execution_20250825",
            enabled: true,
          },
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(
        screen.getByTestId("native-code-execution-badge"),
      ).toBeInTheDocument();
      expect(screen.getByText("Code Execution")).toBeInTheDocument();
    });

    it("shows both badges when both capabilities are available", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "web_search_20250305",
            enabled: true,
          },
          {
            toolName: "code_execution",
            supported: true,
            providerType: "code_execution_20250825",
            enabled: true,
          },
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(
        screen.getByTestId("native-code-execution-badge"),
      ).toBeInTheDocument();
    });

    it("shows provider name in native tools section", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "web_search_20250305",
            enabled: true,
          },
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      // Should show provider name in the native tools section
      const nativeSection = screen.getByTestId("native-tools-section");
      expect(within(nativeSection).getByText(/anthropic/i)).toBeInTheDocument();
    });

    it("shows Google provider for Gemini models", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "googleSearch",
            enabled: true,
          },
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
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            selectedModel="gemini-2.5-pro"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const nativeSection = screen.getByTestId("native-tools-section");
      expect(nativeSection).toBeInTheDocument();
      expect(within(nativeSection).getByText(/google/i)).toBeInTheDocument();
    });

    it("does not show code execution badge for Google models", async () => {
      mockUseNativeCapabilities.mockReturnValue({
        capabilities: [
          {
            toolName: "web_search",
            supported: true,
            providerType: "googleSearch",
            enabled: true,
          },
          {
            toolName: "code_execution",
            supported: false,
            providerType: null,
            enabled: false,
          },
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
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            selectedModel="gemini-2.5-pro"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("native-web-search-badge")).toBeInTheDocument();
      expect(
        screen.queryByTestId("native-code-execution-badge"),
      ).not.toBeInTheDocument();
    });
  });

  // Issue 4: Model Selector Search functionality tests
  describe("Model Search", () => {
    const manyModels: ModelOption[] = [
      {
        id: "claude-opus-4.5",
        name: "Claude Opus 4.5",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "claude-sonnet-4",
        name: "Claude Sonnet 4",
        provider: "anthropic",
        supportsThinking: true,
      },
      {
        id: "claude-haiku-3.5",
        name: "Claude Haiku 3.5",
        provider: "anthropic",
        supportsThinking: false,
      },
      {
        id: "gpt-4o",
        name: "GPT-4o",
        provider: "openai",
        supportsThinking: false,
      },
      {
        id: "gpt-4o-mini",
        name: "GPT-4o Mini",
        provider: "openai",
        supportsThinking: false,
      },
      {
        id: "gemini-2.5-pro",
        name: "Gemini 2.5 Pro",
        provider: "google",
        supportsThinking: true,
      },
      {
        id: "gemini-2.5-flash",
        name: "Gemini 2.5 Flash",
        provider: "google",
        supportsThinking: true,
      },
    ];

    it("shows search input when enableSearch prop is true and many models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("model-search-input")).toBeInTheDocument();
      expect(screen.getByPlaceholderText(/search models/i)).toBeInTheDocument();
    });

    it("filters models based on search query", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "claude");

      // Should only show Claude models in dropdown
      expect(within(dropdown).getByText("Claude Opus 4.5")).toBeInTheDocument();
      expect(within(dropdown).getByText("Claude Sonnet 4")).toBeInTheDocument();
      expect(
        within(dropdown).getByText("Claude Haiku 3.5"),
      ).toBeInTheDocument();

      // Should not show other models in dropdown
      expect(within(dropdown).queryByText("GPT-4o")).not.toBeInTheDocument();
      expect(
        within(dropdown).queryByText("Gemini 2.5 Pro"),
      ).not.toBeInTheDocument();
    });

    it("filters by provider name", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "google");

      // Should show Google models in dropdown
      expect(within(dropdown).getByText("Gemini 2.5 Pro")).toBeInTheDocument();
      expect(
        within(dropdown).getByText("Gemini 2.5 Flash"),
      ).toBeInTheDocument();

      // Should not show other models in dropdown
      expect(
        within(dropdown).queryByText("Claude Opus 4.5"),
      ).not.toBeInTheDocument();
      expect(within(dropdown).queryByText("GPT-4o")).not.toBeInTheDocument();
    });

    it("shows no results message when search has no matches", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.type(screen.getByTestId("model-search-input"), "xyz123");

      expect(screen.getByText(/no models found/i)).toBeInTheDocument();
    });

    it("clears search on dropdown close", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
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
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch={false}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(
        screen.queryByTestId("model-search-input"),
      ).not.toBeInTheDocument();
    });

    it("is case-insensitive", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={manyModels}
            enableSearch
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");
      await user.type(screen.getByTestId("model-search-input"), "CLAUDE");

      // Should find Claude models despite uppercase search (in dropdown)
      expect(within(dropdown).getByText("Claude Opus 4.5")).toBeInTheDocument();
    });
  });
});

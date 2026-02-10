/**
 * HeaderModelSelector Core Tests
 *
 * Covers: Rendering, Dropdown Behavior, Model Selection,
 * Thinking Level Selection, Status Badges, Vendor Display
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
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

  describe("Rendering", () => {
    it("renders the combined selector pill", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toBeInTheDocument();
    });

    it("displays model name and thinking level in pill", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      // Should show combined format: "Claude Opus 4.5 (Medium)"
      expect(screen.getByText(/Claude Opus 4.5/)).toBeInTheDocument();
      expect(screen.getByText(/Medium/i)).toBeInTheDocument();
    });

    it("hides thinking level for models that don't support it", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} selectedModel="gpt-4o" />
        </TestProvider>,
      );

      // Should show only model name, no thinking level
      expect(screen.getByText(/GPT-4o/)).toBeInTheDocument();
      expect(screen.queryByText(/Medium/i)).not.toBeInTheDocument();
    });

    it("shows loading state when models are loading", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("model-loading-spinner")).toBeInTheDocument();
    });

    it("can be disabled", () => {
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} disabled />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      expect(pill).toHaveAttribute("disabled");
    });
  });

  describe("Dropdown Behavior", () => {
    it("opens dropdown on click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      const pill = screen.getByTestId("header-model-selector");
      await user.click(pill);

      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();
    });

    it("closes dropdown on outside click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <div>
            <HeaderModelSelector {...defaultProps} />
            <button data-testid="outside-button">Outside</button>
          </div>
        </TestProvider>,
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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

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
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      mockModels.forEach((model) => {
        expect(within(dropdown).getByText(model.name)).toBeInTheDocument();
      });
    });

    it("shows checkmark next to selected model", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      // Find the selected model option
      const selectedOption = screen.getByRole("option", {
        name: /Claude Opus 4.5/,
      });
      expect(
        within(selectedOption).getByTestId("model-selected-check"),
      ).toBeInTheDocument();
    });

    it("calls onModelChange when a model is selected", async () => {
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
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      expect(onModelChange).toHaveBeenCalledWith("gpt-4o");
    });

    it("closes dropdown after model selection", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("option", { name: /GPT-4o/ }));

      await waitFor(() => {
        expect(screen.queryByTestId("model-dropdown")).not.toBeInTheDocument();
      });
    });

    it("shows thinking badge for models that support thinking", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      // Models with thinking support should have a brain icon
      const opusOption = screen.getByRole("option", {
        name: /Claude Opus 4.5/,
      });
      expect(
        within(opusOption).getByTestId("thinking-badge"),
      ).toBeInTheDocument();

      // GPT-4o doesn't support thinking
      const gptOption = screen.getByRole("option", { name: /GPT-4o/ });
      expect(
        within(gptOption).queryByTestId("thinking-badge"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Thinking Level Selection", () => {
    it("shows thinking level section in dropdown for thinking-capable models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByTestId("thinking-level-section")).toBeInTheDocument();
    });

    it("hides thinking level section for non-thinking models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} selectedModel="gpt-4o" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(
        screen.queryByTestId("thinking-level-section"),
      ).not.toBeInTheDocument();
    });

    it("displays all thinking levels (Low, Medium, High)", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      expect(screen.getByRole("radio", { name: /Low/i })).toBeInTheDocument();
      expect(
        screen.getByRole("radio", { name: /Medium/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("radio", { name: /High/i })).toBeInTheDocument();
    });

    it("highlights current thinking level", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} thinkingLevel="high" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const highRadio = screen.getByRole("radio", { name: /High/i });
      expect(highRadio).toBeChecked();
    });

    it("calls onThinkingLevelChange when level is changed", async () => {
      const user = userEvent.setup();
      const onThinkingLevelChange = vi.fn();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            onThinkingLevelChange={onThinkingLevelChange}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("radio", { name: /High/i }));

      expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
    });

    it("keeps dropdown open after changing thinking level", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      await user.click(screen.getByRole("radio", { name: /High/i }));

      // Dropdown should remain open for further adjustments
      expect(screen.getByTestId("model-dropdown")).toBeInTheDocument();
    });
  });

  describe("Status Badges", () => {
    it("shows preview badge for preview models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));

      const geminiOption = screen.getByRole("option", {
        name: /Gemini 2.5 Pro/,
      });
      expect(within(geminiOption).getByText("Preview")).toBeInTheDocument();
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
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={modelsWithVendor}
            selectedModel="gemini-2.5-flash"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(
        within(dropdown).getByText("Google (Vertex AI)"),
      ).toBeInTheDocument();
    });

    it("shows 'Anthropic (Vertex AI)' for Anthropic via Vertex AI", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={modelsWithVendor}
            selectedModel="claude-opus-vertex"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(
        within(dropdown).getByText("Anthropic (Vertex AI)"),
      ).toBeInTheDocument();
    });

    it("shows 'OpenAI (Azure)' for Azure OpenAI models", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={modelsWithVendor}
            selectedModel="gpt-4o-azure"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      expect(within(dropdown).getByText("OpenAI (Azure)")).toBeInTheDocument();
    });

    it("shows capitalized provider name when no vendor is specified", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <HeaderModelSelector
            {...defaultProps}
            availableModels={modelsWithVendor}
            selectedModel="claude-opus-native"
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("header-model-selector"));
      const dropdown = screen.getByTestId("model-dropdown");

      // Should show "Anthropic" (capitalized) without vendor suffix
      expect(within(dropdown).getByText("Anthropic")).toBeInTheDocument();
    });
  });
});

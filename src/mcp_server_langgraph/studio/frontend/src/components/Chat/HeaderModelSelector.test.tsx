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
});

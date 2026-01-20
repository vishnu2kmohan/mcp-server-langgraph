/**
 * PreferencesMenu Tests
 *
 * Tests for the consolidated preferences menu component that provides
 * access to model, tools, and KB focus settings in a single dropdown.
 *
 * TDD: Write tests FIRST, then implementation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { PreferencesMenu } from "./PreferencesMenu";
import type { ReasoningEffortLevel } from "./ReasoningEffortSelector";
import type { KBFocusMode } from "./KnowledgeBaseFocus";
import type { ToolSelectionMode } from "@/types/tools";

// Mock lucide-react to avoid SVG rendering issues
vi.mock("lucide-react", async () => {
  const actual = await vi.importActual("lucide-react");
  return {
    ...actual,
    Settings2: () => <span data-testid="icon-settings" />,
    ChevronDown: () => <span data-testid="icon-chevron" />,
    Check: () => <span data-testid="icon-check" />,
    Brain: () => <span data-testid="icon-brain" />,
    Wrench: () => <span data-testid="icon-wrench" />,
    Database: () => <span data-testid="icon-database" />,
    Cpu: () => <span data-testid="icon-cpu" />,
  };
});

describe("PreferencesMenu", () => {
  const defaultProps = {
    // Model settings
    selectedModel: "claude-sonnet-4",
    onModelChange: vi.fn(),
    thinkingLevel: "medium" as ReasoningEffortLevel,
    onThinkingLevelChange: vi.fn(),
    // Tool settings
    toolMode: "auto" as ToolSelectionMode,
    onToolModeChange: vi.fn(),
    selectedTools: [] as string[],
    onToolsChange: vi.fn(),
    // KB Focus settings
    kbFocusMode: "all" as KBFocusMode,
    onKBFocusChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the preferences button", () => {
      render(<PreferencesMenu {...defaultProps} />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeInTheDocument();
    });

    it("renders with settings icon", () => {
      render(<PreferencesMenu {...defaultProps} />);

      expect(screen.getByTestId("icon-settings")).toBeInTheDocument();
    });

    it("applies custom className when provided", () => {
      render(<PreferencesMenu {...defaultProps} className="custom-class" />);

      const container = screen.getByTestId("preferences-menu");
      expect(container).toHaveClass("custom-class");
    });

    it("is disabled when disabled prop is true", () => {
      render(<PreferencesMenu {...defaultProps} disabled />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeDisabled();
    });
  });

  describe("Menu Interaction", () => {
    it("opens dropdown when button is clicked", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} />);

      const button = screen.getByTestId("preferences-menu-trigger");
      await user.click(button);

      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("closes dropdown when clicking outside", async () => {
      const user = userEvent.setup();
      render(
        <div>
          <PreferencesMenu {...defaultProps} />
          <button data-testid="outside">Outside</button>
        </div>
      );

      // Open menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();

      // Click outside
      await user.click(screen.getByTestId("outside"));
      expect(screen.queryByTestId("preferences-dropdown")).not.toBeInTheDocument();
    });

    it("closes dropdown when Escape is pressed", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} />);

      // Open menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();

      // Press Escape
      await user.keyboard("{Escape}");
      expect(screen.queryByTestId("preferences-dropdown")).not.toBeInTheDocument();
    });
  });

  describe("Model Section", () => {
    it("displays current model in dropdown", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} selectedModel="claude-opus-4-5" />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(within(dropdown).getByText(/Thinking Level/i)).toBeInTheDocument();
    });

    it("displays current thinking level", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} thinkingLevel="high" />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(within(dropdown).getByText(/Thinking/i)).toBeInTheDocument();
    });

    it("calls onThinkingLevelChange when thinking level is changed", async () => {
      const user = userEvent.setup();
      const onThinkingLevelChange = vi.fn();
      render(
        <PreferencesMenu {...defaultProps} onThinkingLevelChange={onThinkingLevelChange} />
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Find and click a thinking level option
      const highOption = screen.getByRole("option", { name: /high/i });
      await user.click(highOption);

      expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
    });
  });

  describe("Tools Section", () => {
    it("displays current tool mode", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} toolMode="manual" />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(within(dropdown).getByText(/Tools/i)).toBeInTheDocument();
    });

    it("calls onToolModeChange when tool mode is changed", async () => {
      const user = userEvent.setup();
      const onToolModeChange = vi.fn();
      render(<PreferencesMenu {...defaultProps} onToolModeChange={onToolModeChange} />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Find and click a tool mode option
      const manualOption = screen.getByRole("option", { name: /manual/i });
      await user.click(manualOption);

      expect(onToolModeChange).toHaveBeenCalledWith("manual");
    });
  });

  describe("KB Focus Section", () => {
    it("displays current KB focus mode", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} kbFocusMode="kb_only" />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(within(dropdown).getByText(/Knowledge Base/i)).toBeInTheDocument();
    });

    it("calls onKBFocusChange when KB focus mode is changed", async () => {
      const user = userEvent.setup();
      const onKBFocusChange = vi.fn();
      render(<PreferencesMenu {...defaultProps} onKBFocusChange={onKBFocusChange} />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Find and click a KB focus option
      const kbOnlyOption = screen.getByRole("option", { name: /kb only/i });
      await user.click(kbOnlyOption);

      expect(onKBFocusChange).toHaveBeenCalledWith("kb_only");
    });
  });

  describe("Accessibility", () => {
    it("has correct aria-label", () => {
      render(<PreferencesMenu {...defaultProps} />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveAttribute("aria-label", "Open preferences menu");
    });

    it("has aria-expanded reflecting menu state", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveAttribute("aria-expanded", "false");

      await user.click(button);
      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("dropdown has role='menu'", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} />);

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(dropdown).toHaveAttribute("role", "menu");
    });

    it("is keyboard navigable", async () => {
      const user = userEvent.setup();
      render(<PreferencesMenu {...defaultProps} />);

      // Tab to button and open with Enter
      await user.tab();
      await user.keyboard("{Enter}");

      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("meets WCAG 2.5.8 touch target size", () => {
      render(<PreferencesMenu {...defaultProps} />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveClass("min-h-8"); // 32px = 8 * 4px
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when compact prop is true", () => {
      render(<PreferencesMenu {...defaultProps} compact />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveClass("px-2");
    });

    it("hides label text in compact mode", () => {
      render(<PreferencesMenu {...defaultProps} compact />);

      // In compact mode, no "Preferences" text should be visible
      expect(screen.queryByText("Preferences")).not.toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("shows loading indicator when isLoading is true", () => {
      render(<PreferencesMenu {...defaultProps} isLoading />);

      expect(screen.getByTestId("preferences-loading")).toBeInTheDocument();
    });

    it("disables button when loading", () => {
      render(<PreferencesMenu {...defaultProps} isLoading />);

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeDisabled();
    });
  });
});

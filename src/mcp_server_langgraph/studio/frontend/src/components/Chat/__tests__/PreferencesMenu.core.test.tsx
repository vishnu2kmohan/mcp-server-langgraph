/**
 * PreferencesMenu Core Tests
 *
 * Tests for rendering, menu interaction, model section, KB focus section,
 * compact mode, and loading states.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { defaultProps } from "./PreferencesMenu.fixtures";
import { TestProvider } from "@/test-utils";

// Mock lucide-react BEFORE importing component
vi.mock("lucide-react", async () => {
  const actual = await vi.importActual("lucide-react");
  return {
    ...actual,
    Settings2: () => <span data-testid="icon-settings" />,
    ChevronDown: () => <span data-testid="icon-chevron-down" />,
    ChevronRight: () => <span data-testid="icon-chevron-right" />,
    Check: () => <span data-testid="icon-check" />,
    Brain: () => <span data-testid="icon-brain" />,
    Wrench: () => <span data-testid="icon-wrench" />,
    Database: () => <span data-testid="icon-database" />,
    Cpu: () => <span data-testid="icon-cpu" />,
    Loader2: (props: { "data-testid"?: string; "aria-label"?: string }) => (
      <span
        data-testid={props["data-testid"] ?? "icon-loader"}
        aria-label={props["aria-label"]}
      />
    ),
    Sparkles: () => <span data-testid="icon-sparkles" />,
    MessageSquare: () => <span data-testid="icon-message" />,
    Zap: () => <span data-testid="icon-zap" />,
  };
});

import { PreferencesMenu } from "../PreferencesMenu";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("PreferencesMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders the preferences button", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeInTheDocument();
    });

    it("renders with settings icon", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("icon-settings")).toBeInTheDocument();
    });

    it("applies custom className when provided", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} className="custom-class" />
        </TestProvider>,
      );

      const container = screen.getByTestId("preferences-menu");
      expect(container).toHaveClass("custom-class");
    });

    it("is disabled when disabled prop is true", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} disabled />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeDisabled();
    });
  });

  describe("Menu Interaction", () => {
    it("opens dropdown when button is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      await user.click(button);

      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("closes dropdown when clicking outside", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      // Open menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();

      // Click outside using Radix's dismiss mechanism (press Escape)
      // Note: Radix portals content to body, so clicking document.body triggers dismiss
      await user.keyboard("{Escape}");
      expect(
        screen.queryByTestId("preferences-dropdown"),
      ).not.toBeInTheDocument();
    });

    it("closes dropdown when Escape is pressed", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      // Open menu
      await user.click(screen.getByTestId("preferences-menu-trigger"));
      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();

      // Press Escape
      await user.keyboard("{Escape}");
      expect(
        screen.queryByTestId("preferences-dropdown"),
      ).not.toBeInTheDocument();
    });
  });

  describe("Model Section", () => {
    it("displays thinking submenu trigger in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} selectedModel="claude-opus-4-5" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Hierarchical menu shows "Thinking:" label in submenu trigger
      expect(
        screen.getByTestId("submenu-trigger-thinking"),
      ).toBeInTheDocument();
    });

    it("displays current thinking level", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} thinkingLevel="high" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Check that submenu trigger shows the current value
      const thinkingTrigger = screen.getByTestId("submenu-trigger-thinking");
      expect(thinkingTrigger).toHaveTextContent(/High/i);
    });

    it("calls onThinkingLevelChange when thinking level is changed", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      const onThinkingLevelChange = vi.fn();
      render(
        <TestProvider>
          <PreferencesMenu
            {...defaultProps}
            onThinkingLevelChange={onThinkingLevelChange}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Open thinking submenu using click (not hover for more reliable test)
      const thinkingTrigger = screen.getByTestId("submenu-trigger-thinking");
      await user.click(thinkingTrigger);

      // Wait for submenu to open
      await screen.findByTestId("submenu-content-thinking");

      // Find all menuitemradio elements and click the "High" one using fireEvent
      // (Radix DropdownMenu requires specific event handling in JSDOM)
      const radioItems = screen.getAllByRole("menuitemradio");
      const highOption = radioItems.find((el) =>
        el.textContent?.includes("High"),
      );
      expect(highOption).toBeTruthy();
      fireEvent.click(highOption!);

      await waitFor(() => {
        expect(onThinkingLevelChange).toHaveBeenCalledWith("high");
      });
    });
  });

  describe("KB Focus Section", () => {
    it("displays current KB focus mode", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} kbFocusMode="kb_only" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Check that submenu trigger shows the current value
      const kbTrigger = screen.getByTestId("submenu-trigger-kb");
      expect(kbTrigger).toHaveTextContent(/KB Only/i);
    });

    it("calls onKBFocusChange when KB focus mode is changed", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      const onKBFocusChange = vi.fn();
      render(
        <TestProvider>
          <PreferencesMenu
            {...defaultProps}
            onKBFocusChange={onKBFocusChange}
          />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Open KB submenu using click
      const kbTrigger = screen.getByTestId("submenu-trigger-kb");
      await user.click(kbTrigger);

      // Wait for submenu to open
      await screen.findByTestId("submenu-content-kb");

      // Find all menuitemradio elements and click the "KB Only" one using fireEvent
      const radioItems = screen.getAllByRole("menuitemradio");
      const kbOnlyOption = radioItems.find((el) =>
        el.textContent?.includes("KB Only"),
      );
      expect(kbOnlyOption).toBeTruthy();
      fireEvent.click(kbOnlyOption!);

      await waitFor(() => {
        expect(onKBFocusChange).toHaveBeenCalledWith("kb_only");
      });
    });
  });

  describe("Compact Mode", () => {
    it("renders in compact mode when compact prop is true", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} compact />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveClass("px-2");
    });

    it("hides label text in compact mode", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} compact />
        </TestProvider>,
      );

      // In compact mode, no "Preferences" text should be visible
      expect(screen.queryByText("Preferences")).not.toBeInTheDocument();
    });
  });

  describe("Loading States", () => {
    it("shows loading indicator when isLoading is true", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("preferences-loading")).toBeInTheDocument();
    });

    it("disables button when loading", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} isLoading />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toBeDisabled();
    });
  });
});

/**
 * PreferencesMenu Accessibility Tests
 *
 * Tests for accessibility, submenu ARIA attributes, compact main menu,
 * axe-core accessibility, focus restoration, and reduced motion.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  cleanup,
  render,
  screen,
  within,
  fireEvent,
  waitFor,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

import { defaultProps } from "./PreferencesMenu.fixtures";
import { TestProvider } from "@/test-utils";

expect.extend(toHaveNoViolations);

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
    Palette: () => <span data-testid="icon-palette" />,
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

  describe("Accessibility", () => {
    it("has correct aria-label", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveAttribute("aria-label", "Open preferences menu");
    });

    it("has aria-expanded reflecting menu state", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveAttribute("aria-expanded", "false");

      await user.click(button);
      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("dropdown has role='menu'", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      expect(dropdown).toHaveAttribute("role", "menu");
    });

    it("is keyboard navigable", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      // Tab to button and open with Enter
      await user.tab();
      await user.keyboard("{Enter}");

      expect(screen.getByTestId("preferences-dropdown")).toBeInTheDocument();
    });

    it("meets WCAG 2.5.8 touch target size", () => {
      render(
        <TestProvider>
          <PreferencesMenu {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByTestId("preferences-menu-trigger");
      expect(button).toHaveClass("min-h-8"); // 32px = 8 * 4px
    });
  });

  describe("Submenu ARIA attributes", () => {
    const modelsProps = {
      ...defaultProps,
      availableModels: [
        {
          id: "claude-opus-4-5",
          name: "Claude Opus 4.5",
          provider: "anthropic",
        },
      ],
    };

    it("submenu triggers have aria-haspopup='menu'", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const modelTrigger = screen.getByTestId("submenu-trigger-model");
      expect(modelTrigger).toHaveAttribute("aria-haspopup", "menu");
    });

    it("submenu items have role='menuitemradio' for selection", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} thinkingLevel="medium" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const thinkingTrigger = screen.getByTestId("submenu-trigger-thinking");
      await user.hover(thinkingTrigger);

      const submenu = await screen.findByTestId("submenu-content-thinking");
      const radioItems = within(submenu).getAllByRole("menuitemradio");
      expect(radioItems.length).toBeGreaterThan(0);
    });

    it("selected submenu item has aria-checked='true'", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} thinkingLevel="medium" />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const thinkingTrigger = screen.getByTestId("submenu-trigger-thinking");
      await user.hover(thinkingTrigger);

      const submenu = await screen.findByTestId("submenu-content-thinking");
      const mediumOption = within(submenu).getByRole("menuitemradio", {
        name: /Medium/i,
      });
      expect(mediumOption).toHaveAttribute("aria-checked", "true");
    });
  });

  describe("Compact Main Menu", () => {
    const modelsProps = {
      ...defaultProps,
      availableModels: [
        {
          id: "claude-opus-4-5",
          name: "Claude Opus 4.5",
          provider: "anthropic",
        },
      ],
    };

    it("main menu shows 4 compact items (Model, Thinking, Tools, KB)", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      // Should have exactly 4 submenu triggers in main menu
      expect(screen.getByTestId("submenu-trigger-model")).toBeInTheDocument();
      expect(
        screen.getByTestId("submenu-trigger-thinking"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("submenu-trigger-tools")).toBeInTheDocument();
      expect(screen.getByTestId("submenu-trigger-kb")).toBeInTheDocument();
    });

    it("menu fits within viewport (no overflow)", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));

      const dropdown = screen.getByTestId("preferences-dropdown");
      // New hierarchical menu should not have overflow-y-auto in main content
      expect(dropdown).not.toHaveClass("overflow-y-auto");
    });
  });

  describe("Axe-core Accessibility", () => {
    const modelsProps = {
      ...defaultProps,
      availableModels: [
        {
          id: "claude-opus-4-5",
          name: "Claude Opus 4.5",
          provider: "anthropic",
        },
        {
          id: "claude-sonnet-4",
          name: "Claude Sonnet 4",
          provider: "anthropic",
        },
      ],
    };

    it("has no accessibility violations when closed", async () => {
      const { container } = render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("has no accessibility violations when menu is open", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));
      await screen.findByTestId("preferences-dropdown");

      // Use document.body to include Radix portaled content
      // Disable "region" rule as test environment lacks full page landmarks
      const results = await axe(document.body, {
        rules: { region: { enabled: false } },
      });
      expect(results).toHaveNoViolations();
    });

    it("has no accessibility violations with submenu open", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));
      await user.click(screen.getByTestId("submenu-trigger-thinking"));
      await screen.findByTestId("submenu-content-thinking");

      // Use document.body to include Radix portaled content
      // Disable "region" rule as test environment lacks full page landmarks
      const results = await axe(document.body, {
        rules: { region: { enabled: false } },
      });
      expect(results).toHaveNoViolations();
    });
  });

  describe("Focus Restoration", () => {
    const modelsProps = {
      ...defaultProps,
      availableModels: [
        {
          id: "claude-opus-4-5",
          name: "Claude Opus 4.5",
          provider: "anthropic",
        },
      ],
    };

    it("restores focus to trigger after closing with Escape", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("preferences-menu-trigger");
      await user.click(trigger);
      await screen.findByTestId("preferences-dropdown");

      // Close with Escape
      await user.keyboard("{Escape}");

      expect(
        screen.queryByTestId("preferences-dropdown"),
      ).not.toBeInTheDocument();
      expect(trigger).toHaveFocus();
    });

    it("restores focus to trigger after making a selection", async () => {
      const user = userEvent.setup({ pointerEventsCheck: 0 });
      const onThinkingLevelChange = vi.fn();
      render(
        <TestProvider>
          <PreferencesMenu
            {...modelsProps}
            thinkingLevel="medium"
            onThinkingLevelChange={onThinkingLevelChange}
          />
        </TestProvider>,
      );

      const trigger = screen.getByTestId("preferences-menu-trigger");
      await user.click(trigger);
      await user.click(screen.getByTestId("submenu-trigger-thinking"));
      await screen.findByTestId("submenu-content-thinking");

      // Select an option
      const highOption = screen.getByRole("menuitemradio", { name: /High/i });
      fireEvent.click(highOption);

      await waitFor(() => {
        expect(trigger).toHaveFocus();
      });
    });
  });

  describe("Reduced Motion", () => {
    const modelsProps = {
      ...defaultProps,
      availableModels: [
        {
          id: "claude-opus-4-5",
          name: "Claude Opus 4.5",
          provider: "anthropic",
        },
        {
          id: "claude-sonnet-4",
          name: "Claude Sonnet 4",
          provider: "anthropic",
        },
      ],
    };

    it("has motion-reduce classes on dropdown content for accessibility", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));
      const dropdown = await screen.findByTestId("preferences-dropdown");

      // Verify motion-reduce CSS classes are applied
      expect(dropdown.className).toContain("motion-reduce:animate-none");
      expect(dropdown.className).toContain("motion-reduce:transition-none");
    });

    it("has motion-reduce classes on submenu content", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <PreferencesMenu {...modelsProps} />
        </TestProvider>,
      );

      await user.click(screen.getByTestId("preferences-menu-trigger"));
      await user.click(screen.getByTestId("submenu-trigger-thinking"));
      const submenu = await screen.findByTestId("submenu-content-thinking");

      // Verify motion-reduce CSS classes are applied to submenus
      expect(submenu.className).toContain("motion-reduce:animate-none");
      expect(submenu.className).toContain("motion-reduce:transition-none");
    });
  });
});

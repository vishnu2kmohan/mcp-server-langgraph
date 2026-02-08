/**
 * ToolSelector Component Tests
 *
 * TDD: These tests are written FIRST to define the expected behavior
 * of the ToolSelector component for manual tool selection.
 *
 * Tests verify:
 * 1. Renders pill button showing current mode/selection
 * 2. Opens dropdown on click
 * 3. Shows mode toggle (Auto/Manual/None)
 * 4. Shows search input for filtering tools
 * 5. Shows grouped tool list (built-in, MCP by server)
 * 6. Allows multi-select of tools
 * 7. Keyboard navigation support
 * 8. Accessibility (ARIA listbox pattern)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToolSelector } from "./ToolSelector";
import type { ToolSelectionMode } from "@/types/tools";

import { TestProvider } from "@/test-utils";

describe("ToolSelector", () => {
  const defaultProps = {
    selectedTools: [] as string[],
    onSelectionChange: vi.fn(),
    mode: "auto" as ToolSelectionMode,
    onModeChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Pill Button Display Tests
  // ===========================================================================

  describe("pill button display", () => {
    it("should render 'Auto' when mode is auto", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} mode="auto" />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toHaveTextContent(/auto/i);
    });

    it("should render tool count when mode is manual with selections", () => {
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            selectedTools={["calculator", "web_search"]}
          />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toHaveTextContent(/2/);
    });

    it("should render 'None' when mode is none", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} mode="none" />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toHaveTextContent(/none/i);
    });

    it("should be disabled when disabled prop is true", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} disabled />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toBeDisabled();
    });
  });

  // ===========================================================================
  // Dropdown Toggle Tests
  // ===========================================================================

  describe("dropdown toggle", () => {
    it("should open dropdown on click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      await user.click(button);

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should close dropdown on second click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      await user.click(button);
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.click(button);
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("should close dropdown on escape key", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      await user.click(button);
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.keyboard("{Escape}");
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });

    it("should close dropdown on outside click", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <div>
            <ToolSelector {...defaultProps} />
            <button data-testid="outside">Outside</button>
          </div>
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      await user.click(button);
      expect(screen.getByRole("listbox")).toBeInTheDocument();

      await user.click(screen.getByTestId("outside"));
      expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Mode Toggle Tests
  // ===========================================================================

  describe("mode toggle", () => {
    it("should show mode options in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      expect(screen.getByRole("option", { name: /auto/i })).toBeInTheDocument();
      expect(
        screen.getByRole("option", { name: /manual/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("option", { name: /none/i })).toBeInTheDocument();
    });

    it("should call onModeChange when mode is changed", async () => {
      const onModeChange = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} onModeChange={onModeChange} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.click(screen.getByRole("option", { name: /manual/i }));

      expect(onModeChange).toHaveBeenCalledWith("manual");
    });

    it("should highlight current mode", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} mode="manual" />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      const manualOption = screen.getByRole("option", { name: /manual/i });
      expect(manualOption).toHaveAttribute("aria-selected", "true");
    });
  });

  // ===========================================================================
  // Tool List Tests
  // ===========================================================================

  describe("tool list", () => {
    const mockTools = [
      {
        toolId: "builtin:calculator",
        name: "calculator",
        displayName: "Calculator",
        source: "builtin" as const,
      },
      {
        toolId: "builtin:web_search",
        name: "web_search",
        displayName: "Web Search",
        source: "builtin" as const,
      },
      {
        toolId: "mcp:github:create_issue",
        name: "github_create_issue",
        displayName: "Create Issue",
        source: "mcp" as const,
        serverName: "github",
      },
    ];

    it("should show tool list when mode is manual", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      expect(screen.getByText("Calculator")).toBeInTheDocument();
      expect(screen.getByText("Web Search")).toBeInTheDocument();
    });

    it("should group tools by source", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      expect(screen.getByText(/built-in/i)).toBeInTheDocument();
      expect(screen.getByText(/github/i)).toBeInTheDocument();
    });

    it("should show checkboxes for tool selection", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      const checkboxes = screen.getAllByRole("checkbox");
      expect(checkboxes.length).toBeGreaterThan(0);
    });

    it("should check selected tools", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            selectedTools={["builtin:calculator"]} // v7: Uses toolId
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      const calculatorCheckbox = screen.getByRole("checkbox", {
        name: /calculator/i,
      });
      expect(calculatorCheckbox).toBeChecked();
    });
  });

  // ===========================================================================
  // Tool Selection Tests
  // ===========================================================================

  describe("tool selection", () => {
    const mockTools = [
      {
        toolId: "builtin:calculator",
        name: "calculator",
        displayName: "Calculator",
        source: "builtin" as const,
      },
      {
        toolId: "builtin:web_search",
        name: "web_search",
        displayName: "Web Search",
        source: "builtin" as const,
      },
    ];

    it("should call onSelectionChange when tool is selected", async () => {
      const onSelectionChange = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            onSelectionChange={onSelectionChange}
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.click(screen.getByRole("checkbox", { name: /calculator/i }));

      // v7: Uses toolId for selection
      expect(onSelectionChange).toHaveBeenCalledWith(["builtin:calculator"]);
    });

    it("should call onSelectionChange when tool is deselected", async () => {
      const onSelectionChange = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            selectedTools={["builtin:calculator"]} // v7: Uses toolId
            onSelectionChange={onSelectionChange}
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.click(screen.getByRole("checkbox", { name: /calculator/i }));

      expect(onSelectionChange).toHaveBeenCalledWith([]);
    });

    it("should support multi-select", async () => {
      const onSelectionChange = vi.fn();
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            selectedTools={["builtin:calculator"]} // v7: Uses toolId
            onSelectionChange={onSelectionChange}
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.click(screen.getByRole("checkbox", { name: /web search/i }));

      // v7: Uses toolIds for selection
      expect(onSelectionChange).toHaveBeenCalledWith([
        "builtin:calculator",
        "builtin:web_search",
      ]);
    });
  });

  // ===========================================================================
  // Search/Filter Tests
  // ===========================================================================

  describe("search filtering", () => {
    const mockTools = [
      {
        toolId: "builtin:calculator",
        name: "calculator",
        displayName: "Calculator",
        source: "builtin" as const,
      },
      {
        toolId: "builtin:web_search",
        name: "web_search",
        displayName: "Web Search",
        source: "builtin" as const,
      },
      {
        toolId: "mcp:github:create_issue",
        name: "github_create_issue",
        displayName: "Create Issue",
        source: "mcp" as const,
        serverName: "github",
      },
    ];

    it("should show search input in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    });

    it("should filter tools by search term", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.type(screen.getByPlaceholderText(/search/i), "calc");

      expect(screen.getByText("Calculator")).toBeInTheDocument();
      expect(screen.queryByText("Web Search")).not.toBeInTheDocument();
    });

    it("should show 'no results' when no tools match search", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector
            {...defaultProps}
            mode="manual"
            availableTools={mockTools}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));
      await user.type(screen.getByPlaceholderText(/search/i), "nonexistent");

      expect(screen.getByText(/no tools found/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("should have proper ARIA attributes on button", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toHaveAttribute("aria-haspopup", "listbox");
      expect(button).toHaveAttribute("aria-expanded", "false");
    });

    it("should update aria-expanded when opened", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      await user.click(button);

      expect(button).toHaveAttribute("aria-expanded", "true");
    });

    it("should have proper role on dropdown", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have proper role on options", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /tools/i }));

      const options = screen.getAllByRole("option");
      expect(options.length).toBeGreaterThan(0);
    });
  });

  // ===========================================================================
  // Loading State Tests
  // ===========================================================================

  describe("loading state", () => {
    it("should show loading indicator when isLoading is true", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("tool-selector-loading")).toBeInTheDocument();
    });

    it("should disable button when loading", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} isLoading />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toBeDisabled();
    });
  });

  // ===========================================================================
  // Compact Mode Tests
  // ===========================================================================

  describe("compact mode", () => {
    it("should render smaller button in compact mode", () => {
      render(
        <TestProvider>
          <ToolSelector {...defaultProps} compact />
        </TestProvider>,
      );

      const button = screen.getByRole("button", { name: /tools/i });
      expect(button).toHaveClass("text-xs");
    });
  });
});

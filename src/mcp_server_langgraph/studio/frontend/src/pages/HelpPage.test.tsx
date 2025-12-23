/**
 * HelpPage Tests
 *
 * Tests for the Help Center page component.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { HelpPage } from "./HelpPage";
import { TestProvider } from "../test-utils";

// Mock the KeyboardShortcuts component
vi.mock("../help/KeyboardShortcuts", () => ({
  KeyboardShortcuts: ({ className }: { className?: string }) => (
    <div data-testid="keyboard-shortcuts" className={className}>
      Keyboard Shortcuts Mock
    </div>
  ),
}));

describe("HelpPage", () => {
  const renderHelpPage = () =>
    render(
      <TestProvider>
        <HelpPage />
      </TestProvider>,
    );

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the help page with title", () => {
      renderHelpPage();

      expect(screen.getByTestId("help-page")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "Help Center" }),
      ).toBeInTheDocument();
    });

    it("should render the help pane with topics", () => {
      renderHelpPage();

      expect(screen.getByTestId("help-pane")).toBeInTheDocument();
    });

    it("should render the keyboard shortcuts section", () => {
      renderHelpPage();

      expect(screen.getByTestId("keyboard-shortcuts")).toBeInTheDocument();
    });

    it("should show placeholder when no topic is selected", () => {
      renderHelpPage();

      expect(
        screen.getByText("Select a topic to see details"),
      ).toBeInTheDocument();
    });
  });

  describe("topic selection", () => {
    it("should display topic details when a topic is clicked", () => {
      renderHelpPage();

      // Click on "Getting Started" topic
      const gettingStartedButton = screen.getByRole("button", {
        name: /Getting Started/i,
      });
      fireEvent.click(gettingStartedButton);

      // Topic detail panel should appear
      expect(screen.getByTestId("help-topic-detail")).toBeInTheDocument();
      expect(
        screen.getByRole("heading", { name: "Getting Started" }),
      ).toBeInTheDocument();
    });

    it("should show topic content after selection", () => {
      renderHelpPage();

      // Click on "Chat Basics" topic
      const chatBasicsButton = screen.getByRole("button", {
        name: /Chat Basics/i,
      });
      fireEvent.click(chatBasicsButton);

      // Content should be displayed in the detail panel
      const detailPanel = screen.getByTestId("help-topic-detail");
      expect(detailPanel).toHaveTextContent(
        /Use the chat panel to communicate/,
      );
    });

    it("should display category badge for selected topic", () => {
      renderHelpPage();

      // Click on "Compliance Overview" topic
      const complianceButton = screen.getByRole("button", {
        name: /Compliance Overview/i,
      });
      fireEvent.click(complianceButton);

      // Category badge should be visible
      expect(screen.getByTestId("help-topic-detail")).toBeInTheDocument();
      // The category is displayed as a badge within the detail panel
      const detailPanel = screen.getByTestId("help-topic-detail");
      expect(detailPanel).toHaveTextContent("compliance");
    });
  });

  describe("help topics", () => {
    it("should include Getting Started topic", () => {
      renderHelpPage();

      expect(
        screen.getByRole("button", { name: /Getting Started/i }),
      ).toBeInTheDocument();
    });

    it("should include Chat Basics topic", () => {
      renderHelpPage();

      expect(
        screen.getByRole("button", { name: /Chat Basics/i }),
      ).toBeInTheDocument();
    });

    it("should include Canvas Workspace topic", () => {
      renderHelpPage();

      expect(
        screen.getByRole("button", { name: /Canvas Workspace/i }),
      ).toBeInTheDocument();
    });

    it("should include Keyboard Shortcuts topic", () => {
      renderHelpPage();

      // Find the button within the help-pane that contains "Keyboard Shortcuts"
      const helpPane = screen.getByTestId("help-pane");
      const buttons = helpPane.querySelectorAll("button");
      const keyboardShortcutsButton = Array.from(buttons).find((btn) =>
        btn.textContent?.includes("Keyboard Shortcuts"),
      );
      expect(keyboardShortcutsButton).toBeInTheDocument();
    });

    it("should include Compliance Overview topic", () => {
      renderHelpPage();

      expect(
        screen.getByRole("button", { name: /Compliance Overview/i }),
      ).toBeInTheDocument();
    });
  });

  describe("keyboard shortcuts categories", () => {
    it("should export DEFAULT_SHORTCUT_CATEGORIES with admin category", async () => {
      // Import the module to check exports
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      // Find admin category
      const adminCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "admin",
      );

      expect(adminCategory).toBeDefined();
      expect(adminCategory?.name).toBe("Admin Dashboard");
    });

    it("should include Shift+A shortcut for Alerts tab in admin category", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const adminCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "admin",
      );

      const alertsShortcut = adminCategory?.shortcuts.find(
        (s) => s.id === "admin-alerts",
      );

      expect(alertsShortcut).toBeDefined();
      expect(alertsShortcut?.keys).toEqual(["Shift", "A"]);
      expect(alertsShortcut?.description).toContain("Alerts");
    });

    it("should include Shift+O shortcut for Overview tab in admin category", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const adminCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "admin",
      );

      const overviewShortcut = adminCategory?.shortcuts.find(
        (s) => s.id === "admin-overview",
      );

      expect(overviewShortcut).toBeDefined();
      expect(overviewShortcut?.keys).toEqual(["Shift", "O"]);
    });

    it("should include Shift+U shortcut for Users tab in admin category", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const adminCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "admin",
      );

      const usersShortcut = adminCategory?.shortcuts.find(
        (s) => s.id === "admin-users",
      );

      expect(usersShortcut).toBeDefined();
      expect(usersShortcut?.keys).toEqual(["Shift", "U"]);
    });
  });

  describe("MCP keyboard shortcuts categories", () => {
    it("should include MCP category with proper name", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      expect(mcpCategory).toBeDefined();
      expect(mcpCategory?.name).toBe("MCP (Model Context Protocol)");
    });

    it("should include Cmd+M shortcut for toggling MCP panel", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      const toggleShortcut = mcpCategory?.shortcuts.find(
        (s) => s.id === "mcp-toggle-panel",
      );

      expect(toggleShortcut).toBeDefined();
      expect(toggleShortcut?.keys).toEqual(["Cmd", "M"]);
      expect(toggleShortcut?.description).toContain("Toggle");
    });

    it("should include Cmd+Shift+T shortcut for tool invocation", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      const toolShortcut = mcpCategory?.shortcuts.find(
        (s) => s.id === "mcp-tool-dialog",
      );

      expect(toolShortcut).toBeDefined();
      expect(toolShortcut?.keys).toEqual(["Cmd", "Shift", "T"]);
      expect(toolShortcut?.description).toContain("tool");
    });

    it("should include Cmd+Shift+R shortcut for resource viewer", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      const resourceShortcut = mcpCategory?.shortcuts.find(
        (s) => s.id === "mcp-resource-viewer",
      );

      expect(resourceShortcut).toBeDefined();
      expect(resourceShortcut?.keys).toEqual(["Cmd", "Shift", "R"]);
      expect(resourceShortcut?.description).toContain("resource");
    });

    it("should include Cmd+Shift+P shortcut for prompt tester", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      const promptShortcut = mcpCategory?.shortcuts.find(
        (s) => s.id === "mcp-prompt-tester",
      );

      expect(promptShortcut).toBeDefined();
      expect(promptShortcut?.keys).toEqual(["Cmd", "Shift", "P"]);
      expect(promptShortcut?.description).toContain("prompt");
    });

    it("should have all 4 MCP shortcuts defined", async () => {
      const { DEFAULT_SHORTCUT_CATEGORIES } = await import("./HelpPage");

      const mcpCategory = DEFAULT_SHORTCUT_CATEGORIES.find(
        (cat) => cat.id === "mcp",
      );

      expect(mcpCategory?.shortcuts).toHaveLength(4);
    });
  });
});

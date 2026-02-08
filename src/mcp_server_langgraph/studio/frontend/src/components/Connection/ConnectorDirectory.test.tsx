/**
 * ConnectorDirectory Component Tests
 *
 * Tests for the connector directory grid layout.
 * @see ADR-0102
 */

import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ConnectorDirectory } from "./ConnectorDirectory";
import type { ConnectionTemplateCamelCase } from "@/types/connectionTemplate";

import { TestProvider } from "@/test-utils";

// Motion mock is provided globally in src/test/setup.ts
// with proper motion prop filtering to prevent React warnings

const mockTemplates: ConnectionTemplateCamelCase[] = [
  {
    id: "github",
    name: "GitHub",
    description: "Access GitHub repositories",
    icon: "github",
    authType: "oauth2",
    defaultUrl: "https://api.github.com/mcp",
    category: "development",
    oauth2Scopes: [],
    configFields: [],
    keywords: ["github", "repo"],
    popularity: 95,
    documentationUrl: "https://docs.github.com/",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Access Slack channels",
    icon: "slack",
    authType: "oauth2",
    defaultUrl: "https://slack.com/api/mcp",
    category: "communication",
    oauth2Scopes: [],
    configFields: [],
    keywords: ["slack", "channel"],
    popularity: 90,
    documentationUrl: "https://api.slack.com/",
  },
  {
    id: "notion",
    name: "Notion",
    description: "Access Notion pages",
    icon: "notion",
    authType: "oauth2",
    defaultUrl: "https://api.notion.com/mcp",
    category: "productivity",
    oauth2Scopes: [],
    configFields: [],
    keywords: ["notion", "page"],
    popularity: 85,
    documentationUrl: null,
  },
];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("ConnectorDirectory", () => {
  describe("Rendering", () => {
    it("should render all templates as cards", () => {
      render(
        <TestProvider>
          <ConnectorDirectory templates={mockTemplates} onConnect={vi.fn()} />
        </TestProvider>,
      );
      expect(screen.getByText("GitHub")).toBeInTheDocument();
      expect(screen.getByText("Slack")).toBeInTheDocument();
      expect(screen.getByText("Notion")).toBeInTheDocument();
    });

    it("should render in a grid layout", () => {
      render(
        <TestProvider>
          <ConnectorDirectory templates={mockTemplates} onConnect={vi.fn()} />
        </TestProvider>,
      );
      const grid = screen.getByRole("list");
      expect(grid).toHaveClass("grid");
    });

    it("should show empty state when no templates", () => {
      render(
        <TestProvider>
          <ConnectorDirectory templates={[]} onConnect={vi.fn()} />
        </TestProvider>,
      );
      expect(screen.getByText(/no connectors available/i)).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    it("should show category filters when categories are provided", () => {
      const categories = [
        { id: "development", name: "Development", description: "" },
        { id: "communication", name: "Communication", description: "" },
      ];
      render(
        <TestProvider>
          <ConnectorDirectory
            templates={mockTemplates}
            categories={categories}
            onConnect={vi.fn()}
          />
        </TestProvider>,
      );
      expect(screen.getByText("Development")).toBeInTheDocument();
      expect(screen.getByText("Communication")).toBeInTheDocument();
    });

    it("should filter templates by selected category", async () => {
      const categories = [
        { id: "development", name: "Development", description: "" },
        { id: "communication", name: "Communication", description: "" },
      ];
      render(
        <TestProvider>
          <ConnectorDirectory
            templates={mockTemplates}
            categories={categories}
            onConnect={vi.fn()}
          />
        </TestProvider>,
      );

      // Click on Development filter
      fireEvent.click(screen.getByRole("button", { name: /development/i }));

      // Wait for the filter to apply and re-render
      await waitFor(() => {
        // Should only show GitHub - check via article count
        const cards = screen.getAllByRole("article");
        expect(cards.length).toBe(1);
      });

      // Verify the remaining card is GitHub
      expect(screen.getByText("GitHub")).toBeInTheDocument();
    });

    it("should show all templates when All category is selected", () => {
      const categories = [
        { id: "development", name: "Development", description: "" },
      ];
      render(
        <TestProvider>
          <ConnectorDirectory
            templates={mockTemplates}
            categories={categories}
            onConnect={vi.fn()}
          />
        </TestProvider>,
      );

      // Click on All
      fireEvent.click(screen.getByRole("button", { name: /all/i }));

      expect(screen.getByText("GitHub")).toBeInTheDocument();
      expect(screen.getByText("Slack")).toBeInTheDocument();
      expect(screen.getByText("Notion")).toBeInTheDocument();
    });
  });

  describe("Sorting", () => {
    it("should sort templates by popularity by default", () => {
      render(
        <TestProvider>
          <ConnectorDirectory templates={mockTemplates} onConnect={vi.fn()} />
        </TestProvider>,
      );

      const cards = screen.getAllByRole("article");
      // GitHub (95) should be first, then Slack (90), then Notion (85)
      expect(cards[0]).toHaveTextContent("GitHub");
      expect(cards[1]).toHaveTextContent("Slack");
      expect(cards[2]).toHaveTextContent("Notion");
    });
  });

  describe("Interactions", () => {
    it("should call onConnect with template when Connect is clicked", () => {
      const onConnect = vi.fn();
      render(
        <TestProvider>
          <ConnectorDirectory templates={mockTemplates} onConnect={onConnect} />
        </TestProvider>,
      );

      // Click first Connect button (GitHub)
      const connectButtons = screen.getAllByRole("button", {
        name: /connect/i,
      });
      fireEvent.click(connectButtons[0]);

      expect(onConnect).toHaveBeenCalledWith(mockTemplates[0]);
    });
  });

  describe("Connected State", () => {
    it("should show Connected badge for connected templates", () => {
      render(
        <TestProvider>
          <ConnectorDirectory
            templates={mockTemplates}
            onConnect={vi.fn()}
            connectedTemplateIds={["github"]}
          />
        </TestProvider>,
      );

      // Both the badge and button show "Connected" for connected templates
      const connectedElements = screen.getAllByText("Connected");
      expect(connectedElements.length).toBeGreaterThanOrEqual(1);
    });
  });
});

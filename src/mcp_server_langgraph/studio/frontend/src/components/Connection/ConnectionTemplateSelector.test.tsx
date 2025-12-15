/**
 * ConnectionTemplateSelector Tests
 *
 * TDD tests for the connection template selector component.
 * Allows users to select from pre-configured MCP server templates.
 *
 * Uses MSW for realistic API mocking at the network level.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
  act,
} from "@testing-library/react";
import { http, HttpResponse } from "msw";
import { server } from "../../mocks/server";
import { ConnectionTemplateSelector } from "./ConnectionTemplateSelector";

// Mock data
const mockTemplates = [
  {
    id: "github",
    name: "GitHub",
    description: "Access GitHub repositories, issues, and pull requests",
    icon: "github",
    auth_type: "oauth2",
    default_url: "https://api.github.com/mcp",
    category: "development",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Access Slack workspaces, channels, and messages",
    icon: "slack",
    auth_type: "oauth2",
    default_url: "https://slack.com/api/mcp",
    category: "communication",
  },
  {
    id: "filesystem",
    name: "Filesystem",
    description: "Access local filesystem for reading and writing files",
    icon: "folder",
    auth_type: "none",
    default_url: "http://localhost:3001",
    category: "local",
  },
  {
    id: "custom-api",
    name: "Custom API",
    description: "Connect to any MCP server using API key authentication",
    icon: "key",
    auth_type: "api_key",
    default_url: "https://your-mcp-server.example.com",
    category: "custom",
  },
];

const mockCategories = [
  { id: "development", name: "Development", description: "Development tools" },
  {
    id: "communication",
    name: "Communication",
    description: "Communication tools",
  },
  {
    id: "productivity",
    name: "Productivity",
    description: "Productivity tools",
  },
  { id: "local", name: "Local", description: "Local system access" },
  { id: "custom", name: "Custom", description: "Custom integrations" },
];

describe("ConnectionTemplateSelector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Set up default handlers - note: component uses /connection-templates (hyphenated)
    server.use(
      http.get("/api/v1/connection-templates", ({ request }) => {
        const url = new URL(request.url);
        if (url.pathname.includes("/categories")) {
          return HttpResponse.json({ categories: mockCategories });
        }
        return HttpResponse.json({ templates: mockTemplates });
      }),
      http.get("/api/v1/connection-templates/categories", () => {
        return HttpResponse.json({ categories: mockCategories });
      }),
    );
  });

  afterEach(async () => {
    // Wait for any pending state updates to complete
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  describe("Component Structure", () => {
    it("should render title", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      await waitFor(() => {
        expect(screen.getByText(/choose a template/i)).toBeInTheDocument();
      });
    });

    it("should show loading state initially", () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      expect(screen.getByTestId("loading-templates")).toBeInTheDocument();
    });

    it("should display templates after loading", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
        expect(screen.getByText("Slack")).toBeInTheDocument();
      });
    });
  });

  describe("Template Cards", () => {
    it("should display template name and description", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
        expect(
          screen.getByText(/access github repositories/i),
        ).toBeInTheDocument();
      });
    });

    it("should show auth type badge", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      await waitFor(() => {
        expect(screen.getAllByText(/oauth2/i).length).toBeGreaterThan(0);
      });
    });

    it("should show category for each template", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);
      await waitFor(() => {
        // Check for category badges on template cards (uses getAllBy since multiple elements match)
        expect(screen.getAllByText(/development/i).length).toBeGreaterThan(0);
        expect(screen.getAllByText(/communication/i).length).toBeGreaterThan(0);
      });
    });
  });

  describe("Template Selection", () => {
    it("should call onSelect when template clicked", async () => {
      const onSelect = vi.fn();
      render(<ConnectionTemplateSelector onSelect={onSelect} />);

      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByText("GitHub"));
      expect(onSelect).toHaveBeenCalledWith(mockTemplates[0]);
    });

    it("should highlight selected template", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
      });

      const githubCard = screen.getByTestId("template-card-github");
      fireEvent.click(githubCard);

      expect(githubCard).toHaveClass("selected");
    });
  });

  describe("Category Filtering", () => {
    it("should show category filter buttons", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /^all$/i }),
        ).toBeInTheDocument();
        // Get the filter buttons specifically
        const buttons = screen.getAllByRole("button", { name: /development/i });
        expect(buttons.length).toBeGreaterThan(0);
      });
    });

    it("should filter templates by category", async () => {
      let lastRequestUrl = "";
      server.use(
        http.get("/api/v1/connection-templates", ({ request }) => {
          lastRequestUrl = request.url;
          return HttpResponse.json({ templates: mockTemplates });
        }),
      );

      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
      });

      // Find the category filter button (first one with Development text)
      const devButtons = screen.getAllByRole("button", {
        name: /development/i,
      });
      fireEvent.click(devButtons[0]);

      await waitFor(() => {
        expect(lastRequestUrl).toContain("category=development");
      });
    });

    it('should show "All" filter as active by default', async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        const allButton = screen.getByRole("button", { name: /all/i });
        expect(allButton).toHaveClass("active");
      });
    });
  });

  describe("Search", () => {
    it("should show search input", async () => {
      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(
          screen.getByPlaceholderText(/search templates/i),
        ).toBeInTheDocument();
      });
    });

    it("should filter templates on search", async () => {
      let lastRequestUrl = "";
      server.use(
        http.get("/api/v1/connection-templates", ({ request }) => {
          lastRequestUrl = request.url;
          return HttpResponse.json({ templates: mockTemplates });
        }),
      );

      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText("GitHub")).toBeInTheDocument();
      });

      const searchInput = screen.getByPlaceholderText(/search templates/i);
      fireEvent.change(searchInput, { target: { value: "git" } });

      await waitFor(() => {
        expect(lastRequestUrl).toContain("search=git");
      });
    });
  });

  describe("Empty State", () => {
    it("should show message when no templates match", async () => {
      server.use(
        http.get("/api/v1/connection-templates", () => {
          return HttpResponse.json({ templates: [] });
        }),
      );

      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(screen.getByText(/no templates found/i)).toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should show error message on fetch failure", async () => {
      server.use(
        http.get("/api/v1/connection-templates", () => {
          return HttpResponse.error();
        }),
      );

      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(
          screen.getByText(/failed to load templates/i),
        ).toBeInTheDocument();
      });
    });

    it("should show retry button on error", async () => {
      server.use(
        http.get("/api/v1/connection-templates", () => {
          return HttpResponse.error();
        }),
      );

      render(<ConnectionTemplateSelector onSelect={vi.fn()} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /retry/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Custom Template Option", () => {
    it('should show "Custom Connection" option', async () => {
      render(
        <ConnectionTemplateSelector onSelect={vi.fn()} showCustomOption />,
      );

      await waitFor(() => {
        // Use data-testid to find the custom connection card
        expect(
          screen.getByTestId("custom-connection-card"),
        ).toBeInTheDocument();
      });
    });

    it("should call onCustom when custom option clicked", async () => {
      const onCustom = vi.fn();
      render(
        <ConnectionTemplateSelector
          onSelect={vi.fn()}
          onCustom={onCustom}
          showCustomOption
        />,
      );

      await waitFor(() => {
        expect(
          screen.getByTestId("custom-connection-card"),
        ).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId("custom-connection-card"));
      expect(onCustom).toHaveBeenCalled();
    });
  });
});

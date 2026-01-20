/**
 * ConnectorCard Component Tests
 *
 * Tests for the connector card used in the Connections directory view.
 * @see ADR-0102
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConnectorCard } from "./ConnectorCard";
import type { ConnectionTemplateCamelCase } from "@/types/connectionTemplate";

// Motion mock is provided globally in src/test/setup.ts
// with proper motion prop filtering to prevent React warnings

const mockTemplate: ConnectionTemplateCamelCase = {
  id: "github",
  name: "GitHub",
  description: "Access GitHub repositories, issues, and pull requests",
  icon: "github",
  authType: "oauth2",
  defaultUrl: "https://api.github.com/mcp",
  category: "development",
  oauth2Scopes: ["repo", "user", "read:org"],
  configFields: [],
  keywords: ["github", "pr", "pull request", "repository"],
  popularity: 95,
  documentationUrl: "https://docs.github.com/",
};

describe("ConnectorCard", () => {
  describe("Rendering", () => {
    it("should render the connector name", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("GitHub")).toBeInTheDocument();
    });

    it("should render the connector description", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(
        screen.getByText("Access GitHub repositories, issues, and pull requests")
      ).toBeInTheDocument();
    });

    it("should render the icon", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      // Icon is rendered as emoji
      expect(screen.getByTestId("connector-icon")).toBeInTheDocument();
    });

    it("should render the auth type badge", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("OAuth2")).toBeInTheDocument();
    });

    it("should render the category badge", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("development")).toBeInTheDocument();
    });

    it("should render the Connect button", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(
        screen.getByRole("button", { name: /connect/i })
      ).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onConnect when Connect button is clicked", () => {
      const onConnect = vi.fn();
      render(<ConnectorCard template={mockTemplate} onConnect={onConnect} />);

      fireEvent.click(screen.getByRole("button", { name: /connect/i }));
      expect(onConnect).toHaveBeenCalledWith(mockTemplate);
    });

    it("should show documentation link when documentationUrl is provided", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      const docsLink = screen.getByRole("link", { name: /docs/i });
      expect(docsLink).toHaveAttribute("href", "https://docs.github.com/");
    });

    it("should not show documentation link when documentationUrl is null", () => {
      const templateWithoutDocs = {
        ...mockTemplate,
        documentationUrl: null,
      };
      render(
        <ConnectorCard template={templateWithoutDocs} onConnect={vi.fn()} />
      );
      expect(screen.queryByRole("link", { name: /docs/i })).not.toBeInTheDocument();
    });
  });

  describe("Auth Type Display", () => {
    it("should display OAuth2 badge for oauth2 auth type", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("OAuth2")).toBeInTheDocument();
    });

    it("should display API Key badge for api_key auth type", () => {
      const apiKeyTemplate = { ...mockTemplate, authType: "api_key" as const };
      render(<ConnectorCard template={apiKeyTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("API Key")).toBeInTheDocument();
    });

    it("should display No Auth badge for none auth type", () => {
      const noAuthTemplate = { ...mockTemplate, authType: "none" as const };
      render(<ConnectorCard template={noAuthTemplate} onConnect={vi.fn()} />);
      expect(screen.getByText("No Auth")).toBeInTheDocument();
    });
  });

  describe("Connected State", () => {
    it("should show Connected badge when isConnected is true", () => {
      render(
        <ConnectorCard
          template={mockTemplate}
          onConnect={vi.fn()}
          isConnected={true}
        />
      );
      // Both the badge and button text show "Connected"
      const connectedElements = screen.getAllByText("Connected");
      expect(connectedElements.length).toBeGreaterThanOrEqual(1);
    });

    it("should disable Connect button when isConnected is true", () => {
      render(
        <ConnectorCard
          template={mockTemplate}
          onConnect={vi.fn()}
          isConnected={true}
        />
      );
      expect(screen.getByRole("button", { name: /connected/i })).toBeDisabled();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible name for the card", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      expect(
        screen.getByRole("article", { name: /github connector/i })
      ).toBeInTheDocument();
    });

    it("should have accessible external link indicator for docs", () => {
      render(<ConnectorCard template={mockTemplate} onConnect={vi.fn()} />);
      const docsLink = screen.getByRole("link", { name: /docs/i });
      expect(docsLink).toHaveAttribute("target", "_blank");
      expect(docsLink).toHaveAttribute("rel", "noopener noreferrer");
    });
  });
});

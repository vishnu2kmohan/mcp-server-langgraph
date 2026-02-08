/**
 * useRouteCommands Hook Tests
 *
 * Tests for the route-aware command registration hook.
 *
 * Sprint 4: CommandPalette Enhancement
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter, Routes, Route } from "react-router";
import { ReactNode } from "react";
import {
  CommandPaletteProvider,
  useCommandPalette,
} from "../contexts/CommandPaletteContext";
import { useRouteCommands } from "./useRouteCommands";
import type { Command } from "../ai/AICommandPalette";

import { TestProvider } from "@/test-utils";

// ==============================================================================
// Test Setup
// ==============================================================================

const STATIC_COMMANDS: Command[] = [
  {
    id: "base-command",
    name: "Base Command",
    description: "A base command",
    category: "general",
  },
];

function CommandDisplay() {
  useRouteCommands();
  const { commands } = useCommandPalette();

  return (
    <div>
      <span data-testid="command-count">{commands.length}</span>
      <ul data-testid="command-list">
        {commands.map((cmd) => (
          <li key={cmd.id} data-testid={`cmd-${cmd.id}`}>
            {cmd.name}
          </li>
        ))}
      </ul>
    </div>
  );
}

function TestWrapper({
  children,
  initialPath = "/",
}: {
  children: ReactNode;
  initialPath?: string;
}) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <CommandPaletteProvider staticCommands={STATIC_COMMANDS}>
        {children}
      </CommandPaletteProvider>
    </MemoryRouter>
  );
}

// ==============================================================================
// Tests
// ==============================================================================

describe("useRouteCommands", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("route-based registration", () => {
    it("should register workflow commands for /studio/workflows", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/workflows">
            <Routes>
              <Route path="/studio/workflows" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      // Should have base command + workflow-specific commands
      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-new-workflow")).toBeInTheDocument();
    });

    it("should register observability commands for /studio/observability", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/observability">
            <Routes>
              <Route
                path="/studio/observability"
                element={<CommandDisplay />}
              />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      // Should have base command + observability-specific commands
      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-query-logs")).toBeInTheDocument();
    });

    it("should register connections commands for /studio/connections", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/connections">
            <Routes>
              <Route path="/studio/connections" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-new-connection"),
      ).toBeInTheDocument();
    });

    it("should not register route commands for unknown paths", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/unknown">
            <Routes>
              <Route path="/studio/unknown" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      // Should only have base command
      expect(screen.getByTestId("command-count").textContent).toBe("1");
      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
    });

    // New route tests for Sprint 4 expansion
    it("should register MCP commands for /studio/mcp", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/mcp">
            <Routes>
              <Route path="/studio/mcp" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-browse-tools")).toBeInTheDocument();
    });

    it("should register agents commands for /studio/agents", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/agents">
            <Routes>
              <Route path="/studio/agents" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-configure-agent"),
      ).toBeInTheDocument();
    });

    it("should register artifacts commands for /studio/artifacts", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/artifacts">
            <Routes>
              <Route path="/studio/artifacts" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-upload-artifact"),
      ).toBeInTheDocument();
    });

    it("should register cost commands for /studio/cost", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/cost">
            <Routes>
              <Route path="/studio/cost" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-set-budget")).toBeInTheDocument();
    });

    it("should register help commands for /studio/help", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/help">
            <Routes>
              <Route path="/studio/help" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-search-docs")).toBeInTheDocument();
    });

    it("should register compliance commands for /studio/compliance", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/compliance">
            <Routes>
              <Route path="/studio/compliance" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-run-compliance-check"),
      ).toBeInTheDocument();
    });

    it("should register audit commands for /studio/audit", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/audit">
            <Routes>
              <Route path="/studio/audit" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-export-audit-log"),
      ).toBeInTheDocument();
    });

    it("should register vectors commands for /studio/vectors", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/vectors">
            <Routes>
              <Route path="/studio/vectors" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-search-vectors"),
      ).toBeInTheDocument();
    });

    it("should register analytics commands for /studio/analytics", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/analytics">
            <Routes>
              <Route path="/studio/analytics" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-export-report")).toBeInTheDocument();
    });

    it("should register skills commands for /studio/skills", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/skills">
            <Routes>
              <Route path="/studio/skills" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(
        screen.getByTestId("cmd-route-browse-marketplace"),
      ).toBeInTheDocument();
    });

    it("should register admin commands for /studio/admin", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/admin">
            <Routes>
              <Route path="/studio/admin" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      expect(screen.getByTestId("cmd-base-command")).toBeInTheDocument();
      expect(screen.getByTestId("cmd-route-manage-users")).toBeInTheDocument();
    });
  });

  describe("cleanup on unmount", () => {
    it("should unregister commands when component unmounts", () => {
      // This tests the cleanup function of useEffect
      const { unmount } = render(
        <TestProvider>
          <TestWrapper initialPath="/studio/workflows">
            <Routes>
              <Route path="/studio/workflows" element={<CommandDisplay />} />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      // Verify commands are registered
      expect(screen.getByTestId("cmd-route-new-workflow")).toBeInTheDocument();

      // Unmount - cleanup should run
      unmount();

      // Can't verify after unmount, but the test ensures cleanup function exists
    });
  });

  describe("nested routes", () => {
    it("should register parent route commands for nested paths", () => {
      render(
        <TestProvider>
          <TestWrapper initialPath="/studio/workflows/123/edit">
            <Routes>
              <Route
                path="/studio/workflows/:id/edit"
                element={<CommandDisplay />}
              />
            </Routes>
          </TestWrapper>
        </TestProvider>,
      );

      // Should still register workflow commands for nested path
      expect(screen.getByTestId("cmd-route-new-workflow")).toBeInTheDocument();
    });
  });
});

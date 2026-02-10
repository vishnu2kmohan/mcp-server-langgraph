/**
 * StatusBar Core Tests
 *
 * Tests for rendering, keyboard shortcuts, custom status, styling, and error state.
 *
 * Split from StatusBar.test.tsx for memory optimization.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { TestProvider } from "@/test-utils";
import { mockFeatureFlagToggle } from "./StatusBar.fixtures";
import { StatusBar } from "../StatusBar";

// Apply shared mocks
mockFeatureFlagToggle();

describe("StatusBar", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });

    it("should display Idle status by default (context-aware)", () => {
      // StatusBar now derives status from context instead of static "Ready"
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("Idle")).toBeInTheDocument();
    });

    it("should render FeatureFlagToggle", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByTestId("feature-flag-toggle")).toBeInTheDocument();
    });
  });

  describe("keyboard shortcuts", () => {
    it("should display command palette shortcut", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("⌘K Command Palette")).toBeInTheDocument();
    });

    it("should display toggle canvas shortcut", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.getByText("⌘/ Toggle Canvas")).toBeInTheDocument();
    });
  });

  describe("custom status", () => {
    it("should display custom status when provided", () => {
      render(
        <TestProvider>
          <StatusBar status="Loading..." />
        </TestProvider>,
      );

      expect(screen.getByText("Loading...")).toBeInTheDocument();
      expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    });
  });

  describe("styling", () => {
    it("should apply custom className", () => {
      render(
        <TestProvider>
          <StatusBar className="custom-class" />
        </TestProvider>,
      );

      expect(screen.getByTestId("status-bar")).toHaveClass("custom-class");
    });

    it("should have proper dark mode classes", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      const statusBar = screen.getByTestId("status-bar");
      // Uses semantic neutral classes that adapt to dark mode via CSS variables
      expect(statusBar).toHaveClass("bg-neutral-2", "border-neutral-5");
    });
  });

  describe("error state", () => {
    it("should show error indicator when connectionStatus is error", () => {
      render(
        <TestProvider>
          <StatusBar connectionStatus="error" />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveClass("bg-error-9");
    });

    it("should display error message when provided", () => {
      render(
        <TestProvider>
          <StatusBar errorMessage="Connection failed" />
        </TestProvider>,
      );

      expect(screen.getByTestId("error-message")).toBeInTheDocument();
      expect(screen.getByText("Connection failed")).toBeInTheDocument();
    });

    it("should have error styling on error message", () => {
      render(
        <TestProvider>
          <StatusBar errorMessage="Something went wrong" />
        </TestProvider>,
      );

      const errorElement = screen.getByTestId("error-message");
      // Radix step 11 for text per design system
      expect(errorElement).toHaveClass("text-error-11");
    });

    it("should not display error message when not provided", () => {
      render(
        <TestProvider>
          <StatusBar />
        </TestProvider>,
      );

      expect(screen.queryByTestId("error-message")).not.toBeInTheDocument();
    });

    it("should show both connection error indicator and error message", () => {
      render(
        <TestProvider>
          <StatusBar
            connectionStatus="error"
            errorMessage="Server unreachable"
          />
        </TestProvider>,
      );

      const indicator = screen.getByTestId("connection-indicator");
      expect(indicator).toHaveClass("bg-error-9");
      expect(screen.getByText("Server unreachable")).toBeInTheDocument();
    });
  });
});

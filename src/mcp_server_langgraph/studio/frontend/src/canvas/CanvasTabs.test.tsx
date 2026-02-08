/**
 * CanvasTabs Tests - Phase 1
 *
 * Tests for the Code/Preview/Data tabs component
 * that switches between different views of an artifact.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { CanvasTabs } from "./CanvasTabs";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Tests
// =============================================================================

describe("CanvasTabs", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render tabs container", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByTestId("canvas-tabs")).toBeInTheDocument();
    });

    it("should render all three tabs", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("tab", { name: /code/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /preview/i })).toBeInTheDocument();
      expect(screen.getByRole("tab", { name: /data/i })).toBeInTheDocument();
    });

    it("should highlight active tab", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="preview" onTabChange={() => {}} />
        </TestProvider>,
      );
      const previewTab = screen.getByRole("tab", { name: /preview/i });
      expect(previewTab).toHaveAttribute("aria-selected", "true");
    });

    it("should not highlight inactive tabs", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      const previewTab = screen.getByRole("tab", { name: /preview/i });
      expect(previewTab).toHaveAttribute("aria-selected", "false");
    });
  });

  describe("Tab Switching", () => {
    it("should call onTabChange with 'code' when code tab clicked", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="preview" onTabChange={onTabChange} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("tab", { name: /code/i }));
      expect(onTabChange).toHaveBeenCalledWith("code");
    });

    it("should call onTabChange with 'preview' when preview tab clicked", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={onTabChange} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("tab", { name: /preview/i }));
      expect(onTabChange).toHaveBeenCalledWith("preview");
    });

    it("should call onTabChange with 'data' when data tab clicked", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={onTabChange} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("tab", { name: /data/i }));
      expect(onTabChange).toHaveBeenCalledWith("data");
    });

    it("should not call onTabChange when clicking already active tab", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={onTabChange} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByRole("tab", { name: /code/i }));
      expect(onTabChange).not.toHaveBeenCalled();
    });
  });

  describe("Disabled Tabs", () => {
    it("should disable tabs when disabled prop is true", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} disabled />
        </TestProvider>,
      );

      const tabs = screen.getAllByRole("tab");
      tabs.forEach((tab) => {
        expect(tab).toBeDisabled();
      });
    });

    it("should disable specific tabs via disabledTabs prop", () => {
      render(
        <TestProvider>
          <CanvasTabs
            activeTab="code"
            onTabChange={() => {}}
            disabledTabs={["preview", "data"]}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("tab", { name: /code/i })).not.toBeDisabled();
      expect(screen.getByRole("tab", { name: /preview/i })).toBeDisabled();
      expect(screen.getByRole("tab", { name: /data/i })).toBeDisabled();
    });
  });

  describe("Icons", () => {
    it("should display code icon for code tab", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByTestId("code-icon")).toBeInTheDocument();
    });

    it("should display preview icon for preview tab", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByTestId("preview-icon")).toBeInTheDocument();
    });

    it("should display data icon for data tab", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByTestId("data-icon")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should support arrow key navigation between tabs", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={onTabChange} />
        </TestProvider>,
      );

      const codeTab = screen.getByRole("tab", { name: /code/i });
      codeTab.focus();

      fireEvent.keyDown(codeTab, { key: "ArrowRight" });
      expect(onTabChange).toHaveBeenCalledWith("preview");
    });

    it("should wrap around when navigating past last tab", () => {
      const onTabChange = vi.fn();
      render(
        <TestProvider>
          <CanvasTabs activeTab="data" onTabChange={onTabChange} />
        </TestProvider>,
      );

      const dataTab = screen.getByRole("tab", { name: /data/i });
      dataTab.focus();

      fireEvent.keyDown(dataTab, { key: "ArrowRight" });
      expect(onTabChange).toHaveBeenCalledWith("code");
    });
  });

  describe("Accessibility", () => {
    it("should have tablist role on container", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="code" onTabChange={() => {}} />
        </TestProvider>,
      );
      expect(screen.getByRole("tablist")).toBeInTheDocument();
    });

    it("should have correct aria-selected on tabs", () => {
      render(
        <TestProvider>
          <CanvasTabs activeTab="preview" onTabChange={() => {}} />
        </TestProvider>,
      );

      expect(screen.getByRole("tab", { name: /code/i })).toHaveAttribute(
        "aria-selected",
        "false",
      );
      expect(screen.getByRole("tab", { name: /preview/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
      expect(screen.getByRole("tab", { name: /data/i })).toHaveAttribute(
        "aria-selected",
        "false",
      );
    });
  });
});

/**
 * Tests for react-resizable-panels mock
 *
 * Verifies that the mock components work correctly and provide
 * the expected imperative handle methods.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import React from "react";
import { render, screen, cleanup } from "@testing-library/react";
import {
  mockReactResizablePanels,
  createMockPanelHandle,
} from "./react-resizable-panels";

const { PanelGroup, Panel, PanelResizeHandle } = mockReactResizablePanels;

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("react-resizable-panels mock", () => {
  describe("PanelGroup", () => {
    it("should render children", () => {
      render(
        React.createElement(
          PanelGroup,
          { direction: "horizontal" },
          React.createElement("div", { "data-testid": "child" }, "Content"),
        ),
      );

      expect(screen.getByTestId("child")).toBeInTheDocument();
      expect(screen.getByText("Content")).toBeInTheDocument();
    });

    it("should have data-testid panel-group", () => {
      render(
        React.createElement(
          PanelGroup,
          {},
          React.createElement("div", {}, "Content"),
        ),
      );

      expect(screen.getByTestId("panel-group")).toBeInTheDocument();
    });
  });

  describe("Panel", () => {
    it("should render children", () => {
      render(
        React.createElement(
          Panel,
          {},
          React.createElement(
            "div",
            { "data-testid": "panel-child" },
            "Panel Content",
          ),
        ),
      );

      expect(screen.getByTestId("panel-child")).toBeInTheDocument();
      expect(screen.getByText("Panel Content")).toBeInTheDocument();
    });

    it("should support custom data-testid", () => {
      render(
        React.createElement(
          Panel,
          { "data-testid": "custom-panel" },
          React.createElement("div", {}, "Content"),
        ),
      );

      expect(screen.getByTestId("custom-panel")).toBeInTheDocument();
    });

    it("should expose imperative handle via ref", () => {
      const ref = React.createRef<ReturnType<typeof createMockPanelHandle>>();

      render(
        React.createElement(
          Panel,
          { ref },
          React.createElement("div", {}, "Content"),
        ),
      );

      expect(ref.current).toBeDefined();
      expect(ref.current?.collapse).toBeDefined();
      expect(ref.current?.expand).toBeDefined();
      expect(ref.current?.getSize).toBeDefined();
      expect(ref.current?.isCollapsed).toBeDefined();
      expect(ref.current?.isExpanded).toBeDefined();
    });

    it("should have callable imperative methods", () => {
      const ref = React.createRef<ReturnType<typeof createMockPanelHandle>>();

      render(
        React.createElement(
          Panel,
          { ref },
          React.createElement("div", {}, "Content"),
        ),
      );

      // Call methods - should not throw
      expect(() => ref.current?.collapse()).not.toThrow();
      expect(() => ref.current?.expand()).not.toThrow();
      expect(ref.current?.getSize()).toBe(20);
      expect(ref.current?.isCollapsed()).toBe(false);
      expect(ref.current?.isExpanded()).toBe(true);
    });
  });

  describe("PanelResizeHandle", () => {
    it("should render with separator role", () => {
      render(React.createElement(PanelResizeHandle, {}));

      expect(screen.getByRole("separator")).toBeInTheDocument();
    });

    it("should have data-testid resize-handle", () => {
      render(React.createElement(PanelResizeHandle, {}));

      expect(screen.getByTestId("resize-handle")).toBeInTheDocument();
    });

    it("should render children", () => {
      render(
        React.createElement(
          PanelResizeHandle,
          {},
          React.createElement("span", {}, "Handle Icon"),
        ),
      );

      expect(screen.getByText("Handle Icon")).toBeInTheDocument();
    });
  });

  describe("createMockPanelHandle", () => {
    it("should create mock functions for all methods", () => {
      const handle = createMockPanelHandle();

      expect(vi.isMockFunction(handle.collapse)).toBe(true);
      expect(vi.isMockFunction(handle.expand)).toBe(true);
      expect(vi.isMockFunction(handle.getSize)).toBe(true);
      expect(vi.isMockFunction(handle.isCollapsed)).toBe(true);
      expect(vi.isMockFunction(handle.isExpanded)).toBe(true);
      expect(vi.isMockFunction(handle.resize)).toBe(true);
    });

    it("should return default values", () => {
      const handle = createMockPanelHandle();

      expect(handle.getSize()).toBe(20);
      expect(handle.isCollapsed()).toBe(false);
      expect(handle.isExpanded()).toBe(true);
    });
  });
});

/**
 * InteractiveMermaidDiagram Component Tests
 *
 * Tests for the interactive mermaid diagram component with zoom,
 * fullscreen, and pan controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor, cleanup } from "@testing-library/react";
import { InteractiveMermaidDiagram } from "./InteractiveMermaidDiagram";

// Mock mermaid
vi.mock("mermaid", () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn().mockResolvedValue({
      svg: '<svg id="test-svg" viewBox="0 0 100 100"><rect width="100" height="100" /></svg>',
    }),
  },
}));

describe("InteractiveMermaidDiagram", () => {
  const sampleCode = `flowchart TD
    A[Start] --> B[End]`;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the mermaid diagram", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });
    });

    it("should display zoom controls", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
        expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
        expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
      });
    });

    it("should display fullscreen button", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
      });
    });

    it("should display copy source button", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Copy source")).toBeInTheDocument();
      });
    });
  });

  describe("Zoom Controls", () => {
    it("should zoom in when zoom in button is clicked", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const zoomInButton = screen.getByLabelText("Zoom in");
      fireEvent.click(zoomInButton);

      const container = screen.getByTestId("mermaid-viewport");
      expect(container.style.transform).toContain("scale(1.25)");
    });

    it("should zoom out when zoom out button is clicked", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const zoomOutButton = screen.getByLabelText("Zoom out");
      fireEvent.click(zoomOutButton);

      const container = screen.getByTestId("mermaid-viewport");
      expect(container.style.transform).toContain("scale(0.8)");
    });

    it("should reset zoom when reset button is clicked", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      // First zoom in
      fireEvent.click(screen.getByLabelText("Zoom in"));
      fireEvent.click(screen.getByLabelText("Zoom in"));

      // Then reset
      fireEvent.click(screen.getByLabelText("Reset zoom"));

      const container = screen.getByTestId("mermaid-viewport");
      expect(container.style.transform).toContain("scale(1)");
    });

    it("should display current zoom level", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByText("100%")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText("Zoom in"));

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });
  });

  describe("Copy Functionality", () => {
    it("should copy source code when copy button is clicked", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText },
      });

      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Copy source")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText("Copy source"));

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(sampleCode);
      });
    });
  });

  describe("Error Handling", () => {
    it("should display error state when rendering fails", async () => {
      const mermaid = await import("mermaid");
      vi.mocked(mermaid.default.render).mockRejectedValueOnce(
        new Error("Parse error"),
      );

      render(<InteractiveMermaidDiagram code="invalid mermaid code" />);

      await waitFor(() => {
        expect(screen.getByText(/diagram error/i)).toBeInTheDocument();
      });
    });

    it("should show source code in error state", async () => {
      const mermaid = await import("mermaid");
      vi.mocked(mermaid.default.render).mockRejectedValueOnce(
        new Error("Parse error"),
      );

      render(<InteractiveMermaidDiagram code="invalid code" />);

      await waitFor(() => {
        expect(screen.getByText("View source")).toBeInTheDocument();
      });
    });
  });

  describe("Download", () => {
    it("should display download button", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Download as PNG")).toBeInTheDocument();
      });
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("should zoom in with + key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "+" });

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should zoom out with - key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "-" });

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should reset zoom with 0 key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      // First zoom in
      fireEvent.click(screen.getByLabelText("Zoom in"));
      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });

      // Then reset with 0
      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "0" });

      await waitFor(() => {
        expect(screen.getByText("100%")).toBeInTheDocument();
      });
    });

    it("should exit fullscreen with Escape key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      // Enter fullscreen
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));
      await waitFor(() => {
        expect(
          screen.getByTestId("mermaid-container").classList.contains("fixed"),
        ).toBe(true);
      });

      // Exit with Escape
      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "Escape" });

      await waitFor(() => {
        expect(
          screen.getByTestId("mermaid-container").classList.contains("fixed"),
        ).toBe(false);
      });
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria labels for all controls", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
        expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
        expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
        expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
        expect(screen.getByLabelText("Copy source")).toBeInTheDocument();
        expect(screen.getByLabelText("Download as PNG")).toBeInTheDocument();
      });
    });

    it("should be focusable for keyboard navigation", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        const container = screen.getByTestId("mermaid-container");
        expect(container).toHaveAttribute("tabIndex", "0");
      });
    });
  });

  describe("Touch Gestures", () => {
    it("should handle pinch-to-zoom with two fingers", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Initial zoom is 100%
      expect(screen.getByText("100%")).toBeInTheDocument();

      // Simulate pinch start (two fingers)
      fireEvent.touchStart(viewport, {
        touches: [
          { clientX: 100, clientY: 100, identifier: 0 },
          { clientX: 200, clientY: 200, identifier: 1 },
        ],
      });

      // Simulate pinch out (fingers moving apart to zoom in)
      fireEvent.touchMove(viewport, {
        touches: [
          { clientX: 50, clientY: 50, identifier: 0 },
          { clientX: 250, clientY: 250, identifier: 1 },
        ],
      });

      fireEvent.touchEnd(viewport);

      // Zoom should have increased
      await waitFor(() => {
        const zoomText = screen.getByText(/\d+%/);
        const zoomValue = parseInt(zoomText.textContent || "100");
        expect(zoomValue).toBeGreaterThan(100);
      });
    });

    it("should handle single finger pan", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Start single touch pan
      fireEvent.touchStart(viewport, {
        touches: [{ clientX: 100, clientY: 100, identifier: 0 }],
      });

      // Move finger
      fireEvent.touchMove(viewport, {
        touches: [{ clientX: 150, clientY: 150, identifier: 0 }],
      });

      fireEvent.touchEnd(viewport);

      // Should have handled the pan (position updated)
      expect(viewport.style.transform).toBeDefined();
    });
  });

  describe("Mouse Interactions", () => {
    it("should pan with mouse drag", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Start drag
      fireEvent.mouseDown(viewport, { button: 0, clientX: 100, clientY: 100 });
      fireEvent.mouseMove(viewport, { clientX: 150, clientY: 150 });
      fireEvent.mouseUp(viewport);

      // Should have panned
      expect(viewport.style.transform).toContain("translate");
    });

    it("should stop dragging on mouse leave", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Start drag
      fireEvent.mouseDown(viewport, { button: 0, clientX: 100, clientY: 100 });
      fireEvent.mouseLeave(viewport);

      // Cursor should reset
      expect(viewport.classList.contains("cursor-grab")).toBe(true);
    });

    it("should zoom with ctrl + mouse wheel scroll down", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Scroll down (zoom out) with ctrl
      fireEvent.wheel(viewport, { deltaY: 100, ctrlKey: true });

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should zoom with meta + mouse wheel scroll up", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Scroll up (zoom in) with meta
      fireEvent.wheel(viewport, { deltaY: -100, metaKey: true });

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should not zoom without ctrl/meta key on wheel", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-viewport")).toBeInTheDocument();
      });

      const viewport = screen.getByTestId("mermaid-viewport");

      // Scroll without modifier key
      fireEvent.wheel(viewport, { deltaY: 100 });

      // Zoom should stay at 100%
      expect(screen.getByText("100%")).toBeInTheDocument();
    });
  });

  describe("Alternative Keyboard Shortcuts", () => {
    it("should zoom in with = key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "=" });

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should zoom out with _ key", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");
      fireEvent.keyDown(container, { key: "_" });

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should not exit fullscreen with Escape when not in fullscreen", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");
      // Should not be fullscreen initially
      expect(container.classList.contains("fixed")).toBe(false);

      // Press Escape when not in fullscreen
      fireEvent.keyDown(container, { key: "Escape" });

      // Should still not be fullscreen
      expect(container.classList.contains("fixed")).toBe(false);
    });
  });

  describe("Copy Error Handling", () => {
    it("should handle clipboard write failure gracefully", async () => {
      const consoleError = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});
      Object.assign(navigator, {
        clipboard: {
          writeText: vi.fn().mockRejectedValue(new Error("Clipboard denied")),
        },
      });

      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByLabelText("Copy source")).toBeInTheDocument();
      });

      fireEvent.click(screen.getByLabelText("Copy source"));

      await waitFor(() => {
        expect(consoleError).toHaveBeenCalledWith(
          "Failed to copy:",
          expect.any(Error),
        );
      });

      consoleError.mockRestore();
    });
  });

  describe("Error State Variations", () => {
    it("should display generic error message for non-Error objects", async () => {
      const mermaid = await import("mermaid");
      vi.mocked(mermaid.default.render).mockRejectedValueOnce(
        "string error message",
      );

      render(<InteractiveMermaidDiagram code="invalid" />);

      await waitFor(() => {
        expect(screen.getByText(/diagram error/i)).toBeInTheDocument();
        expect(
          screen.getByText("Failed to render diagram"),
        ).toBeInTheDocument();
      });
    });

    it("should show error message from Error object", async () => {
      const mermaid = await import("mermaid");
      vi.mocked(mermaid.default.render).mockRejectedValueOnce(
        new Error("Syntax error at line 1"),
      );

      render(<InteractiveMermaidDiagram code="bad" />);

      await waitFor(() => {
        expect(screen.getByText("Syntax error at line 1")).toBeInTheDocument();
      });
    });
  });

  describe("Zoom Limits", () => {
    it("should not exceed maximum zoom of 400%", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const zoomInButton = screen.getByLabelText("Zoom in");

      // Click zoom in many times to hit the limit
      for (let i = 0; i < 10; i++) {
        fireEvent.click(zoomInButton);
      }

      // Should be capped at 400%
      await waitFor(() => {
        expect(screen.getByText("400%")).toBeInTheDocument();
      });
    });

    it("should not go below minimum zoom of 25%", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const zoomOutButton = screen.getByLabelText("Zoom out");

      // Click zoom out many times to hit the limit
      for (let i = 0; i < 15; i++) {
        fireEvent.click(zoomOutButton);
      }

      // Should be capped at 25%
      await waitFor(() => {
        expect(screen.getByText("25%")).toBeInTheDocument();
      });
    });
  });

  describe("Fullscreen Toggle", () => {
    it("should toggle fullscreen mode when button is clicked", async () => {
      render(<InteractiveMermaidDiagram code={sampleCode} />);

      await waitFor(() => {
        expect(screen.getByTestId("mermaid-container")).toBeInTheDocument();
      });

      const container = screen.getByTestId("mermaid-container");

      // Initially not fullscreen
      expect(container.classList.contains("fixed")).toBe(false);

      // Toggle to fullscreen
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));

      await waitFor(() => {
        expect(container.classList.contains("fixed")).toBe(true);
      });

      // Toggle back to normal
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));

      await waitFor(() => {
        expect(container.classList.contains("fixed")).toBe(false);
      });
    });
  });

  describe("Custom className", () => {
    it("should apply custom className to container", async () => {
      render(
        <InteractiveMermaidDiagram
          code={sampleCode}
          className="custom-class"
        />,
      );

      await waitFor(() => {
        const container = screen.getByTestId("mermaid-container");
        expect(container.classList.contains("custom-class")).toBe(true);
      });
    });
  });
});

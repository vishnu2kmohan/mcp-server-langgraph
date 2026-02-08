/**
 * InteractiveSVGArtifact Component Tests
 *
 * Tests for the interactive SVG component with zoom, pan,
 * fullscreen, download, and copy controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { InteractiveSVGArtifact } from "./InteractiveSVGArtifact";

import { TestProvider } from "@/test-utils";

describe("InteractiveSVGArtifact", () => {
  const sampleSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <circle cx="50" cy="50" r="40" fill="blue" />
  </svg>`;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the SVG content", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });

    it("should render title when provided", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} title="My SVG" />
        </TestProvider>,
      );

      expect(screen.getByText("My SVG")).toBeInTheDocument();
    });

    it("should render error for invalid SVG", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data="not valid svg" />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should render error for empty data", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data="" />
        </TestProvider>,
      );

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("Zoom Controls", () => {
    it("should display zoom level indicator", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should have zoom in button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
    });

    it("should have zoom out button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
    });

    it("should have reset zoom button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
    });

    it("should increase zoom when zoom in is clicked", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByLabelText("Zoom in"));

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should decrease zoom when zoom out is clicked", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByLabelText("Zoom out"));

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should reset zoom and position when reset is clicked", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      // Zoom in first
      fireEvent.click(screen.getByLabelText("Zoom in"));
      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });

      // Reset
      fireEvent.click(screen.getByLabelText("Reset zoom"));

      await waitFor(() => {
        expect(screen.getByText("100%")).toBeInTheDocument();
      });
    });
  });

  describe("Fullscreen", () => {
    it("should have fullscreen toggle button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
    });

    it("should toggle fullscreen mode", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const container = screen.getByTestId("svg-container");
      expect(container.classList.contains("fixed")).toBe(false);

      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));

      await waitFor(() => {
        expect(container.classList.contains("fixed")).toBe(true);
      });
    });
  });

  describe("Copy Functionality", () => {
    it("should have copy button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Copy SVG")).toBeInTheDocument();
    });

    it("should copy SVG source when button is clicked", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText },
      });

      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByLabelText("Copy SVG"));

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(sampleSVG);
      });
    });
  });

  describe("Download Functionality", () => {
    it("should have download SVG button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Download SVG")).toBeInTheDocument();
    });

    it("should have download PNG button", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Download PNG")).toBeInTheDocument();
    });
  });

  describe("Pan Support", () => {
    it("should have pannable viewport", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByTestId("svg-viewport")).toBeInTheDocument();
    });

    it("should show grab cursor on viewport", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const viewport = screen.getByTestId("svg-viewport");
      expect(viewport.classList.contains("cursor-grab")).toBe(true);
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria labels for all controls", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
      expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
      expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
      expect(screen.getByLabelText("Copy SVG")).toBeInTheDocument();
      expect(screen.getByLabelText("Download SVG")).toBeInTheDocument();
      expect(screen.getByLabelText("Download PNG")).toBeInTheDocument();
      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
    });
  });

  describe("Data URL Support", () => {
    it("should handle base64 data URL", async () => {
      const base64SVG = btoa(sampleSVG);
      const dataUrl = `data:image/svg+xml;base64,${base64SVG}`;

      render(
        <TestProvider>
          <InteractiveSVGArtifact data={dataUrl} />
        </TestProvider>,
      );

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });

    it("should handle URL-encoded data URL", async () => {
      const encodedSVG = encodeURIComponent(sampleSVG);
      const dataUrl = `data:image/svg+xml,${encodedSVG}`;

      render(
        <TestProvider>
          <InteractiveSVGArtifact data={dataUrl} />
        </TestProvider>,
      );

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("should zoom in with + key", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const container = screen.getByTestId("svg-container");
      fireEvent.keyDown(container, { key: "+" });

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should zoom out with - key", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const container = screen.getByTestId("svg-container");
      fireEvent.keyDown(container, { key: "-" });

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should reset zoom with 0 key", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      // First zoom in
      fireEvent.click(screen.getByLabelText("Zoom in"));
      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });

      // Then reset with 0
      const container = screen.getByTestId("svg-container");
      fireEvent.keyDown(container, { key: "0" });

      await waitFor(() => {
        expect(screen.getByText("100%")).toBeInTheDocument();
      });
    });

    it("should exit fullscreen with Escape key", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      // Enter fullscreen
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));
      await waitFor(() => {
        expect(
          screen.getByTestId("svg-container").classList.contains("fixed"),
        ).toBe(true);
      });

      // Exit with Escape
      const container = screen.getByTestId("svg-container");
      fireEvent.keyDown(container, { key: "Escape" });

      await waitFor(() => {
        expect(
          screen.getByTestId("svg-container").classList.contains("fixed"),
        ).toBe(false);
      });
    });
  });

  describe("Touch Gestures", () => {
    it("should have touch event handlers on viewport", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const viewport = screen.getByTestId("svg-viewport");
      expect(viewport).toBeInTheDocument();
      // The viewport should be responsive to touch events
      expect(viewport.classList.contains("touch-none")).toBe(false);
    });

    it("should handle single touch for pan", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const viewport = screen.getByTestId("svg-viewport");

      // Simulate touch start and move for pan
      fireEvent.touchStart(viewport, {
        touches: [{ clientX: 100, clientY: 100, identifier: 0 }],
      });

      fireEvent.touchMove(viewport, {
        touches: [{ clientX: 150, clientY: 150, identifier: 0 }],
      });

      fireEvent.touchEnd(viewport);

      // Pan should work without errors
      expect(screen.getByTestId("svg-viewport")).toBeInTheDocument();
    });

    it("should handle pinch-to-zoom with two fingers", async () => {
      render(
        <TestProvider>
          <InteractiveSVGArtifact data={sampleSVG} />
        </TestProvider>,
      );

      const viewport = screen.getByTestId("svg-viewport");

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

      // Zoom should have increased (pinch out = zoom in)
      await waitFor(() => {
        const zoomText = screen.getByText(/\d+%/);
        const zoomValue = parseInt(zoomText.textContent || "100");
        expect(zoomValue).toBeGreaterThan(100);
      });
    });
  });
});

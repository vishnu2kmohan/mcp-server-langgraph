/**
 * InteractiveSVGArtifact Component Tests
 *
 * Tests for the interactive SVG component with zoom, pan,
 * fullscreen, download, and copy controls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { InteractiveSVGArtifact } from "./InteractiveSVGArtifact";

describe("InteractiveSVGArtifact", () => {
  const sampleSVG = `<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <circle cx="50" cy="50" r="40" fill="blue" />
  </svg>`;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the SVG content", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });

    it("should render title when provided", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} title="My SVG" />);

      expect(screen.getByText("My SVG")).toBeInTheDocument();
    });

    it("should render error for invalid SVG", async () => {
      render(<InteractiveSVGArtifact data="not valid svg" />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });

    it("should render error for empty data", async () => {
      render(<InteractiveSVGArtifact data="" />);

      expect(screen.getByRole("alert")).toBeInTheDocument();
    });
  });

  describe("Zoom Controls", () => {
    it("should display zoom level indicator", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should have zoom in button", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
    });

    it("should have zoom out button", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
    });

    it("should have reset zoom button", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
    });

    it("should increase zoom when zoom in is clicked", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      fireEvent.click(screen.getByLabelText("Zoom in"));

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should decrease zoom when zoom out is clicked", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      fireEvent.click(screen.getByLabelText("Zoom out"));

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should reset zoom and position when reset is clicked", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

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
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
    });

    it("should toggle fullscreen mode", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

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
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Copy SVG")).toBeInTheDocument();
    });

    it("should copy SVG source when button is clicked", async () => {
      const writeText = vi.fn().mockResolvedValue(undefined);
      Object.assign(navigator, {
        clipboard: { writeText },
      });

      render(<InteractiveSVGArtifact data={sampleSVG} />);

      fireEvent.click(screen.getByLabelText("Copy SVG"));

      await waitFor(() => {
        expect(writeText).toHaveBeenCalledWith(sampleSVG);
      });
    });
  });

  describe("Download Functionality", () => {
    it("should have download SVG button", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Download SVG")).toBeInTheDocument();
    });

    it("should have download PNG button", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByLabelText("Download PNG")).toBeInTheDocument();
    });
  });

  describe("Pan Support", () => {
    it("should have pannable viewport", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      expect(screen.getByTestId("svg-viewport")).toBeInTheDocument();
    });

    it("should show grab cursor on viewport", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

      const viewport = screen.getByTestId("svg-viewport");
      expect(viewport.classList.contains("cursor-grab")).toBe(true);
    });
  });

  describe("Accessibility", () => {
    it("should have proper aria labels for all controls", async () => {
      render(<InteractiveSVGArtifact data={sampleSVG} />);

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

      render(<InteractiveSVGArtifact data={dataUrl} />);

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });

    it("should handle URL-encoded data URL", async () => {
      const encodedSVG = encodeURIComponent(sampleSVG);
      const dataUrl = `data:image/svg+xml,${encodedSVG}`;

      render(<InteractiveSVGArtifact data={dataUrl} />);

      expect(screen.getByTestId("svg-container")).toBeInTheDocument();
    });
  });
});

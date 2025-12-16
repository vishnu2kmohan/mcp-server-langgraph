/**
 * InteractiveMermaidDiagram Component Tests
 *
 * Tests for the interactive mermaid diagram component with zoom,
 * fullscreen, and pan controls.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
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
  });
});

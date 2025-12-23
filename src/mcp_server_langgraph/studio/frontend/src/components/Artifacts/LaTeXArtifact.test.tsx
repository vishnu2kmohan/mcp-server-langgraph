/**
 * LaTeXArtifact Component Tests
 *
 * TDD tests for rendering LaTeX mathematical expressions.
 * Features:
 * - Render inline math
 * - Render block/display math
 * - Copy to clipboard
 * - Error handling for invalid LaTeX
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { LaTeXArtifact } from "./LaTeXArtifact";

// Mock KaTeX (the rendering library)
vi.mock("katex", () => ({
  default: {
    renderToString: vi.fn(
      (latex: string, options?: { displayMode?: boolean }) => {
        // Simulate KaTeX throwing on invalid input
        if (latex.includes("\\invalid")) {
          throw new Error("KaTeX parse error: Invalid command");
        }
        const mode = options?.displayMode ? "display" : "inline";
        return `<span class="katex-${mode}">${latex}</span>`;
      },
    ),
  },
}));

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn(() => Promise.resolve()),
};
Object.defineProperty(navigator, "clipboard", {
  value: mockClipboard,
  writable: true,
});

describe("LaTeXArtifact", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("should render LaTeX content", () => {
      render(<LaTeXArtifact content="E = mc^2" />);

      // Check that container is rendered
      expect(screen.getByTestId("latex-artifact")).toBeInTheDocument();
    });

    it("should render inline math by default", () => {
      render(<LaTeXArtifact content="x^2 + y^2 = z^2" />);

      const container = screen.getByTestId("latex-artifact");
      expect(container.innerHTML).toContain("katex-inline");
    });

    it("should render display math when displayMode is true", () => {
      render(
        <LaTeXArtifact
          content="\\int_0^\\infty e^{-x} dx = 1"
          displayMode={true}
        />,
      );

      const container = screen.getByTestId("latex-artifact");
      expect(container.innerHTML).toContain("katex-display");
    });

    it("should apply custom className", () => {
      render(<LaTeXArtifact content="a + b" className="custom-latex" />);

      // className is applied to the outer container, not the latex-artifact div
      const container =
        screen.getByTestId("latex-artifact").parentElement?.parentElement;
      expect(container?.className).toContain("custom-latex");
    });
  });

  describe("Copy Functionality", () => {
    it("should render copy button", () => {
      render(
        <LaTeXArtifact content="x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}" />,
      );

      expect(screen.getByRole("button", { name: /copy/i })).toBeInTheDocument();
    });

    it("should copy raw LaTeX to clipboard when copy is clicked", async () => {
      const content = "x = \\frac{-b \\pm \\sqrt{b^2-4ac}}{2a}";
      render(<LaTeXArtifact content={content} />);

      const copyButton = screen.getByRole("button", { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith(content);
      });
    });

    it("should show success message after copying", async () => {
      render(<LaTeXArtifact content="\\sum_{i=1}^n i" />);

      const copyButton = screen.getByRole("button", { name: /copy/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(screen.getByText(/copied/i)).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error message for invalid LaTeX", () => {
      render(<LaTeXArtifact content="\\invalid{command}" />);

      expect(screen.getByText(/error/i)).toBeInTheDocument();
    });

    it("should still display raw LaTeX when there is an error", () => {
      render(<LaTeXArtifact content="\\invalid{command}" />);

      expect(screen.getByText(/\\invalid\{command\}/)).toBeInTheDocument();
    });

    it("should allow retry after error", () => {
      const { rerender } = render(
        <LaTeXArtifact content="\\invalid{command}" />,
      );

      // Verify error is shown
      expect(screen.getByText(/error/i)).toBeInTheDocument();

      // Fix the content
      rerender(<LaTeXArtifact content="x + y" />);

      // Error should be gone
      expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
    });
  });

  describe("Common LaTeX Expressions", () => {
    it("should render fractions", () => {
      render(<LaTeXArtifact content="\\frac{1}{2}" />);
      expect(screen.getByTestId("latex-artifact").innerHTML).toContain(
        "\\frac{1}{2}",
      );
    });

    it("should render square roots", () => {
      render(<LaTeXArtifact content="\\sqrt{x}" />);
      expect(screen.getByTestId("latex-artifact").innerHTML).toContain(
        "\\sqrt{x}",
      );
    });

    it("should render summations", () => {
      render(<LaTeXArtifact content="\\sum_{i=1}^{n} i^2" />);
      expect(screen.getByTestId("latex-artifact").innerHTML).toContain("\\sum");
    });

    it("should render integrals", () => {
      render(<LaTeXArtifact content="\\int_a^b f(x) dx" />);
      expect(screen.getByTestId("latex-artifact").innerHTML).toContain("\\int");
    });

    it("should render matrices", () => {
      render(
        <LaTeXArtifact content="\\begin{pmatrix} a & b \\\\ c & d \\end{pmatrix}" />,
      );
      expect(screen.getByTestId("latex-artifact").innerHTML).toContain(
        "pmatrix",
      );
    });
  });

  describe("Accessibility", () => {
    it("should have role presentation for decorative math", () => {
      render(<LaTeXArtifact content="x^2" />);

      const container = screen.getByTestId("latex-artifact");
      expect(container).toHaveAttribute("role", "img");
    });

    it("should have aria-label with LaTeX content", () => {
      const content = "E = mc^2";
      render(<LaTeXArtifact content={content} />);

      const container = screen.getByTestId("latex-artifact");
      expect(container).toHaveAttribute(
        "aria-label",
        expect.stringContaining("math"),
      );
    });
  });

  describe("Title", () => {
    it("should render title when provided", () => {
      render(<LaTeXArtifact content="x^2" title="Quadratic formula" />);

      expect(screen.getByText("Quadratic formula")).toBeInTheDocument();
    });

    it("should not render title section when not provided", () => {
      render(<LaTeXArtifact content="x^2" />);

      expect(screen.queryByTestId("latex-title")).not.toBeInTheDocument();
    });
  });

  describe("Zoom Controls", () => {
    it("should have zoom in button", () => {
      render(<LaTeXArtifact content="x^2" />);
      expect(screen.getByLabelText("Zoom in")).toBeInTheDocument();
    });

    it("should have zoom out button", () => {
      render(<LaTeXArtifact content="x^2" />);
      expect(screen.getByLabelText("Zoom out")).toBeInTheDocument();
    });

    it("should have reset zoom button", () => {
      render(<LaTeXArtifact content="x^2" />);
      expect(screen.getByLabelText("Reset zoom")).toBeInTheDocument();
    });

    it("should display zoom level", () => {
      render(<LaTeXArtifact content="x^2" />);
      expect(screen.getByText("100%")).toBeInTheDocument();
    });

    it("should increase zoom when zoom in clicked", async () => {
      render(<LaTeXArtifact content="x^2" />);
      const zoomIn = screen.getByLabelText("Zoom in");
      fireEvent.click(zoomIn);
      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });
  });

  describe("Fullscreen", () => {
    it("should have fullscreen toggle button", () => {
      render(<LaTeXArtifact content="x^2" />);
      expect(screen.getByLabelText("Toggle fullscreen")).toBeInTheDocument();
    });

    it("should toggle fullscreen mode", async () => {
      render(<LaTeXArtifact content="x^2" />);
      const container = screen
        .getByTestId("latex-artifact")
        .closest(".rounded-lg");
      expect(container).not.toHaveClass("fixed");

      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));
      await waitFor(() => {
        const updatedContainer = screen
          .getByTestId("latex-artifact")
          .closest("div[class*='fixed']");
        expect(updatedContainer).toBeInTheDocument();
      });
    });
  });

  describe("Keyboard Shortcuts", () => {
    it("should zoom in with + key", async () => {
      render(<LaTeXArtifact content="x^2" />);

      const container = screen.getByTestId("latex-container");
      fireEvent.keyDown(container, { key: "+" });

      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });
    });

    it("should zoom out with - key", async () => {
      render(<LaTeXArtifact content="x^2" />);

      const container = screen.getByTestId("latex-container");
      fireEvent.keyDown(container, { key: "-" });

      await waitFor(() => {
        expect(screen.getByText("80%")).toBeInTheDocument();
      });
    });

    it("should reset zoom with 0 key", async () => {
      render(<LaTeXArtifact content="x^2" />);

      // First zoom in
      fireEvent.click(screen.getByLabelText("Zoom in"));
      await waitFor(() => {
        expect(screen.getByText("125%")).toBeInTheDocument();
      });

      // Then reset with 0
      const container = screen.getByTestId("latex-container");
      fireEvent.keyDown(container, { key: "0" });

      await waitFor(() => {
        expect(screen.getByText("100%")).toBeInTheDocument();
      });
    });

    it("should exit fullscreen with Escape key", async () => {
      render(<LaTeXArtifact content="x^2" />);

      // Enter fullscreen
      fireEvent.click(screen.getByLabelText("Toggle fullscreen"));
      await waitFor(() => {
        const container = screen.getByTestId("latex-container");
        expect(container.classList.contains("fixed")).toBe(true);
      });

      // Exit with Escape
      const container = screen.getByTestId("latex-container");
      fireEvent.keyDown(container, { key: "Escape" });

      await waitFor(() => {
        expect(
          screen.getByTestId("latex-container").classList.contains("fixed"),
        ).toBe(false);
      });
    });

    it("should be focusable for keyboard navigation", async () => {
      render(<LaTeXArtifact content="x^2" />);

      const container = screen.getByTestId("latex-container");
      expect(container).toHaveAttribute("tabIndex", "0");
    });
  });

  describe("Touch Gestures", () => {
    it("should handle pinch-to-zoom with two fingers", async () => {
      render(<LaTeXArtifact content="x^2" />);

      const container = screen.getByTestId("latex-container");

      // Initial zoom is 100%
      expect(screen.getByText("100%")).toBeInTheDocument();

      // Simulate pinch start (two fingers)
      fireEvent.touchStart(container, {
        touches: [
          { clientX: 100, clientY: 100, identifier: 0 },
          { clientX: 200, clientY: 200, identifier: 1 },
        ],
      });

      // Simulate pinch out (fingers moving apart to zoom in)
      fireEvent.touchMove(container, {
        touches: [
          { clientX: 50, clientY: 50, identifier: 0 },
          { clientX: 250, clientY: 250, identifier: 1 },
        ],
      });

      fireEvent.touchEnd(container);

      // Zoom should have increased
      await waitFor(() => {
        const zoomText = screen.getByText(/\d+%/);
        const zoomValue = parseInt(zoomText.textContent || "100");
        expect(zoomValue).toBeGreaterThan(100);
      });
    });
  });
});

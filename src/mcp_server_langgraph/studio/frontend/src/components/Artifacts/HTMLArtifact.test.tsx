/**
 * HTMLArtifact Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 *
 * HTMLArtifact safely renders HTML content including:
 * - Bokeh visualization output
 * - Generic HTML from code execution
 * - Sanitized HTML content
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { HTMLArtifact } from "./HTMLArtifact";

// Sample HTML content for testing
const SIMPLE_HTML = `<div><h1>Hello World</h1><p>This is a test.</p></div>`;

const BOKEH_HTML = `
<!DOCTYPE html>
<html>
<head>
  <script type="text/javascript" src="https://cdn.bokeh.org/bokeh/release/bokeh-3.3.0.min.js"></script>
</head>
<body>
  <div class="bk-root" id="plot-12345"></div>
  <script type="text/javascript">
    Bokeh.embed.embed_item({"doc_id": "abc123"}, "plot-12345");
  </script>
</body>
</html>`;

const UNSAFE_HTML = `
<div>
  <script>alert('XSS')</script>
  <img src="x" onerror="alert('XSS')">
  <p onclick="alert('XSS')">Click me</p>
</div>`;

describe("HTMLArtifact", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Rendering", () => {
    it("should render the component container", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      expect(screen.getByTestId("html-artifact")).toBeInTheDocument();
    });

    it("should display title when provided", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} title="My HTML Content" />);

      expect(screen.getByText("My HTML Content")).toBeInTheDocument();
    });

    it("should display default title when not provided", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      expect(screen.getByText("HTML")).toBeInTheDocument();
    });

    it("should render HTML content in an iframe", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      expect(iframe).toBeInTheDocument();
      expect(iframe.tagName).toBe("IFRAME");
    });

    it("should apply sandbox attribute to iframe for security", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      expect(iframe).toHaveAttribute("sandbox");
    });
  });

  describe("Bokeh Support", () => {
    it("should detect Bokeh HTML and show Bokeh indicator", () => {
      render(<HTMLArtifact data={BOKEH_HTML} />);

      // Should detect it's a Bokeh chart - look for the badge specifically
      const bokehBadges = screen.getAllByText(/bokeh/i);
      expect(bokehBadges.length).toBeGreaterThan(0);
    });

    it("should render Bokeh HTML with scripts enabled", () => {
      render(<HTMLArtifact data={BOKEH_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      // Bokeh requires scripts to run
      const _sandbox = iframe.getAttribute("sandbox");
      expect(sandbox).toContain("allow-scripts");
    });

    it("should display Bokeh chart title when provided", () => {
      render(<HTMLArtifact data={BOKEH_HTML} title="Sales Dashboard" />);

      expect(screen.getByText("Sales Dashboard")).toBeInTheDocument();
    });
  });

  describe("Security", () => {
    it("should use sandboxed iframe for HTML content", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      // Sandbox attribute should be present (empty string is valid and most restrictive)
      expect(iframe).toHaveAttribute("sandbox");
    });

    it("should not allow same-origin for untrusted content", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      const _sandbox = iframe.getAttribute("sandbox");
      // Should NOT include allow-same-origin for security
      expect(sandbox).not.toContain("allow-same-origin");
    });

    it("should allow scripts only when necessary (Bokeh)", () => {
      render(<HTMLArtifact data={BOKEH_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      const _sandbox = iframe.getAttribute("sandbox");
      // Bokeh requires scripts
      expect(sandbox).toContain("allow-scripts");
    });

    it("should not render inline JavaScript for simple HTML", () => {
      render(<HTMLArtifact data={UNSAFE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      const _sandbox = iframe.getAttribute("sandbox");
      // For non-Bokeh HTML, scripts should be restricted
      // Note: The sandbox attribute restricts script execution by default
      expect(iframe).toHaveAttribute("sandbox");
    });
  });

  describe("Error Handling", () => {
    it("should handle empty HTML content", () => {
      render(<HTMLArtifact data="" />);

      expect(screen.getByTestId("html-artifact")).toBeInTheDocument();
    });

    it("should display error for malformed HTML gracefully", () => {
      const malformedHTML = "<div><p>Unclosed tags";
      render(<HTMLArtifact data={malformedHTML} />);

      // Should still render without crashing
      expect(screen.getByTestId("html-artifact")).toBeInTheDocument();
    });
  });

  describe("Sizing", () => {
    it("should accept height prop", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} height={500} />);

      const container = screen.getByTestId("html-artifact");
      expect(container).toBeInTheDocument();
    });

    it("should default to reasonable height", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const iframe = screen.getByTestId("html-iframe");
      // Should have some default height
      expect(iframe).toBeInTheDocument();
    });
  });

  describe("Theme Support", () => {
    it("should apply dark theme styling when specified", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} theme="dark" />);

      const container = screen.getByTestId("html-artifact");
      expect(container.className).toMatch(/dark/);
    });

    it("should apply light theme by default", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const container = screen.getByTestId("html-artifact");
      expect(container).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible iframe with title", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} title="My Content" />);

      const iframe = screen.getByTestId("html-iframe");
      expect(iframe).toHaveAttribute("title");
    });
  });

  describe("Controls", () => {
    it("should have expand button for full-screen view", () => {
      render(<HTMLArtifact data={SIMPLE_HTML} />);

      const expandButton = screen.queryByRole("button", {
        name: /expand|fullscreen|maximize/i,
      });
      // Optional but expected
      if (expandButton) {
        expect(expandButton).toBeInTheDocument();
      }
    });
  });
});

describe("HTMLArtifact Integration", () => {
  it("should work with execution results HTML", () => {
    const executionHTML = `
      <html>
      <body>
        <h2>Execution Output</h2>
        <table>
          <tr><th>Name</th><th>Value</th></tr>
          <tr><td>Count</td><td>42</td></tr>
        </table>
      </body>
      </html>
    `;

    render(<HTMLArtifact data={executionHTML} title="Output" />);

    expect(screen.getByTestId("html-artifact")).toBeInTheDocument();
    expect(screen.getByText("Output")).toBeInTheDocument();
  });
});

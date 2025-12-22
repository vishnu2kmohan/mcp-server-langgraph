/**
 * ExecutableCanvas Tests - Phase 2
 *
 * Tests for sandboxed code execution canvas.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { ExecutableCanvas, type ExecutableConfig } from "./ExecutableCanvas";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockReactConfig: ExecutableConfig = {
  id: "exec-1",
  language: "jsx",
  code: `function App() {
  return <h1>Hello World</h1>;
}`,
  title: "React Component",
};

const mockHtmlConfig: ExecutableConfig = {
  id: "exec-2",
  language: "html",
  code: `<div class="greeting">Hello HTML</div>`,
  title: "HTML Preview",
};

const mockJsConfig: ExecutableConfig = {
  id: "exec-3",
  language: "javascript",
  code: `console.log("Hello JavaScript");`,
  title: "JavaScript Runner",
};

// =============================================================================
// Tests
// =============================================================================

describe("ExecutableCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render canvas container", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("executable-canvas")).toBeInTheDocument();
    });

    it("should display canvas title", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByText("React Component")).toBeInTheDocument();
    });

    it("should render code editor", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("code-editor")).toBeInTheDocument();
    });

    it("should render preview area", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("preview-area")).toBeInTheDocument();
    });
  });

  describe("Language Support", () => {
    it("should show JSX language indicator", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByText("jsx")).toBeInTheDocument();
    });

    it("should show HTML language indicator", () => {
      render(<ExecutableCanvas config={mockHtmlConfig} />);
      expect(screen.getByText("html")).toBeInTheDocument();
    });

    it("should show JavaScript language indicator", () => {
      render(<ExecutableCanvas config={mockJsConfig} />);
      expect(screen.getByText("javascript")).toBeInTheDocument();
    });
  });

  describe("Code Editing", () => {
    it("should display initial code", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("code-editor")).toHaveTextContent(
        "function App()",
      );
    });

    it("should call onChange when code is edited", () => {
      const onChange = vi.fn();
      render(<ExecutableCanvas config={mockReactConfig} onChange={onChange} />);
      const editor = screen.getByTestId("code-input");
      fireEvent.change(editor, { target: { value: "new code" } });
      expect(onChange).toHaveBeenCalledWith("new code");
    });
  });

  describe("Execution", () => {
    it("should show run button", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("run-button")).toBeInTheDocument();
    });

    it("should call onRun when run button clicked", () => {
      const onRun = vi.fn();
      render(<ExecutableCanvas config={mockReactConfig} onRun={onRun} />);
      fireEvent.click(screen.getByTestId("run-button"));
      expect(onRun).toHaveBeenCalledWith(mockReactConfig.code);
    });

    it("should show stop button when running", () => {
      render(<ExecutableCanvas config={mockReactConfig} isRunning />);
      expect(screen.getByTestId("stop-button")).toBeInTheDocument();
    });

    it("should call onStop when stop button clicked", () => {
      const onStop = vi.fn();
      render(
        <ExecutableCanvas config={mockReactConfig} isRunning onStop={onStop} />,
      );
      fireEvent.click(screen.getByTestId("stop-button"));
      expect(onStop).toHaveBeenCalled();
    });
  });

  describe("Console Output", () => {
    it("should show console panel when there is output", () => {
      render(
        <ExecutableCanvas
          config={mockJsConfig}
          consoleOutput={["Hello JavaScript"]}
        />,
      );
      expect(screen.getByTestId("console-panel")).toBeInTheDocument();
    });

    it("should display console messages", () => {
      render(
        <ExecutableCanvas
          config={mockJsConfig}
          consoleOutput={["Log 1", "Log 2"]}
        />,
      );
      expect(screen.getByText("Log 1")).toBeInTheDocument();
      expect(screen.getByText("Log 2")).toBeInTheDocument();
    });

    it("should show clear console button", () => {
      render(
        <ExecutableCanvas
          config={mockJsConfig}
          consoleOutput={["Some output"]}
        />,
      );
      expect(screen.getByTestId("clear-console")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message", () => {
      render(
        <ExecutableCanvas
          config={mockReactConfig}
          error="Syntax error at line 1"
        />,
      );
      expect(screen.getByText("Syntax error at line 1")).toBeInTheDocument();
    });

    it("should show error panel with error styling", () => {
      render(
        <ExecutableCanvas config={mockReactConfig} error="Syntax error" />,
      );
      expect(screen.getByTestId("error-panel")).toHaveClass("error");
    });
  });

  describe("Preview", () => {
    it("should render preview in sandbox iframe", () => {
      render(<ExecutableCanvas config={mockHtmlConfig} />);
      const iframe = screen.getByTestId("sandbox-iframe");
      expect(iframe).toBeInTheDocument();
      expect(iframe).toHaveAttribute("sandbox");
    });

    it("should show preview loading state", () => {
      render(<ExecutableCanvas config={mockHtmlConfig} isPreviewLoading />);
      expect(screen.getByTestId("preview-loading")).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should show split view by default", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByTestId("split-view")).toBeInTheDocument();
    });

    it("should toggle to code-only view", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      fireEvent.click(screen.getByTestId("view-code-only"));
      expect(screen.getByTestId("code-only-view")).toBeInTheDocument();
    });

    it("should toggle to preview-only view", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      fireEvent.click(screen.getByTestId("view-preview-only"));
      expect(screen.getByTestId("preview-only-view")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    // Note: axe-core has issues with iframes in JSDOM, so we exclude them
    const axeOptions = {
      rules: {
        // Skip rules that require iframe analysis
        "frame-title": { enabled: false },
        "frame-tested": { enabled: false },
      },
    };

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ExecutableCanvas config={mockReactConfig} />,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when running", async () => {
      const { container } = render(
        <ExecutableCanvas config={mockReactConfig} isRunning />,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with error", async () => {
      const { container } = render(
        <ExecutableCanvas config={mockReactConfig} error="Syntax error" />,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible region role", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(screen.getByRole("region")).toBeInTheDocument();
    });

    it("should have aria-label for canvas", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      expect(
        screen.getByRole("region", { name: /React Component/i }),
      ).toBeInTheDocument();
    });

    it("should have aria-label on code editor textarea", () => {
      render(<ExecutableCanvas config={mockReactConfig} />);
      const codeInput = screen.getByTestId("code-input");
      expect(codeInput).toHaveAttribute(
        "aria-label",
        "jsx code editor for React Component",
      );
    });
  });
});

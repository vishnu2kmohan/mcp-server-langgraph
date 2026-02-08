/**
 * ExecutableCanvas Tests - Phase 2
 *
 * Tests for sandboxed code execution canvas.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { ExecutableCanvas, type ExecutableConfig } from "./ExecutableCanvas";

import { TestProvider } from "@/test-utils";

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

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render canvas container", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("executable-canvas")).toBeInTheDocument();
    });

    it("should display canvas title", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByText("React Component")).toBeInTheDocument();
    });

    it("should render code editor", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("code-editor")).toBeInTheDocument();
    });

    it("should render preview area", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("preview-area")).toBeInTheDocument();
    });
  });

  describe("Language Support", () => {
    it("should show JSX language indicator", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByText("jsx")).toBeInTheDocument();
    });

    it("should show HTML language indicator", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockHtmlConfig} />
        </TestProvider>,
      );
      expect(screen.getByText("html")).toBeInTheDocument();
    });

    it("should show JavaScript language indicator", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockJsConfig} />
        </TestProvider>,
      );
      expect(screen.getByText("javascript")).toBeInTheDocument();
    });
  });

  describe("Code Editing", () => {
    it("should display initial code", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("code-editor")).toHaveTextContent(
        "function App()",
      );
    });

    it("should call onChange when code is edited", () => {
      const onChange = vi.fn();
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} onChange={onChange} />
        </TestProvider>,
      );
      const editor = screen.getByTestId("code-input");
      fireEvent.change(editor, { target: { value: "new code" } });
      expect(onChange).toHaveBeenCalledWith("new code");
    });
  });

  describe("Execution", () => {
    it("should show run button", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("run-button")).toBeInTheDocument();
    });

    it("should call onRun when run button clicked", () => {
      const onRun = vi.fn();
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} onRun={onRun} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("run-button"));
      expect(onRun).toHaveBeenCalledWith(mockReactConfig.code);
    });

    it("should show stop button when running", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} isRunning />
        </TestProvider>,
      );
      expect(screen.getByTestId("stop-button")).toBeInTheDocument();
    });

    it("should call onStop when stop button clicked", () => {
      const onStop = vi.fn();
      render(
        <TestProvider>
          <ExecutableCanvas
            config={mockReactConfig}
            isRunning
            onStop={onStop}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("stop-button"));
      expect(onStop).toHaveBeenCalled();
    });
  });

  describe("Console Output", () => {
    it("should show console panel when there is output", () => {
      render(
        <TestProvider>
          <ExecutableCanvas
            config={mockJsConfig}
            consoleOutput={["Hello JavaScript"]}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("console-panel")).toBeInTheDocument();
    });

    it("should display console messages", () => {
      render(
        <TestProvider>
          <ExecutableCanvas
            config={mockJsConfig}
            consoleOutput={["Log 1", "Log 2"]}
          />
        </TestProvider>,
      );
      expect(screen.getByText("Log 1")).toBeInTheDocument();
      expect(screen.getByText("Log 2")).toBeInTheDocument();
    });

    it("should show clear console button", () => {
      render(
        <TestProvider>
          <ExecutableCanvas
            config={mockJsConfig}
            consoleOutput={["Some output"]}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("clear-console")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error message", () => {
      render(
        <TestProvider>
          <ExecutableCanvas
            config={mockReactConfig}
            error="Syntax error at line 1"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Syntax error at line 1")).toBeInTheDocument();
    });

    it("should show error panel with error styling", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} error="Syntax error" />
        </TestProvider>,
      );
      expect(screen.getByTestId("error-panel")).toHaveClass("error");
    });
  });

  describe("Preview", () => {
    it("should render preview in sandbox iframe", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockHtmlConfig} />
        </TestProvider>,
      );
      const iframe = screen.getByTestId("sandbox-iframe");
      expect(iframe).toBeInTheDocument();
      expect(iframe).toHaveAttribute("sandbox");
    });

    it("should show preview loading state", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockHtmlConfig} isPreviewLoading />
        </TestProvider>,
      );
      expect(screen.getByTestId("preview-loading")).toBeInTheDocument();
    });
  });

  describe("Layout", () => {
    it("should show split view by default", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByTestId("split-view")).toBeInTheDocument();
    });

    it("should toggle to code-only view", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("view-code-only"));
      expect(screen.getByTestId("code-only-view")).toBeInTheDocument();
    });

    it("should toggle to preview-only view", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
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
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations when running", async () => {
      const { container } = render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} isRunning />
        </TestProvider>,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with error", async () => {
      const { container } = render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} error="Syntax error" />
        </TestProvider>,
      );
      // Remove iframe from container before axe analysis (JSDOM limitation)
      const iframe = container.querySelector("iframe");
      if (iframe) iframe.remove();
      const results = await axe(container, axeOptions);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible region role", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(screen.getByRole("region")).toBeInTheDocument();
    });

    it("should have aria-label for canvas", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("region", { name: /React Component/i }),
      ).toBeInTheDocument();
    });

    it("should have aria-label on code editor textarea", () => {
      render(
        <TestProvider>
          <ExecutableCanvas config={mockReactConfig} />
        </TestProvider>,
      );
      const codeInput = screen.getByTestId("code-input");
      expect(codeInput).toHaveAttribute(
        "aria-label",
        "jsx code editor for React Component",
      );
    });
  });
});

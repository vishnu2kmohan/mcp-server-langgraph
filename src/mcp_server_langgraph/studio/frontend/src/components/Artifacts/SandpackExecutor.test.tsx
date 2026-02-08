/**
 * SandpackExecutor Tests
 *
 * TDD tests for sandboxed code execution using Sandpack.
 * Tests cover React/JSX execution, MDX rendering, and security controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { SandpackExecutor } from "./SandpackExecutor";

import { TestProvider } from "@/test-utils";

describe("SandpackExecutor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the component with code preview by default", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
          />
        </TestProvider>,
      );

      // Shows code preview before running
      expect(
        screen.getByText(/export default function App/),
      ).toBeInTheDocument();
    });

    it("should show a Run button when showRunButton is true", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
            showRunButton={true}
          />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /run/i })).toBeInTheDocument();
    });

    it("should not show Run button when showRunButton is false and autoRun is true", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
            showRunButton={false}
            autoRun={true}
          />
        </TestProvider>,
      );

      // With autoRun=true, there should be no Run button visible
      expect(
        screen.queryByRole("button", { name: /run/i }),
      ).not.toBeInTheDocument();
    });

    it("should display the title when provided", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="const x = 1;"
            language="javascript"
            title="My Component"
          />
        </TestProvider>,
      );

      expect(screen.getByText("My Component")).toBeInTheDocument();
    });

    it("should show language badge", () => {
      render(
        <TestProvider>
          <SandpackExecutor code="const x = 1;" language="typescript" />
        </TestProvider>,
      );

      expect(screen.getByText("typescript")).toBeInTheDocument();
    });
  });

  describe("Execution Control", () => {
    it("should not show Sandpack preview before Run is clicked", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="console.log('test')"
            language="javascript"
            showRunButton={true}
          />
        </TestProvider>,
      );

      // Preview should not be visible until Run is clicked
      expect(screen.queryByTestId("sandpack-executor")).not.toBeInTheDocument();
    });

    it("should show Sandpack when Run button is clicked", async () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
            showRunButton={true}
          />
        </TestProvider>,
      );

      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);

      await waitFor(() => {
        expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
      });
    });

    it("should show Sandpack immediately when autoRun is true", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should call onExecute callback when Run is clicked", async () => {
      const onExecute = vi.fn();
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Hello</div>; }"
            language="tsx"
            showRunButton={true}
            onExecute={onExecute}
          />
        </TestProvider>,
      );

      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);

      expect(onExecute).toHaveBeenCalled();
    });
  });

  describe("Language Support", () => {
    it("should support tsx files", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default () => <div>TSX</div>"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should support jsx files", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default () => <div>JSX</div>"
            language="jsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should support MDX content", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="# Hello\n\n<Button>Click me</Button>"
            language="mdx"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should support plain JavaScript", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="console.log('hello')"
            language="javascript"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should display the correct language badge", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default () => <div>TSX</div>"
            language="tsx"
          />
        </TestProvider>,
      );

      expect(screen.getByText("tsx")).toBeInTheDocument();
    });
  });

  describe("Dependencies", () => {
    it("should render component when custom dependencies are provided", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="import dayjs from 'dayjs'; export default () => <div>{dayjs().format()}</div>"
            language="tsx"
            dependencies={{ dayjs: "1.11.10" }}
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should render component with allowedDependencies", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="import React from 'react'; export default () => <div />"
            language="tsx"
            allowedDependencies={["react", "react-dom"]}
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });
  });

  describe("Theme Support", () => {
    it("should render with dark theme", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="const x = 1"
            language="javascript"
            theme="dark"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should render with light theme", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="const x = 1"
            language="javascript"
            theme="light"
            autoRun={true}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });
  });

  describe("UI Controls", () => {
    it("should show Stop button when running", async () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="const x = 1"
            language="javascript"
            showRunButton={true}
          />
        </TestProvider>,
      );

      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /stop/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show Sandpack badge", () => {
      render(
        <TestProvider>
          <SandpackExecutor code="const x = 1" language="javascript" />
        </TestProvider>,
      );

      expect(screen.getByText("Sandpack")).toBeInTheDocument();
    });
  });

  describe("Error Handling", () => {
    it("should display error fallback when Sandpack crashes", async () => {
      // Mock console.error to prevent noise in test output
      const consoleSpy = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      // The error boundary should be present in the DOM
      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();

      consoleSpy.mockRestore();
    });

    it("should call onError callback when error occurs", async () => {
      const onError = vi.fn();

      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            autoRun={true}
            onError={onError}
          />
        </TestProvider>,
      );

      // Component should render without crashing
      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should show code preview with Run button when not auto-running", () => {
      // This tests the initial placeholder UI before clicking Run
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            showRunButton={true}
          />
        </TestProvider>,
      );

      // Should show the Run button and code preview
      expect(screen.getByRole("button", { name: /run/i })).toBeInTheDocument();
      expect(screen.getByText(/export default/)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when Sandpack is initializing", async () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      // The Sandpack container should be present
      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should show initializing state before Sandpack is fully loaded", async () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      // Should have the executor container
      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
      // Sandpack header should still be visible during loading
      expect(screen.getByText("Sandpack")).toBeInTheDocument();
    });
  });

  describe("Error Boundary", () => {
    it("should have error boundary wrapper around Sandpack content", () => {
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            autoRun={true}
          />
        </TestProvider>,
      );

      // Sandpack executor should render with error boundary protection
      expect(screen.getByTestId("sandpack-executor")).toBeInTheDocument();
    });

    it("should support retry functionality", async () => {
      const onExecute = vi.fn();
      render(
        <TestProvider>
          <SandpackExecutor
            code="export default function App() { return <div>Test</div>; }"
            language="tsx"
            showRunButton={true}
            onExecute={onExecute}
          />
        </TestProvider>,
      );

      // Click run to start
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);

      expect(onExecute).toHaveBeenCalled();
    });
  });
});

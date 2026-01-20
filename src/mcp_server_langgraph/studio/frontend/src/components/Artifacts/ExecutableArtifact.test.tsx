/**
 * ExecutableArtifact Tests
 *
 * TDD tests for executable code artifact component with sandbox execution.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { ExecutableArtifact } from "./ExecutableArtifact";

describe("ExecutableArtifact", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  const pythonCode = `print("Hello, World!")`;
  const defaultConfig = { language: "python" };

  describe("rendering", () => {
    it("should render code block with language label", () => {
      render(<ExecutableArtifact data={pythonCode} config={defaultConfig} />);
      expect(screen.getByText("python")).toBeInTheDocument();
    });

    it("should render the source code", () => {
      render(<ExecutableArtifact data={pythonCode} config={defaultConfig} />);
      expect(screen.getByText(/print.*Hello, World!/)).toBeInTheDocument();
    });

    it("should render run button", () => {
      render(<ExecutableArtifact data={pythonCode} config={defaultConfig} />);
      expect(screen.getByRole("button", { name: /run/i })).toBeInTheDocument();
    });

    it("should render title if provided", () => {
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          title="My Script"
        />,
      );
      expect(screen.getByText("My Script")).toBeInTheDocument();
    });
  });

  describe("execution", () => {
    it("should show loading state when running", () => {
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          requireConfirmation={false}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      expect(screen.getByText(/running/i)).toBeInTheDocument();
    });

    it("should display execution result when provided", () => {
      const result = {
        stdout: "Hello, World!\n",
        stderr: "",
        exitCode: 0,
        executionTime: 150,
      };
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          result={result}
        />,
      );
      expect(screen.getByText("Hello, World!")).toBeInTheDocument();
      expect(screen.getByText(/exit code: 0/i)).toBeInTheDocument();
    });

    it("should display stderr in error style", () => {
      const result = {
        stdout: "",
        stderr: "Error: Something went wrong",
        exitCode: 1,
      };
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          result={result}
        />,
      );
      const errorOutput = screen.getByText(/Something went wrong/);
      expect(errorOutput).toBeInTheDocument();
      expect(errorOutput.closest("div")).toHaveClass("text-error-10");
    });

    it("should show execution time when available", () => {
      const result = {
        stdout: "Done",
        stderr: "",
        exitCode: 0,
        executionTime: 250,
      };
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          result={result}
        />,
      );
      expect(screen.getByText(/250ms/)).toBeInTheDocument();
    });
  });

  describe("runtime options", () => {
    it("should display runtime type when configured", () => {
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={{ ...defaultConfig, runtime: "docker" }}
        />,
      );
      expect(screen.getByText(/docker/i)).toBeInTheDocument();
    });

    it("should display kubernetes runtime", () => {
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={{ ...defaultConfig, runtime: "kubernetes" }}
        />,
      );
      expect(screen.getByText(/kubernetes/i)).toBeInTheDocument();
    });
  });

  describe("callback", () => {
    it("should call onExecute when run button clicked (with confirmation disabled)", () => {
      const onExecute = vi.fn();
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          onExecute={onExecute}
          requireConfirmation={false}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      expect(onExecute).toHaveBeenCalledWith(pythonCode, defaultConfig);
    });
  });

  describe("error handling", () => {
    it("should show error for empty code", () => {
      render(<ExecutableArtifact data="" config={defaultConfig} />);
      expect(screen.getByText(/no code provided/i)).toBeInTheDocument();
    });
  });

  // =========================================================================
  // HITL Confirmation Dialog Tests (Sprint Block 4)
  // =========================================================================

  describe("execution confirmation (HITL)", () => {
    it("should show confirmation dialog by default before execution", () => {
      render(<ExecutableArtifact data={pythonCode} config={defaultConfig} />);
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      // Confirmation dialog should appear
      expect(screen.getByTestId("execution-confirmation")).toBeInTheDocument();
    });

    it("should display warning message in confirmation dialog", () => {
      render(<ExecutableArtifact data={pythonCode} config={defaultConfig} />);
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      expect(
        screen.getByText(/this will execute code in a sandbox/i),
      ).toBeInTheDocument();
    });

    it("should show runtime type in confirmation dialog", () => {
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={{ ...defaultConfig, runtime: "docker" }}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      // Confirmation dialog should show "Docker" in the warning message
      const dialog = screen.getByTestId("execution-confirmation");
      expect(dialog).toHaveTextContent(/Docker/);
    });

    it("should execute code when Confirm button clicked", () => {
      const onExecute = vi.fn();
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          onExecute={onExecute}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      // Click Confirm button
      const confirmButton = screen.getByRole("button", { name: /confirm/i });
      fireEvent.click(confirmButton);
      expect(onExecute).toHaveBeenCalledWith(pythonCode, defaultConfig);
    });

    it("should close dialog and not execute when Cancel clicked", () => {
      const onExecute = vi.fn();
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          onExecute={onExecute}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      // Click Cancel button
      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      fireEvent.click(cancelButton);
      expect(onExecute).not.toHaveBeenCalled();
      expect(
        screen.queryByTestId("execution-confirmation"),
      ).not.toBeInTheDocument();
    });

    it("should skip confirmation when requireConfirmation prop is false", () => {
      const onExecute = vi.fn();
      render(
        <ExecutableArtifact
          data={pythonCode}
          config={defaultConfig}
          onExecute={onExecute}
          requireConfirmation={false}
        />,
      );
      const runButton = screen.getByRole("button", { name: /run/i });
      fireEvent.click(runButton);
      // Should execute immediately without confirmation
      expect(
        screen.queryByTestId("execution-confirmation"),
      ).not.toBeInTheDocument();
      expect(onExecute).toHaveBeenCalledWith(pythonCode, defaultConfig);
    });
  });
});

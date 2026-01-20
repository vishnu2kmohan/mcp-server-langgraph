/**
 * WorkflowHeader Tests
 *
 * Tests for the workflow header component with title, actions, and theme toggle.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { WorkflowHeader } from "./WorkflowHeader";

describe("WorkflowHeader", () => {
  const defaultProps = {
    workflowName: "my_workflow",
    onNameChange: vi.fn(),
    isDarkMode: false,
    onToggleDarkMode: vi.fn(),
    onOpenSettings: vi.fn(),
    onOpenHelp: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render the workflow header with title", () => {
      render(<WorkflowHeader {...defaultProps} />);

      expect(screen.getByText("Visual Workflow Builder")).toBeInTheDocument();
    });

    it("should render workflow name input", () => {
      render(<WorkflowHeader {...defaultProps} />);

      const input = screen.getByDisplayValue("my_workflow");
      expect(input).toBeInTheDocument();
    });

    it("should render dark mode toggle button", () => {
      render(<WorkflowHeader {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /switch to dark mode/i }),
      ).toBeInTheDocument();
    });

    it("should render settings button", () => {
      render(<WorkflowHeader {...defaultProps} />);

      expect(
        screen.getByRole("button", { name: /settings/i }),
      ).toBeInTheDocument();
    });

    it("should render help button", () => {
      render(<WorkflowHeader {...defaultProps} />);

      expect(screen.getByRole("button", { name: /help/i })).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onNameChange when workflow name is updated", () => {
      render(<WorkflowHeader {...defaultProps} />);

      const input = screen.getByDisplayValue("my_workflow");
      fireEvent.change(input, { target: { value: "new_workflow" } });

      expect(defaultProps.onNameChange).toHaveBeenCalledWith("new_workflow");
    });

    it("should call onToggleDarkMode when dark mode button is clicked", () => {
      render(<WorkflowHeader {...defaultProps} />);

      const button = screen.getByRole("button", {
        name: /switch to dark mode/i,
      });
      fireEvent.click(button);

      expect(defaultProps.onToggleDarkMode).toHaveBeenCalled();
    });

    it("should call onOpenSettings when settings button is clicked", () => {
      render(<WorkflowHeader {...defaultProps} />);

      const button = screen.getByRole("button", { name: /settings/i });
      fireEvent.click(button);

      expect(defaultProps.onOpenSettings).toHaveBeenCalled();
    });

    it("should call onOpenHelp when help button is clicked", () => {
      render(<WorkflowHeader {...defaultProps} />);

      const button = screen.getByRole("button", { name: /help/i });
      fireEvent.click(button);

      expect(defaultProps.onOpenHelp).toHaveBeenCalled();
    });
  });

  describe("Dark Mode", () => {
    it("should show sun icon when in dark mode", () => {
      render(<WorkflowHeader {...defaultProps} isDarkMode={true} />);

      expect(
        screen.getByRole("button", { name: /switch to light mode/i }),
      ).toBeInTheDocument();
    });

    it("should apply dark mode styles when isDarkMode is true", () => {
      const { container } = render(
        <WorkflowHeader {...defaultProps} isDarkMode={true} />,
      );

      const header = container.querySelector("header");
      expect(header).toHaveClass("bg-neutral-3");
    });

    it("should apply light mode styles when isDarkMode is false", () => {
      const { container } = render(
        <WorkflowHeader {...defaultProps} isDarkMode={false} />,
      );

      const header = container.querySelector("header");
      expect(header).toHaveClass("bg-neutral-1");
    });
  });
});

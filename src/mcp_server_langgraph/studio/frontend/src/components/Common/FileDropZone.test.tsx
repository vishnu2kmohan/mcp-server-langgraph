/**
 * FileDropZone Tests
 *
 * TDD tests for the drag-and-drop file upload component.
 * Tests cover:
 * - Basic rendering
 * - Drag states
 * - File drop handling
 * - File type validation
 * - Accessibility
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { FileDropZone } from "./FileDropZone";

expect.extend(toHaveNoViolations);

describe("FileDropZone", () => {
  const mockOnFilesSelected = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the drop zone", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      expect(screen.getByTestId("file-drop-zone")).toBeInTheDocument();
    });

    it("should display instruction text", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      expect(
        screen.getByText(/drag and drop|drop files here/i),
      ).toBeInTheDocument();
    });

    it("should render file input", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      expect(screen.getByText(/browse files/i)).toBeInTheDocument();
    });
  });

  describe("drag states", () => {
    it("should show normal state initially", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");
      expect(dropZone).not.toHaveAttribute("data-dragging", "true");
    });

    it("should show dragging state on drag enter", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");

      fireEvent.dragEnter(dropZone);
      expect(dropZone).toHaveAttribute("data-dragging", "true");
    });

    it("should remove dragging state on drag leave", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");

      fireEvent.dragEnter(dropZone);
      fireEvent.dragLeave(dropZone);
      expect(dropZone).toHaveAttribute("data-dragging", "false");
    });
  });

  describe("file drop", () => {
    it("should call onFilesSelected when files are dropped", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");

      const file = new File(["content"], "test.txt", { type: "text/plain" });
      const dataTransfer = {
        files: [file],
        items: [{ kind: "file", type: "text/plain", getAsFile: () => file }],
        types: ["Files"],
      };

      fireEvent.drop(dropZone, { dataTransfer });
      expect(mockOnFilesSelected).toHaveBeenCalledWith([file]);
    });

    it("should handle multiple files", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");

      const file1 = new File(["content1"], "test1.txt", { type: "text/plain" });
      const file2 = new File(["content2"], "test2.txt", { type: "text/plain" });
      const dataTransfer = {
        files: [file1, file2],
        items: [
          { kind: "file", type: "text/plain", getAsFile: () => file1 },
          { kind: "file", type: "text/plain", getAsFile: () => file2 },
        ],
        types: ["Files"],
      };

      fireEvent.drop(dropZone, { dataTransfer });
      expect(mockOnFilesSelected).toHaveBeenCalledWith([file1, file2]);
    });
  });

  describe("file input", () => {
    it("should trigger file input on browse click", async () => {
      const user = userEvent.setup();
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);

      const browseButton = screen.getByRole("button", { name: /browse/i });
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;

      // Mock click function
      const clickSpy = vi.spyOn(fileInput, "click");

      await user.click(browseButton);
      expect(clickSpy).toHaveBeenCalled();
    });
  });

  describe("accept types", () => {
    it("should set accept attribute on file input", () => {
      render(
        <FileDropZone onFilesSelected={mockOnFilesSelected} accept="image/*" />,
      );
      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).toHaveAttribute("accept", "image/*");
    });
  });

  describe("multiple files", () => {
    it("should allow multiple files by default", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).toHaveAttribute("multiple");
    });

    it("should respect multiple=false prop", () => {
      render(
        <FileDropZone onFilesSelected={mockOnFilesSelected} multiple={false} />,
      );
      const fileInput = document.querySelector('input[type="file"]');
      expect(fileInput).not.toHaveAttribute("multiple");
    });
  });

  describe("disabled state", () => {
    it("should be disabled when disabled prop is true", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} disabled />);
      const dropZone = screen.getByTestId("file-drop-zone");
      expect(dropZone).toHaveAttribute("aria-disabled", "true");
    });

    it("should not respond to drops when disabled", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} disabled />);
      const dropZone = screen.getByTestId("file-drop-zone");

      const file = new File(["content"], "test.txt", { type: "text/plain" });
      const dataTransfer = {
        files: [file],
        items: [{ kind: "file", type: "text/plain", getAsFile: () => file }],
        types: ["Files"],
      };

      fireEvent.drop(dropZone, { dataTransfer });
      expect(mockOnFilesSelected).not.toHaveBeenCalled();
    });
  });

  describe("custom children", () => {
    it("should render custom children", () => {
      render(
        <FileDropZone onFilesSelected={mockOnFilesSelected}>
          <div data-testid="custom-content">Custom drop zone content</div>
        </FileDropZone>,
      );
      expect(screen.getByTestId("custom-content")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <FileDropZone onFilesSelected={mockOnFilesSelected} />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have accessible role", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");
      expect(dropZone).toHaveAttribute("role", "region");
    });

    it("should have accessible label", () => {
      render(<FileDropZone onFilesSelected={mockOnFilesSelected} />);
      const dropZone = screen.getByTestId("file-drop-zone");
      expect(dropZone).toHaveAttribute("aria-label");
    });
  });
});

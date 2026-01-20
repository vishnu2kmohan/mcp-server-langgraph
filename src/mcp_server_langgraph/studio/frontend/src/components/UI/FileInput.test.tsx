/**
 * FileInput Component Tests
 *
 * TDD: Tests written FIRST to define expected behavior.
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { FileInput } from "./FileInput";

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("FileInput", () => {
  describe("rendering", () => {
    it("renders a file input", () => {
      render(<FileInput onChange={() => {}} />);
      expect(screen.getByTestId("file-input")).toBeInTheDocument();
    });

    it("renders with label", () => {
      render(<FileInput onChange={() => {}} label="Upload file" />);
      expect(screen.getByText("Upload file")).toBeInTheDocument();
    });

    it("renders with helper text", () => {
      render(<FileInput onChange={() => {}} helperText="Max 5MB" />);
      expect(screen.getByText("Max 5MB")).toBeInTheDocument();
    });

    it("shows drag and drop zone by default", () => {
      render(<FileInput onChange={() => {}} />);
      expect(screen.getByText(/drag.*drop/i)).toBeInTheDocument();
    });

    it("renders compact variant without drag zone", () => {
      render(<FileInput onChange={() => {}} variant="compact" />);
      expect(screen.queryByText(/drag.*drop/i)).not.toBeInTheDocument();
    });
  });

  describe("file selection", () => {
    it("calls onChange when file is selected", () => {
      const onChange = vi.fn();
      render(<FileInput onChange={onChange} />);

      const input = screen.getByTestId("file-input");
      const file = new File(["content"], "test.txt", { type: "text/plain" });

      fireEvent.change(input, { target: { files: [file] } });

      expect(onChange).toHaveBeenCalledWith([file]);
    });

    it("supports multiple file selection", () => {
      const onChange = vi.fn();
      render(<FileInput onChange={onChange} multiple />);

      const input = screen.getByTestId("file-input");
      expect(input).toHaveAttribute("multiple");

      const files = [
        new File(["content1"], "test1.txt", { type: "text/plain" }),
        new File(["content2"], "test2.txt", { type: "text/plain" }),
      ];

      fireEvent.change(input, { target: { files } });

      expect(onChange).toHaveBeenCalledWith(files);
    });

    it("respects accept attribute for file types", () => {
      render(<FileInput onChange={() => {}} accept=".pdf,.doc" />);
      const input = screen.getByTestId("file-input");
      expect(input).toHaveAttribute("accept", ".pdf,.doc");
    });
  });

  describe("disabled state", () => {
    it("can be disabled", () => {
      render(<FileInput onChange={() => {}} disabled />);
      const input = screen.getByTestId("file-input");
      expect(input).toBeDisabled();
    });

    it("shows disabled styling", () => {
      render(<FileInput onChange={() => {}} disabled />);
      const container = screen.getByTestId("file-input-container");
      expect(container).toHaveClass("opacity-50");
    });
  });

  describe("file display", () => {
    it("shows selected file name", () => {
      render(
        <FileInput
          onChange={() => {}}
          selectedFiles={[
            new File(["content"], "document.pdf", { type: "application/pdf" }),
          ]}
        />,
      );
      expect(screen.getByText("document.pdf")).toBeInTheDocument();
    });

    it("shows multiple selected files", () => {
      render(
        <FileInput
          onChange={() => {}}
          multiple
          selectedFiles={[
            new File(["content1"], "file1.pdf", { type: "application/pdf" }),
            new File(["content2"], "file2.pdf", { type: "application/pdf" }),
          ]}
        />,
      );
      expect(screen.getByText("file1.pdf")).toBeInTheDocument();
      expect(screen.getByText("file2.pdf")).toBeInTheDocument();
    });

    it("shows file size", () => {
      const content = "a".repeat(1024); // 1KB
      render(
        <FileInput
          onChange={() => {}}
          showFileSize
          selectedFiles={[
            new File([content], "test.txt", { type: "text/plain" }),
          ]}
        />,
      );
      expect(screen.getByText(/1.*KB/i)).toBeInTheDocument();
    });
  });

  describe("clear functionality", () => {
    it("shows clear button when file is selected and onClear is provided", () => {
      render(
        <FileInput
          onChange={() => {}}
          onClear={() => {}}
          selectedFiles={[
            new File(["content"], "test.txt", { type: "text/plain" }),
          ]}
        />,
      );
      expect(
        screen.getByRole("button", { name: /clear|remove/i }),
      ).toBeInTheDocument();
    });

    it("calls onClear when clear button is clicked", () => {
      const onClear = vi.fn();
      render(
        <FileInput
          onChange={() => {}}
          onClear={onClear}
          selectedFiles={[
            new File(["content"], "test.txt", { type: "text/plain" }),
          ]}
        />,
      );

      const clearButton = screen.getByRole("button", { name: /clear|remove/i });
      fireEvent.click(clearButton);

      expect(onClear).toHaveBeenCalled();
    });
  });

  describe("error state", () => {
    it("shows error message", () => {
      render(<FileInput onChange={() => {}} error="File too large" />);
      expect(screen.getByText("File too large")).toBeInTheDocument();
    });

    it("shows error styling", () => {
      render(<FileInput onChange={() => {}} error="File too large" />);
      const container = screen.getByTestId("file-input-container");
      expect(container).toHaveClass("border-error-9");
    });
  });

  describe("sizes", () => {
    it("renders small size", () => {
      render(<FileInput onChange={() => {}} size="sm" />);
      const container = screen.getByTestId("file-input-container");
      expect(container).toHaveClass("p-3");
    });

    it("renders medium size (default)", () => {
      render(<FileInput onChange={() => {}} />);
      const container = screen.getByTestId("file-input-container");
      expect(container).toHaveClass("p-4");
    });

    it("renders large size", () => {
      render(<FileInput onChange={() => {}} size="lg" />);
      const container = screen.getByTestId("file-input-container");
      expect(container).toHaveClass("p-6");
    });
  });

  describe("accessibility", () => {
    it("associates label with input", () => {
      render(<FileInput onChange={() => {}} label="Upload file" id="upload" />);
      const input = screen.getByTestId("file-input");
      expect(input).toHaveAttribute("id", "upload");
    });

    it("supports aria-label", () => {
      render(<FileInput onChange={() => {}} aria-label="Upload document" />);
      const input = screen.getByTestId("file-input");
      expect(input).toHaveAttribute("aria-label", "Upload document");
    });

    it("can be focused via keyboard", () => {
      render(<FileInput onChange={() => {}} />);
      const input = screen.getByTestId("file-input");
      input.focus();
      expect(input).toHaveFocus();
    });
  });
});

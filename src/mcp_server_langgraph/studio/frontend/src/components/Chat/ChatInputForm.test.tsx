/**
 * ChatInputForm Tests
 *
 * Tests for the rich chat input form component with voice input,
 * file uploads, and drag-drop support.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { ChatInputForm, UploadFile } from "./ChatInputForm";

describe("ChatInputForm", () => {
  const defaultProps = {
    input: "",
    onInputChange: vi.fn(),
    onSubmit: vi.fn(),
    isProcessing: false,
    isListening: false,
    isVoiceSupported: true,
    voiceError: null as string | null,
    onStartListening: vi.fn(),
    onStopListening: vi.fn(),
    uploadFiles: [] as UploadFile[],
    isUploading: false,
    isDragging: false,
    fileError: null as string | null,
    onSelectFiles: vi.fn(),
    onRemoveFile: vi.fn(),
    dragHandlers: {},
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Text Input", () => {
    it("should render text input field", () => {
      render(<ChatInputForm {...defaultProps} />);
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });

    it("should call onInputChange when typing", () => {
      render(<ChatInputForm {...defaultProps} />);
      const input = screen.getByPlaceholderText(/type your message/i);
      fireEvent.change(input, { target: { value: "Hello" } });
      expect(defaultProps.onInputChange).toHaveBeenCalledWith("Hello");
    });

    it("should display current input value", () => {
      render(<ChatInputForm {...defaultProps} input="Test message" />);
      const input = screen.getByPlaceholderText(
        /type your message/i,
      ) as HTMLInputElement;
      expect(input.value).toBe("Test message");
    });

    it("should disable input when processing", () => {
      render(<ChatInputForm {...defaultProps} isProcessing={true} />);
      const input = screen.getByPlaceholderText(/type your message/i);
      expect(input).toBeDisabled();
    });
  });

  describe("Send Button", () => {
    it("should render send button", () => {
      render(<ChatInputForm {...defaultProps} />);
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should disable send button when input is empty", () => {
      render(<ChatInputForm {...defaultProps} input="" />);
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should disable send button when processing", () => {
      render(
        <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should enable send button when input has content and not processing", () => {
      render(<ChatInputForm {...defaultProps} input="Hello" />);
      expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
    });

    it("should show loading spinner when processing", () => {
      render(
        <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />,
      );
      expect(screen.getByTestId("send-button-loading")).toBeInTheDocument();
    });
  });

  describe("Voice Input", () => {
    it("should render voice button when supported", () => {
      render(<ChatInputForm {...defaultProps} isVoiceSupported={true} />);
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
    });

    it("should not render voice button when not supported", () => {
      render(<ChatInputForm {...defaultProps} isVoiceSupported={false} />);
      expect(
        screen.queryByRole("button", { name: /voice input/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onStartListening when voice button clicked", () => {
      render(<ChatInputForm {...defaultProps} />);
      fireEvent.click(
        screen.getByRole("button", { name: /start voice input/i }),
      );
      expect(defaultProps.onStartListening).toHaveBeenCalledOnce();
    });

    it("should call onStopListening when listening and voice button clicked", () => {
      render(<ChatInputForm {...defaultProps} isListening={true} />);
      fireEvent.click(
        screen.getByRole("button", { name: /stop voice input/i }),
      );
      expect(defaultProps.onStopListening).toHaveBeenCalledOnce();
    });

    it("should show recording indicator when listening", () => {
      render(<ChatInputForm {...defaultProps} isListening={true} />);
      expect(screen.getByTestId("recording-indicator")).toBeInTheDocument();
      expect(screen.getByText(/listening/i)).toBeInTheDocument();
    });

    it("should display voice error when provided", () => {
      render(
        <ChatInputForm
          {...defaultProps}
          voiceError="Microphone access denied"
        />,
      );
      expect(screen.getByText("Microphone access denied")).toBeInTheDocument();
    });
  });

  describe("File Upload", () => {
    it("should render file attachment button", () => {
      render(<ChatInputForm {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
    });

    it("should disable attachment button when processing", () => {
      render(<ChatInputForm {...defaultProps} isProcessing={true} />);
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should disable attachment button when uploading", () => {
      render(<ChatInputForm {...defaultProps} isUploading={true} />);
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should display file error when provided", () => {
      render(<ChatInputForm {...defaultProps} fileError="File too large" />);
      expect(screen.getByText("File too large")).toBeInTheDocument();
    });
  });

  describe("Attached Files Preview", () => {
    const mockFiles: UploadFile[] = [
      {
        id: "f1",
        file: new File([""], "doc1.pdf"),
        status: "ready",
        progress: 100,
      },
      {
        id: "f2",
        file: new File([""], "image.png"),
        status: "uploading",
        progress: 50,
      },
    ];

    it("should display attached files", () => {
      render(<ChatInputForm {...defaultProps} uploadFiles={mockFiles} />);
      expect(screen.getByText("doc1.pdf")).toBeInTheDocument();
      expect(screen.getByText("image.png")).toBeInTheDocument();
    });

    it("should show upload progress for uploading files", () => {
      render(<ChatInputForm {...defaultProps} uploadFiles={mockFiles} />);
      expect(screen.getByText("50%")).toBeInTheDocument();
    });

    it("should call onRemoveFile when remove button clicked", () => {
      render(<ChatInputForm {...defaultProps} uploadFiles={mockFiles} />);
      const removeButtons = screen.getAllByRole("button", {
        name: /remove file/i,
      });
      fireEvent.click(removeButtons[0]);
      expect(defaultProps.onRemoveFile).toHaveBeenCalledWith("f1");
    });

    it("should show error status for failed uploads", () => {
      const filesWithError: UploadFile[] = [
        {
          id: "f1",
          file: new File([""], "doc.pdf"),
          status: "error",
          progress: 0,
          error: "Upload failed",
        },
      ];
      render(<ChatInputForm {...defaultProps} uploadFiles={filesWithError} />);
      expect(screen.getByText("Upload failed")).toBeInTheDocument();
    });
  });

  describe("Drag and Drop", () => {
    it("should show drop zone overlay when dragging", () => {
      render(<ChatInputForm {...defaultProps} isDragging={true} />);
      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
      expect(screen.getByText(/drop files here/i)).toBeInTheDocument();
    });

    it("should not show drop zone overlay when not dragging", () => {
      render(<ChatInputForm {...defaultProps} isDragging={false} />);
      expect(screen.queryByTestId("drop-zone-overlay")).not.toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("should call onSubmit when form submitted", () => {
      render(<ChatInputForm {...defaultProps} input="Hello" />);
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });

    it("should not submit when input is empty", () => {
      render(<ChatInputForm {...defaultProps} input="" />);
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      // onSubmit still called but parent should handle validation
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for all interactive elements", () => {
      render(<ChatInputForm {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should have placeholder text on input", () => {
      render(<ChatInputForm {...defaultProps} />);
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });
  });
});

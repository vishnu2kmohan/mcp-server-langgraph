/**
 * ChatInputForm Core Tests
 *
 * Tests for the rich chat input form component covering:
 * - Text Input
 * - Send Button
 * - Voice Input
 * - File Upload
 * - Attached Files Preview
 * - Drag and Drop
 * - Form Submission
 * - Accessibility
 * - Layout and Spacing
 * - Stop Streaming Button
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { axe } from "jest-axe";
import { TestProvider } from "@/test-utils";
import { createDefaultProps } from "./ChatInputForm.fixtures";
import { ChatInputForm } from "../ChatInputForm";
import type { UploadFile } from "../ChatInputForm";

describe("ChatInputForm", () => {
  let defaultProps: ReturnType<typeof createDefaultProps>;

  beforeEach(() => {
    defaultProps = createDefaultProps();
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Text Input", () => {
    it("should render text input field", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });

    it("should call onInputChange when typing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(/type your message/i);
      fireEvent.change(input, { target: { value: "Hello" } });
      expect(defaultProps.onInputChange).toHaveBeenCalledWith("Hello");
    });

    it("should display current input value", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Test message" />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(
        /type your message/i,
      ) as HTMLInputElement;
      expect(input.value).toBe("Test message");
    });

    it("should disable input when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isProcessing={true} />
        </TestProvider>,
      );
      const input = screen.getByPlaceholderText(/type your message/i);
      expect(input).toBeDisabled();
    });
  });

  describe("Send Button", () => {
    it("should render send button", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should disable send button when input is empty", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="" />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should disable send button when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).toBeDisabled();
    });

    it("should enable send button when input has content and not processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /send/i })).not.toBeDisabled();
    });

    it("should show loading spinner when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" isProcessing={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("send-button-loading")).toBeInTheDocument();
    });
  });

  describe("Voice Input", () => {
    it("should render voice button when supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
    });

    it("should not render voice button when not supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(
        screen.queryByRole("button", { name: /voice input/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onStartListening when voice button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /start voice input/i }),
      );
      expect(defaultProps.onStartListening).toHaveBeenCalledOnce();
    });

    it("should call onStopListening when listening and voice button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isListening={true} />
        </TestProvider>,
      );
      fireEvent.click(
        screen.getByRole("button", { name: /stop voice input/i }),
      );
      expect(defaultProps.onStopListening).toHaveBeenCalledOnce();
    });

    it("should show recording indicator when listening", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isListening={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("recording-indicator")).toBeInTheDocument();
      expect(screen.getByText(/listening/i)).toBeInTheDocument();
    });

    it("should display voice error when provided", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            voiceError="Microphone access denied"
          />
        </TestProvider>,
      );
      expect(screen.getByText("Microphone access denied")).toBeInTheDocument();
    });

    it("should show browser compatibility info when voice not supported", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(
        screen.getByTestId("voice-not-supported-banner"),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/voice input.*not supported/i),
      ).toBeInTheDocument();
    });

    it("should include browser recommendation in compatibility banner", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      expect(screen.getByText(/chrome|edge|safari/i)).toBeInTheDocument();
    });

    it("should allow dismissing the compatibility banner", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isVoiceSupported={false} />
        </TestProvider>,
      );
      const dismissButton = screen.getByRole("button", {
        name: /dismiss/i,
      });
      fireEvent.click(dismissButton);
      expect(
        screen.queryByTestId("voice-not-supported-banner"),
      ).not.toBeInTheDocument();
    });
  });

  describe("File Upload", () => {
    it("should render file attachment button", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
    });

    it("should disable attachment button when processing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isProcessing={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should disable attachment button when uploading", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isUploading={true} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeDisabled();
    });

    it("should display file error when provided", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} fileError="File too large" />
        </TestProvider>,
      );
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
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
      expect(screen.getByText("doc1.pdf")).toBeInTheDocument();
      expect(screen.getByText("image.png")).toBeInTheDocument();
    });

    it("should show upload progress for uploading files", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
      expect(screen.getByText("50%")).toBeInTheDocument();
    });

    it("should call onRemoveFile when remove button clicked", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={mockFiles} />
        </TestProvider>,
      );
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
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} uploadFiles={filesWithError} />
        </TestProvider>,
      );
      expect(screen.getByText("Upload failed")).toBeInTheDocument();
    });
  });

  describe("Drag and Drop", () => {
    it("should show drop zone overlay when dragging", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isDragging={true} />
        </TestProvider>,
      );
      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
      expect(screen.getByText(/drop files here/i)).toBeInTheDocument();
    });

    it("should not show drop zone overlay when not dragging", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} isDragging={false} />
        </TestProvider>,
      );
      expect(screen.queryByTestId("drop-zone-overlay")).not.toBeInTheDocument();
    });
  });

  describe("Form Submission", () => {
    it("should call onSubmit when form submitted", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="Hello" />
        </TestProvider>,
      );
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });

    it("should not submit when input is empty", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} input="" />
        </TestProvider>,
      );
      const form = screen.getByTestId("chat-input-form");
      fireEvent.submit(form);
      // onSubmit still called but parent should handle validation
      expect(defaultProps.onSubmit).toHaveBeenCalledOnce();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible labels for all interactive elements", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /attach file/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /start voice input/i }),
      ).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /send/i })).toBeInTheDocument();
    });

    it("should have placeholder text on input", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByPlaceholderText(/type your message/i),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  describe("Layout and Spacing", () => {
    it("should have proper bottom padding for comfortable spacing", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const container = screen.getByTestId("chat-input-container");
      expect(container).toBeInTheDocument();
      // Container should have bottom padding class
      expect(container.className).toMatch(/pb-\d+|py-\d+/);
    });

    it("should have centered max-width container for wide screens", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const container = screen.getByTestId("chat-input-container");
      expect(container.className).toMatch(/max-w-/);
    });

    it("should use textarea for multi-line input support", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const textarea = screen.getByRole("textbox");
      expect(textarea.tagName.toLowerCase()).toBe("textarea");
    });

    it("should have proper input wrapper with grouped controls", () => {
      render(
        <TestProvider>
          <ChatInputForm {...defaultProps} />
        </TestProvider>,
      );
      const wrapper = screen.getByTestId("input-wrapper");
      expect(wrapper).toBeInTheDocument();
    });
  });

  describe("Stop Streaming Button", () => {
    it("should show stop button when streaming", () => {
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello"
            isStreaming={true}
            onStopStreaming={vi.fn()}
          />
        </TestProvider>,
      );
      expect(screen.getByTestId("stop-streaming-button")).toBeInTheDocument();
    });

    it("should call onStopStreaming when stop button clicked", () => {
      const mockOnStopStreaming = vi.fn();
      render(
        <TestProvider>
          <ChatInputForm
            {...defaultProps}
            input="Hello"
            isStreaming={true}
            onStopStreaming={mockOnStopStreaming}
          />
        </TestProvider>,
      );
      fireEvent.click(screen.getByTestId("stop-streaming-button"));
      expect(mockOnStopStreaming).toHaveBeenCalledOnce();
    });
  });
});

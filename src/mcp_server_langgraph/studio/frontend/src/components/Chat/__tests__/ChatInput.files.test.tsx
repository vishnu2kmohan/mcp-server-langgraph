/**
 * ChatInput File Tests
 *
 * Covers: attachment button, drag and drop, file previews, file selection
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { createMockProps } from "./ChatInput.fixtures";
import { TestProvider } from "@/test-utils";
import { ChatInput } from "../ChatInput";

describe("ChatInput - files", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("attachment button", () => {
    it("renders attachment button with plus icon", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps()} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /attach/i }),
      ).toBeInTheDocument();
    });

    it("disables attachment button when disabled", () => {
      render(
        <TestProvider>
          <ChatInput {...createMockProps({ disabled: true })} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /attach/i })).toBeDisabled();
    });
  });

  describe("drag and drop", () => {
    it("shows drop zone overlay when dragging", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isDragging: true,
              dragHandlers: {
                onDragOver: vi.fn(),
                onDragLeave: vi.fn(),
                onDrop: vi.fn(),
              },
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("drop-zone-overlay")).toBeInTheDocument();
    });

    it("hides drop zone overlay when not dragging", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              isDragging: false,
            })}
          />
        </TestProvider>,
      );

      expect(screen.queryByTestId("drop-zone-overlay")).not.toBeInTheDocument();
    });
  });

  describe("file previews", () => {
    it("displays uploaded files", () => {
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              uploadFiles: [
                {
                  id: "1",
                  file: new File([""], "test.pdf"),
                  status: "complete" as const,
                  progress: 100,
                },
              ],
              onRemoveFile: vi.fn(),
            })}
          />
        </TestProvider>,
      );

      expect(screen.getByText("test.pdf")).toBeInTheDocument();
    });

    it("calls onRemoveFile when remove button is clicked", async () => {
      const user = userEvent.setup();
      const onRemoveFile = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              uploadFiles: [
                {
                  id: "1",
                  file: new File([""], "test.pdf"),
                  status: "complete" as const,
                  progress: 100,
                },
              ],
              onRemoveFile,
            })}
          />
        </TestProvider>,
      );

      await user.click(screen.getByRole("button", { name: /remove/i }));

      expect(onRemoveFile).toHaveBeenCalledWith("1");
    });
  });

  describe("file selection", () => {
    it("calls onSelectFiles when attachment button triggers file input", async () => {
      const user = userEvent.setup();
      const onSelectFiles = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              onSelectFiles,
            })}
          />
        </TestProvider>,
      );

      // Find the hidden file input
      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      expect(fileInput).toBeInTheDocument();

      // Create a test file
      const testFile = new File(["test content"], "test.txt", {
        type: "text/plain",
      });

      // Simulate file selection
      await user.upload(fileInput, testFile);

      expect(onSelectFiles).toHaveBeenCalledWith([testFile]);
    });

    it("accepts multiple files when configured", async () => {
      const user = userEvent.setup();
      const onSelectFiles = vi.fn();
      render(
        <TestProvider>
          <ChatInput
            {...createMockProps({
              onSelectFiles,
              acceptMultipleFiles: true,
            })}
          />
        </TestProvider>,
      );

      const fileInput = document.querySelector(
        'input[type="file"]',
      ) as HTMLInputElement;
      expect(fileInput).toHaveAttribute("multiple");

      const file1 = new File(["content1"], "file1.txt", { type: "text/plain" });
      const file2 = new File(["content2"], "file2.txt", { type: "text/plain" });

      await user.upload(fileInput, [file1, file2]);

      expect(onSelectFiles).toHaveBeenCalledWith([file1, file2]);
    });
  });
});

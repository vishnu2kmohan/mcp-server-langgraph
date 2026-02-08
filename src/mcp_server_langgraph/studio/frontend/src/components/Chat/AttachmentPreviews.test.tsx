/**
 * AttachmentPreviews Component Tests
 *
 * Tests for the Slack-style attachment preview chips that appear above the chat input.
 * Features:
 * - File preview chips with icons and names
 * - URL preview chips for fetched URLs
 * - Remove button on each chip
 * - Loading states
 * - Horizontal scroll with overflow
 *
 * TDD RED Phase: Write failing tests first.
 */

import {
  render,
  screen,
  cleanup,
  within,
  waitFor,
} from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import userEvent from "@testing-library/user-event";
import {
  AttachmentPreviews,
  type AttachmentPreviewsProps,
} from "./AttachmentPreviews";
import type { UploadFile } from "../../hooks/useFileUpload";

import { TestProvider } from "@/test-utils";

describe("AttachmentPreviews", () => {
  const mockOnRemoveFile = vi.fn();
  const mockOnRemoveFetchedUrl = vi.fn();

  // Create mock File objects
  const createMockFile = (name: string, size: number, type: string): File => {
    const blob = new Blob([], { type });
    return new File([blob], name, { type });
  };

  const mockFiles: UploadFile[] = [
    {
      id: "file-1",
      file: createMockFile("document.pdf", 1024000, "application/pdf"),
      status: "complete",
      progress: 100,
    },
    {
      id: "file-2",
      file: createMockFile("image.png", 512000, "image/png"),
      status: "complete",
      progress: 100,
    },
    {
      id: "file-3",
      file: createMockFile("data.csv", 256000, "text/csv"),
      status: "uploading",
      progress: 50,
    },
  ];

  const mockFetchedUrls = [
    {
      url: "https://example.com/article",
      title: "Example Article",
      content: "Article content...",
    },
    {
      url: "https://docs.example.com",
      title: "Documentation",
      content: "Docs content...",
    },
  ];

  const defaultProps: AttachmentPreviewsProps = {
    uploadFiles: mockFiles,
    onRemoveFile: mockOnRemoveFile,
    isUploading: false,
    fetchedUrls: mockFetchedUrls,
    onRemoveFetchedUrl: mockOnRemoveFetchedUrl,
    urlFetchLoading: [],
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render file chips for uploaded files", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("document.pdf")).toBeInTheDocument();
      expect(screen.getByText("image.png")).toBeInTheDocument();
      expect(screen.getByText("data.csv")).toBeInTheDocument();
    });

    it("should render with data-testid", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("attachment-previews")).toBeInTheDocument();
    });

    it("should not render when no files and no URLs", () => {
      render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={[]}
            fetchedUrls={[]}
          />
        </TestProvider>,
      );

      expect(
        screen.queryByTestId("attachment-previews"),
      ).not.toBeInTheDocument();
    });

    it("should render URL chips for fetched URLs", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} uploadFiles={[]} />
        </TestProvider>,
      );

      expect(screen.getByText("Example Article")).toBeInTheDocument();
      expect(screen.getByText("Documentation")).toBeInTheDocument();
    });

    it("should show URL domain when no title", () => {
      render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={[]}
            fetchedUrls={[
              { url: "https://example.com/page", content: "Content" },
            ]}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/example\.com/)).toBeInTheDocument();
    });
  });

  describe("file chips", () => {
    it("should show file icon for documents", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const pdfChip = screen
        .getByText("document.pdf")
        .closest("[data-testid^='file-chip-']");
      expect(pdfChip).toBeInTheDocument();
      expect(within(pdfChip!).getByTestId("file-icon")).toBeInTheDocument();
    });

    it("should show image icon for images", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const imageChip = screen
        .getByText("image.png")
        .closest("[data-testid^='file-chip-']");
      expect(within(imageChip!).getByTestId("image-icon")).toBeInTheDocument();
    });

    it("should show loading state for uploading files", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const uploadingChip = screen
        .getByText("data.csv")
        .closest("[data-testid^='file-chip-']");
      expect(
        within(uploadingChip!).getByTestId("uploading-indicator"),
      ).toBeInTheDocument();
    });

    it("should call onRemoveFile when X is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const pdfChip = screen
        .getByText("document.pdf")
        .closest("[data-testid^='file-chip-']");
      const removeButton = within(pdfChip!).getByRole("button", {
        name: /remove/i,
      });
      await user.click(removeButton);

      expect(mockOnRemoveFile).toHaveBeenCalledWith("file-1");
    });

    it("should truncate long filenames", () => {
      const longNameFile: UploadFile = {
        id: "long-file",
        file: createMockFile(
          "this-is-a-very-long-filename-that-should-be-truncated.pdf",
          1024,
          "application/pdf",
        ),
        status: "complete",
        progress: 100,
      };

      render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={[longNameFile]}
            fetchedUrls={[]}
          />
        </TestProvider>,
      );

      const chip = screen.getByTestId("file-chip-long-file");
      expect(chip).toBeInTheDocument();
      // Check that the text element has truncate class
      const textElement = chip.querySelector("[class*='truncate']");
      expect(textElement).toBeInTheDocument();
    });

    it("should show full filename on hover (title attribute)", () => {
      const longNameFile: UploadFile = {
        id: "long-file",
        file: createMockFile(
          "this-is-a-very-long-filename-that-should-be-truncated.pdf",
          1024,
          "application/pdf",
        ),
        status: "complete",
        progress: 100,
      };

      render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={[longNameFile]}
            fetchedUrls={[]}
          />
        </TestProvider>,
      );

      const filenameElement = screen.getByText(
        "this-is-a-very-long-filename-that-should-be-truncated.pdf",
      );
      expect(filenameElement).toHaveAttribute(
        "title",
        "this-is-a-very-long-filename-that-should-be-truncated.pdf",
      );
    });
  });

  describe("URL chips", () => {
    it("should call onRemoveFetchedUrl when X is clicked", async () => {
      const user = userEvent.setup();
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} uploadFiles={[]} />
        </TestProvider>,
      );

      const urlChip = screen
        .getByText("Example Article")
        .closest("[data-testid^='url-chip-']");
      const removeButton = within(urlChip!).getByRole("button", {
        name: /remove/i,
      });
      await user.click(removeButton);

      expect(mockOnRemoveFetchedUrl).toHaveBeenCalledWith(
        "https://example.com/article",
      );
    });

    it("should show loading state for URLs being fetched", () => {
      render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={[]}
            fetchedUrls={[]}
            urlFetchLoading={["https://loading.example.com"]}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("url-loading-chip")).toBeInTheDocument();
    });

    it("should show link icon for URLs", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} uploadFiles={[]} />
        </TestProvider>,
      );

      const urlChip = screen
        .getByText("Example Article")
        .closest("[data-testid^='url-chip-']");
      expect(within(urlChip!).getByTestId("link-icon")).toBeInTheDocument();
    });
  });

  describe("layout", () => {
    it("should have horizontal scroll container", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const container = screen.getByTestId("attachment-previews");
      expect(container.className).toMatch(/overflow-x-auto/);
    });

    it("should render files before URLs", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const container = screen.getByTestId("attachment-previews");
      const chips = container.querySelectorAll(
        "[data-testid^='file-chip-'], [data-testid^='url-chip-']",
      );

      // First chips should be files
      expect(chips[0].getAttribute("data-testid")).toMatch(/^file-chip-/);
      // Last chips should be URLs
      expect(chips[chips.length - 1].getAttribute("data-testid")).toMatch(
        /^url-chip-/,
      );
    });
  });

  describe("styling", () => {
    it("should render chips with rounded-full styling", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const chip = screen.getByTestId("file-chip-file-1");
      expect(chip.className).toMatch(/rounded-full/);
    });

    it("should have gap between chips", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const container = screen.getByTestId("attachment-previews");
      expect(container.className).toMatch(/gap-2/);
    });
  });

  describe("accessibility", () => {
    it("should have accessible remove buttons", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const removeButtons = screen.getAllByRole("button", { name: /remove/i });
      expect(removeButtons.length).toBe(
        mockFiles.length + mockFetchedUrls.length,
      );
    });

    it("should have aria-label on remove buttons", () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      const pdfChip = screen
        .getByText("document.pdf")
        .closest("[data-testid^='file-chip-']");
      const removeButton = within(pdfChip!).getByRole("button");
      expect(removeButton).toHaveAttribute("aria-label");
    });
  });

  describe("Motion Animations", () => {
    it("should animate chips on mount", async () => {
      render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      // Container should exist with motion wrapper
      const container = screen.getByTestId("attachment-previews");
      expect(container).toBeInTheDocument();

      // All chips should be present after mount (animation may still be running)
      expect(screen.getByText("document.pdf")).toBeInTheDocument();
      expect(screen.getByText("image.png")).toBeInTheDocument();

      // Wait for animation to complete and chips to become visible
      await waitFor(() => {
        expect(screen.getByText("document.pdf")).toBeVisible();
        expect(screen.getByText("image.png")).toBeVisible();
      });
    });

    it("should animate chip removal with AnimatePresence", async () => {
      const { rerender } = render(
        <TestProvider>
          <AttachmentPreviews {...defaultProps} />
        </TestProvider>,
      );

      // Verify chip exists
      expect(screen.getByText("document.pdf")).toBeInTheDocument();

      // Simulate removal by rerendering without the file
      const updatedFiles = mockFiles.filter((f) => f.id !== "file-1");
      rerender(
        <AttachmentPreviews {...defaultProps} uploadFiles={updatedFiles} />,
      );

      // After AnimatePresence exit animation, chip should be removed
      await waitFor(() => {
        expect(screen.queryByText("document.pdf")).not.toBeInTheDocument();
      });
    });

    it("should animate new chip addition", async () => {
      const initialFiles = [mockFiles[0]];
      const { rerender } = render(
        <TestProvider>
          <AttachmentPreviews
            {...defaultProps}
            uploadFiles={initialFiles}
            fetchedUrls={[]}
          />
        </TestProvider>,
      );

      // Verify initial state
      expect(screen.getByText("document.pdf")).toBeInTheDocument();
      expect(screen.queryByText("image.png")).not.toBeInTheDocument();

      // Add a new file
      const updatedFiles = [mockFiles[0], mockFiles[1]];
      rerender(
        <AttachmentPreviews
          {...defaultProps}
          uploadFiles={updatedFiles}
          fetchedUrls={[]}
        />,
      );

      // New chip should animate in
      await waitFor(() => {
        expect(screen.getByText("image.png")).toBeInTheDocument();
      });
    });
  });
});

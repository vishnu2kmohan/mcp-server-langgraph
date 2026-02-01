/**
 * AttachmentPreviews Component Stories
 *
 * Storybook stories for the file and URL attachment previews component.
 * Showcases all states including files, URLs, loading, and removal.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import type { UploadFile } from "../../hooks/useFileUpload";
import { AttachmentPreviews } from "./AttachmentPreviews";

// Create mock File objects for stories
const createMockFile = (name: string, type: string, size: number): File => {
  const blob = new Blob([], { type });
  Object.defineProperty(blob, "size", { value: size });
  return new File([blob], name, { type, lastModified: Date.now() });
};

// Helper to create UploadFile with default complete status
const createUploadFile = (
  id: string,
  name: string,
  type: string,
  size: number,
  progress: number = 100,
  status: UploadFile["status"] = "complete",
): UploadFile => ({
  id,
  file: createMockFile(name, type, size),
  status,
  progress,
});

const SAMPLE_FILES: UploadFile[] = [
  createUploadFile("file-1", "document.pdf", "application/pdf", 102400),
  createUploadFile("file-2", "screenshot.png", "image/png", 51200),
  createUploadFile("file-3", "data.csv", "text/csv", 8192),
];

const SAMPLE_URLS = [
  {
    url: "https://example.com/article",
    title: "Example Article",
    content: "Article content...",
  },
  {
    url: "https://docs.example.com/api",
    title: "API Documentation",
    content: "API docs...",
  },
];

const meta: Meta<typeof AttachmentPreviews> = {
  title: "Chat/AttachmentPreviews",
  component: AttachmentPreviews,
  tags: ["autodocs"],
  parameters: {
    layout: "centered",
    docs: {
      description: {
        component:
          "Displays file and URL attachment preview chips. Supports file type icons, loading states, and removal. Uses horizontal scroll for overflow.",
      },
    },
  },
  argTypes: {
    uploadFiles: {
      description: "Array of uploaded files to display",
    },
    onRemoveFile: {
      description: "Callback when a file is removed",
    },
    isUploading: {
      control: "boolean",
      description: "Whether files are currently being uploaded",
    },
    fetchedUrls: {
      description: "Array of fetched URL content to display",
    },
    onRemoveFetchedUrl: {
      description: "Callback when a URL preview is removed",
    },
    urlFetchLoading: {
      description: "Array of URLs currently being fetched",
    },
  },
};

export default meta;
type Story = StoryObj<typeof AttachmentPreviews>;

// =============================================================================
// Basic States
// =============================================================================

export const WithFiles: Story = {
  args: {
    uploadFiles: SAMPLE_FILES,
    onRemoveFile: (id) => console.log("Remove file:", id),
  },
  parameters: {
    docs: {
      description: {
        story:
          "Displays uploaded file previews with type icons and remove buttons.",
      },
    },
  },
};

export const WithUrls: Story = {
  args: {
    uploadFiles: [],
    fetchedUrls: SAMPLE_URLS,
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
  },
  parameters: {
    docs: {
      description: {
        story: "Displays fetched URL previews with titles and remove buttons.",
      },
    },
  },
};

export const WithFilesAndUrls: Story = {
  args: {
    uploadFiles: SAMPLE_FILES.slice(0, 2),
    fetchedUrls: SAMPLE_URLS.slice(0, 1),
    onRemoveFile: (id) => console.log("Remove file:", id),
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
  },
  parameters: {
    docs: {
      description: {
        story: "Mixed files and URLs displayed together.",
      },
    },
  },
};

export const Empty: Story = {
  args: {
    uploadFiles: [],
    fetchedUrls: [],
  },
  parameters: {
    docs: {
      description: {
        story: "Empty state when no attachments are present.",
      },
    },
  },
};

// =============================================================================
// Loading States
// =============================================================================

export const FileUploading: Story = {
  args: {
    uploadFiles: [
      createUploadFile(
        "file-1",
        "large-file.zip",
        "application/zip",
        10485760,
        45,
        "uploading",
      ),
      ...SAMPLE_FILES.slice(0, 1),
    ],
    isUploading: true,
    onRemoveFile: (id) => console.log("Remove file:", id),
  },
  parameters: {
    docs: {
      description: {
        story: "Shows uploading state with progress indicator.",
      },
    },
  },
};

export const UrlFetching: Story = {
  args: {
    uploadFiles: [],
    fetchedUrls: SAMPLE_URLS.slice(0, 1),
    urlFetchLoading: ["https://example.com/loading"],
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
  },
  parameters: {
    docs: {
      description: {
        story: "Shows URL fetching state with loading indicator.",
      },
    },
  },
};

// =============================================================================
// File Types
// =============================================================================

export const VariousFileTypes: Story = {
  args: {
    uploadFiles: [
      createUploadFile("1", "document.pdf", "application/pdf", 102400),
      createUploadFile("2", "photo.jpg", "image/jpeg", 204800),
      createUploadFile(
        "3",
        "spreadsheet.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        51200,
      ),
      createUploadFile("4", "code.py", "text/x-python", 4096),
      createUploadFile("5", "archive.zip", "application/zip", 1048576),
    ],
    onRemoveFile: (id) => console.log("Remove file:", id),
  },
  parameters: {
    docs: {
      description: {
        story: "Shows different file type icons for various attachment types.",
      },
    },
  },
};

// =============================================================================
// Overflow
// =============================================================================

export const ManyAttachments: Story = {
  args: {
    uploadFiles: [
      createUploadFile("1", "file1.pdf", "application/pdf", 10240),
      createUploadFile("2", "file2.png", "image/png", 20480),
      createUploadFile(
        "3",
        "file3.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        30720,
      ),
      createUploadFile("4", "file4.csv", "text/csv", 4096),
      createUploadFile("5", "file5.js", "text/javascript", 8192),
    ],
    fetchedUrls: [
      { url: "https://example.com/1", title: "Link 1", content: "..." },
      { url: "https://example.com/2", title: "Link 2", content: "..." },
    ],
    onRemoveFile: (id) => console.log("Remove file:", id),
    onRemoveFetchedUrl: (url) => console.log("Remove URL:", url),
  },
  decorators: [
    (Story) => (
      <div className="w-[400px]">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        story: "Many attachments with horizontal scroll enabled.",
      },
    },
  },
};

// =============================================================================
// Context Stories
// =============================================================================

export const InChatInputContext: Story = {
  render: () => (
    <div className="w-96 p-3 bg-neutral-2 border border-neutral-6 rounded-lg space-y-2">
      <AttachmentPreviews
        uploadFiles={SAMPLE_FILES.slice(0, 2)}
        fetchedUrls={SAMPLE_URLS.slice(0, 1)}
        onRemoveFile={(id) => console.log("Remove:", id)}
        onRemoveFetchedUrl={(url) => console.log("Remove:", url)}
      />
      <div className="flex items-center gap-2 pt-2 border-t border-neutral-6">
        <span className="flex-1 text-sm text-neutral-9">Message...</span>
        <button className="p-2 rounded-full bg-primary-9 text-neutral-12">
          <svg
            className="w-4 h-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M5 10l7-7m0 0l7 7m-7-7v18"
            />
          </svg>
        </button>
      </div>
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "AttachmentPreviews shown inside a chat input container.",
      },
    },
  },
};

export const DarkMode: Story = {
  render: () => (
    <div className="dark bg-neutral-2 p-6 rounded-lg">
      <AttachmentPreviews
        uploadFiles={SAMPLE_FILES}
        fetchedUrls={SAMPLE_URLS.slice(0, 1)}
        onRemoveFile={(id) => console.log("Remove:", id)}
        onRemoveFetchedUrl={(url) => console.log("Remove:", url)}
      />
    </div>
  ),
  parameters: {
    docs: {
      description: {
        story: "AttachmentPreviews in dark mode context.",
      },
    },
  },
};

// =============================================================================
// Long Filenames
// =============================================================================

export const LongFilenames: Story = {
  args: {
    uploadFiles: [
      createUploadFile(
        "1",
        "very-long-filename-that-should-be-truncated-nicely.pdf",
        "application/pdf",
        102400,
      ),
      createUploadFile(
        "2",
        "another-extremely-long-filename-for-testing-truncation.png",
        "image/png",
        51200,
      ),
    ],
    onRemoveFile: (id) => console.log("Remove file:", id),
  },
  decorators: [
    (Story) => (
      <div className="w-[300px]">
        <Story />
      </div>
    ),
  ],
  parameters: {
    docs: {
      description: {
        story:
          "Long filenames are truncated with ellipsis. Hover to see full name.",
      },
    },
  },
};

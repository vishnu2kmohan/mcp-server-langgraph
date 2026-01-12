/**
 * FileInput Component Stories
 *
 * Storybook documentation for the FileInput component.
 */

import type { Meta, StoryObj } from "@storybook/react-vite";
import { useState } from "react";
import { FileInput } from "./FileInput";

const meta: Meta<typeof FileInput> = {
  title: "Design System/FileInput",
  component: FileInput,
  tags: ["autodocs"],
  parameters: {
    docs: {
      description: {
        component:
          "A file upload component with drag and drop support. Supports multiple files, file type restrictions, size display, and error states.",
      },
    },
  },
  argTypes: {
    accept: {
      control: "text",
      description: "Accepted file types (e.g., .pdf,.doc)",
    },
    multiple: {
      control: "boolean",
      description: "Allow multiple file selection",
    },
    size: {
      control: "select",
      options: ["sm", "md", "lg"],
      description: "Component size",
    },
    variant: {
      control: "select",
      options: ["default", "compact"],
      description: "Display variant",
    },
    label: {
      control: "text",
      description: "Label text",
    },
    helperText: {
      control: "text",
      description: "Helper text",
    },
    error: {
      control: "text",
      description: "Error message",
    },
    disabled: {
      control: "boolean",
      description: "Disabled state",
    },
  },
};

export default meta;
type Story = StoryObj<typeof FileInput>;

/**
 * Default file input with drag and drop zone
 */
export const Default: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
      />
    );
  },
};

/**
 * File input with label and helper text
 */
export const WithLabel: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
        label="Upload document"
        helperText="PDF or Word documents, max 10MB"
      />
    );
  },
};

/**
 * Multiple file selection
 */
export const Multiple: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
        multiple
        showFileSize
        label="Upload files"
        helperText="Select multiple files"
      />
    );
  },
};

/**
 * With file type restrictions
 */
export const AcceptTypes: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
        accept=".pdf,.doc,.docx"
        label="Upload document"
        helperText="Only PDF and Word documents are allowed"
      />
    );
  },
};

/**
 * Compact variant (no drag zone)
 */
export const Compact: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
        variant="compact"
        label="Profile photo"
        accept="image/*"
      />
    );
  },
};

/**
 * With error state
 */
export const WithError: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <FileInput
        onChange={setFiles}
        selectedFiles={files}
        onClear={() => setFiles([])}
        error="File exceeds maximum size of 10MB"
        label="Upload document"
      />
    );
  },
};

/**
 * Disabled state
 */
export const Disabled: Story = {
  render: () => (
    <div className="space-y-4">
      <FileInput onChange={() => {}} disabled label="Disabled (empty)" />
      <FileInput
        onChange={() => {}}
        disabled
        selectedFiles={[
          new File(["content"], "document.pdf", { type: "application/pdf" }),
        ]}
        label="Disabled (with file)"
      />
    </div>
  ),
};

/**
 * All sizes comparison
 */
export const Sizes: Story = {
  render: function Render() {
    const [smFiles, setSmFiles] = useState<File[]>([]);
    const [mdFiles, setMdFiles] = useState<File[]>([]);
    const [lgFiles, setLgFiles] = useState<File[]>([]);
    return (
      <div className="space-y-6">
        <div>
          <span className="text-sm text-neutral-600 dark:text-neutral-400 mb-2 block">
            Small
          </span>
          <FileInput
            size="sm"
            onChange={setSmFiles}
            selectedFiles={smFiles}
            onClear={() => setSmFiles([])}
          />
        </div>
        <div>
          <span className="text-sm text-neutral-600 dark:text-neutral-400 mb-2 block">
            Medium (default)
          </span>
          <FileInput
            size="md"
            onChange={setMdFiles}
            selectedFiles={mdFiles}
            onClear={() => setMdFiles([])}
          />
        </div>
        <div>
          <span className="text-sm text-neutral-600 dark:text-neutral-400 mb-2 block">
            Large
          </span>
          <FileInput
            size="lg"
            onChange={setLgFiles}
            selectedFiles={lgFiles}
            onClear={() => setLgFiles([])}
          />
        </div>
      </div>
    );
  },
};

/**
 * Image upload example
 */
export const ImageUpload: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <div className="max-w-md">
        <FileInput
          onChange={setFiles}
          selectedFiles={files}
          onClear={() => setFiles([])}
          accept="image/png,image/jpeg,image/gif"
          label="Upload images"
          helperText="PNG, JPG, or GIF up to 5MB each"
          showFileSize
          multiple
        />
      </div>
    );
  },
};

/**
 * Dark mode demonstration
 */
export const DarkMode: Story = {
  render: function Render() {
    const [files, setFiles] = useState<File[]>([]);
    return (
      <div className="dark bg-neutral-900 p-6 rounded-lg">
        <FileInput
          onChange={setFiles}
          selectedFiles={files}
          onClear={() => setFiles([])}
          label="Upload document"
          helperText="PDF files only"
          accept=".pdf"
          showFileSize
        />
      </div>
    );
  },
};

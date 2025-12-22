/**
 * CanvasArtifact Tests - Phase 1
 *
 * Tests for the editable artifact component that renders
 * different content types (code, markdown, JSON, etc.)
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { CanvasArtifact } from "./CanvasArtifact";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";

// =============================================================================
// Test Data
// =============================================================================

const mockCodeArtifact: CanvasArtifactType = {
  id: "artifact-1",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: 'function hello() {\n  console.log("Hello!");\n}',
  contentType: "code",
  title: "Hello Function",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
  editMetadata: {
    editedBy: "user",
    language: "javascript",
  },
};

const mockMarkdownArtifact: CanvasArtifactType = {
  id: "artifact-2",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: "# Hello World\n\nThis is **bold** text.",
  contentType: "markdown",
  title: "README",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const mockJsonArtifact: CanvasArtifactType = {
  id: "artifact-3",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: '{"name": "test", "value": 123}',
  contentType: "json",
  title: "Config",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

// =============================================================================
// Tests
// =============================================================================

describe("CanvasArtifact", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render artifact container", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("canvas-artifact")).toBeInTheDocument();
    });

    it("should display artifact title", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText("Hello Function")).toBeInTheDocument();
    });

    it("should display version number", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText(/v1/)).toBeInTheDocument();
    });

    it("should display content type badge", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("content-type-badge")).toHaveTextContent(
        "code",
      );
    });
  });

  describe("Code Artifact", () => {
    it("should render code content in pre element", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText(/function hello/)).toBeInTheDocument();
    });

    it("should display language badge for code artifacts", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("language-badge")).toHaveTextContent(
        "javascript",
      );
    });

    it("should show line numbers when enabled", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} showLineNumbers />);
      expect(screen.getByTestId("line-numbers")).toBeInTheDocument();
    });
  });

  describe("Markdown Artifact", () => {
    it("should render markdown content", () => {
      render(<CanvasArtifact artifact={mockMarkdownArtifact} />);
      expect(screen.getByText(/Hello World/)).toBeInTheDocument();
    });

    it("should render markdown as preview by default", () => {
      render(<CanvasArtifact artifact={mockMarkdownArtifact} />);
      expect(screen.getByTestId("markdown-preview")).toBeInTheDocument();
    });
  });

  describe("JSON Artifact", () => {
    it("should render JSON content", () => {
      render(<CanvasArtifact artifact={mockJsonArtifact} />);
      expect(screen.getByText(/"name"/)).toBeInTheDocument();
    });

    it("should format JSON with indentation", () => {
      render(<CanvasArtifact artifact={mockJsonArtifact} />);
      const content = screen.getByTestId("json-content");
      expect(content.textContent).toContain("name");
    });
  });

  describe("Editing", () => {
    it("should show edit button when editable", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} editable />);
      expect(screen.getByTestId("edit-button")).toBeInTheDocument();
    });

    it("should enter edit mode when edit button clicked", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} editable />);
      fireEvent.click(screen.getByTestId("edit-button"));
      expect(screen.getByTestId("content-editor")).toBeInTheDocument();
    });

    it("should call onChange when content edited", () => {
      const onChange = vi.fn();
      render(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          editable
          isEditing
          onChange={onChange}
        />,
      );

      const editor = screen.getByTestId("content-editor");
      fireEvent.change(editor, { target: { value: "new content" } });

      expect(onChange).toHaveBeenCalledWith("new content");
    });

    it("should show save and cancel buttons in edit mode", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} editable isEditing />);
      expect(screen.getByTestId("save-button")).toBeInTheDocument();
      expect(screen.getByTestId("cancel-button")).toBeInTheDocument();
    });

    it("should call onSave when save clicked", () => {
      const onSave = vi.fn();
      render(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          editable
          isEditing
          onSave={onSave}
        />,
      );

      fireEvent.click(screen.getByTestId("save-button"));
      expect(onSave).toHaveBeenCalled();
    });

    it("should call onCancel when cancel clicked", () => {
      const onCancel = vi.fn();
      render(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          editable
          isEditing
          onCancel={onCancel}
        />,
      );

      fireEvent.click(screen.getByTestId("cancel-button"));
      expect(onCancel).toHaveBeenCalled();
    });
  });

  describe("AI Metadata", () => {
    it("should show AI badge for AI-generated content", () => {
      const aiArtifact: CanvasArtifactType = {
        ...mockCodeArtifact,
        editMetadata: {
          editedBy: "ai-generation",
          aiConfidence: 0.95,
        },
      };

      render(<CanvasArtifact artifact={aiArtifact} />);
      expect(screen.getByTestId("ai-badge")).toBeInTheDocument();
    });

    it("should show confidence score for AI content", () => {
      const aiArtifact: CanvasArtifactType = {
        ...mockCodeArtifact,
        editMetadata: {
          editedBy: "ai-generation",
          aiConfidence: 0.95,
        },
      };

      render(<CanvasArtifact artifact={aiArtifact} />);
      expect(screen.getByText(/95%/)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible name for artifact", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(
        screen.getByRole("region", { name: /Hello Function/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible edit button", () => {
      render(<CanvasArtifact artifact={mockCodeArtifact} editable />);
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });
  });
});

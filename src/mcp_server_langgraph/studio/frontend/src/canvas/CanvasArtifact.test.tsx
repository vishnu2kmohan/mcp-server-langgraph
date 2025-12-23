/**
 * CanvasArtifact Tests - Phase 1 + Sprint 4 AI Enhancement
 *
 * Tests for the editable artifact component that renders
 * different content types (code, markdown, JSON, etc.)
 * Sprint 4: Added Redux Provider wrapping for AI features.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { CanvasArtifact } from "./CanvasArtifact";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";

// Mock the API module for AI features
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            code_analyze: {
              complexity: 12,
              quality_score: 0.78,
              issues: [
                {
                  type: "unused_variable",
                  message: "Variable 'temp' is declared but never used",
                  line: 3,
                  severity: "warning",
                },
              ],
              suggestions: [
                {
                  type: "refactor",
                  description: "Consider extracting repeated logic",
                  priority: "medium",
                },
              ],
              language: "javascript",
              lines_of_code: 45,
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.001",
        }),
    })),
    { isLoading: false },
  ]),
}));

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

// Wrapper with Redux Provider
interface WrapperProps {
  children: React.ReactNode;
}
const Wrapper = ({ children }: WrapperProps) => {
  const store = createTestStore();
  return <Provider store={store}>{children}</Provider>;
};

// Render with provider helper
const renderWithProvider = (ui: React.ReactElement) => {
  return render(ui, { wrapper: Wrapper });
};

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
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("canvas-artifact")).toBeInTheDocument();
    });

    it("should display artifact title", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText("Hello Function")).toBeInTheDocument();
    });

    it("should display version number", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText(/v1/)).toBeInTheDocument();
    });

    it("should display content type badge", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("content-type-badge")).toHaveTextContent(
        "code",
      );
    });
  });

  describe("Code Artifact", () => {
    it("should render code content in pre element", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByText(/function hello/)).toBeInTheDocument();
    });

    it("should display language badge for code artifacts", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(screen.getByTestId("language-badge")).toHaveTextContent(
        "javascript",
      );
    });

    it("should show line numbers when enabled", () => {
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} showLineNumbers />,
      );
      expect(screen.getByTestId("line-numbers")).toBeInTheDocument();
    });
  });

  describe("Markdown Artifact", () => {
    it("should render markdown content", () => {
      renderWithProvider(<CanvasArtifact artifact={mockMarkdownArtifact} />);
      expect(screen.getByText(/Hello World/)).toBeInTheDocument();
    });

    it("should render markdown as preview by default", () => {
      renderWithProvider(<CanvasArtifact artifact={mockMarkdownArtifact} />);
      expect(screen.getByTestId("markdown-preview")).toBeInTheDocument();
    });
  });

  describe("JSON Artifact", () => {
    it("should render JSON content", () => {
      renderWithProvider(<CanvasArtifact artifact={mockJsonArtifact} />);
      expect(screen.getByText(/"name"/)).toBeInTheDocument();
    });

    it("should format JSON with indentation", () => {
      renderWithProvider(<CanvasArtifact artifact={mockJsonArtifact} />);
      const content = screen.getByTestId("json-content");
      expect(content.textContent).toContain("name");
    });
  });

  describe("Editing", () => {
    it("should show edit button when editable", () => {
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} editable />,
      );
      expect(screen.getByTestId("edit-button")).toBeInTheDocument();
    });

    it("should enter edit mode when edit button clicked", () => {
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} editable />,
      );
      fireEvent.click(screen.getByTestId("edit-button"));
      expect(screen.getByTestId("content-editor")).toBeInTheDocument();
    });

    it("should call onChange when content edited", () => {
      const onChange = vi.fn();
      renderWithProvider(
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
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} editable isEditing />,
      );
      expect(screen.getByTestId("save-button")).toBeInTheDocument();
      expect(screen.getByTestId("cancel-button")).toBeInTheDocument();
    });

    it("should call onSave when save clicked", () => {
      const onSave = vi.fn();
      renderWithProvider(
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
      renderWithProvider(
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

      renderWithProvider(<CanvasArtifact artifact={aiArtifact} />);
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

      renderWithProvider(<CanvasArtifact artifact={aiArtifact} />);
      expect(screen.getByText(/95%/)).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have accessible name for artifact", () => {
      renderWithProvider(<CanvasArtifact artifact={mockCodeArtifact} />);
      expect(
        screen.getByRole("region", { name: /Hello Function/i }),
      ).toBeInTheDocument();
    });

    it("should have accessible edit button", () => {
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} editable />,
      );
      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });
  });

  describe("AI Code Analysis (Sprint 4)", () => {
    it("should show AI analysis panel when enabled for code artifacts", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.getByTestId("ai-code-analysis")).toBeInTheDocument();
      expect(screen.getByText("Code Analysis")).toBeInTheDocument();
    });

    it("should not show AI analysis panel when disabled", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          userId="test-user"
          enableAI={false}
        />,
      );

      expect(screen.queryByTestId("ai-code-analysis")).not.toBeInTheDocument();
    });

    it("should not show AI analysis panel without userId", () => {
      renderWithProvider(
        <CanvasArtifact artifact={mockCodeArtifact} enableAI={true} />,
      );

      expect(screen.queryByTestId("ai-code-analysis")).not.toBeInTheDocument();
    });

    it("should not show AI analysis panel for non-code artifacts", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockMarkdownArtifact}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.queryByTestId("ai-code-analysis")).not.toBeInTheDocument();
    });

    it("should display complexity score when available", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.getByTestId("complexity-score")).toBeInTheDocument();
    });

    it("should display quality score when available", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.getByTestId("quality-score")).toBeInTheDocument();
    });

    it("should display code issues when present", () => {
      renderWithProvider(
        <CanvasArtifact
          artifact={mockCodeArtifact}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.getByTestId("code-issues")).toBeInTheDocument();
    });
  });
});

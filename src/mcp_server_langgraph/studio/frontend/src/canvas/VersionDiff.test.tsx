/**
 * VersionDiff Tests
 *
 * TDD tests for artifact version diff view component.
 * Shows text differences between two versions.
 * Sprint 4: Added Redux Provider wrapping for AI features.
 */
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { VersionDiff } from "./VersionDiff";
import type { ArtifactVersion } from "../types/artifacts";

// Mock the API module for AI features
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            diff_explain: {
              summary: "Added authentication middleware",
              changes: [{ type: "addition", description: "New feature", impact: "medium" }],
              breaking_changes: false,
              affected_areas: ["auth"],
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

// Mock versions for testing
const createVersion = (
  version: number,
  content: string,
  editType: "user" | "ai-suggestion" | "ai-generation" = "user",
): ArtifactVersion => ({
  id: `v${version}`,
  artifactId: "artifact-1",
  version,
  content,
  createdAt: new Date(Date.now() - version * 86400000).toISOString(),
  createdBy: "user-1",
  metadata: { editType },
});

const baseVersion = createVersion(1, "function hello() {\n  return 'world';\n}");
const modifiedVersion = createVersion(
  2,
  "function hello() {\n  console.log('starting');\n  return 'world!';\n}",
);

describe("VersionDiff", () => {
  describe("rendering", () => {
    it("should render diff container", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      expect(screen.getByTestId("version-diff")).toBeInTheDocument();
    });

    it("should show version labels", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      expect(screen.getByText(/v1/)).toBeInTheDocument();
      expect(screen.getByText(/v2/)).toBeInTheDocument();
    });

    it("should display diff content", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      expect(screen.getByTestId("diff-content")).toBeInTheDocument();
    });
  });

  describe("diff display", () => {
    it("should show added lines", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      const diffContent = screen.getByTestId("diff-content");
      expect(diffContent.textContent).toContain("console.log");
    });

    it("should show removed lines", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={modifiedVersion}
          comparedVersion={baseVersion}
        />,
      );

      const diffContent = screen.getByTestId("diff-content");
      expect(diffContent.textContent).toContain("return");
    });

    it("should show unchanged lines", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      const diffContent = screen.getByTestId("diff-content");
      expect(diffContent.textContent).toContain("function hello()");
    });
  });

  describe("view modes", () => {
    it("should render unified diff by default", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      expect(screen.getByTestId("diff-content")).toHaveAttribute(
        "data-mode",
        "unified",
      );
    });

    it("should support split view mode", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          mode="split"
        />,
      );

      expect(screen.getByTestId("diff-content")).toHaveAttribute(
        "data-mode",
        "split",
      );
    });
  });

  describe("empty states", () => {
    it("should show no changes message when versions are identical", () => {
      renderWithProvider(
        <VersionDiff baseVersion={baseVersion} comparedVersion={baseVersion} />,
      );

      expect(screen.getByText(/no changes/i)).toBeInTheDocument();
    });
  });

  describe("actions", () => {
    it("should call onClose when close button clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();

      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          onClose={onClose}
        />,
      );

      const closeButton = screen.getByLabelText(/close/i);
      await user.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    it("should call onRestore when restore button clicked", async () => {
      const onRestore = vi.fn();
      const user = userEvent.setup();

      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          onRestore={onRestore}
        />,
      );

      const restoreButton = screen.getByRole("button", { name: /restore/i });
      await user.click(restoreButton);

      expect(onRestore).toHaveBeenCalledWith(baseVersion);
    });
  });

  describe("syntax highlighting", () => {
    it("should apply code styling", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
        />,
      );

      const diffContent = screen.getByTestId("diff-content");
      expect(diffContent).toHaveClass("font-mono");
    });
  });

  describe("AI features (Sprint 4)", () => {
    it("should show AI explanation panel when enabled", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          userId="test-user"
          sessionId="test-session"
          enableAI={true}
        />,
      );

      expect(screen.getByTestId("ai-diff-explanation")).toBeInTheDocument();
      expect(screen.getByText("AI Analysis")).toBeInTheDocument();
    });

    it("should not show AI panel when disabled", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          userId="test-user"
          enableAI={false}
        />,
      );

      expect(screen.queryByTestId("ai-diff-explanation")).not.toBeInTheDocument();
    });

    it("should not show AI panel without userId", () => {
      renderWithProvider(
        <VersionDiff
          baseVersion={baseVersion}
          comparedVersion={modifiedVersion}
          enableAI={true}
        />,
      );

      expect(screen.queryByTestId("ai-diff-explanation")).not.toBeInTheDocument();
    });
  });
});

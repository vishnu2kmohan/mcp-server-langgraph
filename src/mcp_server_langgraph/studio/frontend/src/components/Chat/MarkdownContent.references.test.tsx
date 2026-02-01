/**
 * MarkdownContent References Integration Tests
 *
 * Tests the [[type:qualifier:id]] markdown reference parsing and rendering.
 * Ensures references are transformed into ReferenceChip components.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { MarkdownContent } from "./MarkdownContent";
import { ReferenceResolverProvider as _ReferenceResolverProvider } from "@/contexts/ReferenceResolverContext";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { api } from "@/api";
import type {
  ParsedReference as _ParsedReference,
  ResolvedReference,
} from "@/types/references";

// Mock state - use object to allow mutation in tests
const mockState = {
  resolvedRefs: new Map<string, ResolvedReference>(),
  isLoading: false,
};

vi.mock("@/contexts/ReferenceResolverContext", () => ({
  useReferenceResolver: () => ({
    resolvedRefs: mockState.resolvedRefs,
    isLoading: mockState.isLoading,
    error: undefined,
    resolve: vi.fn(),
  }),
  ReferenceResolverProvider: ({ children }: { children: React.ReactNode }) =>
    children,
}));

// Create a minimal Redux store for RTK Query
function createTestStore() {
  return configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });
}

function renderWithProviders(content: string, isStreaming = false) {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <MarkdownContent
        content={content}
        enableInteractiveArtifacts={true}
        isStreaming={isStreaming}
      />
    </Provider>,
  );
}

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("MarkdownContent References", () => {
  beforeEach(() => {
    mockState.resolvedRefs.clear();
    mockState.isLoading = false;
    vi.clearAllMocks();
  });

  describe("Tool References", () => {
    it("should render tool reference as chip", () => {
      const content = "Use [[tool:filesystem:read_file]] to read files.";
      renderWithProviders(content);

      // The reference should be rendered as a button (ReferenceChip)
      const chip = screen.getByRole("button", {
        name: /tool reference.*filesystem.*read_file/i,
      });
      expect(chip).toBeInTheDocument();
    });

    it("should display tool name from reference", () => {
      const content = "Try [[tool:git:commit]]";
      renderWithProviders(content);

      // Should show the tool name "commit" (extracted from git:commit)
      expect(screen.getByText("commit")).toBeInTheDocument();
    });

    it("should render custom label when provided", () => {
      const content = "Use [[tool:filesystem:read_file|Read a File]] here.";
      renderWithProviders(content);

      expect(screen.getByText("Read a File")).toBeInTheDocument();
    });
  });

  describe("Skill References", () => {
    it("should render skill reference as chip", () => {
      const content = "Run [[skill:code-review]] on your code.";
      renderWithProviders(content);

      const chip = screen.getByRole("button", {
        name: /skill reference.*code-review/i,
      });
      expect(chip).toBeInTheDocument();
    });

    it("should display skill name", () => {
      const content = "Try [[skill:debug-assistant]]";
      renderWithProviders(content);

      expect(screen.getByText("debug-assistant")).toBeInTheDocument();
    });
  });

  describe("Artifact References", () => {
    it("should render artifact reference as chip", () => {
      const content = "See [[artifact:chart-123]] for details.";
      renderWithProviders(content);

      const chip = screen.getByRole("button", {
        name: /artifact reference.*chart-123/i,
      });
      expect(chip).toBeInTheDocument();
    });
  });

  describe("Code Block Exclusion", () => {
    it("should NOT parse references inside fenced code blocks", () => {
      const content = `Here's how to use it:

\`\`\`markdown
Use [[tool:example:test]] syntax
\`\`\`

That's the syntax.`;

      renderWithProviders(content);

      // The reference inside code block should remain as text, not a chip
      // There should be no button for this reference
      const buttons = screen.queryAllByRole("button");
      expect(buttons.length).toBe(0);
    });

    it("should NOT parse references inside inline code", () => {
      const content = "Use `[[tool:example:test]]` syntax for references.";
      renderWithProviders(content);

      // The reference inside inline code should remain as text
      const buttons = screen.queryAllByRole("button");
      expect(buttons.length).toBe(0);
    });
  });

  describe("Multiple References", () => {
    it("should render multiple references in same paragraph", () => {
      const content = "Use [[tool:fs:read]] and [[tool:fs:write]] together.";
      renderWithProviders(content);

      expect(screen.getByText("read")).toBeInTheDocument();
      expect(screen.getByText("write")).toBeInTheDocument();
    });

    it("should render mixed reference types", () => {
      const content =
        "Run [[skill:review]], use [[tool:git:commit]], check [[artifact:report-1]].";
      renderWithProviders(content);

      // All three types should be rendered
      expect(screen.getByText("review")).toBeInTheDocument();
      expect(screen.getByText("commit")).toBeInTheDocument();
      expect(screen.getByText("report-1")).toBeInTheDocument();
    });
  });

  describe("Invalid References", () => {
    it("should not parse tool reference without colon separator", () => {
      const content = "Invalid [[tool:missingname]] reference.";
      renderWithProviders(content);

      // This should NOT be parsed as a valid tool reference
      // (tools require server:name format)
      const buttons = screen.queryAllByRole("button");
      expect(buttons.length).toBe(0);
    });

    it("should not parse malformed references", () => {
      const content = "Try [[invalid:type:id]] or [single bracket].";
      renderWithProviders(content);

      // Invalid type should not create a chip
      const buttons = screen.queryAllByRole("button");
      expect(buttons.length).toBe(0);
    });
  });

  describe("Reference Resolution Status", () => {
    it("should show loading state for unresolved reference", () => {
      // Set loading state with no resolved refs
      mockState.resolvedRefs.clear();
      mockState.isLoading = true;

      const content = "Use [[tool:fs:read]] here.";
      renderWithProviders(content);

      const chip = screen.getByRole("button");
      // Loading state should have animate-pulse class
      expect(chip.className).toContain("animate-pulse");
    });

    it("should show valid state for resolved reference", () => {
      // Add a resolved ref
      mockState.resolvedRefs.set("tool:fs:read", {
        type: "tool",
        qualifier: "fs",
        id: "read",
        displayName: "Read File",
        description: "Read a file from the filesystem",
        status: "valid",
        metadata: { connectionId: "conn-123" },
      });

      const content = "Use [[tool:fs:read]] here.";
      renderWithProviders(content);

      const chip = screen.getByRole("button");
      // Should show the resolved display name
      expect(screen.getByText("Read File")).toBeInTheDocument();
      // Should not be disabled
      expect(chip).not.toBeDisabled();
    });

    it("should show not_found state with line-through", () => {
      mockState.resolvedRefs.set("tool:missing:tool", {
        type: "tool",
        qualifier: "missing",
        id: "tool",
        displayName: "tool",
        status: "not_found",
      });

      const content = "Try [[tool:missing:tool]].";
      renderWithProviders(content);

      const chip = screen.getByRole("button");
      expect(chip.className).toContain("line-through");
      expect(chip).toBeDisabled();
    });

    it("should show unauthorized state", () => {
      mockState.resolvedRefs.set("tool:restricted:secret", {
        type: "tool",
        qualifier: "restricted",
        id: "secret",
        displayName: "secret",
        status: "unauthorized",
      });

      const content = "Try [[tool:restricted:secret]].";
      renderWithProviders(content);

      const chip = screen.getByRole("button");
      expect(chip.className).toContain("opacity-50");
      expect(chip).toBeDisabled();
    });
  });

  describe("Surrounding Text", () => {
    it("should preserve text before and after reference", () => {
      const content = "Start here [[tool:fs:read]] and continue.";
      renderWithProviders(content);

      // The text around the reference should still be present
      expect(screen.getByText(/Start here/)).toBeInTheDocument();
      expect(screen.getByText(/and continue/)).toBeInTheDocument();
    });

    it("should work in list items", () => {
      const content = `- Use [[tool:fs:read]] for reading
- Use [[tool:fs:write]] for writing`;
      renderWithProviders(content);

      expect(screen.getByText("read")).toBeInTheDocument();
      expect(screen.getByText("write")).toBeInTheDocument();
    });

    it("should work in blockquotes", () => {
      const content = "> Try using [[skill:helper]] for assistance.";
      renderWithProviders(content);

      expect(screen.getByText("helper")).toBeInTheDocument();
    });
  });
});

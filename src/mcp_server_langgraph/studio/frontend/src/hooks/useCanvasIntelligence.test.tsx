/**
 * Tests for useCanvasIntelligence hooks.
 *
 * Sprint 4: Canvas + Diagram Intelligence
 * - Artifact type suggestion suggests optimal artifact type for content
 * - Code analysis provides real-time code quality metrics
 * - Diff explanation explains changes between versions
 * - Diagram analysis validates and analyzes Mermaid diagrams
 * - Diagram-to-code generates code from flowcharts/sequence diagrams
 *
 * TDD: Tests written FIRST before implementation.
 * NOTE: Consolidated tests to reduce memory footprint.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Mock the API module - single mock at top level to avoid memory leaks
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            artifact_suggest_type: {
              suggested_type: "mermaid",
              confidence: 0.95,
              alternatives: [
                { type: "code", confidence: 0.3 },
                { type: "markdown", confidence: 0.1 },
              ],
              reason:
                "Content contains flowchart syntax with graph TB declaration",
            },
            code_analyze: {
              complexity: 8,
              quality_score: 0.85,
              issues: [
                {
                  type: "unused_variable",
                  message: "Variable 'temp' is declared but never used",
                  line: 15,
                  severity: "warning",
                },
              ],
              suggestions: [
                {
                  type: "refactor",
                  description: "Extract repeated logic into a helper function",
                  priority: "medium",
                },
              ],
              language: "typescript",
              lines_of_code: 120,
            },
            diff_explain: {
              summary:
                "Added authentication middleware and updated error handling",
              changes: [
                {
                  type: "addition",
                  description: "New JWT validation middleware",
                  impact: "high",
                },
                {
                  type: "modification",
                  description: "Improved error response formatting",
                  impact: "medium",
                },
              ],
              breaking_changes: false,
              affected_areas: ["auth", "error-handling"],
            },
            diagram_analyze: {
              diagram_type: "flowchart",
              is_valid: true,
              node_count: 8,
              edge_count: 10,
              complexity_score: 0.6,
              issues: [],
              suggestions: [
                {
                  type: "simplify",
                  description: "Consider splitting this into two diagrams",
                },
              ],
            },
            diagram_to_code: {
              code: `async function loginFlow(user, password) {
  const isValid = await validateCredentials(user, password);
  if (!isValid) {
    throw new Error("Invalid credentials");
  }
  const token = await generateToken(user);
  return { success: true, token };
}`,
              language: "typescript",
              confidence: 0.88,
              explanation:
                "Generated TypeScript function based on the login flowchart with validation and token generation steps",
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.002",
        }),
    })),
    { isLoading: false },
  ]),
}));

// =============================================================================
// Test Utilities
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = () => {
  const store = createTestStore();
  return function Wrapper({ children }: WrapperProps) {
    return <Provider store={store}>{children}</Provider>;
  };
};

// =============================================================================
// Consolidated Hook Tests (memory-optimized)
// =============================================================================

describe("Canvas Intelligence Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("useArtifactTypeSuggestion", () => {
    it("returns suggested artifact type with confidence", async () => {
      const { useArtifactTypeSuggestion } =
        await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useArtifactTypeSuggestion({
            userId: "test-user",
            sessionId: "session-123",
            content: "graph TB\n  A[Start] --> B[Process]\n  B --> C[End]",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestedType).toBe("mermaid");
      expect(result.current.confidence).toBe(0.95);
      expect(result.current.alternatives).toHaveLength(2);
      expect(result.current.reason).toContain("flowchart syntax");
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useArtifactTypeSuggestion } =
        await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useArtifactTypeSuggestion({
            userId: "test-user",
            sessionId: "session-123",
            content: "test",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.suggestedType).toBeNull();
    });

    it("handles empty content", async () => {
      const { useArtifactTypeSuggestion } =
        await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useArtifactTypeSuggestion({
            userId: "test-user",
            sessionId: "session-123",
            content: "",
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.suggestedType).toBeNull();
    });
  });

  describe("useCodeAnalysis", () => {
    it("returns code quality metrics and issues", async () => {
      const { useCodeAnalysis } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useCodeAnalysis({
            userId: "test-user",
            sessionId: "session-123",
            code: "function test() { const temp = 1; return 2; }",
            language: "typescript",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.complexity).toBe(8);
      expect(result.current.qualityScore).toBe(0.85);
      expect(result.current.issues).toHaveLength(1);
      expect(result.current.issues[0].type).toBe("unused_variable");
      expect(result.current.suggestions).toHaveLength(1);
      expect(result.current.language).toBe("typescript");
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useCodeAnalysis } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useCodeAnalysis({
            userId: "test-user",
            sessionId: "session-123",
            code: "test",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.qualityScore).toBeNull();
    });
  });

  describe("useDiffExplanation", () => {
    it("returns diff explanation with changes", async () => {
      const { useDiffExplanation } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiffExplanation({
            userId: "test-user",
            sessionId: "session-123",
            oldContent: "function old() {}",
            newContent: "function new() { auth(); }",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.summary).toContain("authentication middleware");
      expect(result.current.changes).toHaveLength(2);
      expect(result.current.breakingChanges).toBe(false);
      expect(result.current.affectedAreas).toContain("auth");
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useDiffExplanation } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiffExplanation({
            userId: "test-user",
            sessionId: "session-123",
            oldContent: "a",
            newContent: "b",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.summary).toBeNull();
    });
  });

  describe("useDiagramAnalysis", () => {
    it("returns diagram analysis with validation", async () => {
      const { useDiagramAnalysis } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiagramAnalysis({
            userId: "test-user",
            sessionId: "session-123",
            diagramCode: "graph TB\n  A --> B\n  B --> C",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.diagramType).toBe("flowchart");
      expect(result.current.isValid).toBe(true);
      expect(result.current.nodeCount).toBe(8);
      expect(result.current.edgeCount).toBe(10);
      expect(result.current.complexityScore).toBe(0.6);
      expect(result.current.suggestions).toHaveLength(1);
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useDiagramAnalysis } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiagramAnalysis({
            userId: "test-user",
            sessionId: "session-123",
            diagramCode: "graph TB",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.diagramType).toBeNull();
    });
  });

  describe("useDiagramToCode", () => {
    it("returns generated code from diagram", async () => {
      const { useDiagramToCode } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiagramToCode({
            userId: "test-user",
            sessionId: "session-123",
            diagramCode:
              "graph TB\n  A[Login] --> B{Valid?}\n  B -->|Yes| C[Token]",
            targetLanguage: "typescript",
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.code).toContain("async function loginFlow");
      expect(result.current.language).toBe("typescript");
      expect(result.current.confidence).toBe(0.88);
      expect(result.current.explanation).toContain("login flowchart");
      expect(typeof result.current.refetch).toBe("function");
    });

    it("handles disabled state", async () => {
      const { useDiagramToCode } = await import("./useCanvasIntelligence");

      const { result } = renderHook(
        () =>
          useDiagramToCode({
            userId: "test-user",
            sessionId: "session-123",
            diagramCode: "graph TB",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.code).toBeNull();
    });
  });
});

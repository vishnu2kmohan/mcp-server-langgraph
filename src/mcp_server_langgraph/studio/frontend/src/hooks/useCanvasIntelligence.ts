/**
 * Canvas Intelligence Hooks
 *
 * Sprint 4: Canvas + Diagram Intelligence
 * - Artifact type suggestion suggests optimal artifact type for content
 * - Code analysis provides real-time code quality metrics
 * - Diff explanation explains changes between versions
 * - Diagram analysis validates and analyzes Mermaid diagrams
 * - Diagram-to-code generates code from flowcharts/sequence diagrams
 *
 * These hooks use the unified StudioOrchestrator via RTK Query.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface ArtifactTypeSuggestionOptions {
  userId: string;
  sessionId: string;
  content: string;
  enabled?: boolean;
  /**
   * Whether to auto-fetch when dependencies change.
   * When false, only fetches when refetch() is called explicitly.
   * @default false (opt-in pattern)
   */
  autoFetch?: boolean;
}

export interface ArtifactTypeAlternative {
  type: string;
  confidence: number;
}

export interface ArtifactTypeSuggestionResult {
  suggestedType: string | null;
  confidence: number | null;
  alternatives: ArtifactTypeAlternative[];
  reason: string | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface CodeAnalysisOptions {
  userId: string;
  sessionId: string;
  code: string;
  language?: string;
  enabled?: boolean;
  /** @default false */
  autoFetch?: boolean;
}

export interface CodeIssue {
  type: string;
  message: string;
  line?: number;
  severity: "error" | "warning" | "info";
}

export interface CodeSuggestion {
  type: string;
  description: string;
  priority: "high" | "medium" | "low";
}

export interface CodeAnalysisResult {
  complexity: number | null;
  qualityScore: number | null;
  issues: CodeIssue[];
  suggestions: CodeSuggestion[];
  language: string | null;
  linesOfCode: number | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface DiffExplanationOptions {
  userId: string;
  sessionId: string;
  oldContent: string;
  newContent: string;
  enabled?: boolean;
  /** @default false */
  autoFetch?: boolean;
}

export interface DiffChange {
  type: "addition" | "modification" | "deletion";
  description: string;
  impact: "high" | "medium" | "low";
}

export interface DiffExplanationResult {
  summary: string | null;
  changes: DiffChange[];
  breakingChanges: boolean | null;
  affectedAreas: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface DiagramAnalysisOptions {
  userId: string;
  sessionId: string;
  diagramCode: string;
  enabled?: boolean;
  /** @default false */
  autoFetch?: boolean;
}

export interface DiagramSuggestion {
  type: string;
  description: string;
}

export interface DiagramIssue {
  type: string;
  message: string;
  line?: number;
}

export interface DiagramAnalysisResult {
  diagramType: string | null;
  isValid: boolean | null;
  nodeCount: number | null;
  edgeCount: number | null;
  complexityScore: number | null;
  issues: DiagramIssue[];
  suggestions: DiagramSuggestion[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface DiagramToCodeOptions {
  userId: string;
  sessionId: string;
  diagramCode: string;
  targetLanguage?: string;
  enabled?: boolean;
  /** @default false */
  autoFetch?: boolean;
}

export interface DiagramToCodeResult {
  code: string | null;
  language: string | null;
  confidence: number | null;
  explanation: string | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// =============================================================================
// useArtifactTypeSuggestion
// =============================================================================

/**
 * Hook for suggesting optimal artifact type for content.
 *
 * Uses the StudioOrchestrator's artifact_suggest_type task type to analyze
 * content and suggest the best artifact type (code, mermaid, json, etc.).
 *
 * @param options - Configuration options
 * @returns Artifact type suggestion with confidence score
 */
export function useArtifactTypeSuggestion(
  options: ArtifactTypeSuggestionOptions,
): ArtifactTypeSuggestionResult {
  const {
    userId,
    sessionId,
    content,
    enabled = true,
    autoFetch = false,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    suggestedType: string | null;
    confidence: number | null;
    alternatives: ArtifactTypeAlternative[];
    reason: string | null;
    error: Error | null;
  }>({
    suggestedType: null,
    confidence: null,
    alternatives: [],
    reason: null,
    error: null,
  });

  const fetchSuggestion = useCallback(async () => {
    if (!enabled || !content.trim()) {
      setResult({
        suggestedType: null,
        confidence: null,
        alternatives: [],
        reason: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "canvas",
            type: "artifact_suggest_type",
            data: { content },
          },
        ],
      }).unwrap();

      const suggestionResult = response.analyses?.artifact_suggest_type as
        | {
            suggested_type?: string;
            confidence?: number;
            alternatives?: { type: string; confidence: number }[];
            reason?: string;
          }
        | undefined;

      if (suggestionResult) {
        setResult({
          suggestedType: suggestionResult.suggested_type || null,
          confidence: suggestionResult.confidence ?? null,
          alternatives: suggestionResult.alternatives || [],
          reason: suggestionResult.reason || null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, content, enabled]);

  useEffect(() => {
    // Only auto-fetch when autoFetch is true (default behavior)
    if (autoFetch) {
      fetchSuggestion();
    }
  }, [fetchSuggestion, autoFetch]);

  return useMemo(
    () => ({
      suggestedType: result.suggestedType,
      confidence: result.confidence,
      alternatives: result.alternatives,
      reason: result.reason,
      isLoading,
      error: result.error,
      refetch: fetchSuggestion,
    }),
    [result, isLoading, fetchSuggestion],
  );
}

// =============================================================================
// useCodeAnalysis
// =============================================================================

/**
 * Hook for analyzing code quality and complexity.
 *
 * Uses the StudioOrchestrator's code_analyze task type to provide
 * real-time code quality metrics, issues, and suggestions.
 *
 * @param options - Configuration options
 * @returns Code analysis results with metrics and suggestions
 */
export function useCodeAnalysis(
  options: CodeAnalysisOptions,
): CodeAnalysisResult {
  const {
    userId,
    sessionId,
    code,
    language,
    enabled = true,
    autoFetch = false,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    complexity: number | null;
    qualityScore: number | null;
    issues: CodeIssue[];
    suggestions: CodeSuggestion[];
    language: string | null;
    linesOfCode: number | null;
    error: Error | null;
  }>({
    complexity: null,
    qualityScore: null,
    issues: [],
    suggestions: [],
    language: null,
    linesOfCode: null,
    error: null,
  });

  const fetchAnalysis = useCallback(async () => {
    if (!enabled || !code.trim()) {
      setResult({
        complexity: null,
        qualityScore: null,
        issues: [],
        suggestions: [],
        language: null,
        linesOfCode: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "canvas",
            type: "code_analyze",
            data: { code, language },
          },
        ],
      }).unwrap();

      const analysisResult = response.analyses?.code_analyze as
        | {
            complexity?: number;
            quality_score?: number;
            issues?: {
              type: string;
              message: string;
              line?: number;
              severity: "error" | "warning" | "info";
            }[];
            suggestions?: {
              type: string;
              description: string;
              priority: "high" | "medium" | "low";
            }[];
            language?: string;
            lines_of_code?: number;
          }
        | undefined;

      if (analysisResult) {
        setResult({
          complexity: analysisResult.complexity ?? null,
          qualityScore: analysisResult.quality_score ?? null,
          issues: analysisResult.issues || [],
          suggestions: analysisResult.suggestions || [],
          language: analysisResult.language || null,
          linesOfCode: analysisResult.lines_of_code ?? null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, code, language, enabled]);

  useEffect(() => {
    if (autoFetch) {
      fetchAnalysis();
    }
  }, [fetchAnalysis, autoFetch]);

  return useMemo(
    () => ({
      complexity: result.complexity,
      qualityScore: result.qualityScore,
      issues: result.issues,
      suggestions: result.suggestions,
      language: result.language,
      linesOfCode: result.linesOfCode,
      isLoading,
      error: result.error,
      refetch: fetchAnalysis,
    }),
    [result, isLoading, fetchAnalysis],
  );
}

// =============================================================================
// useDiffExplanation
// =============================================================================

/**
 * Hook for explaining changes between versions.
 *
 * Uses the StudioOrchestrator's diff_explain task type to generate
 * natural language explanations of code changes.
 *
 * @param options - Configuration options
 * @returns Diff explanation with change summary
 */
export function useDiffExplanation(
  options: DiffExplanationOptions,
): DiffExplanationResult {
  const {
    userId,
    sessionId,
    oldContent,
    newContent,
    enabled = true,
    autoFetch = false,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    summary: string | null;
    changes: DiffChange[];
    breakingChanges: boolean | null;
    affectedAreas: string[];
    error: Error | null;
  }>({
    summary: null,
    changes: [],
    breakingChanges: null,
    affectedAreas: [],
    error: null,
  });

  const fetchExplanation = useCallback(async () => {
    if (!enabled) {
      setResult({
        summary: null,
        changes: [],
        breakingChanges: null,
        affectedAreas: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "canvas",
            type: "diff_explain",
            data: { old_content: oldContent, new_content: newContent },
          },
        ],
      }).unwrap();

      const diffResult = response.analyses?.diff_explain as
        | {
            summary?: string;
            changes?: {
              type: "addition" | "modification" | "deletion";
              description: string;
              impact: "high" | "medium" | "low";
            }[];
            breaking_changes?: boolean;
            affected_areas?: string[];
          }
        | undefined;

      if (diffResult) {
        setResult({
          summary: diffResult.summary || null,
          changes: diffResult.changes || [],
          breakingChanges: diffResult.breaking_changes ?? null,
          affectedAreas: diffResult.affected_areas || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, oldContent, newContent, enabled]);

  useEffect(() => {
    if (autoFetch) {
      fetchExplanation();
    }
  }, [fetchExplanation, autoFetch]);

  return useMemo(
    () => ({
      summary: result.summary,
      changes: result.changes,
      breakingChanges: result.breakingChanges,
      affectedAreas: result.affectedAreas,
      isLoading,
      error: result.error,
      refetch: fetchExplanation,
    }),
    [result, isLoading, fetchExplanation],
  );
}

// =============================================================================
// useDiagramAnalysis
// =============================================================================

/**
 * Hook for analyzing Mermaid diagrams.
 *
 * Uses the StudioOrchestrator's diagram_analyze task type to validate
 * diagram syntax and provide analysis of structure and complexity.
 *
 * @param options - Configuration options
 * @returns Diagram analysis with validation and metrics
 */
export function useDiagramAnalysis(
  options: DiagramAnalysisOptions,
): DiagramAnalysisResult {
  const {
    userId,
    sessionId,
    diagramCode,
    enabled = true,
    autoFetch = false,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    diagramType: string | null;
    isValid: boolean | null;
    nodeCount: number | null;
    edgeCount: number | null;
    complexityScore: number | null;
    issues: DiagramIssue[];
    suggestions: DiagramSuggestion[];
    error: Error | null;
  }>({
    diagramType: null,
    isValid: null,
    nodeCount: null,
    edgeCount: null,
    complexityScore: null,
    issues: [],
    suggestions: [],
    error: null,
  });

  const fetchAnalysis = useCallback(async () => {
    if (!enabled || !diagramCode.trim()) {
      setResult({
        diagramType: null,
        isValid: null,
        nodeCount: null,
        edgeCount: null,
        complexityScore: null,
        issues: [],
        suggestions: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "diagram",
            type: "diagram_analyze",
            data: { diagram_code: diagramCode },
          },
        ],
      }).unwrap();

      const analysisResult = response.analyses?.diagram_analyze as
        | {
            diagram_type?: string;
            is_valid?: boolean;
            node_count?: number;
            edge_count?: number;
            complexity_score?: number;
            issues?: { type: string; message: string; line?: number }[];
            suggestions?: { type: string; description: string }[];
          }
        | undefined;

      if (analysisResult) {
        setResult({
          diagramType: analysisResult.diagram_type || null,
          isValid: analysisResult.is_valid ?? null,
          nodeCount: analysisResult.node_count ?? null,
          edgeCount: analysisResult.edge_count ?? null,
          complexityScore: analysisResult.complexity_score ?? null,
          issues: analysisResult.issues || [],
          suggestions: analysisResult.suggestions || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, diagramCode, enabled]);

  useEffect(() => {
    if (autoFetch) {
      fetchAnalysis();
    }
  }, [fetchAnalysis, autoFetch]);

  return useMemo(
    () => ({
      diagramType: result.diagramType,
      isValid: result.isValid,
      nodeCount: result.nodeCount,
      edgeCount: result.edgeCount,
      complexityScore: result.complexityScore,
      issues: result.issues,
      suggestions: result.suggestions,
      isLoading,
      error: result.error,
      refetch: fetchAnalysis,
    }),
    [result, isLoading, fetchAnalysis],
  );
}

// =============================================================================
// useDiagramToCode
// =============================================================================

/**
 * Hook for generating code from diagrams.
 *
 * Uses the StudioOrchestrator's diagram_to_code task type to convert
 * flowcharts and sequence diagrams into executable code.
 *
 * @param options - Configuration options
 * @returns Generated code with explanation
 */
export function useDiagramToCode(
  options: DiagramToCodeOptions,
): DiagramToCodeResult {
  const {
    userId,
    sessionId,
    diagramCode,
    targetLanguage,
    enabled = true,
    autoFetch = false,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    code: string | null;
    language: string | null;
    confidence: number | null;
    explanation: string | null;
    error: Error | null;
  }>({
    code: null,
    language: null,
    confidence: null,
    explanation: null,
    error: null,
  });

  const fetchCode = useCallback(async () => {
    if (!enabled || !diagramCode.trim()) {
      setResult({
        code: null,
        language: null,
        confidence: null,
        explanation: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "diagram",
            type: "diagram_to_code",
            data: {
              diagram_code: diagramCode,
              target_language: targetLanguage,
            },
          },
        ],
      }).unwrap();

      const codeResult = response.analyses?.diagram_to_code as
        | {
            code?: string;
            language?: string;
            confidence?: number;
            explanation?: string;
          }
        | undefined;

      if (codeResult) {
        setResult({
          code: codeResult.code || null,
          language: codeResult.language || null,
          confidence: codeResult.confidence ?? null,
          explanation: codeResult.explanation || null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [
    analyzeMutation,
    userId,
    sessionId,
    diagramCode,
    targetLanguage,
    enabled,
  ]);

  useEffect(() => {
    if (autoFetch) {
      fetchCode();
    }
  }, [fetchCode, autoFetch]);

  return useMemo(
    () => ({
      code: result.code,
      language: result.language,
      confidence: result.confidence,
      explanation: result.explanation,
      isLoading,
      error: result.error,
      refetch: fetchCode,
    }),
    [result, isLoading, fetchCode],
  );
}

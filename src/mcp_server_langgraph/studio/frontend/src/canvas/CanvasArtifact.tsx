/**
 * CanvasArtifact - Phase 1 + Sprint 4 AI Enhancement
 *
 * Editable artifact component that renders different content types
 * (code, markdown, JSON, etc.) with editing capabilities.
 *
 * Features:
 * - Code, markdown, JSON content rendering
 * - Inline editing with save/cancel
 * - AI-powered code analysis (Sprint 4)
 */
import { useState, useCallback, useMemo } from "react";
import { Edit2, Save, X, Sparkles, Loader2, AlertTriangle, CheckCircle2 } from "lucide-react";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useCodeAnalysis } from "../hooks";

// =============================================================================
// Types
// =============================================================================

export interface CanvasArtifactProps {
  /** The artifact to display */
  artifact: CanvasArtifactType;
  /** Whether the artifact is editable */
  editable?: boolean;
  /** Whether currently in edit mode */
  isEditing?: boolean;
  /** Show line numbers for code */
  showLineNumbers?: boolean;
  /** Callback when content changes */
  onChange?: (content: string) => void;
  /** Callback when save is clicked */
  onSave?: () => void;
  /** Callback when cancel is clicked */
  onCancel?: () => void;
  /** Callback when edit mode is entered */
  onEdit?: () => void;
  /** Custom aria-label for the region (for unique landmark identification) */
  ariaLabel?: string;
  /** Additional class name */
  className?: string;
  /** User ID for AI features (Sprint 4) */
  userId?: string;
  /** Session ID for AI features (Sprint 4) */
  sessionId?: string;
  /** Enable AI-powered code analysis (Sprint 4) */
  enableAI?: boolean;
}

// =============================================================================
// Utility
// =============================================================================

function formatJson(content: string): string {
  try {
    return JSON.stringify(JSON.parse(content), null, 2);
  } catch {
    return content;
  }
}

// =============================================================================
// Line Numbers Component
// =============================================================================

function LineNumbers({ content }: { content: string }) {
  const lines = content.split("\n").length;
  return (
    <div
      data-testid="line-numbers"
      className="select-none pr-3 mr-3 border-r border-gray-300 dark:border-gray-600 text-gray-400 text-right"
    >
      {Array.from({ length: lines }, (_, i) => (
        <div key={i + 1}>{i + 1}</div>
      ))}
    </div>
  );
}

// =============================================================================
// Component
// =============================================================================

export function CanvasArtifact({
  artifact,
  editable = false,
  isEditing: isEditingProp,
  showLineNumbers = false,
  onChange,
  onSave,
  onCancel,
  onEdit,
  ariaLabel,
  className,
  userId,
  sessionId,
  enableAI = false,
}: CanvasArtifactProps) {
  // Manage edit state internally if not controlled by parent
  const [internalEditing, setInternalEditing] = useState(false);
  const isEditing =
    isEditingProp !== undefined ? isEditingProp : internalEditing;

  const [editContent, setEditContent] = useState(artifact.content);

  const isAIGenerated =
    artifact.editMetadata?.editedBy === "ai-generation" ||
    artifact.editMetadata?.editedBy === "ai-suggestion";

  const aiConfidence = artifact.editMetadata?.aiConfidence;
  const language = artifact.editMetadata?.language;

  // Determine if this is a code artifact that can be analyzed
  const isCodeArtifact = artifact.contentType === "code";

  // Sprint 4: AI-powered code analysis
  const {
    complexity: aiComplexity,
    qualityScore: aiQualityScore,
    issues: aiIssues,
    suggestions: aiSuggestions,
    isLoading: aiLoading,
    error: aiError,
    refetch: refetchAI,
  } = useCodeAnalysis({
    userId: userId ?? "anonymous",
    sessionId: sessionId ?? "",
    code: artifact.content,
    language: language ?? undefined,
    enabled: enableAI && isCodeArtifact && !!userId && !!sessionId,
  });

  const handleContentChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const newContent = e.target.value;
      setEditContent(newContent);
      onChange?.(newContent);
    },
    [onChange],
  );

  const handleEdit = useCallback(() => {
    setEditContent(artifact.content);
    if (isEditingProp === undefined) {
      setInternalEditing(true);
    }
    onEdit?.();
  }, [artifact.content, onEdit, isEditingProp]);

  const handleCancel = useCallback(() => {
    setEditContent(artifact.content);
    if (isEditingProp === undefined) {
      setInternalEditing(false);
    }
    onCancel?.();
  }, [artifact.content, onCancel, isEditingProp]);

  const handleSave = useCallback(() => {
    if (isEditingProp === undefined) {
      setInternalEditing(false);
    }
    onSave?.();
  }, [onSave, isEditingProp]);

  const formattedContent = useMemo(() => {
    if (artifact.contentType === "json") {
      return formatJson(artifact.content);
    }
    return artifact.content;
  }, [artifact.content, artifact.contentType]);

  const renderContent = () => {
    if (isEditing) {
      return (
        <textarea
          data-testid="content-editor"
          value={editContent}
          onChange={handleContentChange}
          className={cn(
            "w-full h-64 p-4 font-mono text-sm",
            "bg-gray-50 dark:bg-gray-900 rounded-lg",
            "border border-gray-200 dark:border-gray-700",
            "focus:outline-none focus:ring-2 focus:ring-primary-500",
            "resize-y",
          )}
        />
      );
    }

    switch (artifact.contentType) {
      case "markdown":
        return (
          <div
            data-testid="markdown-preview"
            className="prose dark:prose-invert max-w-none"
          >
            {/* Simple markdown rendering - would use react-markdown in production */}
            <div dangerouslySetInnerHTML={{ __html: artifact.content }} />
          </div>
        );

      case "json":
        return (
          <pre
            data-testid="json-content"
            className={cn(
              "p-4 rounded-lg text-sm overflow-auto",
              "bg-gray-50 dark:bg-gray-900",
              "text-gray-800 dark:text-gray-200",
              "font-mono",
            )}
          >
            {formattedContent}
          </pre>
        );

      case "code":
      default:
        return (
          <div className="flex">
            {showLineNumbers && <LineNumbers content={artifact.content} />}
            <pre
              className={cn(
                "flex-1 p-4 rounded-lg text-sm overflow-auto",
                "bg-gray-50 dark:bg-gray-900",
                "text-gray-800 dark:text-gray-200",
                "font-mono",
              )}
            >
              {artifact.content}
            </pre>
          </div>
        );
    }
  };

  return (
    <div
      data-testid="canvas-artifact"
      role="region"
      aria-label={ariaLabel || artifact.title || "Artifact"}
      className={cn(
        "flex flex-col rounded-lg border",
        "bg-white dark:bg-gray-800",
        "border-gray-200 dark:border-gray-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-gray-800 dark:text-gray-200">
            {artifact.title || "Untitled"}
          </h3>
          <span
            data-testid="content-type-badge"
            className="px-1.5 py-0.5 text-xs rounded bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
          >
            {artifact.contentType}
          </span>
          {language && (
            <span
              data-testid="language-badge"
              className="px-1.5 py-0.5 text-xs rounded bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
            >
              {language}
            </span>
          )}
          {isAIGenerated && (
            <span
              data-testid="ai-badge"
              className="flex items-center gap-1 px-1.5 py-0.5 text-xs rounded bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400"
            >
              <Sparkles size={10} />
              AI
              {aiConfidence !== undefined && (
                <span className="ml-0.5">
                  {Math.round(aiConfidence * 100)}%
                </span>
              )}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">v{artifact.version}</span>
          {editable && !isEditing && (
            <button
              data-testid="edit-button"
              type="button"
              onClick={handleEdit}
              aria-label="Edit artifact"
              className={cn(
                "p-1.5 rounded transition-colors",
                "text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200",
                "hover:bg-gray-100 dark:hover:bg-gray-700",
              )}
            >
              <Edit2 size={14} />
            </button>
          )}
          {isEditing && (
            <>
              <button
                data-testid="save-button"
                type="button"
                onClick={handleSave}
                aria-label="Save changes"
                className={cn(
                  "p-1.5 rounded transition-colors",
                  "text-green-600 hover:text-green-700",
                  "hover:bg-green-100 dark:hover:bg-green-900/30",
                )}
              >
                <Save size={14} />
              </button>
              <button
                data-testid="cancel-button"
                type="button"
                onClick={handleCancel}
                aria-label="Cancel editing"
                className={cn(
                  "p-1.5 rounded transition-colors",
                  "text-red-600 hover:text-red-700",
                  "hover:bg-red-100 dark:hover:bg-red-900/30",
                )}
              >
                <X size={14} />
              </button>
            </>
          )}
        </div>
      </div>

      {/* AI Code Analysis Panel (Sprint 4) */}
      {enableAI && userId && isCodeArtifact && (
        <div
          data-testid="ai-code-analysis"
          className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-primary-500" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              Code Analysis
            </span>
            {aiLoading && (
              <Loader2 size={14} className="animate-spin text-primary-500" />
            )}
            {aiError && (
              <button
                type="button"
                onClick={() => refetchAI()}
                className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
              >
                Retry
              </button>
            )}
          </div>

          {aiLoading && (
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Analyzing code...
            </p>
          )}

          {aiError && (
            <p className="text-sm text-red-600 dark:text-red-400">
              Failed to analyze code. Click retry to try again.
            </p>
          )}

          {!aiLoading && !aiError && (
            <div className="space-y-2">
              {/* Metrics Row */}
              <div className="flex items-center gap-4">
                {aiComplexity !== null && (
                  <div
                    data-testid="complexity-score"
                    className="flex items-center gap-1.5"
                  >
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Complexity:
                    </span>
                    <span
                      className={cn(
                        "px-1.5 py-0.5 text-xs font-medium rounded",
                        aiComplexity <= 10
                          ? "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300"
                          : aiComplexity <= 20
                            ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                            : "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300",
                      )}
                    >
                      {aiComplexity}
                    </span>
                  </div>
                )}

                {aiQualityScore !== null && (
                  <div
                    data-testid="quality-score"
                    className="flex items-center gap-1.5"
                  >
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      Quality:
                    </span>
                    <div className="flex items-center gap-1">
                      {aiQualityScore >= 0.8 ? (
                        <CheckCircle2 size={12} className="text-green-500" />
                      ) : aiQualityScore >= 0.6 ? (
                        <AlertTriangle size={12} className="text-yellow-500" />
                      ) : (
                        <AlertTriangle size={12} className="text-red-500" />
                      )}
                      <span
                        className={cn(
                          "text-xs font-medium",
                          aiQualityScore >= 0.8
                            ? "text-green-600 dark:text-green-400"
                            : aiQualityScore >= 0.6
                              ? "text-yellow-600 dark:text-yellow-400"
                              : "text-red-600 dark:text-red-400",
                        )}
                      >
                        {Math.round(aiQualityScore * 100)}%
                      </span>
                    </div>
                  </div>
                )}
              </div>

              {/* Issues */}
              {aiIssues && aiIssues.length > 0 && (
                <div data-testid="code-issues" className="space-y-1">
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    Issues ({aiIssues.length}):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {aiIssues.slice(0, 3).map((issue, idx) => (
                      <span
                        key={idx}
                        className={cn(
                          "px-2 py-0.5 text-xs rounded-full",
                          issue.severity === "error"
                            ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300"
                            : issue.severity === "warning"
                              ? "bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300"
                              : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300",
                        )}
                        title={issue.message}
                      >
                        {issue.type}
                        {issue.line && ` (L${issue.line})`}
                      </span>
                    ))}
                    {aiIssues.length > 3 && (
                      <span className="px-2 py-0.5 text-xs text-gray-500 dark:text-gray-400">
                        +{aiIssues.length - 3} more
                      </span>
                    )}
                  </div>
                </div>
              )}

              {/* Suggestions */}
              {aiSuggestions && aiSuggestions.length > 0 && aiSuggestions[0] && (
                <div className="text-xs text-gray-500 dark:text-gray-400">
                  <span className="font-medium">Suggestion:</span>{" "}
                  {aiSuggestions[0].description}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Content */}
      <div className="flex-1 p-4 overflow-auto">{renderContent()}</div>
    </div>
  );
}

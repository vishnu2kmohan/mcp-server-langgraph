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
import {
  useState,
  useCallback,
  useMemo,
  useEffect,
  lazy,
  Suspense,
} from "react";
import {
  Edit2,
  Save,
  X,
  Sparkles,
  Loader2,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import type { CanvasArtifact as CanvasArtifactType } from "../types/artifacts";
import { cn } from "../utils/cn";
import { useCodeAnalysis } from "../hooks";
import { JSONArtifact } from "../components/Artifacts/JSONArtifact";
import type { JSONArtifact as JSONArtifactType } from "../types/artifacts";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import {
  duotoneLight,
  duotoneDark,
} from "react-syntax-highlighter/dist/esm/styles/prism";

// Lazy load heavy components for better code splitting
const InteractiveMermaidDiagram = lazy(
  () => import("../components/Chat/InteractiveMermaidDiagram"),
);
const SandpackExecutor = lazy(
  () => import("../components/Artifacts/SandpackExecutor"),
);

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
// Pyodide Loader (on-demand for Python execution)
// =============================================================================

const PYODIDE_JS_URL =
  "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/pyodide.js";
const PYODIDE_INDEX_URL = "https://cdn.jsdelivr.net/pyodide/v0.24.1/full/";
// Pyodide type definitions
interface PyodideInterface {
  runPython: (code: string) => unknown;
  runPythonAsync: (code: string) => Promise<unknown>;
  loadPackage: (packages: string | string[]) => Promise<void>;
}

interface PyodideLoaderOptions {
  indexURL: string;
}

type PyodideLoader = (opts?: PyodideLoaderOptions) => Promise<PyodideInterface>;

let pyodidePromise: Promise<PyodideInterface> | null = null;

async function getPyodide(): Promise<PyodideInterface> {
  if (typeof window === "undefined") {
    throw new Error("Python runtime is only available in the browser");
  }

  if (pyodidePromise) return pyodidePromise;

  pyodidePromise = new Promise((resolve, reject) => {
    const win = window as unknown as { loadPyodide?: PyodideLoader };

    // If the loader is already present, just load the runtime
    if (win.loadPyodide) {
      win
        .loadPyodide?.({ indexURL: PYODIDE_INDEX_URL })
        .then(resolve)
        .catch(reject);
      return;
    }

    const script = document.createElement("script");
    script.src = PYODIDE_JS_URL;
    script.async = true;
    script.onload = () => {
      const loader = (window as unknown as { loadPyodide?: PyodideLoader })
        .loadPyodide;
      if (!loader) {
        reject(new Error("Pyodide loader unavailable after script load"));
        return;
      }
      loader({ indexURL: PYODIDE_INDEX_URL }).then(resolve).catch(reject);
    };
    script.onerror = () =>
      reject(new Error("Failed to load Python runtime (Pyodide)"));
    document.head.appendChild(script);
  });

  return pyodidePromise;
}

type ExecutionRuntime = "sandbox" | "pyodide";

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
  const language =
    artifact.editMetadata?.language ||
    (artifact.contentType === "code" ? "plaintext" : artifact.contentType);

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

  // Python execution (client-side, best-effort via Pyodide)
  const [isRunningPython, setIsRunningPython] = useState(false);
  const [pythonStdout, setPythonStdout] = useState<string | null>(null);
  const [pythonStderr, setPythonStderr] = useState<string | null>(null);
  const [pythonImage, setPythonImage] = useState<string | null>(null);
  const [pythonError, setPythonError] = useState<string | null>(null);
  const [runtime, setRuntime] = useState<ExecutionRuntime>(
    language?.toLowerCase() === "python" ? "sandbox" : "sandbox",
  );
  const [isRunningSandbox, setIsRunningSandbox] = useState(false);
  const [sandboxResult, setSandboxResult] = useState<{
    stdout?: string | null;
    stderr?: string | null;
    exitCode?: number | null;
    durationMs?: number | null;
    timedOut?: boolean | null;
    error?: string | null;
  } | null>(null);
  const [sandboxError, setSandboxError] = useState<string | null>(null);

  // Ensure runtime stays valid for the current language
  useEffect(() => {
    if (language?.toLowerCase() !== "python" && runtime === "pyodide") {
      setRuntime("sandbox");
    }
  }, [language, runtime]);

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

  const handleRunSandbox = useCallback(async () => {
    setIsRunningSandbox(true);
    setSandboxError(null);
    setSandboxResult(null);
    try {
      const response = await authenticatedFetch("/api/v1/code/execute", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          language: language ?? "python",
          code: isEditing ? editContent : artifact.content,
          runtime: "sandbox",
        }),
      });

      const data = await response.json().catch(() => null);

      if (!response.ok) {
        const detail =
          (data && (data.detail || data.error)) ||
          `Sandbox execution failed (HTTP ${response.status})`;
        setSandboxError(typeof detail === "string" ? detail : String(detail));
        return;
      }

      setSandboxResult({
        stdout: data?.stdout ?? null,
        stderr: data?.stderr ?? null,
        exitCode: data?.exit_code ?? data?.exitCode ?? null,
        durationMs: data?.duration_ms ?? data?.durationMs ?? null,
        timedOut: data?.timed_out ?? data?.timedOut ?? null,
        error: data?.error ?? null,
      });
    } catch (error) {
      setSandboxError(
        error instanceof Error ? error.message : "Failed to execute code",
      );
    } finally {
      setIsRunningSandbox(false);
    }
  }, [artifact.content, editContent, isEditing, language]);

  const handleRunPython = useCallback(async () => {
    setIsRunningPython(true);
    setPythonStdout(null);
    setPythonStderr(null);
    setPythonImage(null);
    setPythonError(null);

    try {
      const pyodide = await getPyodide();

      // Load common scientific packages (required before import)
      // These are included in Pyodide but need explicit loading
      await pyodide.loadPackage(["matplotlib", "numpy"]);

      // Prepare stdout/stderr capture and matplotlib backend
      await pyodide.runPythonAsync(`
import sys, io, matplotlib
matplotlib.use("agg")
stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
sys.stdout = stdout_buffer
sys.stderr = stderr_buffer
`);

      const codeToRun = isEditing ? editContent : artifact.content;
      await pyodide.runPythonAsync(codeToRun);

      const stdout = pyodide.runPython("stdout_buffer.getvalue()");
      const stderr = pyodide.runPython("stderr_buffer.getvalue()");
      setPythonStdout(String(stdout) || "(no stdout)");
      if (stderr) setPythonStderr(String(stderr));

      // Attempt to grab the latest matplotlib figure (best-effort)
      try {
        const imageBase64 = pyodide.runPython(`
import base64, io
import matplotlib.pyplot as plt
buf = io.BytesIO()
plt.savefig(buf, format="png")
buf.seek(0)
base64.b64encode(buf.read()).decode("utf-8")
`);
        if (imageBase64) {
          setPythonImage(String(imageBase64));
        }
      } catch {
        // Ignore if matplotlib was not used
      }
    } catch (error) {
      setPythonError(
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
      );
    } finally {
      setIsRunningPython(false);
    }
  }, [artifact.content, editContent, isEditing]);

  const formattedContent = useMemo(() => {
    if (artifact.contentType === "json") {
      return formatJson(artifact.content);
    }
    return artifact.content;
  }, [artifact.content, artifact.contentType]);

  const prefersDarkMode =
    typeof document !== "undefined" &&
    document.documentElement.classList.contains("dark");

  const highlightedContent = useMemo(() => {
    if (isEditing) return null;
    return (
      <SyntaxHighlighter
        language={language}
        style={prefersDarkMode ? duotoneDark : duotoneLight}
        showLineNumbers={showLineNumbers}
        wrapLines
        customStyle={{
          margin: 0,
          background: "transparent",
          padding: 0,
        }}
      >
        {artifact.content}
      </SyntaxHighlighter>
    );
  }, [artifact.content, isEditing, language, prefersDarkMode, showLineNumbers]);

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
        // Use JSONArtifact component for interactive JSON viewing
        try {
          const jsonData = JSON.parse(artifact.content);
          const jsonArtifact: JSONArtifactType = {
            id: artifact.id,
            type: "json",
            data: jsonData,
            title: artifact.title,
          };
          return (
            <div data-testid="json-content" className="w-full">
              <JSONArtifact artifact={jsonArtifact} />
            </div>
          );
        } catch {
          // Fallback to pre if JSON parsing fails
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
        }

      case "mermaid":
        return (
          <div data-testid="mermaid-content" className="w-full">
            <Suspense
              fallback={
                <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 animate-pulse">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <Loader2 size={16} className="animate-spin" />
                    <span className="text-sm">Loading diagram...</span>
                  </div>
                  <div className="mt-3 h-32 bg-gray-200 dark:bg-gray-700 rounded" />
                </div>
              }
            >
              <InteractiveMermaidDiagram
                code={artifact.content}
                className="rounded-lg border border-gray-200 dark:border-gray-700"
              />
            </Suspense>
          </div>
        );

      case "html":
        return (
          <div
            data-testid="html-content"
            className={cn(
              "p-4 rounded-lg overflow-auto",
              "bg-white dark:bg-gray-900",
              "border border-gray-200 dark:border-gray-700",
            )}
          >
            {/* Render HTML content in an iframe for sandboxing */}
            <iframe
              title={artifact.title ?? "HTML Preview"}
              srcDoc={artifact.content}
              className="w-full h-64 border-0"
              sandbox="allow-scripts"
            />
          </div>
        );

      case "jsx":
        // JSX artifacts are rendered with SandpackExecutor for live preview
        return (
          <div data-testid="jsx-content" className="w-full">
            <Suspense
              fallback={
                <div className="bg-gray-900 rounded-lg overflow-hidden animate-pulse border border-gray-700">
                  <div className="flex items-center gap-2 p-3 bg-gray-800 border-b border-gray-700">
                    <div className="h-4 bg-gray-700 rounded w-32" />
                    <div className="ml-auto h-6 w-16 bg-gray-700 rounded" />
                  </div>
                  <div className="p-4 space-y-2">
                    <div className="h-3 bg-gray-800 rounded w-2/3" />
                    <div className="h-3 bg-gray-800 rounded w-1/2" />
                    <div className="h-3 bg-gray-800 rounded w-3/4" />
                  </div>
                  <div className="p-4 bg-gray-800 border-t border-gray-700">
                    <div className="flex items-center gap-2 text-gray-500">
                      <Loader2 size={14} className="animate-spin" />
                      <span className="text-xs">
                        Loading interactive editor...
                      </span>
                    </div>
                  </div>
                </div>
              }
            >
              <SandpackExecutor
                code={artifact.content}
                language="jsx"
                title={artifact.title ?? "JSX Preview"}
                showRunButton={true}
                showEditor={true}
                readOnly={!editable}
                theme="dark"
              />
            </Suspense>
          </div>
        );

      case "code":
      default:
        return (
          <div className="flex">
            {showLineNumbers && !highlightedContent && (
              <LineNumbers content={artifact.content} />
            )}
            <div
              className={cn(
                "flex-1 p-4 rounded-lg text-sm overflow-auto",
                "bg-gray-50 dark:bg-gray-900",
                "text-gray-800 dark:text-gray-200",
                "font-mono",
              )}
            >
              {highlightedContent ?? artifact.content}
            </div>
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
              {aiSuggestions &&
                aiSuggestions.length > 0 &&
                aiSuggestions[0] && (
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

      {/* Execution controls (server sandbox + optional Pyodide for Python) */}
      {!isEditing && artifact.contentType === "code" && (
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-3 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600 dark:text-gray-400">
                Runtime:
              </span>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setRuntime("sandbox")}
                  className={cn(
                    "px-2 py-1 text-xs rounded border",
                    runtime === "sandbox"
                      ? "bg-primary-50 dark:bg-primary-900/30 border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-200"
                      : "border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
                  )}
                >
                  Server sandbox
                </button>
                {language?.toLowerCase() === "python" && (
                  <button
                    type="button"
                    onClick={() => setRuntime("pyodide")}
                    className={cn(
                      "px-2 py-1 text-xs rounded border",
                      runtime === "pyodide"
                        ? "bg-primary-50 dark:bg-primary-900/30 border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-200"
                        : "border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800",
                    )}
                  >
                    Pyodide (browser)
                  </button>
                )}
              </div>
            </div>

            <button
              type="button"
              onClick={
                runtime === "pyodide" ? handleRunPython : handleRunSandbox
              }
              disabled={
                runtime === "pyodide" ? isRunningPython : isRunningSandbox
              }
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium",
                "bg-green-600 text-white hover:bg-green-700",
                "disabled:opacity-50 disabled:cursor-not-allowed",
              )}
            >
              {runtime === "pyodide" ? (
                isRunningPython ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    Run in browser
                  </>
                )
              ) : isRunningSandbox ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  Running...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4" />
                  Run on server
                </>
              )}
            </button>
          </div>

          {runtime === "sandbox" && (sandboxResult || sandboxError) && (
            <div className="space-y-2">
              {sandboxError && (
                <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-3 text-sm text-red-800 dark:text-red-200">
                  {sandboxError}
                </div>
              )}
              {sandboxResult && (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-gray-600 dark:text-gray-400">
                    {sandboxResult.exitCode !== undefined &&
                      sandboxResult.exitCode !== null && (
                        <span>
                          Exit code: {sandboxResult.exitCode}
                          {sandboxResult.timedOut ? " (timed out)" : ""}
                        </span>
                      )}
                    {sandboxResult.durationMs !== undefined &&
                      sandboxResult.durationMs !== null && (
                        <span>
                          Duration: {sandboxResult.durationMs.toFixed(1)} ms
                        </span>
                      )}
                  </div>
                  {sandboxResult.stdout && (
                    <div className="rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
                      <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
                        stdout
                      </div>
                      <pre className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                        {sandboxResult.stdout}
                      </pre>
                    </div>
                  )}
                  {sandboxResult.stderr && (
                    <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-3">
                      <div className="text-xs font-semibold text-red-700 dark:text-red-300 mb-1">
                        stderr
                      </div>
                      <pre className="text-sm text-red-800 dark:text-red-200 whitespace-pre-wrap">
                        {sandboxResult.stderr}
                      </pre>
                    </div>
                  )}
                  {sandboxResult.error && !sandboxResult.stderr && (
                    <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-3 text-sm text-red-800 dark:text-red-200">
                      {sandboxResult.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {runtime === "pyodide" &&
            (pythonStdout || pythonStderr || pythonError) && (
              <div className="space-y-2">
                {pythonStdout && (
                  <div className="rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
                    <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-1">
                      stdout
                    </div>
                    <pre className="text-sm text-gray-800 dark:text-gray-100 whitespace-pre-wrap">
                      {pythonStdout}
                    </pre>
                  </div>
                )}
                {pythonStderr && (
                  <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-3">
                    <div className="text-xs font-semibold text-red-700 dark:text-red-300 mb-1">
                      stderr
                    </div>
                    <pre className="text-sm text-red-800 dark:text-red-200 whitespace-pre-wrap">
                      {pythonStderr}
                    </pre>
                  </div>
                )}
                {pythonError && (
                  <div className="rounded border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40 p-3 text-sm text-red-800 dark:text-red-200">
                    {pythonError}
                  </div>
                )}
                {pythonImage && (
                  <div className="rounded border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 p-3">
                    <div className="text-xs font-semibold text-gray-600 dark:text-gray-300 mb-2">
                      Matplotlib Render
                    </div>
                    <img
                      src={`data:image/png;base64,${pythonImage}`}
                      alt="Matplotlib render"
                      className="max-w-full"
                    />
                  </div>
                )}
              </div>
            )}
        </div>
      )}
    </div>
  );
}

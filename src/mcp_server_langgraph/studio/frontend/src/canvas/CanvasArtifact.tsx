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
const VegaLiteArtifact = lazy(() =>
  import("../components/Artifacts/VegaLiteArtifact").then((m) => ({
    default: m.VegaLiteArtifact,
  })),
);
const TableArtifact = lazy(() =>
  import("../components/Artifacts/TableArtifact").then((m) => ({
    default: m.TableArtifact,
  })),
);
const HTMLArtifact = lazy(() =>
  import("../components/Artifacts/HTMLArtifact").then((m) => ({
    default: m.HTMLArtifact,
  })),
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

// Import package utilities from separate module (for testability)
import {
  PYODIDE_CORE_PACKAGES,
  isPackageLoaded,
  markPackagesLoaded,
  getRequiredPackages,
} from "./pyodidePackages";

import { Button } from "@/components/UI";

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

/**
 * Detect if stdout is JSON that looks like a DataFrame (array of objects).
 * Handles Polars to_dicts() and Pandas orient='records' output formats.
 * @exported for testing
 */
export function detectDataFrameJson(stdout: string): {
  isDataFrame: boolean;
  data: Record<string, unknown>[];
  columns: string[];
} {
  const trimmed = stdout.trim();

  // Must start with [ and end with ] to be an array
  if (!trimmed.startsWith("[") || !trimmed.endsWith("]")) {
    return { isDataFrame: false, data: [], columns: [] };
  }

  try {
    const parsed = JSON.parse(trimmed);

    // Must be a non-empty array
    if (!Array.isArray(parsed) || parsed.length === 0) {
      return { isDataFrame: false, data: [], columns: [] };
    }

    // All elements must be objects (not arrays or primitives)
    const allObjects = parsed.every(
      (item) =>
        typeof item === "object" && item !== null && !Array.isArray(item),
    );
    if (!allObjects) {
      return { isDataFrame: false, data: [], columns: [] };
    }

    // Extract columns from the first object
    const firstItem = parsed[0] as Record<string, unknown>;
    const columns = Object.keys(firstItem);

    // Must have at least one column
    if (columns.length === 0) {
      return { isDataFrame: false, data: [], columns: [] };
    }

    // Check that all objects have the same keys (DataFrame-like structure)
    const allSameKeys = parsed.every((item) => {
      const keys = Object.keys(item as Record<string, unknown>);
      return (
        keys.length === columns.length &&
        keys.every((key) => columns.includes(key))
      );
    });

    if (!allSameKeys) {
      return { isDataFrame: false, data: [], columns: [] };
    }

    return {
      isDataFrame: true,
      data: parsed as Record<string, unknown>[],
      columns,
    };
  } catch {
    return { isDataFrame: false, data: [], columns: [] };
  }
}

/**
 * Detect if stdout is HTML containing Bokeh chart markers.
 * Checks for Bokeh CDN references, Bokeh.embed calls, or bk-root class.
 * @exported for testing
 */
export function detectBokehHtml(stdout: string): {
  isBokeh: boolean;
  html: string;
} {
  const trimmed = stdout.trim();

  // Must look like HTML (starts with < or contains DOCTYPE)
  if (
    !trimmed.startsWith("<") &&
    !trimmed.toLowerCase().includes("<!doctype")
  ) {
    return { isBokeh: false, html: "" };
  }

  // Check for Bokeh markers
  const bokehPatterns = [
    /cdn\.bokeh\.org/i, // Bokeh CDN
    /Bokeh\.embed/i, // Bokeh embed function
    /class=["']bk-root["']/i, // Bokeh root container
    /bokehjs/i, // BokehJS reference
  ];

  const isBokeh = bokehPatterns.some((pattern) => pattern.test(trimmed));

  return { isBokeh, html: isBokeh ? trimmed : "" };
}

// =============================================================================
// Line Numbers Component
// =============================================================================

function LineNumbers({ content }: { content: string }) {
  const lines = content.split("\n").length;
  return (
    <div
      data-testid="line-numbers"
      className="select-none pr-3 mr-3 border-r border-neutral-300 dark:border-neutral-600 text-neutral-400 dark:text-neutral-400 text-right"
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

  // Track if user has triggered AI analysis (opt-in pattern)
  const [hasTriggeredAnalysis, setHasTriggeredAnalysis] = useState(false);

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
  const [loadingPackages, setLoadingPackages] = useState<string[] | null>(null);
  // Altair/Vega-Lite chart output
  const [vegaLiteSpec, setVegaLiteSpec] = useState<Record<
    string,
    unknown
  > | null>(null);
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
    setLoadingPackages(null);
    setVegaLiteSpec(null);

    try {
      const pyodide = await getPyodide();
      const codeToRun = isEditing ? editContent : artifact.content;

      // Step 1: Load core packages (always needed)
      // These are loaded once and cached for subsequent runs
      if (!isPackageLoaded("numpy") || !isPackageLoaded("matplotlib")) {
        setLoadingPackages(PYODIDE_CORE_PACKAGES);
        await pyodide.loadPackage(PYODIDE_CORE_PACKAGES);
        markPackagesLoaded(PYODIDE_CORE_PACKAGES);
      }

      // Step 2: Detect and lazy-load additional packages from user code
      const additionalPackages = getRequiredPackages(codeToRun);
      if (additionalPackages.length > 0) {
        setLoadingPackages(additionalPackages);
        await pyodide.loadPackage(additionalPackages);
        markPackagesLoaded(additionalPackages);
      }

      setLoadingPackages(null);

      // Prepare stdout/stderr capture and matplotlib backend
      await pyodide.runPythonAsync(`
import sys, io, matplotlib
matplotlib.use("agg")
stdout_buffer = io.StringIO()
stderr_buffer = io.StringIO()
sys.stdout = stdout_buffer
sys.stderr = stderr_buffer
`);

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

      // Attempt to detect and extract Altair charts (best-effort)
      // Altair charts can be converted to Vega-Lite JSON via .to_dict()
      try {
        const altairJson = pyodide.runPython(`
import json

def _is_altair_chart(obj):
    """Check if an object is an Altair chart."""
    if obj is None:
        return False
    try:
        # Check by module name (most reliable)
        module = getattr(obj.__class__, '__module__', '')
        if module.startswith('altair'):
            return hasattr(obj, 'to_dict')
        # Fallback: check for Altair-like attributes
        return (hasattr(obj, 'to_dict') and
                hasattr(obj, 'mark') and
                hasattr(obj, 'encoding'))
    except Exception:
        return False

def _extract_altair_chart():
    """Find and extract first Altair chart from globals."""
    # Extended list of common variable names for charts
    _common_names = [
        # Basic names
        'chart', 'c', 'fig', 'plot', 'viz', 'visualization',
        # Altair-specific
        'alt_chart', 'altair_chart', 'vega_chart',
        # Chart type names
        'bar', 'line', 'scatter', 'area', 'heatmap', 'histogram',
        'bar_chart', 'line_chart', 'scatter_plot', 'area_chart',
        # Common variations
        'my_chart', 'my_plot', 'data_viz', 'graph',
        # Numbered variants
        'chart1', 'chart2', 'fig1', 'fig2', 'plot1', 'plot2',
        # Result names
        'result', 'output', 'display',
    ]

    # First, check common variable names
    for _var_name in _common_names:
        _obj = globals().get(_var_name)
        if _is_altair_chart(_obj):
            return _obj

    # Check the last expression result
    _last = globals().get('_')
    if _is_altair_chart(_last):
        return _last

    # Scan all globals for any Altair chart (expensive but thorough)
    for _name, _obj in list(globals().items()):
        if not _name.startswith('_') and _is_altair_chart(_obj):
            return _obj

    return None

_chart = _extract_altair_chart()
_altair_spec = json.dumps(_chart.to_dict()) if _chart else None
_altair_spec
`);
        if (altairJson && altairJson !== "None") {
          try {
            const spec = JSON.parse(String(altairJson));
            setVegaLiteSpec(spec);
          } catch {
            // Invalid JSON, ignore
          }
        }
      } catch {
        // Ignore if Altair was not used
      }
    } catch (error) {
      setPythonError(
        error instanceof Error
          ? error.message
          : String(error ?? "Unknown error"),
      );
    } finally {
      setIsRunningPython(false);
      setLoadingPackages(null);
    }
  }, [artifact.content, editContent, isEditing]);

  const formattedContent = useMemo(() => {
    if (artifact.contentType === "json") {
      return formatJson(artifact.content);
    }
    return artifact.content;
  }, [artifact.content, artifact.contentType]);

  // Extract title from Vega-Lite spec (for Altair charts)
  const altairChartTitle = useMemo(() => {
    if (!vegaLiteSpec) return "Altair Chart";
    const spec = vegaLiteSpec as Record<string, unknown>;
    // Check for string title
    if (typeof spec.title === "string") return spec.title;
    // Check for object title with text property
    if (spec.title && typeof spec.title === "object" && "text" in spec.title) {
      return (spec.title as { text: string }).text;
    }
    // Fall back to description
    if (typeof spec.description === "string") return spec.description;
    return "Altair Chart";
  }, [vegaLiteSpec]);

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
            "bg-neutral-50 dark:bg-neutral-900 rounded-lg",
            "border border-neutral-200 dark:border-neutral-700",
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
                "bg-neutral-50 dark:bg-neutral-900",
                "text-neutral-800 dark:text-neutral-200",
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
                <div className="p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 animate-pulse">
                  <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
                    <Loader2 size={16} className="animate-spin" />
                    <span className="text-sm">Loading diagram...</span>
                  </div>
                  <div className="mt-3 h-32 bg-neutral-200 dark:bg-neutral-700 rounded" />
                </div>
              }
            >
              <InteractiveMermaidDiagram
                code={artifact.content}
                className="rounded-lg border border-neutral-200 dark:border-neutral-700"
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
              "bg-white dark:bg-neutral-900",
              "border border-neutral-200 dark:border-neutral-700",
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
                <div className="bg-neutral-900 rounded-lg overflow-hidden animate-pulse border border-neutral-700">
                  <div className="flex items-center gap-2 p-3 bg-neutral-800 border-b border-neutral-700">
                    <div className="h-4 bg-neutral-700 rounded w-32" />
                    <div className="ml-auto h-6 w-16 bg-neutral-700 rounded" />
                  </div>
                  <div className="p-4 space-y-2">
                    <div className="h-3 bg-neutral-800 rounded w-2/3" />
                    <div className="h-3 bg-neutral-800 rounded w-1/2" />
                    <div className="h-3 bg-neutral-800 rounded w-3/4" />
                  </div>
                  <div className="p-4 bg-neutral-800 border-t border-neutral-700">
                    <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400">
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
                "bg-neutral-50 dark:bg-neutral-900",
                "text-neutral-800 dark:text-neutral-200",
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
        "bg-white dark:bg-neutral-800",
        "border-neutral-200 dark:border-neutral-700",
        className,
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex items-center gap-2">
          <h3 className="text-sm font-medium text-neutral-800 dark:text-neutral-200">
            {artifact.title || "Untitled"}
          </h3>
          <span
            data-testid="content-type-badge"
            className="px-1.5 py-0.5 text-xs rounded bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-400"
          >
            {artifact.contentType}
          </span>
          {language && (
            <span
              data-testid="language-badge"
              className="px-1.5 py-0.5 text-xs rounded bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400"
            >
              {language}
            </span>
          )}
          {isAIGenerated && (
            <span
              data-testid="ai-badge"
              className="flex items-center gap-1 px-1.5 py-0.5 text-xs rounded bg-insight-100 dark:bg-insight-900/30 text-insight-600 dark:text-insight-400"
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
          <span className="text-xs text-neutral-400 dark:text-neutral-400">
            v{artifact.version}
          </span>
          {editable && !isEditing && (
            <Button
              data-testid="edit-button"
              type="button"
              onClick={handleEdit}
              aria-label="Edit artifact"
              className={cn(
                "p-1.5 rounded transition-colors",
                "text-neutral-500 dark:text-neutral-400 hover:text-neutral-700 dark:text-neutral-200 dark:text-neutral-400 dark:hover:text-neutral-200",
                "hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-700",
              )}
            >
              <Edit2 size={14} />
            </Button>
          )}
          {isEditing && (
            <>
              <Button
                data-testid="save-button"
                type="button"
                onClick={handleSave}
                aria-label="Save changes"
                className={cn(
                  "p-1.5 rounded transition-colors",
                  "text-success-600 hover:text-success-700",
                  "hover:bg-success-100 dark:hover:bg-success-900/30",
                )}
              >
                <Save size={14} />
              </Button>
              <Button
                data-testid="cancel-button"
                type="button"
                onClick={handleCancel}
                aria-label="Cancel editing"
                className={cn(
                  "p-1.5 rounded transition-colors",
                  "text-error-600 hover:text-error-700",
                  "hover:bg-error-100 dark:hover:bg-error-900/30",
                )}
              >
                <X size={14} />
              </Button>
            </>
          )}
        </div>
      </div>
      {/* AI Code Analysis Panel (Sprint 4) */}
      {enableAI && userId && isCodeArtifact && (
        <div
          data-testid="ai-code-analysis"
          className="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50"
        >
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={16} className="text-primary-500" />
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              Code Analysis
            </span>
            {aiLoading && (
              <Loader2 size={14} className="animate-spin text-primary-500" />
            )}
            {!hasTriggeredAnalysis && !aiLoading && (
              <Button
                type="button"
                data-testid="analyze-code-button"
                onClick={() => {
                  setHasTriggeredAnalysis(true);
                  refetchAI();
                }}
                className={cn(
                  "flex items-center gap-1 px-2 py-1 text-xs font-medium rounded",
                  "bg-primary-100 text-primary-700 hover:bg-primary-200",
                  "dark:bg-primary-900/30 dark:text-primary-300 dark:hover:bg-primary-900/50",
                  "transition-colors",
                )}
              >
                <Sparkles size={12} />
                Analyze
              </Button>
            )}
            {aiError && hasTriggeredAnalysis && (
              <Button
                size="sm"
                className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
                type="button"
                onClick={() => refetchAI()}
              >
                Retry
              </Button>
            )}
          </div>

          {!hasTriggeredAnalysis && !aiLoading && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Click &quot;Analyze&quot; to get AI-powered code insights.
            </p>
          )}

          {aiLoading && (
            <p className="text-sm text-neutral-500 dark:text-neutral-400">
              Analyzing code...
            </p>
          )}

          {aiError && hasTriggeredAnalysis && (
            <p className="text-sm text-error-600 dark:text-error-400">
              Failed to analyze code. Click retry to try again.
            </p>
          )}

          {hasTriggeredAnalysis && !aiLoading && !aiError && (
            <div className="space-y-2">
              {/* Metrics Row */}
              <div className="flex items-center gap-4">
                {aiComplexity !== null && (
                  <div
                    data-testid="complexity-score"
                    className="flex items-center gap-1.5"
                  >
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      Complexity:
                    </span>
                    <span
                      className={cn(
                        "px-1.5 py-0.5 text-xs font-medium rounded",
                        aiComplexity <= 10
                          ? "bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300"
                          : aiComplexity <= 20
                            ? "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300"
                            : "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300",
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
                    <span className="text-xs text-neutral-500 dark:text-neutral-400">
                      Quality:
                    </span>
                    <div className="flex items-center gap-1">
                      {aiQualityScore >= 0.8 ? (
                        <CheckCircle2 size={12} className="text-success-500" />
                      ) : aiQualityScore >= 0.6 ? (
                        <AlertTriangle size={12} className="text-warning-500" />
                      ) : (
                        <AlertTriangle size={12} className="text-error-500" />
                      )}
                      <span
                        className={cn(
                          "text-xs font-medium",
                          aiQualityScore >= 0.8
                            ? "text-success-600 dark:text-success-400"
                            : aiQualityScore >= 0.6
                              ? "text-warning-600 dark:text-warning-400"
                              : "text-error-600 dark:text-error-400",
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
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">
                    Issues ({aiIssues.length}):
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {aiIssues.slice(0, 3).map((issue, idx) => (
                      <span
                        key={idx}
                        className={cn(
                          "px-2 py-0.5 text-xs rounded-full",
                          issue.severity === "error"
                            ? "bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-300"
                            : issue.severity === "warning"
                              ? "bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300"
                              : "bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300",
                        )}
                        title={issue.message}
                      >
                        {issue.type}
                        {issue.line && ` (L${issue.line})`}
                      </span>
                    ))}
                    {aiIssues.length > 3 && (
                      <span className="px-2 py-0.5 text-xs text-neutral-500 dark:text-neutral-400">
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
                  <div className="text-xs text-neutral-500 dark:text-neutral-400">
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
        <div className="border-t border-neutral-200 dark:border-neutral-700 px-4 py-3 space-y-3">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-neutral-600 dark:text-neutral-400">
                Runtime:
              </span>
              <div className="flex items-center gap-1">
                <Button
                  type="button"
                  onClick={() => setRuntime("sandbox")}
                  className={cn(
                    "px-2 py-1 text-xs rounded border",
                    runtime === "sandbox"
                      ? "bg-primary-50 dark:bg-primary-900/30 border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-200"
                      : "border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
                  )}
                >
                  Server sandbox
                </Button>
                {language?.toLowerCase() === "python" && (
                  <Button
                    type="button"
                    onClick={() => setRuntime("pyodide")}
                    className={cn(
                      "px-2 py-1 text-xs rounded border",
                      runtime === "pyodide"
                        ? "bg-primary-50 dark:bg-primary-900/30 border-primary-200 dark:border-primary-700 text-primary-700 dark:text-primary-200"
                        : "border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800",
                    )}
                  >
                    Pyodide (browser)
                  </Button>
                )}
              </div>
            </div>

            <Button
              type="button"
              onClick={
                runtime === "pyodide" ? handleRunPython : handleRunSandbox
              }
              disabled={
                runtime === "pyodide" ? isRunningPython : isRunningSandbox
              }
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded text-sm font-medium",
                "bg-success-600 text-white hover:bg-success-700",
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
            </Button>
          </div>

          {runtime === "sandbox" && (sandboxResult || sandboxError) && (
            <div className="space-y-2">
              {sandboxError && (
                <div className="rounded border border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950/40 p-3 text-sm text-error-800 dark:text-error-200">
                  {sandboxError}
                </div>
              )}
              {sandboxResult && (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-3 text-xs text-neutral-600 dark:text-neutral-400">
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
                  {sandboxResult.stdout &&
                    (() => {
                      // Detect DataFrame JSON (Polars to_dicts() or Pandas orient='records')
                      const dfResult = detectDataFrameJson(
                        sandboxResult.stdout,
                      );
                      if (dfResult.isDataFrame) {
                        return (
                          <div
                            className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3"
                            data-testid="dataframe-output"
                          >
                            <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-2">
                              DataFrame Output
                            </div>
                            <Suspense
                              fallback={
                                <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 p-2">
                                  <Loader2 size={16} className="animate-spin" />
                                  <span className="text-sm">
                                    Loading table...
                                  </span>
                                </div>
                              }
                            >
                              <TableArtifact
                                title=""
                                columns={dfResult.columns.map((col) => ({
                                  key: col,
                                  label: col,
                                  sortable: true,
                                }))}
                                data={dfResult.data}
                              />
                            </Suspense>
                          </div>
                        );
                      }

                      // Detect Bokeh HTML output
                      const bokehResult = detectBokehHtml(sandboxResult.stdout);
                      if (bokehResult.isBokeh) {
                        return (
                          <div
                            className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3"
                            data-testid="bokeh-output"
                          >
                            <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-2">
                              Bokeh Chart
                            </div>
                            <Suspense
                              fallback={
                                <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 p-2">
                                  <Loader2 size={16} className="animate-spin" />
                                  <span className="text-sm">
                                    Loading chart...
                                  </span>
                                </div>
                              }
                            >
                              <HTMLArtifact
                                data={bokehResult.html}
                                title="Bokeh Chart"
                                allowScripts={true}
                              />
                            </Suspense>
                          </div>
                        );
                      }

                      // Default: plain text stdout
                      return (
                        <div className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
                          <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-1">
                            stdout
                          </div>
                          <pre className="text-sm text-neutral-800 dark:text-neutral-100 whitespace-pre-wrap">
                            {sandboxResult.stdout}
                          </pre>
                        </div>
                      );
                    })()}
                  {sandboxResult.stderr && (
                    <div className="rounded border border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950/40 p-3">
                      <div className="text-xs font-semibold text-error-700 dark:text-error-300 mb-1">
                        stderr
                      </div>
                      <pre className="text-sm text-error-800 dark:text-error-200 whitespace-pre-wrap">
                        {sandboxResult.stderr}
                      </pre>
                    </div>
                  )}
                  {sandboxResult.error && !sandboxResult.stderr && (
                    <div className="rounded border border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950/40 p-3 text-sm text-error-800 dark:text-error-200">
                      {sandboxResult.error}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {runtime === "pyodide" && loadingPackages && (
            <div className="rounded border border-info-200 dark:border-info-800 bg-info-50 dark:bg-info-900/30 p-3">
              <div className="flex items-center gap-2 text-sm text-info-600 dark:text-info-400">
                <svg
                  className="animate-spin h-4 w-4"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  ></circle>
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  ></path>
                </svg>
                <span>
                  Installing packages: {loadingPackages.join(", ")}...
                </span>
              </div>
            </div>
          )}

          {runtime === "pyodide" &&
            (pythonStdout || pythonStderr || pythonError) && (
              <div className="space-y-2">
                {pythonStdout && (
                  <div className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
                    <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-1">
                      stdout
                    </div>
                    <pre className="text-sm text-neutral-800 dark:text-neutral-100 whitespace-pre-wrap">
                      {pythonStdout}
                    </pre>
                  </div>
                )}
                {pythonStderr && (
                  <div className="rounded border border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950/40 p-3">
                    <div className="text-xs font-semibold text-error-700 dark:text-error-300 mb-1">
                      stderr
                    </div>
                    <pre className="text-sm text-error-800 dark:text-error-200 whitespace-pre-wrap">
                      {pythonStderr}
                    </pre>
                  </div>
                )}
                {pythonError && (
                  <div className="rounded border border-error-200 dark:border-error-800 bg-error-50 dark:bg-error-950/40 p-3 text-sm text-error-800 dark:text-error-200">
                    {pythonError}
                  </div>
                )}
                {pythonImage && (
                  <div className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
                    <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-2">
                      Matplotlib Render
                    </div>
                    <img
                      src={`data:image/png;base64,${pythonImage}`}
                      alt="Matplotlib render"
                      className="max-w-full"
                    />
                  </div>
                )}
                {vegaLiteSpec && (
                  <div className="rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3">
                    <div className="text-xs font-semibold text-neutral-600 dark:text-neutral-300 mb-2">
                      {altairChartTitle}
                    </div>
                    <Suspense
                      fallback={
                        <div className="flex items-center gap-2 text-neutral-500 dark:text-neutral-400 p-4">
                          <Loader2 size={16} className="animate-spin" />
                          <span className="text-sm">Loading chart...</span>
                        </div>
                      }
                    >
                      <VegaLiteArtifact
                        spec={vegaLiteSpec}
                        title={altairChartTitle}
                      />
                    </Suspense>
                  </div>
                )}
              </div>
            )}
        </div>
      )}
    </div>
  );
}

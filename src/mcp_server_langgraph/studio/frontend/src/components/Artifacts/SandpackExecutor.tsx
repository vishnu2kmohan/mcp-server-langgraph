/**
 * SandpackExecutor Component
 *
 * Sandboxed code execution for React/JSX/TSX/MDX artifacts.
 * Uses CodeSandbox's Sandpack for secure iframe-isolated execution.
 *
 * Security Features:
 * - Iframe isolation (no DOM access to parent)
 * - Configurable timeout for infinite loops
 * - Optional Run button for explicit user consent
 * - Dependency allowlist support
 * - React Error Boundary for graceful failure handling
 *
 * Hybrid Strategy Tier 2:
 * This component handles executable content that requires user opt-in.
 *
 * CSP (Content Security Policy) Requirements:
 * When deploying with Content Security Policy headers, code execution requires:
 *
 * CDN Domains:
 * - codesandbox.io: Sandpack code execution (JS/TS/JSX/TSX)
 * - cdn.jsdelivr.net: Pyodide Python runtime (CanvasArtifact Python execution)
 *
 * 1. frame-src: Allow iframe sources
 *    frame-src 'self' https://*.codesandbox.io https://codesandbox.io;
 *
 * 2. script-src: Allow Sandpack bundler and Pyodide runtime
 *    script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.codesandbox.io https://cdn.jsdelivr.net;
 *
 * 3. style-src: Allow inline styles for Sandpack editor
 *    style-src 'self' 'unsafe-inline';
 *
 * 4. connect-src: Allow WebSocket connections and CDN fetch
 *    connect-src 'self' https://*.codesandbox.io wss://*.codesandbox.io https://cdn.jsdelivr.net;
 *
 * 5. img-src: Allow images from code execution
 *    img-src 'self' data: https:;
 *
 * Example Nginx CSP header:
 * add_header Content-Security-Policy "
 *   default-src 'self';
 *   frame-src 'self' https://*.codesandbox.io https://codesandbox.io;
 *   script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.codesandbox.io https://cdn.jsdelivr.net;
 *   style-src 'self' 'unsafe-inline';
 *   connect-src 'self' https://*.codesandbox.io wss://*.codesandbox.io https://cdn.jsdelivr.net;
 *   img-src 'self' data: https:;
 * ";
 *
 * Note: The Sandpack iframe itself runs in a sandboxed environment and
 * cannot access the parent document, providing defense-in-depth security.
 */

import {
  useState,
  useCallback,
  useEffect,
  useRef,
  Component,
  ReactNode,
} from "react";
import {
  SandpackProvider,
  SandpackLayout,
  SandpackPreview,
  SandpackCodeEditor,
  useSandpack,
} from "@codesandbox/sandpack-react";
import { Play, Square, Terminal, AlertTriangle, RefreshCw } from "lucide-react";

import { Button } from "@/components/UI";

/**
 * Error Boundary for Sandpack component
 *
 * Catches React errors from Sandpack and displays a fallback UI
 * instead of crashing the entire chat interface.
 */
interface ErrorBoundaryProps {
  children: ReactNode;
  onError?: (error: Error) => void;
  onReset?: () => void;
  code: string;
  language: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class SandpackErrorBoundary extends Component<
  ErrorBoundaryProps,
  ErrorBoundaryState
> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error): void {
    this.props.onError?.(error);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
    this.props.onReset?.();
  };

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <div
          className="bg-error-50 dark:bg-error-900/20 rounded-lg border border-error-200 dark:border-error-800 p-4"
          data-testid="sandpack-error-fallback"
        >
          <div className="flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-error-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h3 className="text-sm font-medium text-error-800 dark:text-error-200">
                Code execution failed
              </h3>
              <p className="mt-1 text-sm text-error-600 dark:text-error-300">
                {this.state.error?.message || "An unexpected error occurred"}
              </p>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  className="flex .5 px-3 py-1 text-sm bg-error-100 hover:bg-error-200 dark:bg-error-800 dark:hover:bg-error-700 text-error-800 dark:text-error-200 rounded"
                  onClick={this.handleReset}
                >
                  <RefreshCw size={14} />
                  Retry
                </Button>
              </div>
              {/* Show original code for reference */}
              <details className="mt-3">
                <summary className="text-xs text-error-500 dark:text-error-400 cursor-pointer">
                  View code ({this.props.language})
                </summary>
                <pre className="mt-2 p-2 bg-neutral-900 rounded text-xs font-mono text-neutral-100 overflow-x-auto max-h-32">
                  {this.props.code}
                </pre>
              </details>
            </div>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export interface SandpackExecutorProps {
  code: string;
  language: "tsx" | "jsx" | "javascript" | "typescript" | "mdx";
  title?: string;
  showRunButton?: boolean;
  autoRun?: boolean;
  showEditor?: boolean;
  readOnly?: boolean;
  theme?: "light" | "dark";
  timeout?: number;
  dependencies?: Record<string, string>;
  allowedDependencies?: string[];
  onExecute?: () => void;
  onError?: (error: Error) => void;
  onTimeout?: () => void;
}

// Default dependencies for React projects
const DEFAULT_DEPENDENCIES: Record<string, string> = {
  react: "^18.2.0",
  "react-dom": "^18.2.0",
};

// MDX-specific dependencies
const MDX_DEPENDENCIES: Record<string, string> = {
  ...DEFAULT_DEPENDENCIES,
  "@mdx-js/react": "^3.0.0",
};

/**
 * Template for wrapping user code in a React app
 */
function createAppTemplate(code: string, _language: string): string {
  // If code already exports a default component, use it directly
  if (code.includes("export default")) {
    return code;
  }

  // Otherwise, wrap it in a simple component
  return `
import React from 'react';

${code}

export default function App() {
  return (
    <div style={{ padding: '16px', fontFamily: 'system-ui, sans-serif' }}>
      <p>Code executed successfully</p>
    </div>
  );
}
`.trim();
}

/**
 * Get file extension for language
 */
function getFileExtension(language: string): string {
  switch (language) {
    case "tsx":
    case "typescript":
      return "tsx";
    case "jsx":
    case "javascript":
      return "jsx";
    case "mdx":
      return "mdx";
    default:
      return "tsx";
  }
}

/**
 * Timeout controller component that runs inside Sandpack context
 */
function TimeoutController({
  timeout,
  onTimeout,
}: {
  timeout?: number;
  onTimeout?: () => void;
}) {
  const { sandpack } = useSandpack();
  const timeoutRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    if (timeout && sandpack.status === "running") {
      timeoutRef.current = setTimeout(() => {
        onTimeout?.();
      }, timeout);
    }

    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [timeout, sandpack.status, onTimeout]);

  return null;
}

export function SandpackExecutor({
  code,
  language,
  title,
  showRunButton = true,
  autoRun = false,
  showEditor = false,
  readOnly = false,
  theme = "dark",
  timeout,
  dependencies = {},
  allowedDependencies,
  onExecute,
  onError,
  onTimeout,
}: SandpackExecutorProps) {
  const [isRunning, setIsRunning] = useState(autoRun);
  const [hasRun, setHasRun] = useState(autoRun);

  // Filter dependencies if allowlist is provided
  const filteredDependencies = allowedDependencies
    ? Object.fromEntries(
        Object.entries(dependencies).filter(([dep]) =>
          allowedDependencies.includes(dep),
        ),
      )
    : dependencies;

  // Combine default and custom dependencies
  const allDependencies =
    language === "mdx"
      ? { ...MDX_DEPENDENCIES, ...filteredDependencies }
      : { ...DEFAULT_DEPENDENCIES, ...filteredDependencies };

  // Prepare file content
  const fileExtension = getFileExtension(language);
  const mainFile = `/App.${fileExtension}`;
  const processedCode =
    language === "mdx" ? code : createAppTemplate(code, language);

  const files: Record<string, string> = {
    [mainFile]: processedCode,
  };

  // Add index file for React
  if (language !== "mdx") {
    files["/index.tsx"] = `
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

const root = createRoot(document.getElementById("root")!);
root.render(
  <StrictMode>
    <App />
  </StrictMode>
);
`.trim();
  }

  const handleRun = useCallback(() => {
    setIsRunning(true);
    setHasRun(true);
    onExecute?.();
  }, [onExecute]);

  const handleStop = useCallback(() => {
    setIsRunning(false);
  }, []);

  // If not auto-run and hasn't been run yet, show placeholder
  if (!hasRun && showRunButton) {
    return (
      <div className="bg-neutral-50 dark:bg-neutral-800 rounded-lg overflow-hidden border border-neutral-200 dark:border-neutral-700">
        {/* Header */}
        <div className="px-4 py-2 bg-neutral-100 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {title && (
              <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
                {title}
              </span>
            )}
            <span className="text-xs font-mono bg-neutral-200 dark:bg-neutral-700 px-2 py-0.5 rounded text-neutral-600 dark:text-neutral-400">
              {language}
            </span>
            <span className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
              <Terminal size={14} />
              Sandpack
            </span>
          </div>
          <Button
            variant="success"
            size="sm"
            className="flex .5 px-3 py-1 text-sm bg-success-600 hover:bg-success-700 text-white rounded"
            onClick={handleRun}
          >
            <Play size={14} />
            Run
          </Button>
        </div>
        {/* Code preview */}
        <div className="p-4 bg-neutral-900 overflow-x-auto max-h-64">
          <pre className="text-sm font-mono text-neutral-100 whitespace-pre-wrap">
            {code}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div
      className="rounded-lg overflow-hidden border border-neutral-200 dark:border-neutral-700"
      data-testid="sandpack-executor"
    >
      {/* Header */}
      <div className="px-4 py-2 bg-neutral-100 dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          {title && (
            <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              {title}
            </span>
          )}
          <span className="text-xs font-mono bg-neutral-200 dark:bg-neutral-700 px-2 py-0.5 rounded text-neutral-600 dark:text-neutral-400">
            {language}
          </span>
          <span className="flex items-center gap-1 text-xs text-neutral-500 dark:text-neutral-400">
            <Terminal size={14} />
            Sandpack
          </span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning ? (
            <Button
              variant="danger"
              size="sm"
              className="flex .5 px-3 py-1 text-sm bg-error-600 hover:bg-error-700 text-white rounded"
              onClick={handleStop}
            >
              <Square size={14} />
              Stop
            </Button>
          ) : (
            showRunButton && (
              <Button
                variant="success"
                size="sm"
                className="flex .5 px-3 py-1 text-sm bg-success-600 hover:bg-success-700 text-white rounded"
                onClick={handleRun}
              >
                <Play size={14} />
                Run
              </Button>
            )
          )}
        </div>
      </div>
      {/* Sandpack with Error Boundary */}
      <SandpackErrorBoundary
        code={code}
        language={language}
        onError={onError}
        onReset={handleRun}
      >
        <SandpackProvider
          template="react-ts"
          theme={theme === "dark" ? "dark" : "light"}
          files={files}
          customSetup={{
            dependencies: allDependencies,
            entry: "/index.tsx",
          }}
          options={{
            autorun: isRunning,
            autoReload: false,
          }}
        >
          <TimeoutController timeout={timeout} onTimeout={onTimeout} />
          <SandpackLayout>
            {showEditor && (
              <SandpackCodeEditor
                showLineNumbers
                showTabs
                readOnly={readOnly}
                style={{ height: "300px" }}
              />
            )}
            {isRunning && <SandpackPreview style={{ height: "300px" }} />}
          </SandpackLayout>
        </SandpackProvider>
      </SandpackErrorBoundary>
    </div>
  );
}

export default SandpackExecutor;

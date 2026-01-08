/**
 * MarkdownContent Component
 *
 * Rich markdown renderer with custom components for code blocks,
 * interactive artifacts, and proper styling.
 *
 * Features:
 * - GitHub Flavored Markdown (tables, strikethrough, task lists)
 * - Math rendering with KaTeX
 * - Syntax highlighting for code blocks
 * - Interactive artifacts (mermaid diagrams, charts, JSX/TSX execution)
 *
 * Extracted from ChatMessages.tsx for reusability.
 *
 * @example
 * ```tsx
 * <MarkdownContent
 *   content="# Hello\n\nSome **markdown** content"
 *   enableInteractiveArtifacts={true}
 * />
 * ```
 */

import { useMemo, lazy, Suspense, useState, useEffect, memo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Loader2, AlertCircle } from "lucide-react";
import "katex/dist/katex.min.css";

// Rich media artifact components
import { InteractiveSVGArtifact } from "../Artifacts/InteractiveSVGArtifact";
import { AudioArtifact } from "../Artifacts/AudioArtifact";
import { VideoArtifact } from "../Artifacts/VideoArtifact";
import { ExecutableArtifact } from "../Artifacts/ExecutableArtifact";
import { InteractiveChart, type ChartData } from "./InteractiveChart";

// Lazy loaded components for bundle optimization
const InteractiveMermaidDiagram = lazy(
  () => import("./InteractiveMermaidDiagram"),
);
const CodeBlock = lazy(() => import("./CodeBlock"));
const SandpackExecutor = lazy(() => import("../Artifacts/SandpackExecutor"));

// =============================================================================
// Loading Fallbacks
// =============================================================================

/**
 * Loading fallback for lazy-loaded diagram components
 */
export function DiagramLoadingFallback() {
  return (
    <div className="my-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 animate-pulse">
      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading diagram...</span>
      </div>
      <div className="mt-3 h-32 bg-gray-200 dark:bg-gray-700 rounded" />
    </div>
  );
}

/**
 * Loading fallback for lazy-loaded code blocks
 */
export function CodeLoadingFallback() {
  return (
    <div className="my-2 bg-gray-900 rounded-lg overflow-hidden animate-pulse">
      <div className="p-4">
        <div className="h-4 bg-gray-700 rounded w-1/4 mb-3" />
        <div className="space-y-2">
          <div className="h-3 bg-gray-800 rounded w-3/4" />
          <div className="h-3 bg-gray-800 rounded w-1/2" />
          <div className="h-3 bg-gray-800 rounded w-2/3" />
        </div>
      </div>
    </div>
  );
}

/**
 * Loading fallback for lazy-loaded Sandpack executor
 */
export function SandpackLoadingFallback() {
  return (
    <div className="my-2 bg-gray-900 rounded-lg overflow-hidden animate-pulse border border-gray-700">
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
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 size={14} className="animate-spin" />
          <span className="text-xs">Loading interactive editor...</span>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Streaming Placeholder Component
// =============================================================================

/**
 * Placeholder shown while artifact content is streaming
 */
function StreamingArtifactPlaceholder({ language }: { language?: string }) {
  const getLabel = () => {
    switch (language) {
      case "mermaid":
        return "Mermaid diagram";
      case "chart":
        return "Chart";
      case "svg":
        return "SVG graphic";
      case "json":
        return "JSON data";
      default:
        return "Content";
    }
  };

  return (
    <div
      data-testid="streaming-artifact-placeholder"
      className="my-2 p-4 bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700"
    >
      <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Generating {getLabel()}...</span>
      </div>
      <div className="mt-3 h-24 bg-gray-200 dark:bg-gray-700 rounded animate-pulse" />
    </div>
  );
}

// =============================================================================
// Chart Code Block
// =============================================================================

/**
 * Wrapper component for chart code blocks
 * Parses JSON and passes to InteractiveChart, with error handling
 */
function ChartCodeBlock({ code }: { code: string }) {
  const [error, setError] = useState<string | null>(null);
  const [chartData, setChartData] = useState<ChartData | null>(null);

  useEffect(() => {
    try {
      const parsed = JSON.parse(code) as ChartData;
      if (!parsed.type || !parsed.data || !Array.isArray(parsed.data)) {
        throw new Error("Invalid chart data: missing type or data array");
      }
      setChartData(parsed);
      setError(null);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to parse chart data",
      );
    }
  }, [code]);

  if (error) {
    return (
      <div className="my-2 p-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg">
        <div className="flex items-center gap-2 text-warning-600 dark:text-warning-400 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Chart Error</span>
        </div>
        <pre className="text-xs text-warning-600 overflow-x-auto">{error}</pre>
      </div>
    );
  }

  if (!chartData) return null;

  return <InteractiveChart chartData={chartData} />;
}

// =============================================================================
// Markdown Content Component
// =============================================================================

/**
 * Props for the MarkdownContent component
 */
export interface MarkdownContentProps {
  /** Markdown content to render */
  content: string;
  /** Enable interactive artifact rendering. Default: true */
  enableInteractiveArtifacts?: boolean;
  /** Whether content is actively streaming. Default: false */
  isStreaming?: boolean;
}

/**
 * Markdown renderer with custom components
 */
function MarkdownContentImpl({
  content,
  enableInteractiveArtifacts = true,
  isStreaming = false,
}: MarkdownContentProps) {
  const components = useMemo(
    () => ({
      // Code blocks with syntax highlighting and special renderers
      code: ({
        inline,
        className,
        children,
        ...props
      }: {
        inline?: boolean;
        className?: string;
        children?: React.ReactNode;
      } & React.HTMLAttributes<HTMLElement>) => {
        const match = /language-(\w+)/.exec(className || "");
        const language = match ? match[1] : undefined;
        const codeContent = String(children).replace(/\n$/, "");

        // Interactive artifacts - only render when enabled
        if (enableInteractiveArtifacts) {
          // Parse-prone artifacts: Always defer during streaming (LLM done signal)
          // Content heuristics can't reliably detect incomplete syntax, so we rely
          // entirely on the isStreaming flag for robustness. This prevents:
          // - Mermaid: incomplete dates/task definitions in gantt charts
          // - Chart: incomplete JSON causing parse errors
          // - SVG: unclosed tags causing DOMParser errors
          const isParseProneArtifact =
            language === "mermaid" ||
            language === "chart" ||
            language === "svg";

          if (isParseProneArtifact && isStreaming && !inline) {
            return <StreamingArtifactPlaceholder language={language} />;
          }

          // Handle mermaid diagrams (lazy loaded for bundle optimization)
          if (language === "mermaid" && !inline) {
            return (
              <Suspense fallback={<DiagramLoadingFallback />}>
                <InteractiveMermaidDiagram code={codeContent} />
              </Suspense>
            );
          }

          // Handle chart blocks
          if (language === "chart" && !inline) {
            return <ChartCodeBlock code={codeContent} />;
          }

          // Handle SVG blocks with interactive controls
          if (language === "svg" && !inline) {
            return <InteractiveSVGArtifact data={codeContent} />;
          }

          // Handle audio blocks (URL or base64)
          if (language === "audio" && !inline) {
            return <AudioArtifact data={codeContent.trim()} />;
          }

          // Handle video blocks (URL or base64)
          if (language === "video" && !inline) {
            return <VideoArtifact data={codeContent.trim()} />;
          }

          // Handle executable code blocks (run:python, run:javascript, etc.)
          if (language?.startsWith("run:") && !inline) {
            const execLanguage = language.replace("run:", "");
            return (
              <ExecutableArtifact
                data={codeContent}
                config={{ language: execLanguage, runtime: "docker" }}
              />
            );
          }

          // Handle JSX/TSX code blocks with Sandpack for live execution (lazy loaded)
          if ((language === "jsx" || language === "tsx") && !inline) {
            return (
              <Suspense fallback={<SandpackLoadingFallback />}>
                <SandpackExecutor
                  code={codeContent}
                  language={language}
                  title="Interactive Component"
                  showRunButton={true}
                  autoRun={false}
                  theme="dark"
                />
              </Suspense>
            );
          }

          // Handle MDX code blocks with Sandpack (lazy loaded)
          if (language === "mdx" && !inline) {
            return (
              <Suspense fallback={<SandpackLoadingFallback />}>
                <SandpackExecutor
                  code={codeContent}
                  language="mdx"
                  title="Interactive Report"
                  showRunButton={true}
                  autoRun={false}
                  theme="dark"
                />
              </Suspense>
            );
          }
        }

        if (!inline && codeContent.includes("\n")) {
          return (
            <Suspense fallback={<CodeLoadingFallback />}>
              <CodeBlock language={language}>{codeContent}</CodeBlock>
            </Suspense>
          );
        }

        return (
          <code
            className="bg-gray-200 dark:bg-gray-700 px-1.5 py-0.5 rounded text-sm font-mono text-pink-600 dark:text-pink-400"
            {...props}
          >
            {children}
          </code>
        );
      },
      // Links open in new tab
      a: ({
        href,
        children,
        ...props
      }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-primary-600 dark:text-primary-400 hover:underline"
          {...props}
        >
          {children}
        </a>
      ),
      // Paragraphs with proper spacing
      p: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLParagraphElement>) => (
        <p className="mb-2 last:mb-0" {...props}>
          {children}
        </p>
      ),
      // Lists with proper styling
      ul: ({ children, ...props }: React.HTMLAttributes<HTMLUListElement>) => (
        <ul className="list-disc list-inside mb-2 space-y-1" {...props}>
          {children}
        </ul>
      ),
      ol: ({
        children,
        ...props
      }: React.OlHTMLAttributes<HTMLOListElement>) => (
        <ol className="list-decimal list-inside mb-2 space-y-1" {...props}>
          {children}
        </ol>
      ),
      // Headers with proper sizing
      h1: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h1 className="text-xl font-bold mb-2 mt-4 first:mt-0" {...props}>
          {children}
        </h1>
      ),
      h2: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h2 className="text-lg font-bold mb-2 mt-3 first:mt-0" {...props}>
          {children}
        </h2>
      ),
      h3: ({
        children,
        ...props
      }: React.HTMLAttributes<HTMLHeadingElement>) => (
        <h3 className="text-base font-bold mb-1 mt-2 first:mt-0" {...props}>
          {children}
        </h3>
      ),
      // Blockquotes
      blockquote: ({
        children,
        ...props
      }: React.BlockquoteHTMLAttributes<HTMLQuoteElement>) => (
        <blockquote
          className="border-l-4 border-gray-300 dark:border-gray-600 pl-4 italic text-gray-600 dark:text-gray-400 my-2"
          {...props}
        >
          {children}
        </blockquote>
      ),
      // Tables with GFM support
      table: ({
        children,
        ...props
      }: React.TableHTMLAttributes<HTMLTableElement>) => (
        <div className="overflow-x-auto my-2">
          <table
            className="min-w-full border-collapse border border-gray-300 dark:border-gray-600"
            {...props}
          >
            {children}
          </table>
        </div>
      ),
      th: ({
        children,
        ...props
      }: React.ThHTMLAttributes<HTMLTableHeaderCellElement>) => (
        <th
          className="border border-gray-300 dark:border-gray-600 px-3 py-2 bg-gray-100 dark:bg-gray-700 font-semibold text-left"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({
        children,
        ...props
      }: React.TdHTMLAttributes<HTMLTableDataCellElement>) => (
        <td
          className="border border-gray-300 dark:border-gray-600 px-3 py-2"
          {...props}
        >
          {children}
        </td>
      ),
      // Horizontal rule
      hr: (props: React.HTMLAttributes<HTMLHRElement>) => (
        <hr className="my-4 border-gray-300 dark:border-gray-600" {...props} />
      ),
    }),
    [enableInteractiveArtifacts, isStreaming],
  );

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath]}
      rehypePlugins={[rehypeKatex]}
      components={components}
    >
      {content}
    </ReactMarkdown>
  );
}

export const MarkdownContent = memo(MarkdownContentImpl);
MarkdownContent.displayName = "MarkdownContent";

export default MarkdownContent;

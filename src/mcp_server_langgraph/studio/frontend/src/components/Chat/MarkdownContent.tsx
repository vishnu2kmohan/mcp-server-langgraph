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
 * - Markdown references ([[type:qualifier:id]] syntax)
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
import ReactMarkdown, { defaultUrlTransform } from "react-markdown";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { Loader2, AlertCircle } from "lucide-react";
import "katex/dist/katex.min.css";

// Markdown references support ([[type:qualifier:id]] syntax)
import { remarkReferences } from "@/remark/remarkReferences";
import { ReferenceChip } from "@/components/References";
import type { ReferenceType } from "@/types/references";

// Rich media artifact components
import { InteractiveSVGArtifact } from "../Artifacts/InteractiveSVGArtifact";
import { AudioArtifact } from "../Artifacts/AudioArtifact";
import { VideoArtifact } from "../Artifacts/VideoArtifact";
import { ExecutableArtifact } from "../Artifacts/ExecutableArtifact";
import { InteractiveChart, type ChartData } from "./InteractiveChart";
import { isVegaLiteContent } from "../../utils/artifactParser";

// Lazy loaded components for bundle optimization
const InteractiveMermaidDiagram = lazy(
  () => import("./InteractiveMermaidDiagram"),
);
const CodeBlock = lazy(() => import("./CodeBlock"));
const SandpackExecutor = lazy(() => import("../Artifacts/SandpackExecutor"));
const VegaLiteArtifact = lazy(() =>
  import("../Artifacts/VegaLiteArtifact").then((m) => ({
    default: m.VegaLiteArtifact,
  })),
);

// =============================================================================
// Loading Fallbacks
// =============================================================================

/**
 * Loading fallback for lazy-loaded diagram components
 */
export function DiagramLoadingFallback() {
  return (
    <div className="my-2 p-4 bg-neutral-1 rounded-lg border border-neutral-5 animate-pulse">
      <div className="flex items-center gap-2 text-neutral-10">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Loading diagram...</span>
      </div>
      <div className="mt-3 h-32 bg-neutral-3 rounded" />
    </div>
  );
}

/**
 * Loading fallback for lazy-loaded code blocks
 */
export function CodeLoadingFallback() {
  return (
    <div className="my-2 bg-neutral-2 rounded-lg overflow-hidden animate-pulse">
      <div className="p-4">
        <div className="h-4 bg-neutral-4 rounded w-1/4 mb-3" />
        <div className="space-y-2">
          <div className="h-3 bg-neutral-3 rounded w-3/4" />
          <div className="h-3 bg-neutral-3 rounded w-1/2" />
          <div className="h-3 bg-neutral-3 rounded w-2/3" />
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
    <div className="my-2 bg-neutral-2 rounded-lg overflow-hidden animate-pulse border border-neutral-7">
      <div className="flex items-center gap-2 p-3 bg-neutral-3 border-b border-neutral-7">
        <div className="h-4 bg-neutral-4 rounded w-32" />
        <div className="ml-auto h-6 w-16 bg-neutral-4 rounded" />
      </div>
      <div className="p-4 space-y-2">
        <div className="h-3 bg-neutral-3 rounded w-2/3" />
        <div className="h-3 bg-neutral-3 rounded w-1/2" />
        <div className="h-3 bg-neutral-3 rounded w-3/4" />
      </div>
      <div className="p-4 bg-neutral-3 border-t border-neutral-7">
        <div className="flex items-center gap-2 text-neutral-10">
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
      className="my-2 p-4 bg-neutral-1 rounded-lg border border-neutral-5"
    >
      <div className="flex items-center gap-2 text-neutral-10">
        <Loader2 size={16} className="animate-spin" />
        <span className="text-sm">Generating {getLabel()}...</span>
      </div>
      <div className="mt-3 h-24 bg-neutral-3 rounded animate-pulse" />
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
      <div className="my-2 p-4 bg-warning-3 bg-warning-3 border border-warning-6 dark:border-warning-11 rounded-lg">
        <div className="flex items-center gap-2 text-warning-9 dark:text-warning-9 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Chart Error</span>
        </div>
        <pre className="text-xs text-warning-9 overflow-x-auto">{error}</pre>
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
          // - Vega-Lite/Altair: incomplete JSON specs
          const isVegaLiteLanguage =
            language === "vega-lite" ||
            language === "vega" ||
            language === "altair";
          const isParseProneArtifact =
            language === "mermaid" ||
            language === "chart" ||
            language === "svg" ||
            isVegaLiteLanguage;

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

          // Handle Vega-Lite/Altair blocks (preferred for interactive charts)
          if (isVegaLiteLanguage && !inline) {
            return (
              <Suspense fallback={<DiagramLoadingFallback />}>
                <VegaLiteArtifact spec={codeContent} />
              </Suspense>
            );
          }

          // Handle chart blocks (deprecated: prefer vega-lite)
          if (language === "chart" && !inline) {
            return <ChartCodeBlock code={codeContent} />;
          }

          // Auto-detect Vega-Lite specs in JSON blocks by checking $schema
          // This allows users to paste Vega-Lite JSON without explicit language tag
          if (
            (language === "json" || language === "jsonc") &&
            !inline &&
            isVegaLiteContent(codeContent)
          ) {
            // Defer during streaming to prevent incomplete JSON parse errors
            if (isStreaming) {
              return <StreamingArtifactPlaceholder language="vega-lite" />;
            }
            return (
              <Suspense fallback={<DiagramLoadingFallback />}>
                <VegaLiteArtifact spec={codeContent} />
              </Suspense>
            );
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
            className="bg-neutral-3 px-1.5 py-0.5 rounded text-sm font-mono text-error-10 dark:text-error-11"
            {...props}
          >
            {children}
          </code>
        );
      },
      // Links: handle ref:// for references, otherwise open in new tab
      a: ({
        href,
        children,
        title,
        ...props
      }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
        // Handle markdown references (ref://type/qualifier:id)
        if (href?.startsWith('ref://')) {
          // Parse ref:// URL: ref://type/qualifier:id
          // Examples:
          //   ref://tool/filesystem:read_file -> type=tool, qualifier=filesystem, id=read_file
          //   ref://skill/code-review -> type=skill, qualifier=code-review, id=code-review
          //   ref://artifact/chart-123 -> type=artifact, qualifier=chart-123, id=chart-123
          const match = href.match(/^ref:\/\/(tool|skill|artifact)\/(.+)$/);
          if (match) {
            const [, refType, refId] = match;
            const type = refType as ReferenceType;

            // For tools, split qualifier:id; for others, use id as both
            let qualifier: string;
            let id: string;
            if (type === 'tool' && refId.includes(':')) {
              const colonIndex = refId.indexOf(':');
              qualifier = refId.slice(0, colonIndex);
              id = refId.slice(colonIndex + 1);
            } else {
              qualifier = refId;
              id = refId;
            }

            return (
              <ReferenceChip
                type={type}
                qualifier={qualifier}
                id={id}
                label={title || undefined}
              />
            );
          }
        }

        // Regular link - open in new tab
        return (
          <a
            href={href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-primary-10 dark:text-primary-11 hover:underline"
            {...props}
          >
            {children}
          </a>
        );
      },
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
          className="border-l-4 border-neutral-5 pl-4 italic text-neutral-11 my-2"
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
            className="min-w-full border-collapse border border-neutral-5"
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
          className="border border-neutral-5 px-3 py-2 bg-neutral-2 font-semibold text-left"
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
          className="border border-neutral-5 px-3 py-2"
          {...props}
        >
          {children}
        </td>
      ),
      // Horizontal rule
      hr: (props: React.HTMLAttributes<HTMLHRElement>) => (
        <hr
          className="my-4 border-neutral-5"
          {...props}
        />
      ),
    }),
    [enableInteractiveArtifacts, isStreaming],
  );

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkMath, remarkReferences]}
      rehypePlugins={[rehypeKatex]}
      components={components}
      // Allow ref:// URLs for markdown references (normally sanitized by default)
      urlTransform={(url) =>
        url.startsWith("ref://") ? url : defaultUrlTransform(url)
      }
    >
      {content}
    </ReactMarkdown>
  );
}

export const MarkdownContent = memo(MarkdownContentImpl);
MarkdownContent.displayName = "MarkdownContent";

export default MarkdownContent;

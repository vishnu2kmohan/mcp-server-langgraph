/**
 * ChatMessages Component
 *
 * Displays the message list with streaming response support.
 * Handles empty state, message rendering, and auto-scroll.
 *
 * Features:
 * - Rich markdown rendering with react-markdown
 * - GitHub Flavored Markdown (tables, strikethrough, task lists)
 * - Native emoji support
 * - Syntax highlighting for code blocks
 * - Source citations for AI responses
 *
 * Extracted from ChatPage for improved modularity.
 */

import { useRef, useEffect, useMemo } from "react";
import {
  MessageSquare,
  RefreshCw,
  ExternalLink,
  Copy,
  Check,
  AlertCircle,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { oneDark } from "react-syntax-highlighter/dist/esm/styles/prism";
import { ConfidenceIndicator } from "./ConfidenceIndicator";
// Rich media artifact components for artifact rendering support
import { InteractiveSVGArtifact } from "../Artifacts/InteractiveSVGArtifact";
import { AudioArtifact } from "../Artifacts/AudioArtifact";
import { VideoArtifact } from "../Artifacts/VideoArtifact";
import { ExecutableArtifact } from "../Artifacts/ExecutableArtifact";
import {
  HallucinationIndicator,
  type HallucinationReport,
} from "./HallucinationIndicator";
// Interactive renderers for diagrams and charts
import { InteractiveMermaidDiagram } from "./InteractiveMermaidDiagram";
import { InteractiveChart, type ChartData } from "./InteractiveChart";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useState, useCallback } from "react";
import "katex/dist/katex.min.css";

export interface Source {
  title: string;
  url: string;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  timestamp: number;
  sources?: Source[];
  /** AI confidence score (0-1) for assistant messages */
  confidence?: number;
  /** Whether this message has been flagged for hallucination */
  isReported?: boolean;
}

export interface ThinkingTrace {
  rawOutput?: string;
  steps?: Array<{ name: string; status: string; duration?: number }>;
  tokens?: { input: number; output: number };
}

export interface ChatMessagesProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  isSending?: boolean;
  thinkingTrace?: ThinkingTrace;
  /** Callback when user reports a hallucination */
  onReportHallucination?: (report: HallucinationReport) => void;
}

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
      <div className="my-2 p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg">
        <div className="flex items-center gap-2 text-yellow-600 dark:text-yellow-400 mb-2">
          <AlertCircle size={16} />
          <span className="font-medium">Chart Error</span>
        </div>
        <pre className="text-xs text-yellow-600 overflow-x-auto">{error}</pre>
      </div>
    );
  }

  if (!chartData) return null;

  return <InteractiveChart chartData={chartData} />;
}

/**
 * Get file extension for a language
 */
function getFileExtension(language?: string): string {
  const extensions: Record<string, string> = {
    javascript: "js",
    typescript: "ts",
    python: "py",
    ruby: "rb",
    rust: "rs",
    java: "java",
    cpp: "cpp",
    c: "c",
    go: "go",
    swift: "swift",
    kotlin: "kt",
    scala: "scala",
    php: "php",
    html: "html",
    css: "css",
    scss: "scss",
    json: "json",
    yaml: "yaml",
    xml: "xml",
    sql: "sql",
    bash: "sh",
    shell: "sh",
    markdown: "md",
    text: "txt",
  };
  return extensions[language || ""] || language || "txt";
}

/**
 * Enhanced code block component with syntax highlighting and interactive controls:
 * - Copy to clipboard
 * - Word wrap toggle
 * - Download as file
 */
function CodeBlock({
  language,
  children,
}: {
  language?: string;
  children: string;
}) {
  const [copied, setCopied] = useState(false);
  const [wordWrap, setWordWrap] = useState(false);

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(children);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [children]);

  const handleToggleWordWrap = useCallback(() => {
    setWordWrap((prev) => !prev);
  }, []);

  const handleDownload = useCallback(() => {
    const ext = getFileExtension(language);
    const blob = new Blob([children], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.download = `code.${ext}`;
    link.href = url;
    link.click();
    URL.revokeObjectURL(url);
  }, [children, language]);

  return (
    <div className="relative group my-2">
      {/* Toolbar */}
      <div className="absolute right-2 top-2 z-10 flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={handleToggleWordWrap}
          className={`p-1.5 rounded transition-colors ${
            wordWrap
              ? "bg-blue-600 text-white"
              : "bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white"
          }`}
          title="Toggle word wrap"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="3" y1="6" x2="21" y2="6" />
            <path d="M3 12h15a3 3 0 1 1 0 6h-4" />
            <polyline points="16 16 14 18 16 20" />
            <line x1="3" y1="18" x2="10" y2="18" />
          </svg>
        </button>
        <button
          onClick={handleDownload}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors"
          title="Download file"
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
        </button>
        <button
          onClick={handleCopy}
          className="p-1.5 bg-gray-700 hover:bg-gray-600 rounded text-gray-300 hover:text-white transition-colors"
          title="Copy code"
        >
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
      </div>
      {language && (
        <div className="absolute left-3 top-2 z-10 text-xs text-gray-400 font-mono">
          {language}
        </div>
      )}
      <SyntaxHighlighter
        style={oneDark}
        language={language || "text"}
        showLineNumbers
        wrapLongLines={wordWrap}
        customStyle={{
          margin: 0,
          borderRadius: "0.5rem",
          paddingTop: "2rem",
        }}
        codeTagProps={{
          className: "text-sm font-mono",
        }}
      >
        {children}
      </SyntaxHighlighter>
    </div>
  );
}

/**
 * Markdown renderer with custom components
 */
function MarkdownContent({ content }: { content: string }) {
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

        // Handle mermaid diagrams
        if (language === "mermaid" && !inline) {
          return <InteractiveMermaidDiagram code={codeContent} />;
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

        if (!inline && codeContent.includes("\n")) {
          return <CodeBlock language={language}>{codeContent}</CodeBlock>;
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
          className="text-blue-600 dark:text-blue-400 hover:underline"
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
    [],
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

export function ChatMessages({
  messages,
  isStreaming = false,
  streamingContent = "",
  isSending = false,
  thinkingTrace,
  onReportHallucination,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showThinkingTrace, setShowThinkingTrace] = useState(false);

  // Auto-scroll to bottom when messages or streaming content change
  useEffect(() => {
    // Guard against scrollIntoView not being available (e.g., in jsdom tests)
    if (
      messagesEndRef.current &&
      typeof messagesEndRef.current.scrollIntoView === "function"
    ) {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streamingContent]);

  if (messages.length === 0 && !isStreaming && !isSending) {
    return (
      <div className="flex-1 overflow-y-auto p-6">
        <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
          <MessageSquare size={48} className="mb-4 opacity-50" />
          <p>No messages yet. Start a conversation!</p>
        </div>
        <div ref={messagesEndRef} data-testid="messages-end" />
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto p-6 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[70%] px-4 py-3 rounded-lg ${
              message.role === "user"
                ? "bg-blue-600 text-white"
                : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-900 dark:text-gray-100"
            }`}
          >
            {/* Rich markdown rendering for all messages */}
            <div
              className={`prose prose-sm dark:prose-invert max-w-none ${
                message.role === "user" ? "prose-invert" : ""
              }`}
            >
              <MarkdownContent content={message.content} />
            </div>
            {/* Source Citations - only for assistant messages with sources */}
            {message.role === "assistant" &&
              message.sources &&
              message.sources.length > 0 && (
                <div className="mt-3 pt-2 border-t border-gray-200 dark:border-gray-600">
                  <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">
                    Sources:
                  </p>
                  <div className="flex flex-wrap gap-2">
                    {message.sources.map((source, index) => (
                      <a
                        key={index}
                        href={source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        <ExternalLink size={10} />
                        {source.title}
                      </a>
                    ))}
                  </div>
                </div>
              )}
            {/* AI-specific indicators for assistant messages */}
            {message.role === "assistant" && (
              <div className="mt-2 pt-2 border-t border-gray-100 dark:border-gray-700 flex items-center gap-3 flex-wrap">
                {/* Confidence indicator */}
                {message.confidence !== undefined && (
                  <ConfidenceIndicator score={message.confidence} />
                )}

                {/* Hallucination report button */}
                {onReportHallucination && (
                  <HallucinationIndicator
                    messageId={message.id}
                    onReport={onReportHallucination}
                    isReported={message.isReported}
                  />
                )}
              </div>
            )}

            <p
              className={`text-xs mt-1 ${
                message.role === "user" ? "text-blue-200" : "text-gray-400"
              }`}
            >
              {new Date(message.timestamp).toLocaleTimeString()}
            </p>
          </div>
        </div>
      ))}

      {/* Streaming response with markdown rendering */}
      {isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-[70%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg text-gray-900 dark:text-gray-100">
            {streamingContent ? (
              <div className="relative prose prose-sm dark:prose-invert max-w-none">
                <MarkdownContent content={streamingContent} />
                <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Clickable thinking indicator */}
                <button
                  onClick={() => setShowThinkingTrace(!showThinkingTrace)}
                  className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
                  aria-expanded={showThinkingTrace}
                  aria-label="Toggle thinking trace"
                >
                  <RefreshCw size={16} className="animate-spin" />
                  <span>Thinking...</span>
                  <span className="text-xs text-blue-500 hover:text-blue-600">
                    {showThinkingTrace ? "Hide trace" : "Show trace"}
                  </span>
                </button>

                {/* Thinking trace panel */}
                {showThinkingTrace && thinkingTrace && (
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs font-mono">
                    {/* Steps visualization */}
                    {thinkingTrace.steps && thinkingTrace.steps.length > 0 && (
                      <div className="mb-2">
                        <p className="text-gray-500 dark:text-gray-400 mb-1 font-sans text-xs font-semibold">
                          Execution Steps:
                        </p>
                        <ul className="space-y-1">
                          {thinkingTrace.steps.map((step, i) => (
                            <li key={i} className="flex items-center gap-2">
                              <span
                                className={`w-2 h-2 rounded-full ${
                                  step.status === "completed"
                                    ? "bg-green-500"
                                    : step.status === "running"
                                      ? "bg-blue-500 animate-pulse"
                                      : "bg-gray-400"
                                }`}
                              />
                              <span className="text-gray-700 dark:text-gray-300">
                                {step.name}
                              </span>
                              {step.duration && (
                                <span className="text-gray-400">
                                  ({step.duration}ms)
                                </span>
                              )}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Token usage */}
                    {thinkingTrace.tokens && (
                      <div className="mb-2 flex gap-4 text-gray-500 dark:text-gray-400">
                        <span>Input: {thinkingTrace.tokens.input} tokens</span>
                        <span>
                          Output: {thinkingTrace.tokens.output} tokens
                        </span>
                      </div>
                    )}

                    {/* Raw output */}
                    {thinkingTrace.rawOutput && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-sans">
                          Raw Output
                        </summary>
                        <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto max-h-48 overflow-y-auto text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                          {thinkingTrace.rawOutput}
                        </pre>
                      </details>
                    )}

                    {/* Fallback when no trace data */}
                    {!thinkingTrace.steps &&
                      !thinkingTrace.tokens &&
                      !thinkingTrace.rawOutput && (
                        <p className="text-gray-400 italic font-sans">
                          Processing... trace data will appear here.
                        </p>
                      )}
                  </div>
                )}

                {/* Placeholder when trace toggle is on but no data */}
                {showThinkingTrace && !thinkingTrace && (
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs">
                    <p className="text-gray-400 italic">
                      Trace data not available. Enable verbose mode in settings
                      to see execution details.
                    </p>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Legacy sending indicator (fallback) */}
      {isSending && !isStreaming && (
        <div className="flex justify-start">
          <div className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg">
            <button
              onClick={() => setShowThinkingTrace(!showThinkingTrace)}
              className="flex items-center gap-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
              aria-expanded={showThinkingTrace}
            >
              <RefreshCw size={16} className="animate-spin" />
              <span>Thinking...</span>
              <span className="text-xs text-blue-500 hover:text-blue-600">
                {showThinkingTrace ? "Hide trace" : "Show trace"}
              </span>
            </button>
            {showThinkingTrace && (
              <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs text-gray-400 italic">
                Waiting for trace data...
              </div>
            )}
          </div>
        </div>
      )}

      <div ref={messagesEndRef} data-testid="messages-end" />
    </div>
  );
}

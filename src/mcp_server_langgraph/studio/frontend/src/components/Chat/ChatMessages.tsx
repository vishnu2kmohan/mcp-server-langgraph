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

import { useRef, useEffect, useMemo, lazy, Suspense } from "react";
import {
  MessageSquare,
  RefreshCw,
  ExternalLink,
  AlertCircle,
  GitBranch,
  Play,
  Square,
  Wrench,
  GitFork,
  Bot,
  Circle,
  CheckCircle,
  XCircle,
  Loader2,
  ArrowRight,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
// Note: SyntaxHighlighter moved to CodeBlock.tsx for lazy loading
import { ConfidenceIndicator } from "./ConfidenceIndicator";
import { MessageActions } from "./MessageActions";
// Rich media artifact components for artifact rendering support
import { InteractiveSVGArtifact } from "../Artifacts/InteractiveSVGArtifact";
import { AudioArtifact } from "../Artifacts/AudioArtifact";
import { VideoArtifact } from "../Artifacts/VideoArtifact";
import { ExecutableArtifact } from "../Artifacts/ExecutableArtifact";
// SandpackExecutor lazy loaded below for bundle optimization (612 KB sandpack)
import {
  HallucinationIndicator,
  type HallucinationReport,
} from "./HallucinationIndicator";
// LLM native thinking trace display (for Claude Opus 4.5, Gemini 2.5, etc.)
import { LLMThinkingTrace } from "./LLMThinkingTrace";
import {
  AIFollowUpSuggestions,
  type FollowUpSuggestion,
} from "./AIFollowUpSuggestions";
// Interactive renderers for diagrams and charts (lazy loaded for bundle optimization)
const InteractiveMermaidDiagram = lazy(
  () => import("./InteractiveMermaidDiagram"),
);
// Code block with syntax highlighting (lazy loaded - 618 KB react-syntax-highlighter)
const CodeBlock = lazy(() => import("./CodeBlock"));
// Interactive code execution (lazy loaded - 612 KB sandpack)
const SandpackExecutor = lazy(() => import("../Artifacts/SandpackExecutor"));
import { InteractiveChart, type ChartData } from "./InteractiveChart";

/**
 * Loading fallback for lazy-loaded diagram components
 */
function DiagramLoadingFallback() {
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
function CodeLoadingFallback() {
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
function SandpackLoadingFallback() {
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
        <div className="flex items-center gap-2 text-gray-500">
          <Loader2 size={14} className="animate-spin" />
          <span className="text-xs">Loading interactive editor...</span>
        </div>
      </div>
    </div>
  );
}
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import { useState } from "react";
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
  /** LLM thinking/reasoning content (from Claude extended thinking, Gemini thinking_content, etc.) */
  thinkingContent?: string;
  /** Number of tokens used for thinking/reasoning */
  thinkingTokens?: number;
  /** Model name that generated this message */
  modelName?: string;
}

/**
 * LangGraph node types for visualization
 */
export type LangGraphNodeType =
  | "start"
  | "end"
  | "tool"
  | "conditional"
  | "agent"
  | "default";

/**
 * LangGraph node status
 */
export type LangGraphNodeStatus =
  | "pending"
  | "running"
  | "completed"
  | "error"
  | "skipped";

/**
 * LangGraph node for execution visualization
 */
export interface LangGraphNode {
  id: string;
  name: string;
  type: LangGraphNodeType;
  status: LangGraphNodeStatus;
  /** Duration in milliseconds */
  duration?: number;
  /** Tool/function output if applicable */
  output?: string;
}

/**
 * LangGraph edge connecting nodes
 */
export interface LangGraphEdge {
  from: string;
  to: string;
  /** Condition label for conditional edges */
  condition?: string;
}

/**
 * Agent execution trace (distinct from LLM thinking content)
 * Tracks agent steps, token usage, and raw output for observability.
 * Supports LangGraph node/edge visualization.
 */
export interface AgentExecutionTrace {
  rawOutput?: string;
  steps?: Array<{ name: string; status: string; duration?: number }>;
  tokens?: { input: number; output: number };
  /** LangGraph nodes for graph visualization */
  nodes?: LangGraphNode[];
  /** LangGraph edges connecting nodes */
  edges?: LangGraphEdge[];
  /** Currently active node ID */
  currentNode?: string;
}

/**
 * @deprecated Use AgentExecutionTrace instead. Renamed for clarity.
 */
export type AgentTrace = AgentExecutionTrace;

/**
 * @deprecated Use AgentExecutionTrace instead. Renamed to clarify distinction from LLM thinking.
 */
export type ThinkingTrace = AgentExecutionTrace;

// Re-export FollowUpSuggestion type for consumers
export type { FollowUpSuggestion };

export interface ChatMessagesProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  isSending?: boolean;
  /** Agent execution trace (steps, tokens, raw output). Distinct from LLM thinking. */
  agentExecutionTrace?: AgentExecutionTrace;
  /** Callback when user reports a hallucination */
  onReportHallucination?: (report: HallucinationReport) => void;
  /** Enable interactive artifact rendering (mermaid, charts, SVG, etc.). Default: true */
  enableInteractiveArtifacts?: boolean;
  /** Callback when user wants to edit a message (user messages only) */
  onEditMessage?: (messageId: string) => void;
  /** Callback when user wants to regenerate a response (assistant messages only) */
  onRegenerateMessage?: (messageId: string) => void;
  /** Callback when user wants to delete a message */
  onDeleteMessage?: (messageId: string) => void;
  /** Whether a message is being regenerated */
  isRegenerating?: boolean;
  // LLM native thinking trace props (for extended thinking models like Claude Opus 4.5, Gemini 2.5)
  /** LLM native thinking/reasoning content */
  llmThinkingContent?: string;
  /** Number of thinking tokens used */
  llmThinkingTokens?: number;
  /** Whether thinking trace is expanded */
  isThinkingExpanded?: boolean;
  /** Callback to toggle thinking trace expansion */
  onToggleThinking?: () => void;
  /** LLM model name for display */
  llmModelName?: string;
  /** Whether the current model supports extended thinking */
  isThinkingModel?: boolean;
  // AI Follow-Up Suggestions props
  /** Follow-up suggestions to display after the last assistant message */
  suggestions?: FollowUpSuggestion[];
  /** Callback when a suggestion is selected */
  onSuggestionSelect?: (suggestion: FollowUpSuggestion) => void;
  /** Callback when feedback is provided on a suggestion (thumbs up/down) */
  onSuggestionFeedback?: (
    suggestion: FollowUpSuggestion,
    feedback: "positive" | "negative",
  ) => void;
  /** Whether suggestions are loading */
  suggestionsLoading?: boolean;
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

// Note: CodeBlock component moved to CodeBlock.tsx for lazy loading

// =============================================================================
// LangGraph Node Visualization
// =============================================================================

interface LangGraphNodeVisualizationProps {
  nodes: LangGraphNode[];
  edges?: LangGraphEdge[];
  currentNode?: string;
}

/**
 * Get icon for node type
 */
function getNodeTypeIcon(type: LangGraphNodeType, size: number = 14) {
  const iconProps = { size, className: "flex-shrink-0" };
  switch (type) {
    case "start":
      return <Play {...iconProps} data-testid="node-type-start" />;
    case "end":
      return <Square {...iconProps} data-testid="node-type-end" />;
    case "tool":
      return <Wrench {...iconProps} data-testid="node-type-tool" />;
    case "conditional":
      return <GitFork {...iconProps} data-testid="node-type-conditional" />;
    case "agent":
      return <Bot {...iconProps} data-testid="node-type-agent" />;
    default:
      return <Circle {...iconProps} data-testid="node-type-default" />;
  }
}

/**
 * Get status indicator for node
 */
function getNodeStatusIndicator(status: LangGraphNodeStatus) {
  switch (status) {
    case "completed":
      return (
        <CheckCircle
          size={12}
          className="text-green-500"
          data-testid="node-status-completed"
        />
      );
    case "running":
      return (
        <Loader2
          size={12}
          className="text-blue-500 animate-spin"
          data-testid="node-status-running"
        />
      );
    case "error":
      return (
        <XCircle
          size={12}
          className="text-red-500"
          data-testid="node-status-error"
        />
      );
    case "pending":
      return (
        <Circle
          size={12}
          className="text-gray-400"
          data-testid="node-status-pending"
        />
      );
    case "skipped":
      return (
        <Circle
          size={12}
          className="text-gray-300 opacity-50"
          data-testid="node-status-skipped"
        />
      );
  }
}

/**
 * Get node background color based on type and status
 */
function getNodeColor(
  type: LangGraphNodeType,
  status: LangGraphNodeStatus,
): string {
  if (status === "error")
    return "bg-red-50 dark:bg-red-900/20 border-red-300 dark:border-red-700";
  if (status === "running")
    return "bg-blue-50 dark:bg-blue-900/20 border-blue-300 dark:border-blue-700";
  if (status === "completed")
    return "bg-green-50 dark:bg-green-900/20 border-green-300 dark:border-green-700";

  switch (type) {
    case "start":
      return "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-700";
    case "end":
      return "bg-slate-50 dark:bg-slate-900/20 border-slate-300 dark:border-slate-700";
    case "conditional":
      return "bg-amber-50 dark:bg-amber-900/20 border-amber-300 dark:border-amber-700";
    case "tool":
      return "bg-purple-50 dark:bg-purple-900/20 border-purple-300 dark:border-purple-700";
    case "agent":
      return "bg-indigo-50 dark:bg-indigo-900/20 border-indigo-300 dark:border-indigo-700";
    default:
      return "bg-gray-50 dark:bg-gray-900/20 border-gray-300 dark:border-gray-700";
  }
}

/**
 * LangGraph node visualization component
 * Displays a visual representation of the workflow execution
 */
function LangGraphNodeVisualization({
  nodes,
  edges = [],
  currentNode,
}: LangGraphNodeVisualizationProps) {
  return (
    <div
      data-testid="langgraph-node-visualization"
      className="flex flex-col gap-2"
    >
      {/* Node list with edges */}
      {nodes.map((node, index) => {
        const isActive = node.id === currentNode;
        const outgoingEdges = edges.filter((e) => e.from === node.id);

        return (
          <div key={node.id} className="flex flex-col">
            {/* Node */}
            <div
              data-testid={`node-${node.id}`}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-lg border
                ${getNodeColor(node.type, node.status)}
                ${isActive ? "ring-2 ring-blue-500 ring-offset-1 dark:ring-offset-gray-900" : ""}
                transition-all duration-200
              `}
            >
              {/* Type icon */}
              <span className="text-gray-600 dark:text-gray-400">
                {getNodeTypeIcon(node.type)}
              </span>

              {/* Name */}
              <span className="flex-1 text-sm font-medium text-gray-800 dark:text-gray-200">
                {node.name}
              </span>

              {/* Duration */}
              {node.duration !== undefined && (
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  {node.duration}ms
                </span>
              )}

              {/* Status indicator */}
              {getNodeStatusIndicator(node.status)}
            </div>

            {/* Edges from this node */}
            {outgoingEdges.length > 0 && index < nodes.length - 1 && (
              <div className="flex flex-col gap-1 ml-4 my-1">
                {outgoingEdges.map((edge) => (
                  <div
                    key={`${edge.from}-${edge.to}`}
                    data-testid={`edge-${edge.from}-to-${edge.to}`}
                    className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500"
                  >
                    <ArrowRight size={10} />
                    {edge.condition && (
                      <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-700 rounded text-gray-600 dark:text-gray-300">
                        {edge.condition}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// =============================================================================
// Markdown Content
// =============================================================================

interface MarkdownContentProps {
  content: string;
  /** Enable interactive artifact rendering. Default: true */
  enableInteractiveArtifacts?: boolean;
}

/**
 * Markdown renderer with custom components
 */
function MarkdownContent({
  content,
  enableInteractiveArtifacts = true,
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
    [enableInteractiveArtifacts],
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
  agentExecutionTrace,
  onReportHallucination,
  enableInteractiveArtifacts = true,
  onEditMessage,
  onRegenerateMessage,
  onDeleteMessage,
  isRegenerating = false,
  // LLM native thinking trace props
  llmThinkingContent = "",
  llmThinkingTokens,
  isThinkingExpanded = false,
  onToggleThinking,
  llmModelName,
  isThinkingModel = false,
  // AI Follow-Up Suggestions props
  suggestions = [],
  onSuggestionSelect,
  onSuggestionFeedback,
  suggestionsLoading = false,
}: ChatMessagesProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [showAgentExecutionTrace, setShowAgentExecutionTrace] = useState(false);

  // Determine if we should show the LLM thinking trace
  const showLLMThinkingTrace =
    llmThinkingContent && llmThinkingContent.trim().length > 0;

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
          className={`group flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div className="relative flex items-start gap-2">
            {/* Message Actions - appears on hover (before message for assistant, after for user) */}
            {message.role !== "user" &&
              (onEditMessage || onRegenerateMessage || onDeleteMessage) && (
                <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
                  <MessageActions
                    messageId={message.id}
                    content={message.content}
                    role={message.role}
                    onEdit={onEditMessage}
                    onRegenerate={onRegenerateMessage}
                    onDelete={onDeleteMessage}
                    isRegenerating={isRegenerating}
                  />
                </div>
              )}
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
                <MarkdownContent
                  content={message.content}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                />
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
            {/* Message Actions for user messages - appears on hover (after message) */}
            {message.role === "user" &&
              (onEditMessage || onRegenerateMessage || onDeleteMessage) && (
                <div className="opacity-0 group-hover:opacity-100 transition-opacity pt-3">
                  <MessageActions
                    messageId={message.id}
                    content={message.content}
                    role={message.role}
                    onEdit={onEditMessage}
                    onRegenerate={onRegenerateMessage}
                    onDelete={onDeleteMessage}
                    isRegenerating={isRegenerating}
                  />
                </div>
              )}
          </div>
        </div>
      ))}

      {/* LLM Native Thinking Trace - displayed during streaming when thinking content is present */}
      {showLLMThinkingTrace && onToggleThinking && (
        <div className="flex justify-start">
          <div className="max-w-[70%]">
            <LLMThinkingTrace
              thinkingContent={llmThinkingContent}
              isExpanded={isThinkingExpanded}
              onToggle={onToggleThinking}
              thinkingTokens={llmThinkingTokens}
              modelName={llmModelName}
              isThinkingModel={isThinkingModel}
              isStreaming={isStreaming}
            />
          </div>
        </div>
      )}

      {/* Streaming response with markdown rendering */}
      {isStreaming && (
        <div className="flex justify-start">
          <div className="max-w-[70%] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 px-4 py-3 rounded-lg text-gray-900 dark:text-gray-100">
            {streamingContent ? (
              <div className="relative prose prose-sm dark:prose-invert max-w-none">
                <MarkdownContent
                  content={streamingContent}
                  enableInteractiveArtifacts={enableInteractiveArtifacts}
                />
                <span className="inline-block w-2 h-4 ml-1 bg-blue-500 animate-pulse align-middle" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Processing indicator with agent trace toggle */}
                <div className="flex items-center gap-3">
                  <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                    <RefreshCw size={16} className="animate-spin" />
                    <span>Processing...</span>
                  </div>
                  {/* Agent trace toggle button (graph icon) */}
                  <button
                    onClick={() =>
                      setShowAgentExecutionTrace(!showAgentExecutionTrace)
                    }
                    className={`p-1.5 rounded transition-colors ${
                      showAgentExecutionTrace
                        ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                        : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                    }`}
                    aria-expanded={showAgentExecutionTrace}
                    aria-label="Toggle agent execution trace"
                    title={
                      showAgentExecutionTrace
                        ? "Hide execution trace"
                        : "Show execution trace"
                    }
                  >
                    <GitBranch size={14} />
                  </button>
                </div>

                {/* Thinking trace panel */}
                {showAgentExecutionTrace && agentExecutionTrace && (
                  <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs font-mono">
                    {/* LangGraph Node Visualization - when nodes are provided */}
                    {agentExecutionTrace.nodes &&
                      agentExecutionTrace.nodes.length > 0 && (
                        <div className="mb-3">
                          <p className="text-gray-500 dark:text-gray-400 mb-2 font-sans text-xs font-semibold">
                            Workflow Execution:
                          </p>
                          <LangGraphNodeVisualization
                            nodes={agentExecutionTrace.nodes}
                            edges={agentExecutionTrace.edges}
                            currentNode={agentExecutionTrace.currentNode}
                          />
                        </div>
                      )}

                    {/* Simple Steps visualization - fallback when no nodes */}
                    {(!agentExecutionTrace.nodes ||
                      agentExecutionTrace.nodes.length === 0) &&
                      agentExecutionTrace.steps &&
                      agentExecutionTrace.steps.length > 0 && (
                        <div className="mb-2">
                          <p className="text-gray-500 dark:text-gray-400 mb-1 font-sans text-xs font-semibold">
                            Execution Steps:
                          </p>
                          <ul className="space-y-1">
                            {agentExecutionTrace.steps.map((step, i) => (
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
                    {agentExecutionTrace.tokens && (
                      <div className="mb-2 flex gap-4 text-gray-500 dark:text-gray-400">
                        <span>
                          Input: {agentExecutionTrace.tokens.input} tokens
                        </span>
                        <span>
                          Output: {agentExecutionTrace.tokens.output} tokens
                        </span>
                      </div>
                    )}

                    {/* Raw output */}
                    {agentExecutionTrace.rawOutput && (
                      <details className="mt-2">
                        <summary className="cursor-pointer text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 font-sans">
                          Raw Output
                        </summary>
                        <pre className="mt-1 p-2 bg-gray-100 dark:bg-gray-800 rounded overflow-x-auto max-h-48 overflow-y-auto text-gray-600 dark:text-gray-300 whitespace-pre-wrap">
                          {agentExecutionTrace.rawOutput}
                        </pre>
                      </details>
                    )}

                    {/* Fallback when no trace data */}
                    {!agentExecutionTrace.steps &&
                      !agentExecutionTrace.tokens &&
                      !agentExecutionTrace.rawOutput && (
                        <p className="text-gray-400 italic font-sans">
                          Processing... trace data will appear here.
                        </p>
                      )}
                  </div>
                )}

                {/* Placeholder when trace toggle is on but no data */}
                {showAgentExecutionTrace && !agentExecutionTrace && (
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
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
                <RefreshCw size={16} className="animate-spin" />
                <span>Processing...</span>
              </div>
              {/* Agent trace toggle button (graph icon) */}
              <button
                onClick={() =>
                  setShowAgentExecutionTrace(!showAgentExecutionTrace)
                }
                className={`p-1.5 rounded transition-colors ${
                  showAgentExecutionTrace
                    ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
                    : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
                }`}
                aria-expanded={showAgentExecutionTrace}
                aria-label="Toggle agent execution trace"
                title={
                  showAgentExecutionTrace
                    ? "Hide execution trace"
                    : "Show execution trace"
                }
              >
                <GitBranch size={14} />
              </button>
            </div>
            {showAgentExecutionTrace && (
              <div className="mt-2 p-3 bg-gray-50 dark:bg-gray-900 rounded border border-gray-200 dark:border-gray-700 text-xs text-gray-400 italic">
                Waiting for trace data...
              </div>
            )}
          </div>
        </div>
      )}

      {/* AI Follow-Up Suggestions - show after all messages when not streaming */}
      {!isStreaming && !isSending && onSuggestionSelect && (
        <div className="flex justify-start">
          <div className="max-w-[70%]">
            <AIFollowUpSuggestions
              suggestions={suggestions}
              onSelect={onSuggestionSelect}
              onFeedback={onSuggestionFeedback}
              isLoading={suggestionsLoading}
              compact={true}
            />
          </div>
        </div>
      )}

      <div ref={messagesEndRef} data-testid="messages-end" />
    </div>
  );
}

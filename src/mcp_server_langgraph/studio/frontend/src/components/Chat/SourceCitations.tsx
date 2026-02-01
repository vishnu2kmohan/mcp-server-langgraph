/**
 * SourceCitations Component
 *
 * Reusable component for displaying source citations from web search
 * results and knowledge base references. Extracted from MessageList
 * for reuse across the application.
 *
 * ## Features
 * - Accessible link navigation with ARIA labels
 * - Truncation for long titles via CSS
 * - Tooltip with snippet preview
 * - Overflow indicator for many sources (`+N more`)
 * - Graceful handling of malformed URLs
 * - Support for relevance_score (sorting should be done externally)
 *
 * ## Usage
 *
 * ### Basic usage with web search results
 * ```tsx
 * import { SourceCitations } from "@/components/Chat";
 *
 * <SourceCitations
 *   sources={[
 *     { title: "Python Docs", url: "https://python.org", snippet: "..." },
 *     { title: "Real Python", url: "https://realpython.com" }
 *   ]}
 * />
 * ```
 *
 * ### With maxVisible limit
 * ```tsx
 * <SourceCitations sources={sources} maxVisible={3} />
 * ```
 *
 * ### With custom styling
 * ```tsx
 * <SourceCitations sources={sources} className="border-primary-6" />
 * ```
 *
 * ### In MessageList context (with deduplication)
 * ```tsx
 * import { dedupeByDomain } from "@/conversation/sourceUtils";
 *
 * const displaySources = message.sources ? dedupeByDomain(message.sources) : [];
 * <SourceCitations sources={displaySources} />
 * ```
 *
 * @see {@link SourceCitation} for the source citation type
 * @see {@link dedupeByDomain} for source deduplication utility
 * @see {@link sortByRelevance} for sorting by relevance score
 */
import { FileText, ExternalLink, BookOpen } from "lucide-react";
import type { SourceCitation } from "../../types/session";
import {
  extractDomain,
  truncateSnippet,
  getSourceAriaLabel,
  isKBSource,
  groupSourcesByType,
} from "../../conversation/sourceUtils";
import { cn } from "../../utils/cn";

// =============================================================================
// Types
// =============================================================================

/**
 * Props for the SourceCitations component.
 */
export interface SourceCitationsProps {
  /**
   * Array of source citations to display.
   * Sources should be pre-processed (deduplicated, sorted) before passing.
   *
   * @example
   * ```ts
   * const sources: SourceCitation[] = [
   *   { title: "Python Docs", url: "https://python.org", snippet: "Official docs" },
   *   { title: "Tutorial", url: "https://example.com", relevance_score: 0.95 }
   * ];
   * ```
   */
  sources: SourceCitation[];

  /**
   * Maximum number of sources to display before showing "+N more" indicator.
   * @default 5
   */
  maxVisible?: number;

  /**
   * Additional CSS classes to apply to the container.
   * Useful for customizing border color, padding, or margins.
   */
  className?: string;

  /**
   * Group sources by type (web vs knowledge base).
   * When enabled, shows separate sections for web and KB sources.
   * @default false
   */
  groupByType?: boolean;
}

// =============================================================================
// Component
// =============================================================================

/**
 * Displays a list of source citations as accessible, clickable pill links.
 *
 * The component renders nothing if the sources array is empty or undefined,
 * making it safe to use conditionally without additional checks.
 *
 * @param props - Component props
 * @returns JSX element or null if no sources
 *
 * @example Basic usage
 * ```tsx
 * <SourceCitations
 *   sources={[
 *     { title: "Python Docs", url: "https://python.org", snippet: "..." }
 *   ]}
 * />
 * ```
 *
 * @example With deduplication (recommended for web search results)
 * ```tsx
 * import { dedupeByDomain } from "@/conversation/sourceUtils";
 *
 * const dedupedSources = dedupeByDomain(message.sources ?? []);
 * <SourceCitations sources={dedupedSources} maxVisible={5} />
 * ```
 *
 * @example Sorting by relevance before display
 * ```tsx
 * const sortedSources = [...sources].sort(
 *   (a, b) => (b.relevance_score ?? 0) - (a.relevance_score ?? 0)
 * );
 * <SourceCitations sources={sortedSources} />
 * ```
 */
export function SourceCitations({
  sources,
  maxVisible = 5,
  className,
  groupByType = false,
}: SourceCitationsProps) {
  // Return null for empty or undefined sources
  if (!sources || sources.length === 0) {
    return null;
  }

  // Render a single source link with appropriate icon
  const renderSourceLink = (source: SourceCitation, index: number) => {
    const isKB = isKBSource(source);

    // Safe rendering - handle malformed URLs gracefully
    let displayTitle: string;
    try {
      displayTitle = source.title?.trim()
        ? source.title
        : extractDomain(source.url);
    } catch {
      displayTitle = source.title || source.url;
    }

    // Tooltip content: snippet if available, otherwise title
    const tooltipContent = source.snippet
      ? (truncateSnippet(source.snippet) ?? source.title)
      : source.title;

    return (
      <a
        key={`source-${index}-${source.url}`}
        href={source.url}
        target="_blank"
        rel="noopener noreferrer"
        className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs bg-neutral-3 hover:bg-neutral-4 text-neutral-11 rounded-full transition-colors group focus:outline-none focus:ring-2 focus:ring-primary-6 focus:ring-offset-1"
        title={tooltipContent}
        aria-label={getSourceAriaLabel(source)}
      >
        <span className="truncate max-w-[150px]">{displayTitle}</span>
        {isKB ? (
          <BookOpen
            size={10}
            className="flex-shrink-0 opacity-50 group-hover:opacity-100"
            aria-hidden="true"
            data-testid="kb-icon"
          />
        ) : (
          <ExternalLink
            size={10}
            className="flex-shrink-0 opacity-50 group-hover:opacity-100"
            aria-hidden="true"
            data-testid="web-icon"
          />
        )}
      </a>
    );
  };

  // Grouped rendering
  if (groupByType) {
    const { web, kb } = groupSourcesByType(sources);

    return (
      <div
        data-testid="sources-section"
        className={cn("mt-3 pt-3 border-t border-neutral-6/50", className)}
      >
        {/* Header with total count */}
        <div className="flex items-center gap-1.5 text-xs text-neutral-10 mb-2">
          <FileText size={12} />
          <span>Sources ({sources.length})</span>
        </div>

        {/* Web sources group */}
        {web.length > 0 && (
          <div data-testid="web-sources-group" className="mb-3">
            <div className="text-xs text-neutral-9 mb-1.5 flex items-center gap-1">
              <ExternalLink size={10} />
              <span>Web ({web.length})</span>
            </div>
            <nav className="flex flex-wrap gap-2" aria-label="Web sources">
              {web
                .slice(0, maxVisible)
                .map((source, index) => renderSourceLink(source, index))}
              {web.length > maxVisible && (
                <span className="text-xs text-neutral-10 px-2 py-1">
                  +{web.length - maxVisible} more
                </span>
              )}
            </nav>
          </div>
        )}

        {/* KB sources group */}
        {kb.length > 0 && (
          <div data-testid="kb-sources-group">
            <div className="text-xs text-neutral-9 mb-1.5 flex items-center gap-1">
              <BookOpen size={10} />
              <span>Knowledge Base ({kb.length})</span>
            </div>
            <nav
              className="flex flex-wrap gap-2"
              aria-label="Knowledge base sources"
            >
              {kb
                .slice(0, maxVisible)
                .map((source, index) => renderSourceLink(source, index))}
              {kb.length > maxVisible && (
                <span className="text-xs text-neutral-10 px-2 py-1">
                  +{kb.length - maxVisible} more
                </span>
              )}
            </nav>
          </div>
        )}
      </div>
    );
  }

  // Default flat rendering
  const displaySources = sources.slice(0, maxVisible);
  const hasMore = sources.length > maxVisible;
  const overflowCount = sources.length - maxVisible;

  return (
    <div
      data-testid="sources-section"
      className={cn("mt-3 pt-3 border-t border-neutral-6/50", className)}
    >
      {/* Header with count */}
      <div className="flex items-center gap-1.5 text-xs text-neutral-10 mb-2">
        <FileText size={12} />
        <span>Sources ({sources.length})</span>
      </div>

      {/* Source links navigation */}
      <nav className="flex flex-wrap gap-2" aria-label="Source citations">
        {displaySources.map((source, index) => renderSourceLink(source, index))}

        {/* Overflow indicator */}
        {hasMore && (
          <span className="text-xs text-neutral-10 px-2 py-1">
            +{overflowCount} more
          </span>
        )}
      </nav>
    </div>
  );
}

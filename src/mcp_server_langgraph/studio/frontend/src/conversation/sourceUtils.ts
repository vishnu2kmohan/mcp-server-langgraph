/**
 * Source Citation Utilities
 *
 * Utility functions for processing source citations in the message list.
 * Extracted for testability and reuse across components.
 */

import type { SourceCitation } from "../types/session";

/**
 * Extract domain from URL for display.
 * Removes 'www.' prefix for cleaner display.
 *
 * @param url - The URL to extract domain from
 * @returns The domain or original string if parsing fails
 */
export function extractDomain(url: string): string {
  try {
    const parsed = new URL(url);
    return parsed.hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

/**
 * Truncate snippet to max length with ellipsis.
 *
 * @param snippet - The snippet text to truncate
 * @param maxLength - Maximum length before truncation (default: 120)
 * @returns Truncated snippet with "..." or null if no snippet
 */
export function truncateSnippet(
  snippet: string | null | undefined,
  maxLength = 120,
): string | null {
  if (!snippet) return null;
  if (snippet.length <= maxLength) return snippet;
  return snippet.slice(0, maxLength) + "...";
}

/**
 * Deduplicate sources by domain, keeping first occurrence.
 * Useful for cleaner display when multiple results from same domain.
 *
 * @param sources - Array of sources with url property
 * @returns Deduplicated array with one source per domain
 */
export function dedupeByDomain<T extends { url: string }>(sources: T[]): T[] {
  const seen = new Set<string>();
  return sources.filter((source) => {
    const domain = extractDomain(source.url);
    if (seen.has(domain)) return false;
    seen.add(domain);
    return true;
  });
}

/**
 * Safe source rendering - handles malformed URLs gracefully.
 *
 * @param source - Source citation to get display title for
 * @returns Display title (source title or extracted domain)
 */
export function getSourceDisplayTitle(source: SourceCitation): string {
  if (source.title && source.title.trim()) {
    return source.title;
  }
  return extractDomain(source.url);
}

/**
 * Get accessible label for source link.
 *
 * @param source - Source citation
 * @returns Accessible label for screen readers
 */
export function getSourceAriaLabel(source: SourceCitation): string {
  const title = getSourceDisplayTitle(source);
  return `Source: ${title} (opens in new tab)`;
}

/**
 * Sort sources by relevance score in descending order.
 * Sources without a relevance_score are placed at the end.
 * Does not mutate the original array.
 *
 * @param sources - Array of source citations
 * @returns New array sorted by relevance_score descending
 *
 * @example
 * ```ts
 * const sorted = sortByRelevance([
 *   { title: "Low", url: "...", relevance_score: 0.3 },
 *   { title: "High", url: "...", relevance_score: 0.9 },
 * ]);
 * // sorted[0].title === "High"
 * ```
 */
export function sortByRelevance(sources: SourceCitation[]): SourceCitation[] {
  return [...sources].sort((a, b) => {
    const scoreA = a.relevance_score ?? 0;
    const scoreB = b.relevance_score ?? 0;
    return scoreB - scoreA;
  });
}

/**
 * Check if a source is from the knowledge base (KB).
 * KB sources have URLs starting with `/kb/` or `kb://`.
 *
 * @param source - Source citation to check
 * @returns True if the source is from the knowledge base
 *
 * @example
 * ```ts
 * isKBSource({ title: "API Guide", url: "/kb/docs/api.md" }); // true
 * isKBSource({ title: "Python", url: "https://python.org" }); // false
 * ```
 */
export function isKBSource(source: SourceCitation): boolean {
  if (!source.url) return false;
  return source.url.startsWith("/kb/") || source.url.startsWith("kb://");
}

/**
 * Group sources by type (web vs knowledge base).
 * Preserves order within each group.
 *
 * @param sources - Array of source citations
 * @returns Object with `web` and `kb` arrays
 *
 * @example
 * ```ts
 * const { web, kb } = groupSourcesByType(sources);
 * // web contains external web sources
 * // kb contains knowledge base sources
 * ```
 */
export function groupSourcesByType(sources: SourceCitation[]): {
  web: SourceCitation[];
  kb: SourceCitation[];
} {
  const web: SourceCitation[] = [];
  const kb: SourceCitation[] = [];

  for (const source of sources) {
    if (isKBSource(source)) {
      kb.push(source);
    } else {
      web.push(source);
    }
  }

  return { web, kb };
}

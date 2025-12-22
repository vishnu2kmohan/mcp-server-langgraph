/**
 * useUrlContentFetch Hook
 *
 * Detects "#<url>" patterns in input and fetches URL content for
 * inclusion in chat context (OpenWebUI-style URL integration).
 *
 * Usage:
 *   const { detectUrls, fetchUrl, fetchedContent, isLoading, getContextString } = useUrlContentFetch();
 *
 *   // In input handler:
 *   detectUrls(inputValue);
 *
 *   // To fetch detected URLs:
 *   for (const detected of detectedUrls) {
 *     await fetchUrl(detected.url);
 *   }
 *
 *   // Get context for LLM:
 *   const urlContext = getContextString();
 *
 * Auto-fetch mode:
 *   const { detectUrls } = useUrlContentFetch({ autoFetch: true, debounceMs: 300 });
 *   // URLs are automatically fetched when detected
 */

import { useState, useCallback, useRef, useEffect } from "react";

// =============================================================================
// Types
// =============================================================================

export interface DetectedUrl {
  /** The raw matched string (e.g., "#https://example.com") */
  raw: string;
  /** The extracted URL */
  url: string;
}

export interface FetchedContent {
  /** The URL that was fetched */
  url: string;
  /** Page title if available */
  title?: string;
  /** Extracted text content */
  content?: string;
  /** Content type (text/html, application/json, etc.) */
  contentType?: string;
  /** Error message if fetch failed */
  error?: string;
}

export interface UseUrlContentFetchOptions {
  /** Whether to automatically fetch URLs when detected */
  autoFetch?: boolean;
  /** Debounce delay in milliseconds for auto-fetch (default: 0) */
  debounceMs?: number;
}

export interface UseUrlContentFetchResult {
  /** List of detected URLs from input */
  detectedUrls: DetectedUrl[];
  /** Detect URLs in input string */
  detectUrls: (input: string) => void;
  /** Fetch content from a URL */
  fetchUrl: (url: string) => Promise<void>;
  /** List of fetched URL content */
  fetchedContent: FetchedContent[];
  /** Whether any fetch is in progress */
  isLoading: boolean;
  /** URLs currently being fetched */
  loadingUrls: string[];
  /** Clear all fetched content */
  clearContent: () => void;
  /** Clear specific URL content */
  clearUrl: (url: string) => void;
  /** Get formatted context string for LLM */
  getContextString: () => string;
}

// =============================================================================
// URL Pattern
// =============================================================================

/**
 * Regex pattern to match "#<url>" at start of string or after whitespace
 * Captures URLs starting with http:// or https://
 */
const URL_PATTERN = /(?:^|\s)#(https?:\/\/[^\s]+)/g;

// =============================================================================
// Hook Implementation
// =============================================================================

export function useUrlContentFetch(
  options: UseUrlContentFetchOptions = {},
): UseUrlContentFetchResult {
  const { autoFetch = false, debounceMs = 0 } = options;

  const [detectedUrls, setDetectedUrls] = useState<DetectedUrl[]>([]);
  const [fetchedContent, setFetchedContent] = useState<FetchedContent[]>([]);
  const [loadingUrls, setLoadingUrls] = useState<string[]>([]);

  // Track already fetched URLs to avoid duplicate requests
  const fetchedUrlsRef = useRef<Set<string>>(new Set());
  // Track debounce timer
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  // Track pending URLs for debounced fetch
  const pendingUrlsRef = useRef<string[]>([]);

  /**
   * Detect URLs in input string matching the "#<url>" pattern
   */
  const detectUrls = useCallback((input: string) => {
    const matches: DetectedUrl[] = [];
    let match;

    // Reset lastIndex for global regex
    URL_PATTERN.lastIndex = 0;

    while ((match = URL_PATTERN.exec(input)) !== null) {
      const url = match[1];
      if (!url) continue;
      matches.push({
        raw: match[0].trim(),
        url,
      });
    }

    setDetectedUrls(matches);
  }, []);

  /**
   * Fetch content from a URL via the backend API
   */
  const fetchUrl = useCallback(async (url: string) => {
    // Skip if already fetched
    if (fetchedUrlsRef.current.has(url)) {
      return;
    }

    // Mark as fetched to prevent duplicate requests
    fetchedUrlsRef.current.add(url);

    // Add to loading state
    setLoadingUrls((prev) => [...prev, url]);

    try {
      const response = await fetch("/api/v1/ai/fetch-url", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(
          errorData.detail || `Failed to fetch URL: ${response.status}`,
        );
      }

      const data = await response.json();

      setFetchedContent((prev) => [
        ...prev,
        {
          url: data.url || url,
          title: data.title,
          content: data.content,
          contentType: data.content_type,
          error: undefined,
        },
      ]);
    } catch (error) {
      setFetchedContent((prev) => [
        ...prev,
        {
          url,
          error: error instanceof Error ? error.message : "Failed to fetch URL",
        },
      ]);
    } finally {
      // Remove from loading state
      setLoadingUrls((prev) => prev.filter((u) => u !== url));
    }
  }, []);

  /**
   * Clear all fetched content
   */
  const clearContent = useCallback(() => {
    setFetchedContent([]);
    fetchedUrlsRef.current.clear();
  }, []);

  /**
   * Clear content for a specific URL
   */
  const clearUrl = useCallback((url: string) => {
    setFetchedContent((prev) => prev.filter((c) => c.url !== url));
    fetchedUrlsRef.current.delete(url);
  }, []);

  /**
   * Generate a formatted context string from fetched content
   * for inclusion in LLM prompts
   */
  const getContextString = useCallback(() => {
    if (fetchedContent.length === 0) {
      return "";
    }

    const contextParts = fetchedContent
      .filter((c) => c.content && !c.error)
      .map((c) => {
        const titlePart = c.title ? `Title: ${c.title}\n` : "";
        return `--- URL: ${c.url} ---\n${titlePart}${c.content}\n--- End URL ---`;
      });

    if (contextParts.length === 0) {
      return "";
    }

    return `\n\n[Referenced URLs]\n${contextParts.join("\n\n")}`;
  }, [fetchedContent]);

  /**
   * Auto-fetch effect: automatically fetch detected URLs
   */
  useEffect(() => {
    if (!autoFetch || detectedUrls.length === 0) {
      return;
    }

    // Get URLs that haven't been fetched yet
    const newUrls = detectedUrls
      .map((d) => d.url)
      .filter((url) => !fetchedUrlsRef.current.has(url));

    if (newUrls.length === 0) {
      return;
    }

    // Store pending URLs
    pendingUrlsRef.current = newUrls;

    // Function to trigger fetches
    const triggerFetches = () => {
      const urlsToFetch = pendingUrlsRef.current;
      pendingUrlsRef.current = [];

      for (const url of urlsToFetch) {
        fetchUrl(url);
      }
    };

    // If debouncing, set up timer
    if (debounceMs > 0) {
      // Clear existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      debounceTimerRef.current = setTimeout(triggerFetches, debounceMs);
    } else {
      // Fetch immediately
      triggerFetches();
    }

    // Cleanup
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [autoFetch, debounceMs, detectedUrls, fetchUrl]);

  return {
    detectedUrls,
    detectUrls,
    fetchUrl,
    fetchedContent,
    isLoading: loadingUrls.length > 0,
    loadingUrls,
    clearContent,
    clearUrl,
    getContextString,
  };
}

export default useUrlContentFetch;

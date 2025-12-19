/**
 * useProjectContext Hook
 *
 * Hook to manage project context files (.studio/context.md).
 * Features:
 * - Auto-detect project context on load
 * - Load and parse context content
 * - Update context content
 * - Create new context file
 *
 * Based on GEMINI.md, AGENTS.md, CLAUDE.md patterns.
 */

import { useState, useEffect, useCallback } from "react";

// ==============================================================================
// Types
// ==============================================================================

export interface ProjectContextState {
  /** Whether context is currently loading */
  isLoading: boolean;
  /** Whether project has context file */
  hasContext: boolean;
  /** Context file content */
  content: string | null;
  /** Context file path */
  contextPath: string | null;
  /** Error message if any */
  error: string | null;
  /** Update context content */
  updateContent: (content: string) => Promise<void>;
  /** Create new context file */
  createContext: (content: string) => Promise<void>;
  /** Refresh context data */
  refresh: () => Promise<void>;
}

// ==============================================================================
// API Constants
// ==============================================================================

const API_BASE = "/api/v1/context";

// ==============================================================================
// Hook
// ==============================================================================

export function useProjectContext(): ProjectContextState {
  const [isLoading, setIsLoading] = useState(true);
  const [hasContext, setHasContext] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [contextPath, setContextPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Fetch context data from API
  const fetchContext = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(API_BASE);

      if (!response.ok) {
        throw new Error("Failed to fetch context");
      }

      const data = await response.json();

      setHasContext(data.exists);
      setContent(data.content || null);
      setContextPath(data.path || null);
    } catch {
      setError("Failed to load project context");
      setHasContext(false);
      setContent(null);
      setContextPath(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load context on mount
  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  // Update context content
  const updateContent = useCallback(async (newContent: string) => {
    try {
      await fetch(API_BASE, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content: newContent }),
      });
      setContent(newContent);
    } catch {
      throw new Error("Failed to update context");
    }
  }, []);

  // Create new context file
  const createContext = useCallback(async (initialContent: string) => {
    try {
      const response = await fetch(API_BASE, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ content: initialContent }),
      });

      const data = await response.json();

      setHasContext(true);
      setContent(initialContent);
      setContextPath(data.path);
    } catch {
      throw new Error("Failed to create context");
    }
  }, []);

  return {
    isLoading,
    hasContext,
    content,
    contextPath,
    error,
    updateContent,
    createContext,
    refresh: fetchContext,
  };
}

export default useProjectContext;

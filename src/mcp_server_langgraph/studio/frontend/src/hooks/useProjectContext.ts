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
import { useNavigate } from "react-router";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

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
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState(true);
  const [hasContext, setHasContext] = useState(false);
  const [content, setContent] = useState<string | null>(null);
  const [contextPath, setContextPath] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Handle auth failure - redirect to login
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Fetch context data from API
  const fetchContext = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await authenticatedFetch(API_BASE, {
        onAuthFailure: handleAuthFailure,
      });

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
  }, [handleAuthFailure]);

  // Load context on mount
  useEffect(() => {
    fetchContext();
  }, [fetchContext]);

  // Update context content
  const updateContent = useCallback(
    async (newContent: string) => {
      try {
        await authenticatedFetch(API_BASE, {
          method: "PUT",
          body: JSON.stringify({ content: newContent }),
          onAuthFailure: handleAuthFailure,
        });
        setContent(newContent);
      } catch {
        throw new Error("Failed to update context");
      }
    },
    [handleAuthFailure],
  );

  // Create new context file
  const createContext = useCallback(
    async (initialContent: string) => {
      try {
        const response = await authenticatedFetch(API_BASE, {
          method: "POST",
          body: JSON.stringify({ content: initialContent }),
          onAuthFailure: handleAuthFailure,
        });

        const data = await response.json();

        setHasContext(true);
        setContent(initialContent);
        setContextPath(data.path);
      } catch {
        throw new Error("Failed to create context");
      }
    },
    [handleAuthFailure],
  );

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

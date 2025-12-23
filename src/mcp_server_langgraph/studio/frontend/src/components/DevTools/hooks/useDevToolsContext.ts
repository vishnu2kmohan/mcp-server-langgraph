/**
 * useDevToolsContext Hook
 *
 * Detects the current DevTools context from the route.
 * Updates Redux state when context changes.
 *
 * Features:
 * - Detects session context from /studio/chat routes
 * - Detects workflow context from /studio/workflows routes
 * - Falls back to global context for other routes
 * - Extracts entity IDs from URL params or path segments
 * - Generates human-readable context labels
 */

import { useEffect, useMemo } from "react";
import { useLocation, useSearchParams } from "react-router";
import { useAppDispatch, useAppSelector } from "../../../store/hooks";
import {
  setDetectedContext,
  setContextEntityId,
  selectDetectedContext,
  selectContextEntityId,
  type DevToolsContext,
} from "../../../store/slices/devToolsSlice";

// =============================================================================
// Route Pattern Matching
// =============================================================================

interface RouteContextConfig {
  /** Pattern to match route */
  pattern: RegExp;
  /** Context type for this route */
  context: DevToolsContext;
  /** URL param for entity ID (e.g., "session", "workflow") */
  entityIdParam?: string;
  /** Regex group index for entity ID from path (if using path segment) */
  entityIdPathGroup?: number;
}

const ROUTE_CONTEXT_CONFIGS: RouteContextConfig[] = [
  // Session context: chat routes
  {
    pattern: /^\/studio(?:\/v2)?\/chat(?:\/([^/]+))?/,
    context: "session",
    entityIdParam: "session",
    entityIdPathGroup: 1, // Captures ID from /chat/:id
  },
  // Workflow context: workflow routes
  {
    pattern: /^\/studio(?:\/v2)?\/workflows(?:\/([^/]+))?/,
    context: "workflow",
    entityIdParam: "workflow",
    entityIdPathGroup: 1, // Captures ID from /workflows/:id
  },
  // Global context: all other studio routes (settings, observability, cost, etc.)
  {
    pattern: /^\/studio/,
    context: "global",
  },
];

// =============================================================================
// Hook Return Type
// =============================================================================

export interface UseDevToolsContextReturn {
  /** Current context type */
  context: DevToolsContext;
  /** Entity ID (session or workflow ID) */
  entityId: string | null;
  /** Human-readable context label (e.g., "Session: abc-123") */
  contextLabel: string;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Detect DevTools context from current route.
 * Updates Redux state when context or entity ID changes.
 */
export function useDevToolsContext(): UseDevToolsContextReturn {
  const dispatch = useAppDispatch();
  const location = useLocation();
  const [searchParams] = useSearchParams();

  // Get current state from Redux
  const currentContext = useAppSelector(selectDetectedContext);
  const currentEntityId = useAppSelector(selectContextEntityId);

  // Detect context and entity ID from route
  const { context, entityId } = useMemo(() => {
    const pathname = location.pathname;

    // Find matching route config
    for (const config of ROUTE_CONTEXT_CONFIGS) {
      const match = pathname.match(config.pattern);
      if (match) {
        // Extract entity ID
        let extractedEntityId: string | null = null;

        // Try URL param first
        if (config.entityIdParam) {
          extractedEntityId = searchParams.get(config.entityIdParam);
        }

        // Fall back to path segment if no param
        if (!extractedEntityId && config.entityIdPathGroup !== undefined) {
          extractedEntityId = match[config.entityIdPathGroup] ?? null;
        }

        return {
          context: config.context,
          entityId: extractedEntityId,
        };
      }
    }

    // Default to global
    return { context: "global" as DevToolsContext, entityId: null };
  }, [location.pathname, searchParams]);

  // Update Redux state when context changes
  useEffect(() => {
    if (context !== currentContext) {
      dispatch(setDetectedContext(context));
    }
  }, [context, currentContext, dispatch]);

  // Update Redux state when entity ID changes
  useEffect(() => {
    if (entityId !== currentEntityId) {
      dispatch(setContextEntityId(entityId));
    }
  }, [entityId, currentEntityId, dispatch]);

  // Generate context label
  const contextLabel = useMemo(() => {
    if (context === "global") {
      return "Global";
    }

    const contextName = context === "session" ? "Session" : "Workflow";

    if (entityId) {
      return `${contextName}: ${entityId}`;
    }

    return contextName;
  }, [context, entityId]);

  return {
    context,
    entityId,
    contextLabel,
  };
}

export default useDevToolsContext;

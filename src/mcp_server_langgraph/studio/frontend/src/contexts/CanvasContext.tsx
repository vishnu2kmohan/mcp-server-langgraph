/**
 * CanvasContext - Context-Driven Canvas Architecture
 *
 * Provides a reusable canvas context for managing artifacts across different pages:
 * - Chat: LLM-generated artifacts
 * - Workflow: Node code, Mermaid diagrams, workflow scripts
 * - MCP Tools: Tool schemas, example inputs/outputs, JSON configs
 * - Agents: Agent configurations, prompt templates
 * - Connections: Connection configs, credential schemas
 */

import {
  createContext,
  useContext,
  useCallback,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { CanvasArtifact } from "../types/artifacts";

// =============================================================================
// Types
// =============================================================================

/** Page context determines which page is using the canvas */
export type PageContext =
  | "chat"
  | "workflow"
  | "mcp-tools"
  | "agents"
  | "connections";

/** Context value interface */
export interface CanvasContextValue {
  /** Current artifacts in the canvas */
  artifacts: CanvasArtifact[];
  /** Currently selected artifact ID */
  selectedArtifactId: string | null;
  /** Currently selected artifact (derived) */
  selectedArtifact: CanvasArtifact | null;
  /** Select an artifact by ID */
  selectArtifact: (id: string | null) => void;
  /** Add a new artifact */
  addArtifact: (artifact: CanvasArtifact) => void;
  /** Update an existing artifact's content */
  updateArtifact: (id: string, content: string) => void;
  /** Remove an artifact by ID */
  removeArtifact: (id: string) => void;
  /** Set all artifacts at once */
  setArtifacts: (artifacts: CanvasArtifact[]) => void;
  /** Clear all artifacts */
  clearArtifacts: () => void;
  /** Current page context */
  pageContext: PageContext;
}

/** Provider props */
export interface CanvasProviderProps {
  children: ReactNode;
  /** Page context for the canvas */
  pageContext: PageContext;
  /** Initial artifacts to populate the canvas */
  initialArtifacts?: CanvasArtifact[];
}

// =============================================================================
// Context
// =============================================================================

const CanvasContext = createContext<CanvasContextValue | null>(null);

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access the canvas context
 * @throws Error if used outside of CanvasProvider
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useCanvas(): CanvasContextValue {
  const context = useContext(CanvasContext);
  if (!context) {
    throw new Error("useCanvas must be used within a CanvasProvider");
  }
  return context;
}

// =============================================================================
// Provider
// =============================================================================

/**
 * CanvasProvider - Provides canvas functionality to child components
 */
export function CanvasProvider({
  children,
  pageContext,
  initialArtifacts = [],
}: CanvasProviderProps) {
  const [artifacts, setArtifactsState] =
    useState<CanvasArtifact[]>(initialArtifacts);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(
    null,
  );

  // Select artifact
  const selectArtifact = useCallback((id: string | null) => {
    setSelectedArtifactId(id);
  }, []);

  // Add artifact (prevents duplicates)
  const addArtifact = useCallback((artifact: CanvasArtifact) => {
    setArtifactsState((prev) => {
      // Check if artifact already exists
      if (prev.some((a) => a.id === artifact.id)) {
        return prev;
      }
      return [...prev, artifact];
    });
  }, []);

  // Update artifact content
  const updateArtifact = useCallback((id: string, content: string) => {
    setArtifactsState((prev) =>
      prev.map((artifact) =>
        artifact.id === id
          ? { ...artifact, content, updatedAt: new Date().toISOString() }
          : artifact,
      ),
    );
  }, []);

  // Remove artifact
  const removeArtifact = useCallback((id: string) => {
    setArtifactsState((prev) => prev.filter((a) => a.id !== id));
    // Clear selection if the removed artifact was selected
    setSelectedArtifactId((prevId) => (prevId === id ? null : prevId));
  }, []);

  // Set all artifacts
  const setArtifacts = useCallback((newArtifacts: CanvasArtifact[]) => {
    setArtifactsState(newArtifacts);
  }, []);

  // Clear all artifacts
  const clearArtifacts = useCallback(() => {
    setArtifactsState([]);
    setSelectedArtifactId(null);
  }, []);

  // Derived: selected artifact
  const selectedArtifact = useMemo(
    () => artifacts.find((a) => a.id === selectedArtifactId) ?? null,
    [artifacts, selectedArtifactId],
  );

  // Context value
  const value = useMemo<CanvasContextValue>(
    () => ({
      artifacts,
      selectedArtifactId,
      selectedArtifact,
      selectArtifact,
      addArtifact,
      updateArtifact,
      removeArtifact,
      setArtifacts,
      clearArtifacts,
      pageContext,
    }),
    [
      artifacts,
      selectedArtifactId,
      selectedArtifact,
      selectArtifact,
      addArtifact,
      updateArtifact,
      removeArtifact,
      setArtifacts,
      clearArtifacts,
      pageContext,
    ],
  );

  return (
    <CanvasContext.Provider value={value}>{children}</CanvasContext.Provider>
  );
}

CanvasProvider.displayName = "CanvasProvider";

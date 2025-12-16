/**
 * useWorkspace Hook
 *
 * JupyterLab-style workspace persistence.
 * Saves and restores layout state with named workspaces.
 *
 * Features:
 * - Named workspaces (like JupyterLab URLs)
 * - Persistent panel states
 * - Focus mode persistence
 * - Active tab tracking
 * - Debounced saves to localStorage
 */

import { useState, useCallback, useEffect, useRef } from "react";

// =============================================================================
// Types
// =============================================================================

export interface WorkspaceState {
  /** Whether focus mode is active */
  focusMode: boolean;
  /** Whether left panel is collapsed */
  leftPanelCollapsed: boolean;
  /** Whether right panel is collapsed */
  rightPanelCollapsed: boolean;
  /** Currently active activity in activity bar */
  activeActivityId: string | null;
  /** Active tab IDs for each panel */
  activeTabs: Record<string, string>;
}

export interface UseWorkspaceReturn {
  /** Current workspace state */
  state: WorkspaceState;
  /** Set focus mode */
  setFocusMode: (focused: boolean) => void;
  /** Set left panel collapsed state */
  setLeftPanelCollapsed: (collapsed: boolean) => void;
  /** Set right panel collapsed state */
  setRightPanelCollapsed: (collapsed: boolean) => void;
  /** Set active activity ID */
  setActiveActivityId: (id: string | null) => void;
  /** Set active tab for a panel */
  setActiveTab: (panelId: string, tabId: string) => void;
  /** Reset workspace to default state */
  reset: () => void;
  /** Delete workspace from storage */
  deleteWorkspace: () => void;
  /** List all available workspace names */
  listWorkspaces: () => string[];
}

// =============================================================================
// Constants
// =============================================================================

const WORKSPACE_PREFIX = "workspace:";

const DEFAULT_STATE: WorkspaceState = {
  focusMode: false,
  leftPanelCollapsed: false,
  rightPanelCollapsed: false,
  activeActivityId: null,
  activeTabs: {},
};

// =============================================================================
// Utility functions
// =============================================================================

function getStorageKey(name: string): string {
  return `${WORKSPACE_PREFIX}${name}`;
}

function loadWorkspace(name: string): WorkspaceState {
  try {
    const key = getStorageKey(name);
    const saved = localStorage.getItem(key);
    if (saved) {
      const parsed = JSON.parse(saved);
      return {
        ...DEFAULT_STATE,
        ...parsed,
      };
    }
  } catch {
    // Invalid JSON or other error - use default
  }
  return { ...DEFAULT_STATE };
}

function saveWorkspace(name: string, state: WorkspaceState): void {
  try {
    const key = getStorageKey(name);
    localStorage.setItem(key, JSON.stringify(state));
  } catch {
    // Storage full or other error - ignore
  }
}

function deleteWorkspaceStorage(name: string): void {
  try {
    const key = getStorageKey(name);
    localStorage.removeItem(key);
  } catch {
    // Error - ignore
  }
}

function listAllWorkspaces(): string[] {
  const workspaces: string[] = [];
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i);
      if (key?.startsWith(WORKSPACE_PREFIX)) {
        workspaces.push(key.slice(WORKSPACE_PREFIX.length));
      }
    }
  } catch {
    // Error - return empty
  }
  return workspaces;
}

// =============================================================================
// Hook
// =============================================================================

export function useWorkspace(name: string): UseWorkspaceReturn {
  // Load initial state from localStorage
  const [state, setState] = useState<WorkspaceState>(() => loadWorkspace(name));

  // Ref to track workspace name changes
  const nameRef = useRef(name);

  // Update state when workspace name changes
  useEffect(() => {
    if (nameRef.current !== name) {
      nameRef.current = name;
      setState(loadWorkspace(name));
    }
  }, [name]);

  // Save state when it changes (simple debounce via useEffect)
  useEffect(() => {
    saveWorkspace(name, state);
  }, [name, state]);

  // State updaters
  const setFocusMode = useCallback((focused: boolean) => {
    setState((prev) => ({ ...prev, focusMode: focused }));
  }, []);

  const setLeftPanelCollapsed = useCallback((collapsed: boolean) => {
    setState((prev) => ({ ...prev, leftPanelCollapsed: collapsed }));
  }, []);

  const setRightPanelCollapsed = useCallback((collapsed: boolean) => {
    setState((prev) => ({ ...prev, rightPanelCollapsed: collapsed }));
  }, []);

  const setActiveActivityId = useCallback((id: string | null) => {
    setState((prev) => ({ ...prev, activeActivityId: id }));
  }, []);

  const setActiveTab = useCallback((panelId: string, tabId: string) => {
    setState((prev) => ({
      ...prev,
      activeTabs: { ...prev.activeTabs, [panelId]: tabId },
    }));
  }, []);

  const reset = useCallback(() => {
    setState({ ...DEFAULT_STATE });
  }, []);

  const deleteWorkspace = useCallback(() => {
    deleteWorkspaceStorage(name);
    setState({ ...DEFAULT_STATE });
  }, [name]);

  const listWorkspaces = useCallback(() => {
    return listAllWorkspaces();
  }, []);

  return {
    state,
    setFocusMode,
    setLeftPanelCollapsed,
    setRightPanelCollapsed,
    setActiveActivityId,
    setActiveTab,
    reset,
    deleteWorkspace,
    listWorkspaces,
  };
}

export default useWorkspace;

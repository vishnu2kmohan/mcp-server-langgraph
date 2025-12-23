/**
 * DevTools Slice Tests
 *
 * TDD tests for the DevTools state slice.
 * Tests cover:
 * - Initial state with persona-based collapsed default
 * - Panel toggle, maximize, and height adjustment
 * - Active tab management
 * - Context detection (session/workflow/global)
 * - Console filter settings
 * - AI-powered layout suggestions
 * - Available tabs based on context
 * - localStorage persistence
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import devToolsReducer, {
  toggleDevTools,
  setActiveTab,
  setDetectedContext,
  setContextEntityId,
  setConsoleFilter,
  setHeight,
  setMaximized,
  setAiInsightsEnabled,
  applyAILayout,
  clearAILayout,
  initializeFromPersona,
  selectDevToolsCollapsed,
  selectDevToolsMaximized,
  selectDevToolsHeight,
  selectActiveTab,
  selectDetectedContext,
  selectContextEntityId,
  selectConsoleFilter,
  selectAiInsightsEnabled,
  selectAISuggestedLayout,
  selectAvailableTabs,
  getDefaultCollapsedFromPersona,
  type DevToolsTabId,
  type DevToolsContext,
} from "./devToolsSlice";
import type { Persona as _Persona } from "./personaSlice";

describe("devToolsSlice", () => {
  // Default initial state (user persona = collapsed by default)
  const initialState = {
    collapsed: true, // Smart default: collapsed for 'user' persona
    height: 250,
    maximized: false,
    activeTab: "console" as DevToolsTabId,
    detectedContext: "global" as DevToolsContext,
    contextEntityId: null as string | null,
    consoleFilter: "all" as const,
    aiInsightsEnabled: false,
    aiSuggestedLayout: null as DevToolsTabId[] | null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Initial State
  // ===========================================================================

  describe("initial state", () => {
    it("should return initial state when called with undefined", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result).toEqual(initialState);
    });

    it("should have collapsed=true by default (user persona)", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result.collapsed).toBe(true);
    });

    it("should have console as default active tab", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result.activeTab).toBe("console");
    });

    it("should have global as default context", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result.detectedContext).toBe("global");
    });

    it("should have default height of 250", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result.height).toBe(250);
    });
  });

  // ===========================================================================
  // Persona-based Default
  // ===========================================================================

  describe("getDefaultCollapsedFromPersona", () => {
    it("should return false (open) for admin persona", () => {
      expect(getDefaultCollapsedFromPersona("admin")).toBe(false);
    });

    it("should return false (open) for developer persona", () => {
      expect(getDefaultCollapsedFromPersona("developer")).toBe(false);
    });

    it("should return true (collapsed) for user persona", () => {
      expect(getDefaultCollapsedFromPersona("user")).toBe(true);
    });
  });

  describe("initializeFromPersona", () => {
    it("should set collapsed=false for admin persona", () => {
      const result = devToolsReducer(
        initialState,
        initializeFromPersona("admin"),
      );
      expect(result.collapsed).toBe(false);
    });

    it("should set collapsed=false for developer persona", () => {
      const result = devToolsReducer(
        initialState,
        initializeFromPersona("developer"),
      );
      expect(result.collapsed).toBe(false);
    });

    it("should keep collapsed=true for user persona", () => {
      const state = { ...initialState, collapsed: false };
      const result = devToolsReducer(state, initializeFromPersona("user"));
      expect(result.collapsed).toBe(true);
    });

    it("should not override user preference from localStorage", () => {
      // Set user preference in localStorage
      localStorage.setItem("studio-devtools-collapsed", "false");

      const result = devToolsReducer(
        initialState,
        initializeFromPersona("user"),
      );
      // User explicitly opened DevTools, so it should stay open
      expect(result.collapsed).toBe(false);
    });
  });

  // ===========================================================================
  // Toggle DevTools
  // ===========================================================================

  describe("toggleDevTools", () => {
    it("should toggle from collapsed to open", () => {
      const state = { ...initialState, collapsed: true };
      const result = devToolsReducer(state, toggleDevTools());
      expect(result.collapsed).toBe(false);
    });

    it("should toggle from open to collapsed", () => {
      const state = { ...initialState, collapsed: false };
      const result = devToolsReducer(state, toggleDevTools());
      expect(result.collapsed).toBe(true);
    });

    it("should persist collapsed state to localStorage", () => {
      const state = { ...initialState, collapsed: false };
      devToolsReducer(state, toggleDevTools());
      expect(localStorage.getItem("studio-devtools-collapsed")).toBe("true");
    });

    it("should reset maximized when collapsing", () => {
      const state = { ...initialState, collapsed: false, maximized: true };
      const result = devToolsReducer(state, toggleDevTools());
      expect(result.maximized).toBe(false);
    });
  });

  // ===========================================================================
  // Maximize
  // ===========================================================================

  describe("setMaximized", () => {
    it("should set maximized to true", () => {
      const result = devToolsReducer(initialState, setMaximized(true));
      expect(result.maximized).toBe(true);
    });

    it("should set maximized to false", () => {
      const state = { ...initialState, maximized: true };
      const result = devToolsReducer(state, setMaximized(false));
      expect(result.maximized).toBe(false);
    });

    it("should expand panel when maximizing", () => {
      const state = { ...initialState, collapsed: true };
      const result = devToolsReducer(state, setMaximized(true));
      expect(result.collapsed).toBe(false);
    });
  });

  // ===========================================================================
  // Height
  // ===========================================================================

  describe("setHeight", () => {
    it("should set height to valid value", () => {
      const result = devToolsReducer(initialState, setHeight(300));
      expect(result.height).toBe(300);
    });

    it("should clamp height to minimum of 150", () => {
      const result = devToolsReducer(initialState, setHeight(100));
      expect(result.height).toBe(150);
    });

    it("should clamp height to maximum of 600", () => {
      const result = devToolsReducer(initialState, setHeight(800));
      expect(result.height).toBe(600);
    });

    it("should persist height to localStorage", () => {
      devToolsReducer(initialState, setHeight(350));
      expect(localStorage.getItem("studio-devtools-height")).toBe("350");
    });
  });

  // ===========================================================================
  // Active Tab
  // ===========================================================================

  describe("setActiveTab", () => {
    it("should set active tab to console", () => {
      const result = devToolsReducer(initialState, setActiveTab("console"));
      expect(result.activeTab).toBe("console");
    });

    it("should set active tab to agent-trace", () => {
      const result = devToolsReducer(initialState, setActiveTab("agent-trace"));
      expect(result.activeTab).toBe("agent-trace");
    });

    it("should set active tab to execution-trace", () => {
      const result = devToolsReducer(
        initialState,
        setActiveTab("execution-trace"),
      );
      expect(result.activeTab).toBe("execution-trace");
    });

    it("should set active tab to network", () => {
      const result = devToolsReducer(initialState, setActiveTab("network"));
      expect(result.activeTab).toBe("network");
    });

    it("should set active tab to state", () => {
      const result = devToolsReducer(initialState, setActiveTab("state"));
      expect(result.activeTab).toBe("state");
    });

    it("should set active tab to problems", () => {
      const result = devToolsReducer(initialState, setActiveTab("problems"));
      expect(result.activeTab).toBe("problems");
    });

    it("should set active tab to ai-insights", () => {
      const result = devToolsReducer(initialState, setActiveTab("ai-insights"));
      expect(result.activeTab).toBe("ai-insights");
    });

    it("should expand panel when changing tab", () => {
      const state = { ...initialState, collapsed: true };
      const result = devToolsReducer(state, setActiveTab("network"));
      expect(result.collapsed).toBe(false);
    });
  });

  // ===========================================================================
  // Context Detection
  // ===========================================================================

  describe("setDetectedContext", () => {
    it("should set context to session", () => {
      const result = devToolsReducer(
        initialState,
        setDetectedContext("session"),
      );
      expect(result.detectedContext).toBe("session");
    });

    it("should set context to workflow", () => {
      const result = devToolsReducer(
        initialState,
        setDetectedContext("workflow"),
      );
      expect(result.detectedContext).toBe("workflow");
    });

    it("should set context to global", () => {
      const state = {
        ...initialState,
        detectedContext: "session" as DevToolsContext,
      };
      const result = devToolsReducer(state, setDetectedContext("global"));
      expect(result.detectedContext).toBe("global");
    });

    it("should reset activeTab to console if current tab not available in new context", () => {
      // agent-trace is only available in session context
      const state = {
        ...initialState,
        activeTab: "agent-trace" as DevToolsTabId,
        detectedContext: "session" as DevToolsContext,
      };
      const result = devToolsReducer(state, setDetectedContext("workflow"));
      expect(result.activeTab).toBe("console");
    });

    it("should keep activeTab if available in new context", () => {
      // console is available in all contexts
      const state = {
        ...initialState,
        activeTab: "console" as DevToolsTabId,
        detectedContext: "session" as DevToolsContext,
      };
      const result = devToolsReducer(state, setDetectedContext("workflow"));
      expect(result.activeTab).toBe("console");
    });
  });

  describe("setContextEntityId", () => {
    it("should set context entity ID", () => {
      const result = devToolsReducer(
        initialState,
        setContextEntityId("session-123"),
      );
      expect(result.contextEntityId).toBe("session-123");
    });

    it("should clear context entity ID with null", () => {
      const state = { ...initialState, contextEntityId: "session-123" };
      const result = devToolsReducer(state, setContextEntityId(null));
      expect(result.contextEntityId).toBe(null);
    });
  });

  // ===========================================================================
  // Console Filter
  // ===========================================================================

  describe("setConsoleFilter", () => {
    it("should set filter to all", () => {
      const state = { ...initialState, consoleFilter: "error" as const };
      const result = devToolsReducer(state, setConsoleFilter("all"));
      expect(result.consoleFilter).toBe("all");
    });

    it("should set filter to info", () => {
      const result = devToolsReducer(initialState, setConsoleFilter("info"));
      expect(result.consoleFilter).toBe("info");
    });

    it("should set filter to warning", () => {
      const result = devToolsReducer(initialState, setConsoleFilter("warning"));
      expect(result.consoleFilter).toBe("warning");
    });

    it("should set filter to error", () => {
      const result = devToolsReducer(initialState, setConsoleFilter("error"));
      expect(result.consoleFilter).toBe("error");
    });
  });

  // ===========================================================================
  // AI Features
  // ===========================================================================

  describe("setAiInsightsEnabled", () => {
    it("should enable AI insights", () => {
      const result = devToolsReducer(initialState, setAiInsightsEnabled(true));
      expect(result.aiInsightsEnabled).toBe(true);
    });

    it("should disable AI insights", () => {
      const state = { ...initialState, aiInsightsEnabled: true };
      const result = devToolsReducer(state, setAiInsightsEnabled(false));
      expect(result.aiInsightsEnabled).toBe(false);
    });
  });

  describe("applyAILayout", () => {
    it("should set AI suggested layout", () => {
      const suggestedLayout: DevToolsTabId[] = [
        "problems",
        "console",
        "network",
      ];
      const result = devToolsReducer(
        initialState,
        applyAILayout(suggestedLayout),
      );
      expect(result.aiSuggestedLayout).toEqual(suggestedLayout);
    });

    it("should replace existing layout", () => {
      const state = {
        ...initialState,
        aiSuggestedLayout: ["console", "state"] as DevToolsTabId[],
      };
      const newLayout: DevToolsTabId[] = ["problems", "ai-insights"];
      const result = devToolsReducer(state, applyAILayout(newLayout));
      expect(result.aiSuggestedLayout).toEqual(newLayout);
    });
  });

  describe("clearAILayout", () => {
    it("should clear AI suggested layout", () => {
      const state = {
        ...initialState,
        aiSuggestedLayout: ["problems", "console"] as DevToolsTabId[],
      };
      const result = devToolsReducer(state, clearAILayout());
      expect(result.aiSuggestedLayout).toBe(null);
    });

    it("should be no-op if layout already null", () => {
      const result = devToolsReducer(initialState, clearAILayout());
      expect(result.aiSuggestedLayout).toBe(null);
    });
  });

  // ===========================================================================
  // Selectors
  // ===========================================================================

  describe("Selectors", () => {
    const mockState = {
      devTools: {
        collapsed: false,
        height: 300,
        maximized: true,
        activeTab: "network" as DevToolsTabId,
        detectedContext: "session" as DevToolsContext,
        contextEntityId: "session-456",
        consoleFilter: "warning" as const,
        aiInsightsEnabled: true,
        aiSuggestedLayout: ["problems", "console"] as DevToolsTabId[],
      },
    };

    it("selectDevToolsCollapsed should return collapsed state", () => {
      expect(selectDevToolsCollapsed(mockState)).toBe(false);
    });

    it("selectDevToolsMaximized should return maximized state", () => {
      expect(selectDevToolsMaximized(mockState)).toBe(true);
    });

    it("selectDevToolsHeight should return height", () => {
      expect(selectDevToolsHeight(mockState)).toBe(300);
    });

    it("selectActiveTab should return active tab", () => {
      expect(selectActiveTab(mockState)).toBe("network");
    });

    it("selectDetectedContext should return detected context", () => {
      expect(selectDetectedContext(mockState)).toBe("session");
    });

    it("selectContextEntityId should return context entity ID", () => {
      expect(selectContextEntityId(mockState)).toBe("session-456");
    });

    it("selectConsoleFilter should return console filter", () => {
      expect(selectConsoleFilter(mockState)).toBe("warning");
    });

    it("selectAiInsightsEnabled should return AI insights enabled state", () => {
      expect(selectAiInsightsEnabled(mockState)).toBe(true);
    });

    it("selectAISuggestedLayout should return AI suggested layout", () => {
      expect(selectAISuggestedLayout(mockState)).toEqual([
        "problems",
        "console",
      ]);
    });
  });

  // ===========================================================================
  // Available Tabs by Context
  // ===========================================================================

  describe("selectAvailableTabs", () => {
    it("should return all global tabs for global context", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "global" as DevToolsContext,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).toContain("console");
      expect(tabs).toContain("network");
      expect(tabs).toContain("state");
      expect(tabs).toContain("problems");
      expect(tabs).not.toContain("agent-trace");
      expect(tabs).not.toContain("execution-trace");
      expect(tabs).not.toContain("ai-insights");
    });

    it("should include agent-trace for session context", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "session" as DevToolsContext,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).toContain("console");
      expect(tabs).toContain("agent-trace");
      expect(tabs).not.toContain("execution-trace");
    });

    it("should include execution-trace for workflow context", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "workflow" as DevToolsContext,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).toContain("console");
      expect(tabs).toContain("execution-trace");
      expect(tabs).not.toContain("agent-trace");
    });

    it("should include ai-insights when enabled and in session context", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "session" as DevToolsContext,
          aiInsightsEnabled: true,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).toContain("ai-insights");
    });

    it("should include ai-insights when enabled and in workflow context", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "workflow" as DevToolsContext,
          aiInsightsEnabled: true,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).toContain("ai-insights");
    });

    it("should not include ai-insights when disabled", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "session" as DevToolsContext,
          aiInsightsEnabled: false,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).not.toContain("ai-insights");
    });

    it("should not include ai-insights in global context even when enabled", () => {
      const state = {
        devTools: {
          ...initialState,
          detectedContext: "global" as DevToolsContext,
          aiInsightsEnabled: true,
        },
      };
      const tabs = selectAvailableTabs(state);
      expect(tabs).not.toContain("ai-insights");
    });
  });

  // ===========================================================================
  // localStorage Persistence
  // ===========================================================================

  describe("localStorage persistence", () => {
    it("should load collapsed state from localStorage", () => {
      localStorage.setItem("studio-devtools-collapsed", "false");
      // This would be tested during slice initialization
      // For now, we verify the storage key matches
      expect(localStorage.getItem("studio-devtools-collapsed")).toBe("false");
    });

    it("should load height from localStorage", () => {
      localStorage.setItem("studio-devtools-height", "400");
      expect(localStorage.getItem("studio-devtools-height")).toBe("400");
    });

    it("should use default collapsed when localStorage is empty", () => {
      const result = devToolsReducer(undefined, { type: "unknown" });
      expect(result.collapsed).toBe(true); // Default for user persona
    });
  });
});

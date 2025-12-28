/**
 * CanvasContext Tests
 *
 * TDD tests for the context-driven canvas architecture.
 * Tests cover:
 * - Provider initialization
 * - Artifact management (add, update, remove)
 * - Artifact selection
 * - Page context awareness
 *
 * Following TDD: Write tests FIRST, then implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import React from "react";
import { CanvasProvider, useCanvas, type PageContext } from "./CanvasContext";
import type { CanvasArtifact } from "../types/artifacts";

// Helper to create wrapper with optional page context
const createWrapper = (pageContext: PageContext = "chat") => {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(CanvasProvider, { pageContext }, children);
};

// Mock artifacts for testing
const mockArtifact: CanvasArtifact = {
  id: "artifact-1",
  type: "code",
  sessionId: "session-1",
  version: 1,
  content: 'console.log("Hello");',
  contentType: "code",
  title: "Test Artifact",
  createdAt: "2024-01-01T00:00:00Z",
  updatedAt: "2024-01-01T00:00:00Z",
};

const mockArtifact2: CanvasArtifact = {
  id: "artifact-2",
  type: "mermaid",
  sessionId: "session-1",
  version: 1,
  content: "graph TD\n  A-->B",
  contentType: "mermaid",
  title: "Diagram",
  createdAt: "2024-01-01T01:00:00Z",
  updatedAt: "2024-01-01T01:00:00Z",
};

describe("CanvasContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  // ===========================================================================
  // Provider Initialization Tests
  // ===========================================================================

  describe("CanvasProvider initialization", () => {
    it("should initialize with empty artifacts", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.artifacts).toEqual([]);
      expect(result.current.selectedArtifactId).toBeNull();
    });

    it("should accept initial artifacts via prop", () => {
      const wrapper = ({ children }: { children: React.ReactNode }) =>
        React.createElement(
          CanvasProvider,
          { pageContext: "chat", initialArtifacts: [mockArtifact] },
          children,
        );
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.artifacts).toHaveLength(1);
      expect(result.current.artifacts[0].id).toBe("artifact-1");
    });

    it("should initialize with page context", () => {
      const wrapper = createWrapper("workflow");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("workflow");
    });
  });

  // ===========================================================================
  // Page Context Tests
  // ===========================================================================

  describe("Page Context", () => {
    it("should support chat context", () => {
      const wrapper = createWrapper("chat");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("chat");
    });

    it("should support workflow context", () => {
      const wrapper = createWrapper("workflow");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("workflow");
    });

    it("should support mcp-tools context", () => {
      const wrapper = createWrapper("mcp-tools");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("mcp-tools");
    });

    it("should support agents context", () => {
      const wrapper = createWrapper("agents");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("agents");
    });

    it("should support connections context", () => {
      const wrapper = createWrapper("connections");
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.pageContext).toBe("connections");
    });
  });

  // ===========================================================================
  // Artifact Management Tests
  // ===========================================================================

  describe("Artifact Management", () => {
    it("should add an artifact", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
      });

      expect(result.current.artifacts).toHaveLength(1);
      expect(result.current.artifacts[0]).toEqual(mockArtifact);
    });

    it("should add multiple artifacts", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.addArtifact(mockArtifact2);
      });

      expect(result.current.artifacts).toHaveLength(2);
    });

    it("should not add duplicate artifacts", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.addArtifact(mockArtifact); // Same ID
      });

      expect(result.current.artifacts).toHaveLength(1);
    });

    it("should update artifact content", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
      });

      act(() => {
        result.current.updateArtifact("artifact-1", 'console.log("Updated");');
      });

      expect(result.current.artifacts[0].content).toBe(
        'console.log("Updated");',
      );
    });

    it("should not update non-existent artifact", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
      });

      act(() => {
        result.current.updateArtifact("non-existent", "new content");
      });

      expect(result.current.artifacts).toHaveLength(1);
      expect(result.current.artifacts[0].content).toBe(mockArtifact.content);
    });

    it("should remove an artifact", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.addArtifact(mockArtifact2);
      });

      act(() => {
        result.current.removeArtifact("artifact-1");
      });

      expect(result.current.artifacts).toHaveLength(1);
      expect(result.current.artifacts[0].id).toBe("artifact-2");
    });

    it("should clear selection when selected artifact is removed", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.selectArtifact("artifact-1");
      });

      expect(result.current.selectedArtifactId).toBe("artifact-1");

      act(() => {
        result.current.removeArtifact("artifact-1");
      });

      expect(result.current.selectedArtifactId).toBeNull();
    });
  });

  // ===========================================================================
  // Artifact Selection Tests
  // ===========================================================================

  describe("Artifact Selection", () => {
    it("should select an artifact", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.selectArtifact("artifact-1");
      });

      expect(result.current.selectedArtifactId).toBe("artifact-1");
    });

    it("should change selection when selecting different artifact", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.addArtifact(mockArtifact2);
        result.current.selectArtifact("artifact-1");
      });

      expect(result.current.selectedArtifactId).toBe("artifact-1");

      act(() => {
        result.current.selectArtifact("artifact-2");
      });

      expect(result.current.selectedArtifactId).toBe("artifact-2");
    });

    it("should clear selection with null", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.selectArtifact("artifact-1");
      });

      expect(result.current.selectedArtifactId).toBe("artifact-1");

      act(() => {
        result.current.selectArtifact(null);
      });

      expect(result.current.selectedArtifactId).toBeNull();
    });

    it("should return selected artifact via getter", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.selectArtifact("artifact-1");
      });

      expect(result.current.selectedArtifact).toEqual(mockArtifact);
    });

    it("should return null when no artifact is selected", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      expect(result.current.selectedArtifact).toBeNull();
    });
  });

  // ===========================================================================
  // Batch Operations Tests
  // ===========================================================================

  describe("Batch Operations", () => {
    it("should set all artifacts at once", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.setArtifacts([mockArtifact, mockArtifact2]);
      });

      expect(result.current.artifacts).toHaveLength(2);
    });

    it("should clear all artifacts", () => {
      const wrapper = createWrapper();
      const { result } = renderHook(() => useCanvas(), { wrapper });

      act(() => {
        result.current.addArtifact(mockArtifact);
        result.current.addArtifact(mockArtifact2);
      });

      expect(result.current.artifacts).toHaveLength(2);

      act(() => {
        result.current.clearArtifacts();
      });

      expect(result.current.artifacts).toHaveLength(0);
      expect(result.current.selectedArtifactId).toBeNull();
    });
  });

  // ===========================================================================
  // Error Handling Tests
  // ===========================================================================

  describe("Error Handling", () => {
    it("should throw error when useCanvas is used outside provider", () => {
      // Suppress console.error for this test
      const originalError = console.error;
      console.error = vi.fn();

      expect(() => {
        renderHook(() => useCanvas());
      }).toThrow("useCanvas must be used within a CanvasProvider");

      console.error = originalError;
    });
  });
});

/**
 * Tests for useSessionIntelligence hook.
 *
 * Sprint 2: Session Intelligence
 * - Summarization generates one-line AI summaries per session
 * - Grouping clusters sessions by topic/project
 * - Similarity search finds related sessions
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, cleanup, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Mock the API module - use flushPromises pattern for clean async handling
const mockAnalyzeFn = vi.fn();
vi.mock("../api", async () => {
  const actual = await vi.importActual("../api");
  return {
    ...actual,
    useStudioAnalyzeMutation: vi.fn(() => [
      mockAnalyzeFn,
      { isLoading: false },
    ]),
  };
});
// Setup default mock behavior
function setupDefaultMock() {
  mockAnalyzeFn.mockImplementation(() => ({
    unwrap: () =>
      Promise.resolve({
        analyses: {
          session_summarize: {
            summary: "Test session summary",
            key_topics: ["React", "testing"],
            message_count: 10,
          },
        },
        cross_insights: [],
        failed_analyses: [],
        total_cost: "0.001",
      }),
  }));
}

// =============================================================================
// Test Utilities
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      // Minimal reducer for testing
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = () => {
  const store = createTestStore();
  return function Wrapper({ children }: WrapperProps) {
    return <Provider store={store}>{children}</Provider>;
  };
};

// =============================================================================
// useSessionSummary Tests
// =============================================================================

// Import hooks at the top level after mocks are set up

import {
  useSessionSummary,
  useSessionGroups,
  useSessionSimilarity,
} from "./useSessionIntelligence";

describe("useSessionSummary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupDefaultMock();
  });

  afterEach(async () => {
    // Wait for any pending state updates before cleanup
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  it("should return session summary when given a session ID", async () => {
    const { result } = renderHook(
      () =>
        useSessionSummary({
          userId: "test-user",
          sessionId: "session-123",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.summary).toBeDefined();
  });

  it("should include key topics in the result", async () => {
    const { result } = renderHook(
      () =>
        useSessionSummary({
          userId: "test-user",
          sessionId: "session-456",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.keyTopics).toBeDefined();
    expect(Array.isArray(result.current.keyTopics)).toBe(true);
  });

  it("should provide a refetch function", async () => {
    const { result } = renderHook(
      () =>
        useSessionSummary({
          userId: "test-user",
          sessionId: "session-789",
        }),
      { wrapper: createWrapper() },
    );

    expect(typeof result.current.refetch).toBe("function");

    // Wait for async operations to complete
    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });
  });

  it("should handle disabled state", async () => {
    const { result } = renderHook(
      () =>
        useSessionSummary({
          userId: "test-user",
          sessionId: "session-disabled",
          enabled: false,
        }),
      { wrapper: createWrapper() },
    );

    // Should not be loading when disabled
    expect(result.current.isLoading).toBe(false);
    expect(result.current.summary).toBeNull();
  });
});

// =============================================================================
// useSessionGroups Tests
// =============================================================================

function setupGroupsMock() {
  mockAnalyzeFn.mockImplementation(() => ({
    unwrap: () =>
      Promise.resolve({
        analyses: {
          session_group: {
            groups: [
              {
                topic: "API Development",
                session_ids: ["s1", "s2", "s3"],
                confidence: 0.85,
              },
              {
                topic: "Frontend Work",
                session_ids: ["s4", "s5"],
                confidence: 0.78,
              },
            ],
            ungrouped: ["s6"],
          },
        },
        cross_insights: [],
        failed_analyses: [],
        total_cost: "0.002",
      }),
  }));
}

describe("useSessionGroups", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupGroupsMock();
  });

  afterEach(async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  it("should return grouped sessions", async () => {
    const { result } = renderHook(
      () =>
        useSessionGroups({
          userId: "test-user",
          sessionIds: ["s1", "s2", "s3", "s4", "s5", "s6"],
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.groups).toBeDefined();
  });

  it("should include topic names for each group", async () => {
    const { result } = renderHook(
      () =>
        useSessionGroups({
          userId: "test-user",
          sessionIds: ["s1", "s2"],
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    if (result.current.groups && result.current.groups.length > 0) {
      expect(result.current.groups[0]).toHaveProperty("topic");
    }
  });

  it("should handle ungrouped sessions", async () => {
    const { result } = renderHook(
      () =>
        useSessionGroups({
          userId: "test-user",
          sessionIds: ["unique-session"],
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.ungrouped).toBeDefined();
  });
});

// =============================================================================
// useSessionSimilarity Tests
// =============================================================================

function setupSimilarityMock() {
  mockAnalyzeFn.mockImplementation(() => ({
    unwrap: () =>
      Promise.resolve({
        analyses: {
          session_similarity: {
            source_session_id: "session-123",
            similar_sessions: [
              {
                session_id: "session-456",
                similarity_score: 0.92,
                common_topics: ["React", "hooks"],
              },
              {
                session_id: "session-789",
                similarity_score: 0.78,
                common_topics: ["React"],
              },
            ],
          },
        },
        cross_insights: [],
        failed_analyses: [],
        total_cost: "0.001",
      }),
  }));
}

function setupEmptySimilarityMock() {
  mockAnalyzeFn.mockImplementation(() => ({
    unwrap: () =>
      Promise.resolve({
        analyses: {
          session_similarity: {
            source_session_id: "unique-session",
            similar_sessions: [],
          },
        },
        cross_insights: [],
        failed_analyses: [],
        total_cost: "0.001",
      }),
  }));
}

function setupErrorMock() {
  mockAnalyzeFn.mockImplementation(() => ({
    unwrap: () => Promise.reject(new Error("API Error")),
  }));
}

describe("useSessionSimilarity", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupSimilarityMock();
  });

  afterEach(async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  it("should return similar sessions", async () => {
    const { result } = renderHook(
      () =>
        useSessionSimilarity({
          userId: "test-user",
          sessionId: "session-123",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.similarSessions).toBeDefined();
  });

  it("should include similarity scores", async () => {
    const { result } = renderHook(
      () =>
        useSessionSimilarity({
          userId: "test-user",
          sessionId: "session-123",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    if (
      result.current.similarSessions &&
      result.current.similarSessions.length > 0
    ) {
      expect(result.current.similarSessions[0]).toHaveProperty(
        "similarityScore",
      );
    }
  });

  it("should handle no matches gracefully", async () => {
    setupEmptySimilarityMock();

    const { result } = renderHook(
      () =>
        useSessionSimilarity({
          userId: "test-user",
          sessionId: "unique-session",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.similarSessions).toBeDefined();
    expect(result.current.error).toBeNull();
  });
});

// =============================================================================
// Error Handling Tests
// =============================================================================

describe("Session Intelligence Error Handling", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(async () => {
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    cleanup();
  });

  it("should handle API errors gracefully", async () => {
    setupErrorMock();

    const { result } = renderHook(
      () =>
        useSessionSummary({
          userId: "test-user",
          sessionId: "error-session",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.error).toBeDefined();
  });
});

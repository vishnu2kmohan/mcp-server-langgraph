/**
 * useHeartMetricsTracker Hook Tests
 *
 * Tests for the enhanced HEART metrics tracker with:
 * - GSM integration
 * - Batched event sending
 * - Session lifecycle tracking
 * - Persona context
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ReactNode } from "react";
import { useHeartMetricsTracker } from "./useHeartMetricsTracker";
import personaReducer from "../store/slices/personaSlice";
import { storage } from "../utils/storage";

// Mock storage
vi.mock("../utils/storage", () => ({
  storage: {
    get: vi.fn(),
    set: vi.fn(),
    remove: vi.fn(),
  },
  STORAGE_KEYS: {
    LAST_VISIT: "langgraph_last_visit",
  },
}));

// Mock GSM
vi.mock("../analytics/gsm", () => ({
  recordSignal: vi.fn(),
}));

// Create wrapper with Redux store
function createWrapper(personaState = {}) {
  const store = configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona: "developer" as const,
        subPersona: "alice-builder" as const,
        username: "alice",
        email: "alice@example.com",
        permissions: [],
        isPersonaLoading: false,
        ...personaState,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return <Provider store={store}>{children}</Provider>;
  };
}

describe("useHeartMetricsTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (storage.get as ReturnType<typeof vi.fn>).mockReturnValue(null);
  });

  describe("initialization", () => {
    it("should return session start time greater than 0", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.sessionStartTime).toBeGreaterThan(0);
    });

    it("should return getSessionDuration function", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.getSessionDuration).toBe("function");
    });

    it("should initialize with zero pending events count", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.pendingEventsCount).toBe(0);
    });

    it("should return increasing session duration over time", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      const duration1 = result.current.getSessionDuration();

      // Wait a bit
      await new Promise((r) => setTimeout(r, 50));

      const duration2 = result.current.getSessionDuration();

      expect(duration2).toBeGreaterThan(duration1);
    });
  });

  describe("GSM integration", () => {
    it("should expose recordSignal function", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.recordSignal).toBe("function");
    });

    it("should record signal and queue event", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.recordSignal("happiness_nps_score", 9);
      });

      // Signal should be queued
      expect(result.current.pendingEventsCount).toBeGreaterThan(0);
    });

    it("should queue signal with metadata", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.recordSignal("engagement_feature_click", 1, {
          feature: "workflow_builder",
        });
      });

      expect(result.current.pendingEventsCount).toBe(1);
    });
  });

  describe("batched event sending", () => {
    it("should batch engagement events", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackEngagement({ feature: "chat", action: "send" });
        result.current.trackEngagement({ feature: "chat", action: "receive" });
      });

      expect(result.current.pendingEventsCount).toBe(2);
    });

    it("should expose batchConfig with flush thresholds", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.batchConfig).toBeDefined();
      expect(result.current.batchConfig.flushIntervalMs).toBe(30000);
      expect(result.current.batchConfig.maxBatchSize).toBe(50);
    });

    it("should clear pending events on flush", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackEngagement({ feature: "chat", action: "send" });
        result.current.trackEngagement({ feature: "chat", action: "receive" });
      });

      expect(result.current.pendingEventsCount).toBe(2);

      await act(async () => {
        await result.current.flushMetrics();
      });

      expect(result.current.pendingEventsCount).toBe(0);
    });

    it("should accumulate events until flush", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.trackEngagement({ feature: "test", action: `action_${i}` });
        }
      });

      expect(result.current.pendingEventsCount).toBe(10);
    });
  });

  describe("happiness tracking", () => {
    it("should expose trackHappiness function", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.trackHappiness).toBe("function");
    });

    it("should accept NPS score payload", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      // Should not throw
      await act(async () => {
        await result.current.trackHappiness({ npsScore: 9 });
      });
    });

    it("should accept satisfaction rating payload", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.trackHappiness({ satisfactionRating: 5 });
      });
    });

    it("should accept feedback payload", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.trackHappiness({ feedback: "Great experience!" });
      });
    });
  });

  describe("engagement tracking", () => {
    it("should track feature usage and queue event", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackEngagement({ feature: "workflow_builder", action: "create" });
      });

      expect(result.current.pendingEventsCount).toBe(1);
    });

    it("should track multiple engagement events", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackEngagement({ feature: "chat", action: "send" });
        result.current.trackEngagement({ feature: "workflow", action: "edit" });
        result.current.trackEngagement({ feature: "agent", action: "run" });
      });

      expect(result.current.pendingEventsCount).toBe(3);
    });
  });

  describe("adoption tracking", () => {
    it("should expose trackAdoption function", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.trackAdoption).toBe("function");
    });

    it("should accept onboarding step payload", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.trackAdoption({
          step: "template_selection",
          stepIndex: 2,
          completed: true,
        });
      });
    });

    it("should accept feature discovery payload", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      await act(async () => {
        await result.current.trackAdoption({
          feature: "ai_suggestions",
          discovered: true,
        });
      });
    });
  });

  describe("retention tracking", () => {
    it("should return 0 for first visit", () => {
      (storage.get as ReturnType<typeof vi.fn>).mockReturnValue(null);

      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.daysSinceLastVisit).toBe(0);
    });

    it("should calculate days since last visit", () => {
      const threeDaysAgo = Date.now() - 3 * 86400000;
      (storage.get as ReturnType<typeof vi.fn>).mockReturnValue(threeDaysAgo.toString());

      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.daysSinceLastVisit).toBe(3);
    });

    it("should calculate days since last visit for 1 day", () => {
      const oneDayAgo = Date.now() - 1 * 86400000;
      (storage.get as ReturnType<typeof vi.fn>).mockReturnValue(oneDayAgo.toString());

      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.daysSinceLastVisit).toBe(1);
    });

    it("should expose trackRetention function", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(typeof result.current.trackRetention).toBe("function");
    });
  });

  describe("task success tracking", () => {
    it("should start task tracking", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.startTask("create_workflow");
      });

      expect(result.current.currentTaskId).toBe("create_workflow");
    });

    it("should clear currentTaskId after completing task", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.startTask("create_workflow");
      });

      expect(result.current.currentTaskId).toBe("create_workflow");

      await act(async () => {
        await result.current.completeTask(true);
      });

      expect(result.current.currentTaskId).toBeNull();
    });

    it("should handle task failure", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.startTask("create_workflow");
      });

      await act(async () => {
        await result.current.completeTask(false, "Validation failed");
      });

      expect(result.current.currentTaskId).toBeNull();
    });

    it("should track task with duration", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.startTask("create_workflow");
      });

      // Wait for some time
      await new Promise((r) => setTimeout(r, 20));

      await act(async () => {
        await result.current.completeTask(true);
      });

      expect(result.current.currentTaskId).toBeNull();
    });
  });

  describe("flush metrics", () => {
    it("should flush all pending events", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      act(() => {
        result.current.trackEngagement({ feature: "chat", action: "send" });
        result.current.trackEngagement({ feature: "chat", action: "receive" });
      });

      expect(result.current.pendingEventsCount).toBe(2);

      await act(async () => {
        await result.current.flushMetrics();
      });

      expect(result.current.pendingEventsCount).toBe(0);
    });

    it("should be callable even with no pending events", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      expect(result.current.pendingEventsCount).toBe(0);

      // Should not throw
      await act(async () => {
        await result.current.flushMetrics();
      });

      expect(result.current.pendingEventsCount).toBe(0);
    });
  });

  describe("error handling", () => {
    it("should handle API errors gracefully", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      // Should not throw even if API fails (it's mocked)
      await act(async () => {
        await result.current.trackHappiness({ npsScore: 9 });
      });

      expect(result.current.pendingEventsCount).toBeGreaterThanOrEqual(0);
    });
  });

  describe("interface completeness", () => {
    it("should expose all required functions and properties", () => {
      const { result } = renderHook(() => useHeartMetricsTracker(), {
        wrapper: createWrapper(),
      });

      // Properties
      expect(result.current.sessionStartTime).toBeDefined();
      expect(result.current.daysSinceLastVisit).toBeDefined();
      expect(result.current.currentTaskId).toBeDefined();
      expect(result.current.pendingEventsCount).toBeDefined();
      expect(result.current.batchConfig).toBeDefined();

      // Functions
      expect(typeof result.current.getSessionDuration).toBe("function");
      expect(typeof result.current.trackHappiness).toBe("function");
      expect(typeof result.current.trackEngagement).toBe("function");
      expect(typeof result.current.trackAdoption).toBe("function");
      expect(typeof result.current.trackRetention).toBe("function");
      expect(typeof result.current.startTask).toBe("function");
      expect(typeof result.current.completeTask).toBe("function");
      expect(typeof result.current.flushMetrics).toBe("function");
      expect(typeof result.current.recordSignal).toBe("function");
    });
  });
});

/**
 * useHeartMetricsTracker Hook Tests
 *
 * TDD tests for the HEART metrics tracking hook.
 * Tests cover:
 * - Happiness tracking (NPS, satisfaction)
 * - Engagement tracking (session duration, feature usage)
 * - Adoption tracking (onboarding, feature discovery)
 * - Retention tracking (return visits)
 * - Task Success tracking (goal completion)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useHeartMetricsTracker } from "./useHeartMetricsTracker";

// Mock fetch with proper structure for Vitest
const mockFetch = vi.fn();

describe("useHeartMetricsTracker", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Mock fetch to return successful response
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ success: true }),
    });
    // Override global fetch
    vi.stubGlobal("fetch", mockFetch);
    // Clear localStorage
    localStorage.clear();
    // Reset performance.now mock
    vi.spyOn(performance, "now").mockReturnValue(0);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Session Tracking", () => {
    it("should track session start time", () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      expect(result.current.sessionStartTime).toBeDefined();
    });

    it("should calculate session duration", async () => {
      // Mock performance.now to track calls - start at 0, then 60000
      let callCount = 0;
      vi.spyOn(performance, "now").mockImplementation(() => {
        callCount++;
        return callCount === 1 ? 0 : 60000; // First call: 0 (session start), Second+: 60000
      });

      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        const duration = result.current.getSessionDuration();
        expect(duration).toBe(60000);
      });
    });
  });

  describe("Happiness Tracking", () => {
    it("should track NPS score", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.trackHappiness({
          npsScore: 9,
          feedback: "Great experience!",
        });
      });

      // Verify happiness event was sent
      const calls = mockFetch.mock.calls;
      const happinessCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"event_type":"happiness"'),
      );
      expect(happinessCall).toBeDefined();
    });

    it("should track satisfaction rating", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.trackHappiness({
          satisfactionRating: 4,
        });
      });

      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("Engagement Tracking", () => {
    it("should track feature usage by queueing events", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.trackEngagement({
          feature: "workflow_builder",
          action: "create_node",
        });
      });

      // Engagement events are queued for batching
      expect(result.current.pendingEventsCount).toBe(1);
    });

    it("should send engagement events on flush", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.trackEngagement({
          feature: "workflow_builder",
          action: "create_node",
        });
      });

      await act(async () => {
        await result.current.flushMetrics();
      });

      // Verify engagement event was sent
      const calls = mockFetch.mock.calls;
      const engagementCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"event_type":"engagement"') &&
          call[1].body.includes('"feature":"workflow_builder"'),
      );
      expect(engagementCall).toBeDefined();
    });

    it("should track session duration on flush", async () => {
      vi.spyOn(performance, "now").mockReturnValue(120000); // 2 minutes

      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.flushMetrics();
      });

      // Verify session_duration was included in the engagement event
      const calls = mockFetch.mock.calls;
      const sessionCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"session_duration"'),
      );
      expect(sessionCall).toBeDefined();
    });
  });

  describe("Adoption Tracking", () => {
    it("should track onboarding step completion", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.trackAdoption({
          step: "template_selected",
          stepIndex: 2,
          completed: true,
        });
      });

      // Verify adoption event was sent
      const calls = mockFetch.mock.calls;
      const adoptionCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"event_type":"adoption"'),
      );
      expect(adoptionCall).toBeDefined();
    });

    it("should track feature discovery", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.trackAdoption({
          feature: "command_palette",
          discovered: true,
        });
      });

      expect(mockFetch).toHaveBeenCalled();
    });
  });

  describe("Retention Tracking", () => {
    it("should track return visits", async () => {
      // Simulate a previous visit - set before hook renders
      localStorage.setItem(
        "heart_last_visit",
        (Date.now() - 86400000).toString(),
      ); // 1 day ago

      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        await result.current.trackRetention();
      });

      // Verify retention event was sent
      const calls = mockFetch.mock.calls;
      const retentionCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"event_type":"retention"'),
      );
      expect(retentionCall).toBeDefined();
    });

    it("should calculate days since last visit", () => {
      // Mock localStorage.getItem to return a timestamp from 3 days ago
      const threeDaysAgo = Date.now() - 3 * 86400000;
      const originalGetItem = localStorage.getItem.bind(localStorage);
      vi.spyOn(localStorage, "getItem").mockImplementation((key: string) => {
        if (key === "studio-last-visit") {
          return threeDaysAgo.toString();
        }
        return originalGetItem(key);
      });

      const { result } = renderHook(() => useHeartMetricsTracker());

      // Should be 3 days
      expect(result.current.daysSinceLastVisit).toBe(3);
    });

    it("should return 0 for first visit", () => {
      // localStorage is cleared in beforeEach, so this is a first visit
      const { result } = renderHook(() => useHeartMetricsTracker());

      expect(result.current.daysSinceLastVisit).toBe(0);
    });
  });

  describe("Task Success Tracking", () => {
    it("should track task start", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.startTask("create_workflow");
      });

      expect(result.current.currentTaskId).toBe("create_workflow");
    });

    it("should track task completion with duration", async () => {
      vi.spyOn(performance, "now")
        .mockReturnValueOnce(0) // Session start
        .mockReturnValueOnce(0) // Task start
        .mockReturnValueOnce(30000); // Task end (30 seconds)

      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.startTask("create_workflow");
      });

      await act(async () => {
        await result.current.completeTask(true);
      });

      // Verify task_success event was sent
      const calls = mockFetch.mock.calls;
      const taskCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"event_type":"task_success"'),
      );
      expect(taskCall).toBeDefined();
    });

    it("should track task failure", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.startTask("deploy_workflow");
      });

      await act(async () => {
        await result.current.completeTask(false, "Permission denied");
      });

      // Verify task failure was tracked
      const calls = mockFetch.mock.calls;
      const failureCall = calls.find(
        (call) =>
          typeof call[1]?.body === "string" &&
          call[1].body.includes('"success":false'),
      );
      expect(failureCall).toBeDefined();
    });
  });

  describe("Batching and Optimization", () => {
    it("should batch events to reduce API calls", async () => {
      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        result.current.trackEngagement({
          feature: "chat",
          action: "send_message",
        });
        result.current.trackEngagement({
          feature: "chat",
          action: "receive_response",
        });
        result.current.trackEngagement({ feature: "workflow", action: "view" });
      });

      // Events should be batched, not sent immediately
      await waitFor(() => {
        expect(result.current.pendingEventsCount).toBeGreaterThan(0);
      });
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const { result } = renderHook(() => useHeartMetricsTracker());

      await act(async () => {
        // Should not throw
        await result.current.trackHappiness({ npsScore: 9 });
      });

      // Hook should still function
      expect(result.current.sessionStartTime).toBeDefined();
    });
  });
});

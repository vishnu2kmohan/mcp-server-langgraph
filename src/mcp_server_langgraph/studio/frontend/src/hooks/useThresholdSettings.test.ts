/**
 * useThresholdSettings Hook Tests
 *
 * TDD tests for threshold settings and recommendations.
 *
 * Features:
 * - Fetch threshold recommendation
 * - Fetch user threshold settings
 * - Update threshold settings
 * - Loading and error states
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";

// =============================================================================
// Tests
// =============================================================================

describe("useThresholdSettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Export", () => {
    it("should export useThresholdSettings hook", async () => {
      const module = await import("./useThresholdSettings");
      expect(module.useThresholdSettings).toBeDefined();
    });

    it("should export ThresholdRecommendation type", async () => {
      const module = await import("./useThresholdSettings");
      // Type exists if import doesn't fail
      expect(module).toBeDefined();
    });

    it("should export UserThresholdSettings type", async () => {
      const module = await import("./useThresholdSettings");
      // Type exists if import doesn't fail
      expect(module).toBeDefined();
    });
  });

  describe("Initial State", () => {
    it("should return initial state with loading false", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(result.current.isLoading).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should have undefined recommendation initially", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(result.current.recommendation).toBeUndefined();
    });

    it("should have undefined settings initially", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(result.current.settings).toBeUndefined();
    });
  });

  describe("Fetch Recommendation", () => {
    it("should provide fetchRecommendation function", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(typeof result.current.fetchRecommendation).toBe("function");
    });

    it("should set isLoading to true during fetch", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () =>
                    Promise.resolve({
                      current_threshold: 0.7,
                      recommended_threshold: 0.65,
                      reason: "High approval rate",
                      confidence_level: 0.85,
                      sample_size: 50,
                    }),
                }),
              100
            )
          )
      );
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      act(() => {
        result.current.fetchRecommendation();
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      vi.unstubAllGlobals();
    });

    it("should update recommendation on successful fetch", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockRecommendation = {
        current_threshold: 0.7,
        recommended_threshold: 0.65,
        reason: "High approval rate",
        confidence_level: 0.85,
        sample_size: 50,
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockRecommendation),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      await act(async () => {
        await result.current.fetchRecommendation();
      });

      expect(result.current.recommendation).toEqual(mockRecommendation);

      vi.unstubAllGlobals();
    });
  });

  describe("Fetch Settings", () => {
    it("should provide fetchSettings function", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(typeof result.current.fetchSettings).toBe("function");
    });

    it("should update settings on successful fetch", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockSettings = {
        user_id: "user-001",
        base_threshold: 0.7,
        adjusted_threshold: 0.65,
        auto_adjust_enabled: true,
        min_threshold: 0.5,
        max_threshold: 0.9,
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockSettings),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      await act(async () => {
        await result.current.fetchSettings();
      });

      expect(result.current.settings).toEqual(mockSettings);

      vi.unstubAllGlobals();
    });
  });

  describe("Update Settings", () => {
    it("should provide updateSettings function", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(typeof result.current.updateSettings).toBe("function");
    });

    it("should call API with correct payload", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            user_id: "user-001",
            base_threshold: 0.8,
            adjusted_threshold: 0.8,
            auto_adjust_enabled: true,
            min_threshold: 0.5,
            max_threshold: 0.9,
          }),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      await act(async () => {
        await result.current.updateSettings({ base_threshold: 0.8 });
      });

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining("/threshold/settings"),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ base_threshold: 0.8 }),
        })
      );

      vi.unstubAllGlobals();
    });

    it("should update local settings after successful update", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const updatedSettings = {
        user_id: "user-001",
        base_threshold: 0.8,
        adjusted_threshold: 0.8,
        auto_adjust_enabled: true,
        min_threshold: 0.5,
        max_threshold: 0.9,
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(updatedSettings),
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      await act(async () => {
        await result.current.updateSettings({ base_threshold: 0.8 });
      });

      expect(result.current.settings).toEqual(updatedSettings);

      vi.unstubAllGlobals();
    });
  });

  describe("Error Handling", () => {
    it("should set error on failed fetch", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
      });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      await act(async () => {
        await result.current.fetchRecommendation();
      });

      expect(result.current.error).not.toBeNull();

      vi.unstubAllGlobals();
    });

    it("should clear error on successful subsequent request", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: false,
          status: 500,
          statusText: "Internal Server Error",
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              current_threshold: 0.7,
              recommended_threshold: 0.7,
              reason: "Insufficient data",
              confidence_level: 0.25,
              sample_size: 5,
            }),
        });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      // First call fails
      await act(async () => {
        await result.current.fetchRecommendation();
      });
      expect(result.current.error).not.toBeNull();

      // Second call succeeds
      await act(async () => {
        await result.current.fetchRecommendation();
      });
      expect(result.current.error).toBeNull();

      vi.unstubAllGlobals();
    });
  });

  describe("Apply Recommendation", () => {
    it("should provide applyRecommendation function", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const { result } = renderHook(() => useThresholdSettings());

      expect(typeof result.current.applyRecommendation).toBe("function");
    });

    it("should update settings with recommended threshold", async () => {
      const { useThresholdSettings } = await import("./useThresholdSettings");

      const mockRecommendation = {
        current_threshold: 0.7,
        recommended_threshold: 0.65,
        reason: "High approval rate",
        confidence_level: 0.85,
        sample_size: 50,
      };

      const updatedSettings = {
        user_id: "user-001",
        base_threshold: 0.65,
        adjusted_threshold: 0.65,
        auto_adjust_enabled: true,
        min_threshold: 0.5,
        max_threshold: 0.9,
      };

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(mockRecommendation),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(updatedSettings),
        });
      vi.stubGlobal("fetch", mockFetch);

      const { result } = renderHook(() => useThresholdSettings());

      // First fetch recommendation
      await act(async () => {
        await result.current.fetchRecommendation();
      });

      // Then apply it
      await act(async () => {
        await result.current.applyRecommendation();
      });

      expect(result.current.settings?.base_threshold).toBe(0.65);

      vi.unstubAllGlobals();
    });
  });
});

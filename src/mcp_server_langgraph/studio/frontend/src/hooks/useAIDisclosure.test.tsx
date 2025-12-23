/**
 * useAIDisclosure Hook Tests
 *
 * Sprint 3 - Phase 6.1: AI-Augmented Progressive Disclosure
 */

import React from "react";
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, waitFor, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { http, HttpResponse, delay } from "msw";
import { server } from "../mocks/server";
import { useAIDisclosure } from "./useAIDisclosure";
import disclosureReducer, {
  selectDisclosureLevel,
  type DisclosureLevel,
} from "../store/slices/disclosureSlice";
import { api } from "../api";

// Mock AI response
const mockAnalysis = {
  current_level: "intermediate" as DisclosureLevel,
  recommended_level: "advanced" as DisclosureLevel,
  confidence: 0.85,
  unlock_features: ["workflow_builder", "custom_agents"],
  personalized_message: "You've mastered chat! Ready to build workflows?",
};

// Create a test store factory with RTK Query support
const createTestStore = () =>
  configureStore({
    reducer: {
      disclosure: disclosureReducer,
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

// Wrapper for all tests to provide Redux context
const createWrapper =
  (store: ReturnType<typeof createTestStore>) =>
  ({ children }: { children: React.ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );

describe("useAIDisclosure", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    vi.clearAllMocks();
    store = createTestStore();
  });

  afterEach(() => {
    cleanup();
    server.resetHandlers();
  });

  describe("initial state", () => {
    it("should return initial state", () => {
      const { result } = renderHook(() => useAIDisclosure(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.level).toBe("beginner");
      expect(result.current.recommendedLevel).toBeNull();
      expect(result.current.confidence).toBe(0);
      expect(result.current.isAIAvailable).toBe(false);
      expect(result.current.isAnalyzing).toBe(false);
    });
  });

  describe("analyze", () => {
    it("should fetch AI recommendation", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          await delay(50);
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.analyze();
      });

      await waitFor(() => {
        expect(result.current.recommendedLevel).toBe("advanced");
      });

      expect(result.current.confidence).toBe(0.85);
      expect(result.current.unlockFeatures).toContain("workflow_builder");
    });

    it("should return personalized message", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.analyze();
      });

      expect(result.current.personalizedMessage).toBe(
        "You've mastered chat! Ready to build workflows?",
      );
    });

    it("should set isAnalyzing during analysis", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          await delay(200);
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.analyze();
      });

      await waitFor(() => {
        expect(result.current.isAnalyzing).toBe(true);
      });

      await waitFor(() => {
        expect(result.current.isAnalyzing).toBe(false);
      });
    });
  });

  describe("acceptRecommendation", () => {
    it("should call accept callback", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.analyze();
      });

      // Accept should clear recommendation
      act(() => {
        result.current.acceptRecommendation();
      });

      expect(result.current.recommendedLevel).toBeNull();
    });
  });

  describe("dismissRecommendation", () => {
    it("should clear recommendation on dismiss", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: true }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.analyze();
      });

      expect(result.current.recommendedLevel).not.toBeNull();

      act(() => {
        result.current.dismissRecommendation();
      });

      expect(result.current.recommendedLevel).toBeNull();
    });
  });

  describe("disabled mode", () => {
    it("should not fetch when disabled", async () => {
      let apiCalled = false;
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", () => {
          apiCalled = true;
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(() => useAIDisclosure({ enabled: false }), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.analyze();
      });

      expect(apiCalled).toBe(false);
    });
  });

  describe("minConfidence", () => {
    it("should not recommend when below minConfidence", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json({
            ...mockAnalysis,
            confidence: 0.5,
          });
        }),
      );

      const { result } = renderHook(
        () => useAIDisclosure({ enabled: true, minConfidence: 0.7 }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await result.current.analyze();
      });

      // Should not show recommendation if confidence < minConfidence
      expect(result.current.recommendedLevel).toBeNull();
    });

    it("should recommend when above minConfidence", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json({
            ...mockAnalysis,
            confidence: 0.9,
          });
        }),
      );

      const { result } = renderHook(
        () => useAIDisclosure({ enabled: true, minConfidence: 0.7 }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await result.current.analyze();
      });

      expect(result.current.recommendedLevel).toBe("advanced");
    });
  });

  describe("Redux integration", () => {
    it("should read initial level from Redux store", () => {
      const { result } = renderHook(() => useAIDisclosure({ useRedux: true }), {
        wrapper: createWrapper(store),
      });

      expect(result.current.level).toBe("beginner");
    });

    it("should update Redux store when accepting recommendation", async () => {
      server.use(
        http.post("/api/v1/ai/disclosure/analyze", async () => {
          return HttpResponse.json(mockAnalysis);
        }),
      );

      const { result } = renderHook(
        () => useAIDisclosure({ enabled: true, useRedux: true }),
        { wrapper: createWrapper(store) },
      );

      await act(async () => {
        await result.current.analyze();
      });

      expect(result.current.recommendedLevel).toBe("advanced");

      act(() => {
        result.current.acceptRecommendation();
      });

      // Redux store should be updated
      const state = store.getState();
      expect(selectDisclosureLevel(state)).toBe("advanced");
    });

    it("should sync with Redux level changes", () => {
      const { result } = renderHook(() => useAIDisclosure({ useRedux: true }), {
        wrapper: createWrapper(store),
      });

      expect(result.current.level).toBe("beginner");

      // Dispatch action to change level
      act(() => {
        store.dispatch({
          type: "disclosure/setDisclosureLevel",
          payload: "intermediate",
        });
      });

      expect(result.current.level).toBe("intermediate");
    });
  });
});

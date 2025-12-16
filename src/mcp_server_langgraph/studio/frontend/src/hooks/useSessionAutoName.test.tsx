/**
 * useSessionAutoName Hook Tests
 *
 * Tests for the session auto-naming hook that generates AI-powered
 * session titles based on the first user message.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useSessionAutoName } from "./useSessionAutoName";
import { api } from "../api";
import type { ReactNode } from "react";

// Mock the RTK Query mutation
vi.mock("../api", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api")>();
  return {
    ...original,
    useGenerateSessionTitleMutation: vi.fn(() => [
      vi.fn().mockResolvedValue({
        data: { title: "Generated Title", confidence: 0.9 },
      }),
      { isLoading: false, isSuccess: false, data: undefined },
    ]),
  };
});

// Mock the dispatch for renameSession
const mockDispatch = vi.fn();
vi.mock("../store/hooks", () => ({
  useAppDispatch: () => mockDispatch,
}));

describe("useSessionAutoName", () => {
  let store: ReturnType<typeof configureStore>;

  function createWrapper() {
    store = configureStore({
      reducer: {
        [api.reducerPath]: api.reducer,
      },
      middleware: (getDefaultMiddleware) =>
        getDefaultMiddleware().concat(api.middleware),
    });

    return function Wrapper({ children }: { children: ReactNode }) {
      return <Provider store={store}>{children}</Provider>;
    };
  }

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Initial State", () => {
    it("should not trigger for sessions without messages", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isGenerating).toBe(false);
      expect(result.current.generatedTitle).toBeUndefined();
    });

    it("should not trigger when disabled", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "New Chat",
            enabled: false,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isGenerating).toBe(false);
    });
  });

  describe("Trigger Conditions", () => {
    it("should not trigger for sessions with custom names", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "My Custom Session",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.isGenerating).toBe(false);
    });

    it("should trigger for sessions with default 'New Chat' name", async () => {
      const mockGenerate = vi.fn().mockResolvedValue({
        data: { title: "Hello World Discussion", confidence: 0.95 },
      });

      const { useGenerateSessionTitleMutation } = await import("../api");
      vi.mocked(useGenerateSessionTitleMutation).mockReturnValue([
        mockGenerate,
        { isLoading: false, isSuccess: false, data: undefined },
      ] as ReturnType<typeof useGenerateSessionTitleMutation>);

      renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello, world!" }],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(mockGenerate).toHaveBeenCalled();
      });
    });

    it("should only trigger once per session", async () => {
      const mockGenerate = vi.fn().mockResolvedValue({
        data: { title: "Generated Title", confidence: 0.9 },
      });

      const { useGenerateSessionTitleMutation } = await import("../api");
      vi.mocked(useGenerateSessionTitleMutation).mockReturnValue([
        mockGenerate,
        {
          isLoading: false,
          isSuccess: true,
          data: { title: "Generated Title", confidence: 0.9 },
        },
      ] as ReturnType<typeof useGenerateSessionTitleMutation>);

      const { rerender } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      // Re-render with more messages
      rerender();

      // Should only have been called once
      expect(mockGenerate).toHaveBeenCalledTimes(1);
    });
  });

  describe("Title Generation", () => {
    it("should dispatch renameSession after successful generation", async () => {
      const mockGenerate = vi.fn().mockResolvedValue({
        data: { title: "AI Assistant Chat", confidence: 0.92 },
      });

      const { useGenerateSessionTitleMutation } = await import("../api");
      vi.mocked(useGenerateSessionTitleMutation).mockReturnValue([
        mockGenerate,
        {
          isLoading: false,
          isSuccess: true,
          data: { title: "AI Assistant Chat", confidence: 0.92 },
        },
      ] as ReturnType<typeof useGenerateSessionTitleMutation>);

      renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Help me with AI" }],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      await waitFor(() => {
        expect(mockDispatch).toHaveBeenCalled();
      });
    });

    it("should expose generated title", async () => {
      const { useGenerateSessionTitleMutation } = await import("../api");
      vi.mocked(useGenerateSessionTitleMutation).mockReturnValue([
        vi.fn().mockResolvedValue({
          data: { title: "Test Title", confidence: 0.9 },
        }),
        {
          isLoading: false,
          isSuccess: true,
          data: { title: "Test Title", confidence: 0.9 },
        },
      ] as ReturnType<typeof useGenerateSessionTitleMutation>);

      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Test message" }],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.generatedTitle).toBe("Test Title");
    });
  });

  describe("Default Name Detection", () => {
    it("should recognize 'New Chat' as default name", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "New Chat",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });

    it("should recognize 'Untitled Session' as default name", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "Untitled Session",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.hasDefaultName).toBe(true);
    });

    it("should recognize custom names as non-default", () => {
      const { result } = renderHook(
        () =>
          useSessionAutoName({
            sessionId: "session-123",
            messages: [{ role: "user", content: "Hello" }],
            currentName: "My Project Discussion",
            enabled: true,
          }),
        { wrapper: createWrapper() },
      );

      expect(result.current.hasDefaultName).toBe(false);
    });
  });
});

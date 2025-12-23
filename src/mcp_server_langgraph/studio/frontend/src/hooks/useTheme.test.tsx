/**
 * useTheme Hook Tests
 *
 * Tests for the theme management hook that applies dark/light mode
 * to the document and respects user preferences.
 */

import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { useTheme } from "./useTheme";
import uiReducer from "../store/slices/uiSlice";
import type { ReactNode } from "react";

// Create test store
const createTestStore = (theme: "light" | "dark" | "system" = "dark") =>
  configureStore({
    reducer: { ui: uiReducer },
    preloadedState: {
      ui: {
        sidebarOpen: true,
        sidebarCollapsed: false,
        theme,
        isLoading: false,
        activeView: "workflows" as const,
        notifications: [],
      },
    },
  });

// Wrapper component for hooks
const createWrapper =
  (store: ReturnType<typeof createTestStore>) =>
  ({ children }: { children: ReactNode }) => (
    <Provider store={store}>{children}</Provider>
  );

describe("useTheme", () => {
  // Mock matchMedia for system preference detection
  const mockMatchMedia = vi.fn();

  beforeEach(() => {
    // Clear document classes
    document.documentElement.classList.remove("dark", "light");

    // Mock matchMedia
    mockMatchMedia.mockReturnValue({
      matches: false, // Default to light system preference
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
    window.matchMedia = mockMatchMedia;

    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    document.documentElement.classList.remove("dark", "light");
    vi.clearAllMocks();
  });

  describe("dark theme", () => {
    it("should apply dark class to document when theme is dark", () => {
      const store = createTestStore("dark");
      renderHook(() => useTheme(), { wrapper: createWrapper(store) });

      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should return isDark as true when theme is dark", () => {
      const store = createTestStore("dark");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isDark).toBe(true);
    });
  });

  describe("light theme", () => {
    it("should remove dark class when theme is light", () => {
      // Start with dark class
      document.documentElement.classList.add("dark");

      const store = createTestStore("light");
      renderHook(() => useTheme(), { wrapper: createWrapper(store) });

      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });

    it("should return isDark as false when theme is light", () => {
      const store = createTestStore("light");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      expect(result.current.isDark).toBe(false);
    });
  });

  describe("system theme", () => {
    it("should apply dark class when system prefers dark", () => {
      mockMatchMedia.mockReturnValue({
        matches: true, // System prefers dark
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      });

      const store = createTestStore("system");
      renderHook(() => useTheme(), { wrapper: createWrapper(store) });

      expect(document.documentElement.classList.contains("dark")).toBe(true);
    });

    it("should remove dark class when system prefers light", () => {
      mockMatchMedia.mockReturnValue({
        matches: false, // System prefers light
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      });

      const store = createTestStore("system");
      renderHook(() => useTheme(), { wrapper: createWrapper(store) });

      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  describe("setTheme action", () => {
    it("should provide setTheme function", () => {
      const store = createTestStore("dark");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      expect(typeof result.current.setTheme).toBe("function");
    });

    it("should update theme when setTheme is called", () => {
      const store = createTestStore("dark");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.setTheme("light");
      });

      expect(result.current.theme).toBe("light");
      expect(document.documentElement.classList.contains("dark")).toBe(false);
    });
  });

  describe("toggleTheme action", () => {
    it("should toggle from dark to light", () => {
      const store = createTestStore("dark");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("light");
    });

    it("should toggle from light to dark", () => {
      const store = createTestStore("light");
      const { result } = renderHook(() => useTheme(), {
        wrapper: createWrapper(store),
      });

      act(() => {
        result.current.toggleTheme();
      });

      expect(result.current.theme).toBe("dark");
    });
  });
});

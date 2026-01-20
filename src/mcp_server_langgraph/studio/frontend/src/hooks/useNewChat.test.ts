/**
 * useNewChat Tests
 *
 * TDD tests for the new chat hook that creates a session
 * and navigates to it.
 *
 * Uses MSW for realistic API mocking.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore, type Middleware } from "@reduxjs/toolkit";
import { http, HttpResponse } from "msw";
import React from "react";
import { useNewChat } from "./useNewChat";
import sessionReducer from "../store/slices/sessionSlice";
import { server } from "../mocks/server";
import { TelemetryProvider } from "../contexts/TelemetryContext";

// =============================================================================
// Mocks
// =============================================================================

// Mock react-router's useNavigate and useRevalidator
const mockNavigate = vi.fn();
const mockRevalidate = vi.fn();
vi.mock("react-router", () => ({
  useNavigate: () => mockNavigate,
  useRevalidator: () => ({ revalidate: mockRevalidate }),
}));

// =============================================================================
// Test Setup
// =============================================================================

const createTestStore = () => {
  // Create a middleware that silences the RTK warnings
  const silentMiddleware: Middleware = () => (next) => (action) => {
    return next(action);
  };

  return configureStore({
    reducer: {
      session: sessionReducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware({
        serializableCheck: false,
      }).concat(silentMiddleware),
  });
};

const createWrapper = (store: ReturnType<typeof createTestStore>) => {
  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      TelemetryProvider,
      null,
      React.createElement(Provider, { store }, children),
    );
  };
};

// =============================================================================
// Tests
// =============================================================================

describe("useNewChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Session Creation", () => {
    it("should create a new session when createNewChat is called", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Verify navigation happened (session was created)
      expect(mockNavigate).toHaveBeenCalled();
      // Navigation path should start with /studio/chat/
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringMatching(/^\/studio\/chat\/session-/),
      );
    });

    it("should navigate to the new session after creation", async () => {
      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Verify navigation happened with a session ID
      expect(mockNavigate).toHaveBeenCalledTimes(1);
      const navigatePath = mockNavigate.mock.calls[0][0];
      expect(navigatePath).toMatch(/^\/studio\/chat\/session-[a-f0-9]+$/);
    });

    it("should accept a custom session name", async () => {
      // Override handler to capture the request body
      let capturedName: string | undefined;
      server.use(
        http.post("/api/v1/sessions", async ({ request }) => {
          const body = (await request.json()) as { name?: string };
          capturedName = body.name;
          return HttpResponse.json(
            {
              id: "session-custom",
              name: body.name,
              status: "active",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            { status: 201 },
          );
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat({ name: "My Project Chat" });
      });

      // Verify custom name was passed
      expect(capturedName).toBe("My Project Chat");
    });

    it("should return loading state during creation", async () => {
      // Use a delayed handler
      server.use(
        http.post("/api/v1/sessions", async () => {
          await new Promise((resolve) => setTimeout(resolve, 100));
          return HttpResponse.json(
            {
              id: "session-delayed",
              name: "New Chat",
              status: "active",
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
            },
            { status: 201 },
          );
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      // Start creation but don't await
      let createPromise: Promise<void>;
      act(() => {
        createPromise = result.current.createNewChat();
      });

      // Check loading state immediately
      expect(result.current.isCreating).toBe(true);

      // Wait for completion
      await act(async () => {
        await createPromise;
      });

      // After completion, loading should be false
      expect(result.current.isCreating).toBe(false);
    });

    it("should handle API errors gracefully", async () => {
      // Override handler to return an error
      server.use(
        http.post("/api/v1/sessions", () => {
          return HttpResponse.json(
            { detail: "Failed to create session" },
            { status: 500 },
          );
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Should have an error
      expect(result.current.error).toBe("Failed to create session");

      // Should NOT navigate on error
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should handle network errors", async () => {
      // Override handler to simulate network error
      server.use(
        http.post("/api/v1/sessions", () => {
          return HttpResponse.error();
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Should have an error
      expect(result.current.error).toBeTruthy();

      // Should NOT navigate on error
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it("should clear error when creating a new chat again", async () => {
      // First call fails
      server.use(
        http.post("/api/v1/sessions", () => {
          return HttpResponse.json(
            { detail: "First failure" },
            { status: 500 },
          );
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      expect(result.current.error).toBe("First failure");

      // Reset to success handler
      server.resetHandlers();

      await act(async () => {
        await result.current.createNewChat();
      });

      // Error should be cleared
      expect(result.current.error).toBeNull();
    });
  });

  describe("Custom Navigation Base", () => {
    it("should use custom base path if provided", async () => {
      const store = createTestStore();
      const { result } = renderHook(
        () => useNewChat({ basePath: "/studio/chat" }),
        {
          wrapper: createWrapper(store),
        },
      );

      await act(async () => {
        await result.current.createNewChat();
      });

      // Verify navigation used custom base path
      expect(mockNavigate).toHaveBeenCalledWith(
        expect.stringMatching(/^\/studio\/chat\/session-/),
      );
    });
  });

  describe("Error handling edge cases", () => {
    it("should handle non-Error objects thrown during API call", async () => {
      // Override handler to throw a non-Error object
      server.use(
        http.post("/api/v1/sessions", () => {
          throw "string-error"; // Throwing a string instead of Error
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Should have fallback error message
      expect(result.current.error).toBe("Failed to create session");
    });

    it("should handle API response without detail field", async () => {
      server.use(
        http.post("/api/v1/sessions", () => {
          return HttpResponse.json(
            { message: "Something went wrong" }, // No 'detail' field
            { status: 500 },
          );
        }),
      );

      const store = createTestStore();
      const { result } = renderHook(() => useNewChat(), {
        wrapper: createWrapper(store),
      });

      await act(async () => {
        await result.current.createNewChat();
      });

      // Should use fallback error message since no 'detail'
      expect(result.current.error).toBe("Failed to create session");
    });
  });
});

/**
 * OAuth2CallbackPage Tests
 *
 * TDD tests for the OAuth2 callback handler page.
 * Tests cover:
 * - Extracting code and state from URL
 * - Calling callback API
 * - Success state with redirect
 * - Error handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { OAuth2CallbackPage } from "./OAuth2CallbackPage";

// Create a minimal store for testing
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

const renderWithRouter = async (initialPath: string) => {
  const store = createTestStore();
  let result: ReturnType<typeof render>;
  await act(async () => {
    result = render(
      <Provider store={store}>
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[initialPath]}
        >
          <Routes>
            <Route path="/oauth2/callback" element={<OAuth2CallbackPage />} />
            <Route
              path="/studio/connections"
              element={<div>Connections Page</div>}
            />
          </Routes>
        </MemoryRouter>
      </Provider>,
    );
  });
  return result!;
};

describe("OAuth2CallbackPage", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    // CRITICAL: Reset window.opener BEFORE rendering to ensure isPopup = false
    Object.defineProperty(window, "opener", {
      value: null,
      writable: true,
      configurable: true,
    });
    // Reset fetch to a no-op to prevent test bleeding
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    global.fetch = originalFetch;
  });

  describe("URL Parameter Extraction", () => {
    it("should show loading state initially", async () => {
      global.fetch = vi.fn().mockImplementation(
        () =>
          new Promise((resolve) => {
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () =>
                    Promise.resolve({
                      success: true,
                      connection_id: "conn-123",
                    }),
                }),
              1000,
            );
          }),
      );

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      expect(screen.getByText(/processing/i)).toBeInTheDocument();
    });

    it("should show error when code is missing", async () => {
      await renderWithRouter("/oauth2/callback?state=test-state");

      await waitFor(() => {
        expect(
          screen.getByText(/missing authorization code/i),
        ).toBeInTheDocument();
      });
    });

    it("should show error when state is missing", async () => {
      await renderWithRouter("/oauth2/callback?code=test-code");

      await waitFor(() => {
        expect(
          screen.getByText(/missing state parameter/i),
        ).toBeInTheDocument();
      });
    });

    it("should show error when callback contains error parameter", async () => {
      await renderWithRouter(
        "/oauth2/callback?error=access_denied&error_description=User%20denied%20access",
      );

      await waitFor(() => {
        expect(screen.getByText(/access_denied/i)).toBeInTheDocument();
      });
    });
  });

  describe("API Callback", () => {
    it("should call API with code and state", async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });
      global.fetch = mockFetch;

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Verify the call was made to the correct endpoint with correct method and body
      const callArgs = mockFetch.mock.calls[0];
      expect(callArgs[0]).toBe("/api/v1/connections/oauth/callback");
      expect(callArgs[1].method).toBe("POST");
      const body = JSON.parse(callArgs[1].body);
      expect(body.code).toBe("test-code");
      expect(body.state).toBe("test-state");
    });

    it("should show success message on successful callback", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(
          screen.getByText(/authorization successful/i),
        ).toBeInTheDocument();
      });
    });

    it("should display connection ID on success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(screen.getByText(/conn-123/)).toBeInTheDocument();
      });
    });

    it("should show redirecting message after success", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(screen.getByText(/redirecting/i)).toBeInTheDocument();
      });
    });
  });

  describe("Error Handling", () => {
    it("should show error when API call fails", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Invalid state parameter" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=invalid-state",
      );

      await waitFor(() => {
        // Use getByRole to get the specific heading element
        expect(
          screen.getByRole("heading", { name: /authorization failed/i }),
        ).toBeInTheDocument();
      });
    });

    it("should display API error detail", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Invalid state parameter" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=invalid-state",
      );

      await waitFor(() => {
        expect(screen.getByText(/Invalid state parameter/)).toBeInTheDocument();
      });
    });

    it("should show error when API is unreachable", async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error("Network error"));

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(screen.getByText(/connection error/i)).toBeInTheDocument();
      });
    });

    it("should have retry button on error", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Server error" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /try again/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have back to connections link on error", async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: "Server error" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(
          screen.getByRole("link", { name: /connections/i }),
        ).toBeInTheDocument();
      });
    });
  });

  describe("Popup Mode (ADR-0102)", () => {
    let mockPostMessage: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      mockPostMessage = vi.fn();
      // window.opener is already reset to null by global beforeEach
    });

    it("should detect popup mode when window.opener exists", async () => {
      // Mock window.opener to simulate popup context
      Object.defineProperty(window, "opener", {
        value: { postMessage: mockPostMessage },
        writable: true,
        configurable: true,
      });
      const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      // Wait for postMessage to be called
      await waitFor(() => {
        expect(mockPostMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: "oauth-callback",
            success: true,
            connectionId: "conn-123",
          }),
          window.location.origin,
        );
      });

      closeSpy.mockRestore();
    });

    it("should post error message to opener on OAuth failure in popup", async () => {
      Object.defineProperty(window, "opener", {
        value: { postMessage: mockPostMessage },
        writable: true,
        configurable: true,
      });
      const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: () => Promise.resolve({ detail: "Invalid state" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=invalid-state",
      );

      await waitFor(() => {
        expect(mockPostMessage).toHaveBeenCalledWith(
          expect.objectContaining({
            type: "oauth-callback",
            success: false,
            error: expect.stringContaining("Invalid state"),
          }),
          window.location.origin,
        );
      });

      closeSpy.mockRestore();
    });

    it("should close popup after sending message on success", async () => {
      Object.defineProperty(window, "opener", {
        value: { postMessage: mockPostMessage },
        writable: true,
        configurable: true,
      });
      const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      // Wait for window.close to be called
      await waitFor(
        () => {
          expect(closeSpy).toHaveBeenCalled();
        },
        { timeout: 2000 },
      );

      closeSpy.mockRestore();
    });

    it("should not post message when not in popup mode", async () => {
      // Ensure window.opener is null (not in popup)
      Object.defineProperty(window, "opener", {
        value: null,
        writable: true,
        configurable: true,
      });

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        expect(
          screen.getByText(/authorization successful/i),
        ).toBeInTheDocument();
      });

      // postMessage should not be called (window.opener is null)
      expect(mockPostMessage).not.toHaveBeenCalled();
    });

    it("should show popup-specific message when in popup mode", async () => {
      Object.defineProperty(window, "opener", {
        value: { postMessage: mockPostMessage },
        writable: true,
        configurable: true,
      });
      const closeSpy = vi.spyOn(window, "close").mockImplementation(() => {});

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({ success: true, connection_id: "conn-123" }),
      });

      await renderWithRouter(
        "/oauth2/callback?code=test-code&state=test-state",
      );

      await waitFor(() => {
        // Should show closing message in popup mode
        expect(
          screen.getByText(/closing|window will close/i),
        ).toBeInTheDocument();
      });

      closeSpy.mockRestore();
    });
  });
});

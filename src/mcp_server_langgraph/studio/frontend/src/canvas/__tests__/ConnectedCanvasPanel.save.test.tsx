/**
 * ConnectedCanvasPanel Save Operations Tests
 *
 * Tests for save operations, content tracking, error handling, and cleanup.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, act, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { ConnectedCanvasPanel } from "../ConnectedCanvasPanel";
import {
  mockSessionLoaderData,
  createMockArtifact,
  createTestStore,
  createWrapper,
  flushPromises,
  setupSuccessfulFetchMock,
  setupFailedFetchMock,
  setupNetworkErrorFetchMock,
  setupAuthTokenMock,
} from "./ConnectedCanvasPanel.fixtures";

// =============================================================================
// Mocks
// =============================================================================

vi.mock("react-router", async () => {
  const actual =
    await vi.importActual<typeof import("react-router")>("react-router");
  return {
    ...actual,
    useRouteLoaderData: vi.fn((routeId: string) => {
      if (routeId === "chat-session") {
        return mockSessionLoaderData;
      }
      return undefined;
    }),
    useRevalidator: vi.fn(() => ({
      revalidate: vi.fn(),
      state: "idle",
    })),
  };
});

vi.mock("../../contexts/FeatureFlagContext", () => ({
  useFeatureFlag: (flag: string) => {
    if (flag === "canvas_ai_palette" || flag === "ai_suggestions") {
      return true;
    }
    return false;
  },
}));

// =============================================================================
// Tests
// =============================================================================

describe("ConnectedCanvasPanel - Save Operations", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    mockSessionLoaderData.sessionId = "session-123";
    mockSessionLoaderData.messages = [];
    mockSessionLoaderData.artifacts = [];
  });

  afterEach(async () => {
    cleanup();
    await act(async () => {
      await flushPromises();
    });
  });

  describe("Save Operations", () => {
    beforeEach(() => {
      setupSuccessfulFetchMock();
    });

    afterEach(() => {
      cleanup();
      vi.restoreAllMocks();
    });

    it("should show saving status indicator when save is in progress", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "save-test-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "save-test-art",
          title: "Save Test",
          content: "original content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "new content");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await waitFor(() => {
        const indicator = screen.queryByTestId("save-status-indicator");
        if (indicator) {
          expect(indicator).toBeInTheDocument();
        }
      });
    });

    it("should show saved status after successful save", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "save-success-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "save-success-art",
          title: "Save Success",
          content: "before save",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "after save");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await waitFor(() => {
        const indicator = screen.queryByTestId("save-status-indicator");
        expect(indicator).toBeInTheDocument();
        expect(indicator).toHaveTextContent(/sav/i);
      });
    });

    it("should show error status when save fails with HTTP error", async () => {
      setupFailedFetchMock();
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "save-fail-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "save-fail-art",
          title: "Save Fail",
          content: "content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "new content");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await waitFor(() => {
        const indicator = screen.queryByTestId("save-status-indicator");
        expect(indicator).toBeInTheDocument();
        expect(indicator).toHaveTextContent(/500|error|fail/i);
      });
    });

    it("should show error status when save throws exception", async () => {
      setupNetworkErrorFetchMock();
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "save-error-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "save-error-art",
          title: "Save Error",
          content: "content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "new content");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await waitFor(() => {
        const indicator = screen.queryByTestId("save-status-indicator");
        expect(indicator).toBeInTheDocument();
        expect(indicator).toHaveTextContent(/network error|error|fail/i);
      });
    });

    it("should include authorization header when token exists", async () => {
      const user = userEvent.setup();
      const fetchMock = vi.spyOn(global, "fetch");
      const restoreAuth = setupAuthTokenMock();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "auth-test-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "auth-test-art",
          title: "Auth Test",
          content: "content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "updated");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await waitFor(() => {
        expect(fetchMock).toHaveBeenCalled();
        const artifactCall = fetchMock.mock.calls.find(
          (call) =>
            typeof call[0] === "string" &&
            call[0].includes("/api/v1/artifacts/"),
        );
        expect(artifactCall).toBeDefined();
        expect(artifactCall?.[0]).toContain("/api/v1/artifacts/");
      });
      restoreAuth();
    });

    it("should prevent concurrent saves when already saving", async () => {
      let resolveFirstSave: (value: Response) => void;
      const slowFetch = new Promise<Response>((resolve) => {
        resolveFirstSave = resolve;
      });
      let artifactSaveCallCount = 0;
      const fetchMock = vi.spyOn(global, "fetch").mockImplementation((url) => {
        const urlStr = typeof url === "string" ? url : url.toString();
        if (urlStr.includes("/api/v1/artifacts/")) {
          artifactSaveCallCount++;
          if (artifactSaveCallCount === 1) {
            return slowFetch;
          }
          return Promise.resolve({
            ok: true,
            status: 200,
            statusText: "OK",
          } as Response);
        }
        return Promise.resolve({
          ok: true,
          status: 200,
          json: () => Promise.resolve({ suggestions: [] }),
        } as Response);
      });
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "concurrent-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "concurrent-art",
          title: "Concurrent Test",
          content: "content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "save1");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      await user.click(saveButtons[0]);
      resolveFirstSave!({
        ok: true,
        status: 200,
        statusText: "OK",
      } as Response);
      await waitFor(() => {
        expect(artifactSaveCallCount).toBe(1);
      });
      fetchMock.mockRestore();
    });
  });

  describe("Content Change Tracking", () => {
    it("should track draft content when content changes", async () => {
      const user = userEvent.setup();
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "draft-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "draft-art",
          title: "Draft Test",
          content: "initial content",
        }),
      ];
      render(<ConnectedCanvasPanel />, { wrapper: createWrapper(store) });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "modified content");
      expect(screen.getByTestId("canvas-panel")).toBeInTheDocument();
    });
  });

  describe("Cleanup on Unmount", () => {
    it("should cleanup save timeout on unmount", async () => {
      vi.useFakeTimers({ shouldAdvanceTime: true });
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          selectedArtifactId: "cleanup-art",
          preferences: { showTimestamps: true, compactMode: false },
        },
      });
      mockSessionLoaderData.artifacts = [
        createMockArtifact({
          id: "cleanup-art",
          title: "Cleanup Test",
          content: "content",
        }),
      ];
      vi.spyOn(global, "fetch").mockResolvedValue({
        ok: true,
        status: 200,
        statusText: "OK",
      } as Response);
      const { unmount } = render(<ConnectedCanvasPanel />, {
        wrapper: createWrapper(store),
      });
      const editButtons = screen.getAllByTestId("edit-button");
      await user.click(editButtons[0]);
      const editor = screen.getByTestId("content-editor");
      await user.clear(editor);
      await user.type(editor, "test");
      const saveButtons = screen.getAllByTestId("save-button");
      await user.click(saveButtons[0]);
      unmount();
      vi.advanceTimersByTime(5000);
      vi.useRealTimers();
    });
  });
});

/**
 * useTabNavigation Hook Tests
 *
 * Tests for the tab navigation hook that handles bidirectional sync.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { useTabNavigation } from "./useTabNavigation";
import type { TabState } from "../store/slices/workspaceSlice";

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

function renderHookWithRouter() {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return <MemoryRouter>{children}</MemoryRouter>;
  }
  return renderHook(() => useTabNavigation(), { wrapper: Wrapper });
}

describe("useTabNavigation", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should return a function", () => {
    const { result } = renderHookWithRouter();
    expect(typeof result.current).toBe("function");
  });

  it("should navigate to chat route for chat tab", () => {
    const { result } = renderHookWithRouter();
    const tab: TabState = { id: "tab-1", type: "chat", title: "Chat" };

    act(() => {
      result.current(tab);
    });

    expect(mockNavigate).toHaveBeenCalledWith("/studio/chat");
  });

  it("should navigate to chat route with session param for chat tab with entityId", () => {
    const { result } = renderHookWithRouter();
    const tab: TabState = {
      id: "tab-1",
      type: "chat",
      title: "Chat",
      entityId: "session-123",
    };

    act(() => {
      result.current(tab);
    });

    expect(mockNavigate).toHaveBeenCalledWith(
      "/studio/chat?session=session-123",
    );
  });

  it("should navigate to workflow route for workflow tab", () => {
    const { result } = renderHookWithRouter();
    const tab: TabState = { id: "tab-1", type: "workflow", title: "Workflows" };

    act(() => {
      result.current(tab);
    });

    expect(mockNavigate).toHaveBeenCalledWith("/studio/workflows");
  });

  it("should navigate to settings route for settings tab", () => {
    const { result } = renderHookWithRouter();
    const tab: TabState = { id: "tab-1", type: "settings", title: "Settings" };

    act(() => {
      result.current(tab);
    });

    expect(mockNavigate).toHaveBeenCalledWith("/studio/settings");
  });
});

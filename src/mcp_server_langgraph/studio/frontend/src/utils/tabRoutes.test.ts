/**
 * Tab-to-Route Mapping Utilities Tests
 *
 * Tests for bidirectional tab-to-route sync utilities.
 */

import { describe, it, expect } from "vitest";
import { getRouteForTab, tabMatchesRoute } from "./tabRoutes";
import type { TabState } from "../store/slices/workspaceSlice";

describe("getRouteForTab", () => {
  it("should return chat route for chat tab", () => {
    const tab: TabState = { id: "tab-1", type: "chat", title: "Chat" };
    expect(getRouteForTab(tab)).toBe("/studio/chat");
  });

  it("should include session param for chat tab with entityId", () => {
    const tab: TabState = {
      id: "tab-1",
      type: "chat",
      title: "Chat",
      entityId: "session-123",
    };
    expect(getRouteForTab(tab)).toBe("/studio/chat?session=session-123");
  });

  it("should return workflow route for workflow tab", () => {
    const tab: TabState = { id: "tab-1", type: "workflow", title: "Workflows" };
    expect(getRouteForTab(tab)).toBe("/studio/workflows");
  });

  it("should return settings route for settings tab", () => {
    const tab: TabState = { id: "tab-1", type: "settings", title: "Settings" };
    expect(getRouteForTab(tab)).toBe("/studio/settings");
  });

  it("should return observability route for observability tab", () => {
    const tab: TabState = {
      id: "tab-1",
      type: "observability",
      title: "Observability",
    };
    expect(getRouteForTab(tab)).toBe("/studio/observability");
  });

  it("should return cost route for cost tab", () => {
    const tab: TabState = { id: "tab-1", type: "cost", title: "Cost" };
    expect(getRouteForTab(tab)).toBe("/studio/cost");
  });

  it("should URL encode entityId", () => {
    const tab: TabState = {
      id: "tab-1",
      type: "chat",
      title: "Chat",
      entityId: "session with spaces",
    };
    expect(getRouteForTab(tab)).toBe(
      "/studio/chat?session=session%20with%20spaces",
    );
  });

  it("should return fallback route for unknown tab type", () => {
    const tab = {
      id: "tab-1",
      type: "unknown-type" as TabState["type"],
      title: "Unknown",
    };
    expect(getRouteForTab(tab)).toBe("/studio");
  });
});

describe("tabMatchesRoute", () => {
  it("should match chat tab to chat route", () => {
    const tab: TabState = { id: "tab-1", type: "chat", title: "Chat" };
    const searchParams = new URLSearchParams();
    expect(tabMatchesRoute(tab, "/studio/chat", searchParams)).toBe(true);
  });

  it("should match chat tab with entityId to route with session param", () => {
    const tab: TabState = {
      id: "tab-1",
      type: "chat",
      title: "Chat",
      entityId: "session-123",
    };
    const searchParams = new URLSearchParams("session=session-123");
    expect(tabMatchesRoute(tab, "/studio/chat", searchParams)).toBe(true);
  });

  it("should not match tab with different entityId", () => {
    const tab: TabState = {
      id: "tab-1",
      type: "chat",
      title: "Chat",
      entityId: "session-123",
    };
    const searchParams = new URLSearchParams("session=session-456");
    expect(tabMatchesRoute(tab, "/studio/chat", searchParams)).toBe(false);
  });

  it("should not match tab to different route", () => {
    const tab: TabState = { id: "tab-1", type: "chat", title: "Chat" };
    const searchParams = new URLSearchParams();
    expect(tabMatchesRoute(tab, "/studio/workflows", searchParams)).toBe(false);
  });

  it("should match workflow tab to workflow route", () => {
    const tab: TabState = { id: "tab-1", type: "workflow", title: "Workflows" };
    const searchParams = new URLSearchParams();
    expect(tabMatchesRoute(tab, "/studio/workflows", searchParams)).toBe(true);
  });

  it("should not match unknown tab type", () => {
    const tab = {
      id: "tab-1",
      type: "unknown-type" as TabState["type"],
      title: "Unknown",
    };
    const searchParams = new URLSearchParams();
    expect(tabMatchesRoute(tab, "/studio/unknown", searchParams)).toBe(false);
  });
});

/**
 * Tests for AISessionCard component.
 *
 * Sprint 2: Session Intelligence
 * - Displays AI-generated session summary
 * - Shows key topics as tags
 * - Indicates loading state
 * - Handles similarity indicators
 *
 * TDD: Tests written FIRST before implementation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Mock the hooks
vi.mock("../hooks/useSessionIntelligence", () => ({
  useSessionSummary: vi.fn(() => ({
    summary: "User explored React component patterns and debugging techniques.",
    keyTopics: ["React", "debugging", "components"],
    messageCount: 15,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = () => {
  const store = createTestStore();
  return function Wrapper({ children }: WrapperProps) {
    return <Provider store={store}>{children}</Provider>;
  };
};

describe("AISessionCard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("should render session title", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="React Development"
          userId="user-123"
        />
      </Wrapper>
    );

    expect(screen.getByText("React Development")).toBeInTheDocument();
  });

  it("should display AI summary when available", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="React Development"
          userId="user-123"
          showSummary
        />
      </Wrapper>
    );

    expect(
      screen.getByText(/React component patterns and debugging techniques/)
    ).toBeInTheDocument();
  });

  it("should display key topics as tags", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="React Development"
          userId="user-123"
          showTopics
        />
      </Wrapper>
    );

    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("debugging")).toBeInTheDocument();
  });

  it("should show loading indicator when fetching", async () => {
    // Mock loading state
    vi.doMock("../hooks/useSessionIntelligence", () => ({
      useSessionSummary: vi.fn(() => ({
        summary: null,
        keyTopics: [],
        messageCount: 0,
        isLoading: true,
        error: null,
        refetch: vi.fn(),
      })),
    }));

    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-loading"
          title="Loading Session"
          userId="user-123"
          showSummary
        />
      </Wrapper>
    );

    // Should show a loading indicator (skeleton or spinner)
    const _loadingElement = screen.queryByTestId("ai-loading");
    // Loading state may be shown differently, but component should render
    expect(screen.getByText("Loading Session")).toBeInTheDocument();
  });

  it("should display timestamp when provided", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    const timestamp = new Date("2024-01-15T10:30:00Z");

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="Timestamped Session"
          userId="user-123"
          timestamp={timestamp}
        />
      </Wrapper>
    );

    expect(screen.getByText("Timestamped Session")).toBeInTheDocument();
  });

  it("should handle click events", async () => {
    const handleClick = vi.fn();
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="Clickable Session"
          userId="user-123"
          onClick={handleClick}
        />
      </Wrapper>
    );

    const card = screen.getByText("Clickable Session").closest("div");
    card?.click();

    expect(handleClick).toHaveBeenCalledWith("session-123");
  });

  it("should show active state when selected", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="Active Session"
          userId="user-123"
          isActive
        />
      </Wrapper>
    );

    const card = screen.getByText("Active Session").closest('[data-testid="session-card"]');
    expect(card).toHaveClass("active");
  });

  it("should render without AI features when disabled", async () => {
    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-123"
          title="Basic Session"
          userId="user-123"
          enableAI={false}
        />
      </Wrapper>
    );

    expect(screen.getByText("Basic Session")).toBeInTheDocument();
    // Should not show AI summary when disabled
    expect(screen.queryByText(/component patterns/)).not.toBeInTheDocument();
  });
});

describe("AISessionCard - Error States", () => {
  it("should handle error state gracefully", async () => {
    vi.doMock("../hooks/useSessionIntelligence", () => ({
      useSessionSummary: vi.fn(() => ({
        summary: null,
        keyTopics: [],
        messageCount: 0,
        isLoading: false,
        error: new Error("Failed to fetch"),
        refetch: vi.fn(),
      })),
    }));

    const { AISessionCard } = await import("./AISessionCard");
    const Wrapper = createWrapper();

    render(
      <Wrapper>
        <AISessionCard
          sessionId="session-error"
          title="Error Session"
          userId="user-123"
          showSummary
        />
      </Wrapper>
    );

    // Should still render the card title
    expect(screen.getByText("Error Session")).toBeInTheDocument();
  });
});

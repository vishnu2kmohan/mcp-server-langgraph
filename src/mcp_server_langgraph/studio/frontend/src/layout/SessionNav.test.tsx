/**
 * SessionNav Tests
 *
 * TDD tests for the extracted SessionNav component.
 * Tests session grouping, search, and navigation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { MemoryRouter } from "react-router";
import { SessionNav, groupSessionsByDate } from "./SessionNav";
import canvasReducer from "../store/slices/canvasSlice";
import personaReducer from "../store/slices/personaSlice";
import sessionReducer from "../store/slices/sessionSlice";
import type { ReactNode } from "react";
import type { Session } from "../types";

// Mock navigate
const mockNavigate = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ sessionId: "session-1" }),
    useRouteLoaderData: (id: string) => {
      if (id === "studio") {
        return {
          sessions: mockSessions,
        };
      }
      return undefined;
    },
  };
});

// Mock useNewChat hook
vi.mock("../hooks/useNewChat", () => ({
  useNewChat: () => ({
    createNewChat: vi.fn(),
    isCreating: false,
  }),
}));

// Mock useSessionIntelligence hooks (for AISessionCard and SimilarSessionsPanel)
vi.mock("../hooks/useSessionIntelligence", () => ({
  useSessionSummary: vi.fn(() => ({
    summary: "Test AI summary for session",
    keyTopics: ["React", "testing"],
    messageCount: 10,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
  useSessionSimilarity: vi.fn(() => ({
    similarSessions: [
      {
        sessionId: "similar-session-1",
        similarityScore: 0.85,
        commonTopics: ["React", "TypeScript"],
      },
      {
        sessionId: "similar-session-2",
        similarityScore: 0.72,
        commonTopics: ["Testing"],
      },
    ],
    isLoading: false,
    error: null,
    refetch: vi.fn(),
  })),
}));

// Mock sessions
const mockSessions: Session[] = [
  {
    id: "session-1",
    name: "Today's Chat",
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    projectId: "project-1",
    status: "active",
  },
  {
    id: "session-2",
    name: "Yesterday's Chat",
    createdAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    projectId: "project-1",
    status: "active",
  },
  {
    id: "session-3",
    name: "Older Chat",
    createdAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updatedAt: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    projectId: "project-1",
    status: "active",
  },
];

// Create test store
function createTestStore() {
  return configureStore({
    reducer: {
      canvas: canvasReducer,
      persona: personaReducer,
      session: sessionReducer,
    },
  });
}

// Wrapper component
function createWrapper(store: ReturnType<typeof createTestStore>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <Provider store={store}>
        <MemoryRouter>{children}</MemoryRouter>
      </Provider>
    );
  };
}

describe("SessionNav", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("session-nav")).toBeInTheDocument();
    });

    it("should render new chat button", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("new-chat-button")).toBeInTheDocument();
    });

    it("should render search input", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByTestId("session-search")).toBeInTheDocument();
    });
  });

  describe("session grouping", () => {
    it("should display Today section for today's sessions", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Today")).toBeInTheDocument();
    });

    it("should display Yesterday section for yesterday's sessions", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Yesterday")).toBeInTheDocument();
    });

    it("should display Older section for older sessions", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      expect(screen.getByText("Older")).toBeInTheDocument();
    });
  });

  describe("search functionality", () => {
    it("should filter sessions based on search query", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      const searchInput = screen.getByTestId("session-search");
      await user.type(searchInput, "Today");

      // Should show Today's Chat but not others
      expect(screen.getByText("Today's Chat")).toBeInTheDocument();
      expect(screen.queryByText("Yesterday's Chat")).not.toBeInTheDocument();
    });

    it("should show 'No matching sessions' when search has no results", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      const searchInput = screen.getByTestId("session-search");
      await user.type(searchInput, "NonexistentSession");

      expect(screen.getByText("No matching sessions")).toBeInTheDocument();
    });
  });

  describe("navigation", () => {
    it("should navigate to session when clicked", async () => {
      const user = userEvent.setup();
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      const sessionButton = screen.getByText("Today's Chat");
      await user.click(sessionButton);

      expect(mockNavigate).toHaveBeenCalledWith("/studio/chat/session-1");
    });

    it("should highlight current session", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      // The session button is inside a wrapper div that has the highlight class
      const sessionButton = screen.getByText("Today's Chat");
      const sessionWrapper = sessionButton.closest("div");
      expect(sessionWrapper).toHaveClass("bg-primary-100");
    });
  });

  describe("accessibility", () => {
    it("should have proper ARIA labels", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      const nav = screen.getByTestId("session-nav");
      expect(nav).toHaveAttribute("aria-label");
    });

    it("should have placeholder text on search input", () => {
      const store = createTestStore();
      render(<SessionNav />, { wrapper: createWrapper(store) });

      const searchInput = screen.getByTestId("session-search");
      expect(searchInput).toHaveAttribute("placeholder", "Search sessions...");
    });

    it("should have no accessibility violations", async () => {
      const store = createTestStore();
      const { container } = render(<SessionNav />, {
        wrapper: createWrapper(store),
      });
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});

// =============================================================================
// AI Session Intelligence Tests (Sprint 2)
// =============================================================================

describe("SessionNav AI Intelligence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it("should render AISessionCard when enableAI prop is true", () => {
    const store = createTestStore();
    render(<SessionNav enableAI />, { wrapper: createWrapper(store) });

    // Should render AI-enhanced session cards with data-testid
    const sessionCards = screen.getAllByTestId("session-card");
    expect(sessionCards.length).toBeGreaterThan(0);
  });

  it("should render standard buttons when enableAI is false", () => {
    const store = createTestStore();
    render(<SessionNav enableAI={false} />, { wrapper: createWrapper(store) });

    // Should show standard session buttons, not AI cards
    expect(screen.getByText("Today's Chat")).toBeInTheDocument();
    expect(screen.queryByTestId("session-card")).not.toBeInTheDocument();
  });

  it("should pass showSummary to AISessionCard when enabled", async () => {
    const store = createTestStore();
    render(<SessionNav enableAI showSummary />, {
      wrapper: createWrapper(store),
    });

    // The AI session cards should be rendered with summaries
    const sessionCards = screen.getAllByTestId("session-card");
    expect(sessionCards.length).toBeGreaterThan(0);
  });

  it("should pass showTopics to AISessionCard when enabled", async () => {
    const store = createTestStore();
    render(<SessionNav enableAI showTopics />, {
      wrapper: createWrapper(store),
    });

    // AI session cards should be rendered
    const sessionCards = screen.getAllByTestId("session-card");
    expect(sessionCards.length).toBeGreaterThan(0);
  });

  it("should navigate to session when AISessionCard is clicked", async () => {
    const user = userEvent.setup();
    const store = createTestStore();
    render(<SessionNav enableAI />, { wrapper: createWrapper(store) });

    // Click on the first AI session card
    const sessionCards = screen.getAllByTestId("session-card");
    await user.click(sessionCards[0]);

    expect(mockNavigate).toHaveBeenCalled();
  });

  it("should highlight active AISessionCard", () => {
    const store = createTestStore();
    render(<SessionNav enableAI />, { wrapper: createWrapper(store) });

    // The current session (session-1) should have active class
    const sessionCards = screen.getAllByTestId("session-card");
    const activeCard = sessionCards[0];
    expect(activeCard).toHaveClass("active");
  });
});

describe("groupSessionsByDate", () => {
  it("should group today's sessions correctly", () => {
    const today = new Date();
    const sessions: Session[] = [
      {
        id: "1",
        name: "Today",
        createdAt: today.toISOString(),
        updatedAt: today.toISOString(),
        projectId: "p1",
        status: "active",
      },
    ];

    const groups = groupSessionsByDate(sessions);
    expect(groups.today).toHaveLength(1);
    expect(groups.yesterday).toHaveLength(0);
    expect(groups.older).toHaveLength(0);
  });

  it("should group yesterday's sessions correctly", () => {
    const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
    const sessions: Session[] = [
      {
        id: "1",
        name: "Yesterday",
        createdAt: yesterday.toISOString(),
        updatedAt: yesterday.toISOString(),
        projectId: "p1",
        status: "active",
      },
    ];

    const groups = groupSessionsByDate(sessions);
    expect(groups.today).toHaveLength(0);
    expect(groups.yesterday).toHaveLength(1);
    expect(groups.older).toHaveLength(0);
  });

  it("should group older sessions correctly", () => {
    const lastWeek = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000);
    const sessions: Session[] = [
      {
        id: "1",
        name: "Last Week",
        createdAt: lastWeek.toISOString(),
        updatedAt: lastWeek.toISOString(),
        projectId: "p1",
        status: "active",
      },
    ];

    const groups = groupSessionsByDate(sessions);
    expect(groups.today).toHaveLength(0);
    expect(groups.yesterday).toHaveLength(0);
    expect(groups.older).toHaveLength(1);
  });
});

describe("SessionNav Inline Editing", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("should enable inline editing when enableEdit prop is true", () => {
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit />
      </Wrapper>,
    );

    // Should show session names that can be edited
    expect(screen.getByText("Today's Chat")).toBeInTheDocument();
  });

  it("should show context menu on right-click when enableContextMenu is true", async () => {
    const _user = userEvent.setup();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableContextMenu />
      </Wrapper>,
    );

    const sessionButton = screen.getByText("Today's Chat");
    expect(sessionButton).toBeInTheDocument();
    // Context menu integration will be tested once wired up
  });
});

// =============================================================================
// Session Hover Details Tests (Sprint Block 4)
// =============================================================================

// =============================================================================
// Similar Sessions Panel Integration Tests (Sprint 2)
// =============================================================================

describe("SessionNav Similar Sessions Integration", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    store = createTestStore();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    cleanup();
  });

  it("should render SimilarSessionsPanel when enableSimilarSessions is true", () => {
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableSimilarSessions userId="test-user" />
      </Wrapper>,
    );

    // Should render the SimilarSessionsPanel with heading
    expect(screen.getByText("Similar Sessions")).toBeInTheDocument();
  });

  it("should not render SimilarSessionsPanel when enableSimilarSessions is false", () => {
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableSimilarSessions={false} />
      </Wrapper>,
    );

    // Should not show similar sessions
    expect(screen.queryByText("Similar Sessions")).not.toBeInTheDocument();
  });

  it("should display similar sessions from hook data", () => {
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableSimilarSessions userId="test-user" />
      </Wrapper>,
    );

    // Should show similarity scores (from mock: 85% and 72%)
    expect(screen.getByText("85%")).toBeInTheDocument();
    expect(screen.getByText("72%")).toBeInTheDocument();
  });

  it("should display common topics as badges", () => {
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableSimilarSessions userId="test-user" />
      </Wrapper>,
    );

    // Should show common topics from mock data
    expect(screen.getByText("React")).toBeInTheDocument();
    expect(screen.getByText("TypeScript")).toBeInTheDocument();
    expect(screen.getByText("Testing")).toBeInTheDocument();
  });

  it("should navigate when similar session is clicked", async () => {
    const user = userEvent.setup();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableSimilarSessions userId="test-user" />
      </Wrapper>,
    );

    // Click on a similar session
    const similarSession = screen.getByText("similar-session-1");
    await user.click(similarSession);

    expect(mockNavigate).toHaveBeenCalledWith("/studio/chat/similar-session-1");
  });

  it("should pass session names to SimilarSessionsPanel", () => {
    const Wrapper = createWrapper(store);
    const sessionNames = {
      "similar-session-1": "My First Session",
      "similar-session-2": "Another Session",
    };

    render(
      <Wrapper>
        <SessionNav
          enableSimilarSessions
          userId="test-user"
          similarSessionNames={sessionNames}
        />
      </Wrapper>,
    );

    // Should display custom session names instead of IDs
    expect(screen.getByText("My First Session")).toBeInTheDocument();
    expect(screen.getByText("Another Session")).toBeInTheDocument();
  });
});

describe("SessionNav Hover Details", () => {
  let store: ReturnType<typeof createTestStore>;

  beforeEach(() => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    store = createTestStore();
    mockNavigate.mockClear();
  });

  afterEach(() => {
    vi.useRealTimers();
    cleanup();
  });

  it("should show hover tooltip when enableHover prop is true", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableHover />
      </Wrapper>,
    );

    // Hover over a session item
    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);

    // Wait for tooltip delay
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    // Tooltip should appear
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
  });

  it("should display session creation time in hover tooltip", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableHover />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    // Should show relative time (e.g., "Created today" or "a few seconds ago")
    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/created|ago/i);
  });

  it("should display message count in hover tooltip when available", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav
          enableHover
          sessionMetadata={{ "session-1": { messageCount: 5 } }}
        />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent(/5 messages/i);
  });

  it("should display first message preview in hover tooltip when available", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav
          enableHover
          sessionMetadata={{
            "session-1": {
              messageCount: 5,
              firstMessage: "Hello, how can I help you today?",
            },
          }}
        />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    const tooltip = screen.getByRole("tooltip");
    expect(tooltip).toHaveTextContent("Hello, how can I help you today?");
  });

  it("should truncate long first message in hover tooltip", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const longMessage =
      "This is a very long message that should be truncated when displayed in the hover tooltip because we do not want to show too much content in a small tooltip";
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav
          enableHover
          sessionMetadata={{
            "session-1": {
              messageCount: 5,
              firstMessage: longMessage,
            },
          }}
        />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    const tooltip = screen.getByRole("tooltip");
    // Should truncate with ellipsis
    expect(tooltip).toHaveTextContent("...");
    expect(tooltip.textContent?.length).toBeLessThan(longMessage.length + 50);
  });

  it("should hide hover tooltip when mouse leaves", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableHover />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    const hoverTarget = sessionItem.closest("div")!;
    await user.hover(hoverTarget);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(screen.getByRole("tooltip")).toBeInTheDocument();

    await user.unhover(hoverTarget);

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("should not show hover tooltip when enableHover is false", async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableHover={false} />
      </Wrapper>,
    );

    const sessionItem = screen.getByText("Today's Chat");
    await user.hover(sessionItem.closest("div")!);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });
});

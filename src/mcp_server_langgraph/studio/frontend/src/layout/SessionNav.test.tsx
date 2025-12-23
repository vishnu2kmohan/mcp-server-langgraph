/**
 * SessionNav Tests
 *
 * TDD tests for the extracted SessionNav component.
 * Tests session grouping, search, and navigation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
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

// Mock useSessionIntelligence hooks (for AISessionCard)
vi.mock("../hooks/useSessionIntelligence", () => ({
  useSessionSummary: vi.fn(() => ({
    summary: "Test AI summary for session",
    keyTopics: ["React", "testing"],
    messageCount: 10,
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
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    project_id: "project-1",
  },
  {
    id: "session-2",
    name: "Yesterday's Chat",
    created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
    project_id: "project-1",
  },
  {
    id: "session-3",
    name: "Older Chat",
    created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    updated_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
    project_id: "project-1",
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

      const sessionButton = screen.getByText("Today's Chat");
      expect(sessionButton).toHaveClass("bg-primary-100");
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
        created_at: today.toISOString(),
        updated_at: today.toISOString(),
        project_id: "p1",
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
        created_at: yesterday.toISOString(),
        updated_at: yesterday.toISOString(),
        project_id: "p1",
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
        created_at: lastWeek.toISOString(),
        updated_at: lastWeek.toISOString(),
        project_id: "p1",
      },
    ];

    const groups = groupSessionsByDate(sessions);
    expect(groups.today).toHaveLength(0);
    expect(groups.yesterday).toHaveLength(0);
    expect(groups.older).toHaveLength(1);
  });
});

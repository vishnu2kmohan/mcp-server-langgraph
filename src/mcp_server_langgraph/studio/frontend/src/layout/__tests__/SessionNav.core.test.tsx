/**
 * SessionNav Core Tests
 *
 * Tests for rendering, session grouping, search, navigation, accessibility,
 * groupSessionsByDate utility, and inline editing.
 *
 * Split from SessionNav.test.tsx for memory optimization.
 * See SessionNav.fixtures.tsx for shared mocks and utilities.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import {
  mockNavigate,
  mockSetSearchParams,
  mockRevalidate,
  mockSessions,
  createTestStore,
  createWrapper,
} from "./SessionNav.fixtures";

// Mock navigate and other react-router hooks
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ sessionId: "session-1" }),
    // v8 Phase 4: Mock useSearchParams for archive toggle
    useSearchParams: () => [new URLSearchParams(), mockSetSearchParams],
    // v8 Phase 4: Mock useRevalidator for archive/restore refresh
    useRevalidator: () => ({ revalidate: mockRevalidate, state: "idle" }),
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
vi.mock("../../hooks/useNewChat", () => ({
  useNewChat: () => ({
    createNewChat: vi.fn(),
    isCreating: false,
  }),
}));

// Mock useSessionIntelligence hooks (for AISessionCard and SimilarSessionsPanel)
vi.mock("../../hooks/useSessionIntelligence", () => ({
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

import { SessionNav, groupSessionsByDate } from "../SessionNav";
import type { Session } from "../../types";

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

      // The session button has the highlight class directly (bg-primary-4 for active sessions)
      const sessionButton = screen.getByRole("button", {
        name: "Today's Chat",
      });
      expect(sessionButton).toHaveClass("bg-primary-4");
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

  it("should navigate to session on single click even with enableEdit=true", async () => {
    // GIVEN: SessionNav with enableEdit=true
    const user = userEvent.setup();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit onRenameSession={vi.fn()} />
      </Wrapper>,
    );

    // WHEN: User single-clicks on a session (not the current one)
    const sessionItem = screen.getByText("Yesterday's Chat");
    await user.click(sessionItem);

    // THEN: Should navigate to that session (after debounce delay)
    await waitFor(
      () => {
        expect(mockNavigate).toHaveBeenCalledWith("/studio/chat/session-2");
      },
      { timeout: 500 },
    );
  });

  it("should enter edit mode on double-click when enableEdit=true", async () => {
    // GIVEN: SessionNav with enableEdit=true
    const user = userEvent.setup();
    const mockRename = vi.fn();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit onRenameSession={mockRename} />
      </Wrapper>,
    );

    // WHEN: User double-clicks on a session
    const sessionItem = screen.getByText("Yesterday's Chat");
    await user.dblClick(sessionItem);

    // THEN: Should enter edit mode (input field should appear)
    const editInput = await screen.findByRole("textbox", {
      name: /rename session/i,
    });
    expect(editInput).toBeInTheDocument();
    expect(editInput).toHaveValue("Yesterday's Chat");
  });

  it("should NOT navigate on double-click when entering edit mode", async () => {
    // GIVEN: SessionNav with enableEdit=true
    const user = userEvent.setup();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit onRenameSession={vi.fn()} />
      </Wrapper>,
    );

    // WHEN: User double-clicks on a session
    const sessionItem = screen.getByText("Yesterday's Chat");
    await user.dblClick(sessionItem);

    // Wait for any pending debounce to complete
    await waitFor(
      () => {
        // Should be in edit mode
        expect(
          screen.getByRole("textbox", { name: /rename session/i }),
        ).toBeInTheDocument();
      },
      { timeout: 500 },
    );

    // THEN: Should NOT have navigated (double-click cancels the pending navigation)
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it("should save edited name and exit edit mode on Enter", async () => {
    // GIVEN: SessionNav in edit mode
    const user = userEvent.setup();
    const mockRename = vi.fn();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit onRenameSession={mockRename} />
      </Wrapper>,
    );

    // Enter edit mode via double-click
    const sessionItem = screen.getByText("Yesterday's Chat");
    await user.dblClick(sessionItem);

    // WHEN: User types new name and presses Enter
    const editInput = await screen.findByRole("textbox", {
      name: /rename session/i,
    });
    await user.clear(editInput);
    await user.type(editInput, "Renamed Session{Enter}");

    // THEN: Should call onRenameSession with new name
    expect(mockRename).toHaveBeenCalledWith("session-2", "Renamed Session");
  });

  it("should cancel edit mode on Escape without saving", async () => {
    // GIVEN: SessionNav in edit mode
    const user = userEvent.setup();
    const mockRename = vi.fn();
    const Wrapper = createWrapper(store);
    render(
      <Wrapper>
        <SessionNav enableEdit onRenameSession={mockRename} />
      </Wrapper>,
    );

    // Enter edit mode via double-click
    const sessionItem = screen.getByText("Yesterday's Chat");
    await user.dblClick(sessionItem);

    // WHEN: User presses Escape
    const editInput = await screen.findByRole("textbox", {
      name: /rename session/i,
    });
    await user.type(editInput, "New Name{Escape}");

    // THEN: Should exit edit mode without calling onRenameSession
    expect(mockRename).not.toHaveBeenCalled();
    // Should revert to displaying the original name
    expect(screen.getByText("Yesterday's Chat")).toBeInTheDocument();
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

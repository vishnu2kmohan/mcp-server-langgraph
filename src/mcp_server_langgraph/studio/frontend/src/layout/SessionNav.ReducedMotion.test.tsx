/**
 * SessionNav Reduced Motion Accessibility Tests
 *
 * Tests for WCAG 2.2 AA compliance - verifying that SessionNav
 * properly respects the prefers-reduced-motion preference.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import type { ReactNode } from "react";

// Mock motion/react for reduced motion testing
const mockUseReducedMotion = vi.fn(() => false);
vi.mock("motion/react", () => ({
  useReducedMotion: () => mockUseReducedMotion(),
  motion: {
    div: "div",
    span: "span",
    button: "button",
    ul: "ul",
    li: "li",
  },
  AnimatePresence: ({ children }: { children: ReactNode }) => children,
}));

// Mock react-router hooks
vi.mock("react-router", async () => {
  const actual = await vi.importActual("react-router");
  return {
    ...actual,
    useRouteLoaderData: () => ({
      sessions: [
        {
          id: "session-1",
          name: "Test Session 1",
          createdAt: new Date().toISOString(),
        },
        {
          id: "session-2",
          name: "Test Session 2",
          createdAt: new Date(Date.now() - 86400000).toISOString(), // Yesterday
        },
      ],
    }),
    useNavigate: () => vi.fn(),
    useParams: () => ({}),
  };
});

// Mock route loader data
vi.mock("../hooks/useSafeRouteLoaderData", () => ({
  useSafeRouteLoaderData: () => ({
    sessions: [
      {
        id: "session-1",
        name: "Test Session 1",
        createdAt: new Date().toISOString(),
      },
      {
        id: "session-2",
        name: "Test Session 2",
        createdAt: new Date(Date.now() - 86400000).toISOString(), // Yesterday
      },
    ],
  }),
}));

// Mock useNewChat hook
vi.mock("../hooks/useNewChat", () => ({
  useNewChat: () => ({
    createNewChat: vi.fn(),
    isCreating: false,
  }),
}));

// Import after mocks
import { SessionNav } from "./SessionNav";

// =============================================================================
// Test Suite
// =============================================================================

describe("SessionNav Reduced Motion Accessibility (WCAG 2.2 AA)", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
  });

  describe("when reduced motion is preferred", () => {
    beforeEach(() => {
      mockUseReducedMotion.mockReturnValue(true);
    });

    it("renders all sessions correctly with reduced motion", () => {
      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      expect(screen.getByText("Test Session 1")).toBeInTheDocument();
      expect(screen.getByText("Test Session 2")).toBeInTheDocument();
    });

    it("calls useReducedMotion hook", () => {
      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      expect(mockUseReducedMotion).toHaveBeenCalled();
    });
  });

  describe("when reduced motion is not preferred", () => {
    beforeEach(() => {
      mockUseReducedMotion.mockReturnValue(false);
    });

    it("renders all sessions correctly without reduced motion", () => {
      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      expect(screen.getByText("Test Session 1")).toBeInTheDocument();
      expect(screen.getByText("Test Session 2")).toBeInTheDocument();
    });

    it("calls useReducedMotion hook", () => {
      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      expect(mockUseReducedMotion).toHaveBeenCalled();
    });
  });

  describe("functional equivalence", () => {
    it("search works with reduced motion enabled", () => {
      mockUseReducedMotion.mockReturnValue(true);

      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      const searchInput = screen.getByPlaceholderText("Search sessions...");
      expect(searchInput).toBeInTheDocument();
    });

    it("new chat button works with reduced motion enabled", () => {
      mockUseReducedMotion.mockReturnValue(true);

      render(
        <MemoryRouter>
          <SessionNav />
        </MemoryRouter>,
      );

      const newChatButton = screen.getByTestId("new-chat-button");
      expect(newChatButton).toBeInTheDocument();
      expect(newChatButton).not.toBeDisabled();
    });
  });
});

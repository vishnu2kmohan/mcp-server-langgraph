/**
 * ThinkingBudgetCard Tests
 *
 * TDD tests for the ThinkingBudgetCard component.
 * Tests cover:
 * - Display of thinking budget defaults
 * - Complexity to level mapping display
 * - Persona-based visibility (only admin, developer)
 * - Read-only display behavior
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { ThinkingBudgetCard } from "./ThinkingBudgetCard";
import personaReducer from "../../store/slices/personaSlice";
import type { ThinkingBudgetDefaults } from "../../types/api";

// Mock the API mutation
vi.mock("../../api", () => ({
  useUpdateThinkingBudgetMutation: () => [
    vi.fn().mockReturnValue({ unwrap: vi.fn().mockResolvedValue({}) }),
    { isLoading: false },
  ],
}));

// Helper to create a test store with specific persona
function createTestStoreWithPersona(persona: "admin" | "developer" | "user") {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
        visibleModules: [],
        featureFlags: {},
        apiVersion: null,
      },
    },
  });
}

// Mock thinking budget data (camelCase per ADR-0091 Phase 6)
const mockThinkingBudgetDefaults: ThinkingBudgetDefaults = {
  enabled: true,
  defaultLevel: "medium",
  levels: [
    {
      level: "low",
      claudeOpusEffort: "low",
      otherModelsTokens: 1024,
      description: "Quick responses for simple tasks",
    },
    {
      level: "medium",
      claudeOpusEffort: "medium",
      otherModelsTokens: 8192,
      description: "Balanced thinking for typical tasks",
    },
    {
      level: "high",
      claudeOpusEffort: "high",
      otherModelsTokens: 32768,
      description: "Deep reasoning for complex tasks",
    },
    {
      level: "ultra",
      claudeOpusEffort: "high",
      otherModelsTokens: 131072,
      description: "Maximum reasoning for the most complex tasks",
    },
  ],
  complexityMapping: {
    simple: "low",
    complicated: "medium",
    complex: "high",
    chaotic: "ultra",
  },
};

describe("ThinkingBudgetCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Admin Persona", () => {
    it("should render card for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(screen.getByText(/Thinking Budget/i)).toBeInTheDocument();
    });

    it("should display enabled status", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(screen.getByText(/Enabled/i)).toBeInTheDocument();
    });

    it("should display default level", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      // Check that "medium" appears (may appear multiple times in UI)
      expect(screen.getAllByText(/medium/i).length).toBeGreaterThan(0);
    });

    it("should display complexity mapping", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      // Check complexity labels are shown (may match multiple elements)
      expect(screen.getAllByText(/simple/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/complicated/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/complex/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/chaotic/i).length).toBeGreaterThan(0);
    });

    it("should display thinking levels", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      // Check level info is shown (may match multiple elements)
      expect(screen.getAllByText(/low/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/high/i).length).toBeGreaterThan(0);
      expect(screen.getAllByText(/ultra/i).length).toBeGreaterThan(0);
    });
  });

  describe("Developer Persona", () => {
    it("should render card for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(screen.getByText(/Thinking Budget/i)).toBeInTheDocument();
    });
  });

  describe("User Persona", () => {
    it("should NOT render card for user persona", () => {
      const store = createTestStoreWithPersona("user");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(screen.queryByText(/Thinking Budget/i)).not.toBeInTheDocument();
    });
  });

  describe("Null Data Handling", () => {
    it("should render nothing when data is null", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={null} />
        </Provider>,
      );

      expect(screen.queryByText(/Thinking Budget/i)).not.toBeInTheDocument();
    });

    it("should render nothing when data is undefined", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={undefined} />
        </Provider>,
      );

      expect(screen.queryByText(/Thinking Budget/i)).not.toBeInTheDocument();
    });
  });

  describe("Disabled State", () => {
    it("should display disabled status when thinking is disabled", () => {
      const store = createTestStoreWithPersona("admin");
      const disabledData = { ...mockThinkingBudgetDefaults, enabled: false };

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={disabledData} />
        </Provider>,
      );

      expect(screen.getByText(/Disabled/i)).toBeInTheDocument();
    });
  });

  describe("Edit Functionality", () => {
    it("should show edit button for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(
        screen.getByTestId("edit-thinking-budget-button"),
      ).toBeInTheDocument();
    });

    it("should show edit button for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      expect(
        screen.getByTestId("edit-thinking-budget-button"),
      ).toBeInTheDocument();
    });

    it("should show level selector when edit mode is active", async () => {
      const store = createTestStoreWithPersona("admin");
      const user = userEvent.setup();

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-thinking-budget-button");
      await user.click(editButton);

      expect(screen.getByTestId("thinking-level-selector")).toBeInTheDocument();
    });

    it("should show enabled toggle when edit mode is active", async () => {
      const store = createTestStoreWithPersona("admin");
      const user = userEvent.setup();

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-thinking-budget-button");
      await user.click(editButton);

      expect(screen.getByTestId("thinking-enabled-toggle")).toBeInTheDocument();
    });

    it("should show save and cancel buttons in edit mode", async () => {
      const store = createTestStoreWithPersona("admin");
      const user = userEvent.setup();

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-thinking-budget-button");
      await user.click(editButton);

      expect(
        screen.getByTestId("save-thinking-budget-button"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("cancel-edit-button")).toBeInTheDocument();
    });

    it("should exit edit mode when cancel is clicked", async () => {
      const store = createTestStoreWithPersona("admin");
      const user = userEvent.setup();

      render(
        <Provider store={store}>
          <ThinkingBudgetCard data={mockThinkingBudgetDefaults} />
        </Provider>,
      );

      const editButton = screen.getByTestId("edit-thinking-budget-button");
      await user.click(editButton);

      const cancelButton = screen.getByTestId("cancel-edit-button");
      await user.click(cancelButton);

      // Edit button should be visible again, selector should not be
      expect(
        screen.getByTestId("edit-thinking-budget-button"),
      ).toBeInTheDocument();
      expect(
        screen.queryByTestId("thinking-level-selector"),
      ).not.toBeInTheDocument();
    });
  });
});

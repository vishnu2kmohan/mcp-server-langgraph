/**
 * OrchestratorsListCard Tests
 *
 * TDD tests for the OrchestratorsListCard component.
 * Tests cover:
 * - Display of orchestrator registry
 * - Feature flag status for each orchestrator
 * - Task categories display
 * - Persona-based visibility (only admin, developer)
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { OrchestratorsListCard } from "./OrchestratorsListCard";
import personaReducer from "../../store/slices/personaSlice";
import type { OrchestratorInfo } from "../../types/api";

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

// Mock orchestrators data (camelCase per ADR-0091)
const mockOrchestrators: OrchestratorInfo[] = [
  {
    name: "Orchestrator",
    displayName: "Multi-Agent Orchestrator",
    description: "Lead agent that decomposes complex tasks",
    featureFlag: "enable_multi_agent_orchestration",
    taskCategories: ["decomposition", "delegation", "synthesis"],
  },
  {
    name: "StudioOrchestrator",
    displayName: "Studio AI Orchestrator",
    description: "Unified Studio AI orchestration",
    featureFlag: "enable_studio_ai",
    taskCategories: ["UX", "SESSION", "CONVERSATION", "CANVAS"],
  },
  {
    name: "LoopAgent",
    displayName: "Loop Agent",
    description: "Iterative task execution agent",
    featureFlag: "enable_loop_agent",
    taskCategories: ["iteration", "refinement"],
  },
];

// Mock feature flags for testing enabled/disabled status
const mockFeatureFlags: Record<string, boolean> = {
  enable_multi_agent_orchestration: true,
  enable_studio_ai: true,
  enable_loop_agent: false,
};

describe("OrchestratorsListCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Admin Persona", () => {
    it("should render card for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // The title "Orchestrators" appears, may also appear in count badge
      expect(screen.getAllByText(/Orchestrators/i).length).toBeGreaterThan(0);
    });

    it("should display orchestrator count", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getByText(/3 orchestrators/i)).toBeInTheDocument();
    });

    it("should display orchestrator names", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getByText("Multi-Agent Orchestrator")).toBeInTheDocument();
      expect(screen.getByText("Studio AI Orchestrator")).toBeInTheDocument();
      expect(screen.getByText("Loop Agent")).toBeInTheDocument();
    });

    it("should display enabled/disabled status based on feature flags", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // 2 orchestrators are enabled, 1 is disabled
      const enabledBadges = screen.getAllByText("Enabled");
      const disabledBadges = screen.getAllByText("Disabled");
      expect(enabledBadges.length).toBe(2);
      expect(disabledBadges.length).toBe(1);
    });

    it("should display task categories", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // Check some task categories are shown
      expect(screen.getByText(/decomposition/i)).toBeInTheDocument();
      expect(screen.getByText(/UX/)).toBeInTheDocument();
      expect(screen.getByText(/iteration/i)).toBeInTheDocument();
    });
  });

  describe("Developer Persona", () => {
    it("should render card for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getAllByText(/Orchestrators/i).length).toBeGreaterThan(0);
    });
  });

  describe("User Persona", () => {
    it("should NOT render card for user persona", () => {
      const store = createTestStoreWithPersona("user");

      render(
        <Provider store={store}>
          <OrchestratorsListCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.queryByText(/Orchestrators/i)).not.toBeInTheDocument();
    });
  });

  describe("Empty Data Handling", () => {
    it("should render nothing when orchestrators is empty", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <OrchestratorsListCard orchestrators={[]} featureFlags={{}} />
        </Provider>,
      );

      expect(screen.queryByText(/Orchestrators/i)).not.toBeInTheDocument();
    });
  });
});

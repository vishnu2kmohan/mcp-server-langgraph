/**
 * FeatureFlagsCard Tests
 *
 * TDD tests for the FeatureFlagsCard component.
 * Tests cover:
 * - Display of agent-related feature flags
 * - Enabled/disabled status badges
 * - Persona-based visibility (only admin, developer)
 * - Read-only display behavior
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { FeatureFlagsCard } from "./FeatureFlagsCard";
import personaReducer from "../../store/slices/personaSlice";

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

// Mock feature flags data
const mockFeatureFlags: Record<string, boolean> = {
  enable_thinking_budget: true,
  enable_multi_agent_orchestration: true,
  enable_studio_ai: false,
  enable_ai_explanations: true,
  enable_loop_agent: false,
};

describe("FeatureFlagsCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Admin Persona", () => {
    it("should render card for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      expect(screen.getByText(/Feature Flags/i)).toBeInTheDocument();
    });

    it("should display all feature flag names", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      // Check some flag names are displayed
      expect(screen.getByText(/thinking_budget/i)).toBeInTheDocument();
      expect(
        screen.getByText(/multi_agent_orchestration/i),
      ).toBeInTheDocument();
      expect(screen.getByText(/studio_ai/i)).toBeInTheDocument();
    });

    it("should display enabled badges for enabled flags", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      // There should be at least 3 "Enabled" badges (3 flags are enabled)
      const enabledBadges = screen.getAllByText("Enabled");
      expect(enabledBadges.length).toBe(3);
    });

    it("should display disabled badges for disabled flags", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      // There should be 2 "Disabled" badges (2 flags are disabled)
      const disabledBadges = screen.getAllByText("Disabled");
      expect(disabledBadges.length).toBe(2);
    });

    it("should display total count of flags", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      // Should show "5 flags" somewhere
      expect(screen.getByText(/5 flags/i)).toBeInTheDocument();
    });
  });

  describe("Developer Persona", () => {
    it("should render card for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      expect(screen.getByText(/Feature Flags/i)).toBeInTheDocument();
    });
  });

  describe("User Persona", () => {
    it("should NOT render card for user persona", () => {
      const store = createTestStoreWithPersona("user");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={mockFeatureFlags} />
        </Provider>,
      );

      expect(screen.queryByText(/Feature Flags/i)).not.toBeInTheDocument();
    });
  });

  describe("Null Data Handling", () => {
    it("should render nothing when data is null", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={null} />
        </Provider>,
      );

      expect(screen.queryByText(/Feature Flags/i)).not.toBeInTheDocument();
    });

    it("should render nothing when data is undefined", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={undefined} />
        </Provider>,
      );

      expect(screen.queryByText(/Feature Flags/i)).not.toBeInTheDocument();
    });

    it("should render nothing when data is empty object", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <FeatureFlagsCard data={{}} />
        </Provider>,
      );

      expect(screen.queryByText(/Feature Flags/i)).not.toBeInTheDocument();
    });
  });
});

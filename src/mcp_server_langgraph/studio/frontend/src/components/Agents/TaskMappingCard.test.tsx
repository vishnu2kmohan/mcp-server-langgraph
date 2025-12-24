/**
 * TaskMappingCard Tests
 *
 * TDD tests for the TaskMappingCard component.
 * Tests cover:
 * - Display of task-to-orchestrator mapping
 * - Task categories per orchestrator
 * - Feature flag status
 * - Persona-based visibility (only developer)
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { TaskMappingCard } from "./TaskMappingCard";
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

// Mock orchestrators data
const mockOrchestrators: OrchestratorInfo[] = [
  {
    name: "StudioOrchestrator",
    display_name: "Studio AI Orchestrator",
    description: "Unified Studio AI orchestration",
    feature_flag: "enable_studio_ai",
    task_categories: ["UX", "SESSION", "CONVERSATION", "CANVAS", "DIAGRAM"],
  },
  {
    name: "ExplanationOrchestrator",
    display_name: "Explanation Orchestrator",
    description: "Generates AI-powered explanations for HITL dialogs",
    feature_flag: "enable_ai_explanations",
    task_categories: ["uncertainty", "risk", "alternatives", "evidence"],
  },
  {
    name: "AlertOrchestrator",
    display_name: "Alert Orchestrator",
    description: "Orchestrates alert analysis tasks",
    feature_flag: "enable_orchestrated_alert_analysis",
    task_categories: ["correlation", "root_cause", "recommendations"],
  },
];

// Mock feature flags
const mockFeatureFlags: Record<string, boolean> = {
  enable_studio_ai: true,
  enable_ai_explanations: true,
  enable_orchestrated_alert_analysis: false,
};

describe("TaskMappingCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Developer Persona", () => {
    it("should render card for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getByText(/Task Mapping/i)).toBeInTheDocument();
    });

    it("should display total task categories count", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // Total: 5 + 4 + 3 = 12 task categories
      expect(screen.getByText(/12 task categories/i)).toBeInTheDocument();
    });

    it("should display orchestrator names in table", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getByText("Studio AI Orchestrator")).toBeInTheDocument();
      expect(screen.getByText("Explanation Orchestrator")).toBeInTheDocument();
      expect(screen.getByText("Alert Orchestrator")).toBeInTheDocument();
    });

    it("should display task categories for each orchestrator", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // Check some task categories are shown
      expect(screen.getByText("UX")).toBeInTheDocument();
      expect(screen.getByText("SESSION")).toBeInTheDocument();
      expect(screen.getByText("uncertainty")).toBeInTheDocument();
      expect(screen.getByText("correlation")).toBeInTheDocument();
    });

    it("should display enabled/disabled status for each orchestrator", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // 2 enabled, 1 disabled
      const enabledBadges = screen.getAllByText("Active");
      const disabledBadges = screen.getAllByText("Inactive");
      expect(enabledBadges.length).toBe(2);
      expect(disabledBadges.length).toBe(1);
    });

    it("should display category count for each orchestrator", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      // Studio has 5 categories, Explanation has 4, Alert has 3
      expect(screen.getByText("5")).toBeInTheDocument();
      expect(screen.getByText("4")).toBeInTheDocument();
      expect(screen.getByText("3")).toBeInTheDocument();
    });
  });

  describe("Admin Persona", () => {
    it("should render card for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.getByText(/Task Mapping/i)).toBeInTheDocument();
    });
  });

  describe("User Persona", () => {
    it("should NOT render card for user persona", () => {
      const store = createTestStoreWithPersona("user");

      render(
        <Provider store={store}>
          <TaskMappingCard
            orchestrators={mockOrchestrators}
            featureFlags={mockFeatureFlags}
          />
        </Provider>,
      );

      expect(screen.queryByText(/Task Mapping/i)).not.toBeInTheDocument();
    });
  });

  describe("Empty Data Handling", () => {
    it("should render nothing when orchestrators is empty", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <TaskMappingCard orchestrators={[]} featureFlags={{}} />
        </Provider>,
      );

      expect(screen.queryByText(/Task Mapping/i)).not.toBeInTheDocument();
    });
  });
});

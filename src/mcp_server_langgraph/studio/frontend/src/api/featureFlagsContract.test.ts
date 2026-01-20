/**
 * Feature Flags API Contract Tests
 *
 * TDD tests to ensure consistency between:
 * - Backend API response format (short names like "workflows")
 * - TypeScript type definitions
 * - MSW mock handlers
 *
 * These tests verify that the frontend correctly handles the API response format.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { mockFeatureFlags } from "../mocks/handlers";
import type { FeatureFlags } from "../types/api";

/**
 * Expected API response format from backend.
 * The backend uses short names (e.g., "workflows" not "enable_workflows_feature")
 * See: src/mcp_server_langgraph/core/feature_flags.py - get_ui_features_for_role()
 */
const _EXPECTED_API_RESPONSE_KEYS = [
  // Canvas/Studio v2 UI
  "studio_canvas_shell",
  "canvas_editable",
  "canvas_agents",
  "canvas_ai_palette",
  "canvas_compliance",
  "canvas_help",
  // Core features (SHORT NAMES - not enable_* prefixes)
  "workflows",
  "sessions",
  "cost_dashboard",
  "observability",
  "code_export",
  "ai_suggestions",
  "llm_suggestions", // DEPRECATED: use suggestion_strategy
  "suggestion_strategy", // Sprint Block 5: "llm" | "heuristic" | "hybrid"
  "multi_agent_strategy", // Sprint Block 5: "orchestrator" | "peer" | "hybrid"
  "notification_preferences",
  "mcp_websocket",
  "interactive_artifacts",
  "url_content_fetch",
  "slash_commands",
  "style_presets",
  // UX Enhancement Features
  "user_preferences_sync",
  "session_export",
  "project_context",
  "onboarding_wizard",
  "guided_tour",
  "sus_survey",
  "command_palette",
  "keyboard_shortcuts",
  "theme_customization",
  "confirmation_dialogs",
  // AI UX Features (Phase 6 AI-Native Integration)
  "ai_disclosure",
  "ai_empty_states",
  "ai_nudges",
  "ai_error_recovery",
  "ai_onboarding",
  "ai_metrics_insights",
  "ai_persona_analysis",
  "batch_composite_analysis",
  // HITL Features (Confidence-Based Agent Approval)
  "agent_hitl",
  // Markdown References ([[type:qualifier:id]] syntax)
  "markdown_references",
] as const;

describe("Feature Flags API Contract", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("MSW Mock Format", () => {
    it("should use API response format (short names) not backend field names", () => {
      // The API returns short names like "workflows", not "enable_workflows_feature"
      // This test will fail if the mock uses wrong field names

      // These should NOT be in the mock (backend field names)
      const backendFieldNames = [
        "enable_workflows_feature",
        "enable_sessions_feature",
        "enable_cost_dashboard",
        "enable_cost_dashboard_users",
        "enable_observability_ui",
      ];

      for (const fieldName of backendFieldNames) {
        expect(mockFeatureFlags).not.toHaveProperty(fieldName);
      }
    });

    it("should include all core feature flags with short names", () => {
      // These should be in the mock (API response format)
      const expectedShortNames = [
        "studio_canvas_shell",
        "workflows",
        "sessions",
        "cost_dashboard",
        "observability",
        "code_export",
        "ai_suggestions",
        "mcp_websocket",
        "interactive_artifacts",
      ];

      for (const fieldName of expectedShortNames) {
        expect(mockFeatureFlags).toHaveProperty(fieldName);
        expect(typeof mockFeatureFlags[fieldName]).toBe("boolean");
      }
    });

    it("should include canvas phase flags", () => {
      const canvasPhaseFlags = [
        "studio_canvas_shell", // Phase 1
        "canvas_editable", // Phase 2
        "canvas_agents", // Phase 4
        "canvas_ai_palette", // Phase 4
        "canvas_compliance", // Phase 5
        "canvas_help", // Phase 6
      ];

      for (const flagName of canvasPhaseFlags) {
        expect(mockFeatureFlags).toHaveProperty(flagName);
      }
    });

    it("should include HITL feature flags", () => {
      // HITL feature flags for confidence-based agent approval
      // Backend: enable_agent_hitl → API response: agent_hitl
      expect(mockFeatureFlags).toHaveProperty("agent_hitl");
      expect(typeof mockFeatureFlags.agent_hitl).toBe("boolean");
    });

    it("should include markdown references feature flag", () => {
      // Markdown references ([[type:qualifier:id]] syntax)
      // Backend: enable_markdown_references → API response: markdown_references
      expect(mockFeatureFlags).toHaveProperty("markdown_references");
      expect(typeof mockFeatureFlags.markdown_references).toBe("boolean");
    });

    it("should include Sprint Block 5 strategy fields", () => {
      // Sprint Block 5 introduced strategy enums to replace boolean pairs
      // These are STRING values, not booleans

      // suggestion_strategy: "llm" | "heuristic" | "hybrid"
      expect(mockFeatureFlags).toHaveProperty("suggestion_strategy");
      expect(typeof mockFeatureFlags.suggestion_strategy).toBe("string");
      expect(["llm", "heuristic", "hybrid"]).toContain(
        mockFeatureFlags.suggestion_strategy,
      );

      // multi_agent_strategy: "orchestrator" | "peer" | "hybrid"
      expect(mockFeatureFlags).toHaveProperty("multi_agent_strategy");
      expect(typeof mockFeatureFlags.multi_agent_strategy).toBe("string");
      expect(["orchestrator", "peer", "hybrid"]).toContain(
        mockFeatureFlags.multi_agent_strategy,
      );
    });

    it("should include AI UX feature flags", () => {
      // AI UX features for Phase 6 AI-Native Integration
      const aiUxFlags = [
        "ai_disclosure",
        "ai_empty_states",
        "ai_nudges",
        "ai_error_recovery",
        "ai_onboarding",
        "ai_metrics_insights",
        "ai_persona_analysis",
        "batch_composite_analysis",
      ];

      for (const flagName of aiUxFlags) {
        expect(mockFeatureFlags).toHaveProperty(flagName);
        expect(typeof mockFeatureFlags[flagName]).toBe("boolean");
      }
    });
  });

  describe("TypeScript Type Compatibility", () => {
    it("should have index signature for flexible access", () => {
      // The FeatureFlags type should allow accessing any string key
      // This is important because we use dynamic flag names
      const flags: FeatureFlags = mockFeatureFlags;

      // Should be able to access with string key
      const flagName = "workflows";
      expect(typeof flags[flagName]).toBe("boolean");
    });

    it("should allow short name access", () => {
      const flags: FeatureFlags = mockFeatureFlags;

      // API returns short names, so these should work
      expect(flags.workflows).toBeDefined();
      expect(flags.sessions).toBeDefined();
      expect(flags.cost_dashboard).toBeDefined();
      expect(flags.observability).toBeDefined();
    });
  });
});

describe("Feature Flag Naming Convention", () => {
  it("should document the naming convention", () => {
    /**
     * NAMING CONVENTION:
     *
     * Backend (Python):
     *   - Uses enable_* prefix: enable_workflows_feature, enable_sessions_feature
     *   - Environment vars: FF_ENABLE_WORKFLOWS_FEATURE, FF_STUDIO_CANVAS_SHELL
     *
     * API Response:
     *   - Uses short names: workflows, sessions, cost_dashboard
     *   - Canvas flags keep names: studio_canvas_shell, canvas_editable
     *
     * Frontend (TypeScript):
     *   - Types should match API response format (short names)
     *   - Hook: useFeatureFlag("workflows") not useFeatureFlag("enable_workflows_feature")
     */
    expect(true).toBe(true); // Documentation test
  });
});

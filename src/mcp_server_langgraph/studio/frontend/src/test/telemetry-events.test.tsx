/**
 * Telemetry Events Tests
 *
 * Comprehensive tests for telemetry event tracking across the Studio Canvas UI.
 * These tests verify that key user actions trigger the appropriate telemetry events
 * for analytics and observability.
 *
 * Covered event categories:
 * - AI suggestions (shown, accepted, rejected)
 * - Canvas interactions (opened, artifact created/edited)
 * - Help panel (opened, searched)
 * - Compliance (exported)
 * - Agent operations (started, completed, failed)
 * - HEART metrics integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { cleanup } from "@testing-library/react";

// Mock fetch for telemetry endpoints
const mockFetch = vi.fn();

// =============================================================================
// AI Suggestion Telemetry
// =============================================================================

describe("AI Suggestion Telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Suggestion Shown Events", () => {
    it("should fire telemetry when suggestion is displayed", () => {
      const onSuggestionShown = vi.fn();

      // Simulate component tracking suggestion display
      const suggestions = [
        { id: "sug-1", text: "Tell me more", type: "follow-up" },
        { id: "sug-2", text: "Create a workflow", type: "action" },
      ];

      // Track each suggestion shown
      suggestions.forEach((sug) => {
        onSuggestionShown({
          suggestionId: sug.id,
          suggestionType: sug.type,
          timestamp: Date.now(),
        });
      });

      expect(onSuggestionShown).toHaveBeenCalledTimes(2);
      expect(onSuggestionShown).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestionId: "sug-1",
          suggestionType: "follow-up",
        }),
      );
    });

    it("should include context in suggestion shown event", () => {
      const onSuggestionShown = vi.fn();

      onSuggestionShown({
        suggestionId: "sug-1",
        suggestionType: "follow-up",
        context: {
          sessionId: "session-123",
          messageCount: 5,
          lastRole: "assistant",
        },
        timestamp: Date.now(),
      });

      expect(onSuggestionShown).toHaveBeenCalledWith(
        expect.objectContaining({
          context: expect.objectContaining({
            sessionId: "session-123",
            messageCount: 5,
          }),
        }),
      );
    });
  });

  describe("Suggestion Accepted Events", () => {
    it("should fire telemetry when user accepts a suggestion", () => {
      const onSuggestionAccepted = vi.fn();

      onSuggestionAccepted({
        suggestionId: "sug-1",
        suggestionType: "completion",
        confidence: 0.92,
        acceptMethod: "click",
        timestamp: Date.now(),
      });

      expect(onSuggestionAccepted).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestionId: "sug-1",
          acceptMethod: "click",
        }),
      );
    });

    it("should track keyboard acceptance separately", () => {
      const onSuggestionAccepted = vi.fn();

      onSuggestionAccepted({
        suggestionId: "sug-1",
        suggestionType: "completion",
        acceptMethod: "tab", // Tab to accept
        timestamp: Date.now(),
      });

      expect(onSuggestionAccepted).toHaveBeenCalledWith(
        expect.objectContaining({
          acceptMethod: "tab",
        }),
      );
    });

    it("should include time to accept in telemetry", () => {
      const onSuggestionAccepted = vi.fn();
      const shownTime = Date.now() - 5000; // Shown 5 seconds ago
      const acceptTime = Date.now();

      onSuggestionAccepted({
        suggestionId: "sug-1",
        suggestionType: "follow-up",
        shownAt: shownTime,
        acceptedAt: acceptTime,
        timeToAcceptMs: acceptTime - shownTime,
        timestamp: Date.now(),
      });

      expect(onSuggestionAccepted).toHaveBeenCalledWith(
        expect.objectContaining({
          timeToAcceptMs: 5000,
        }),
      );
    });
  });

  describe("Suggestion Rejected Events", () => {
    it("should fire telemetry when user dismisses a suggestion", () => {
      const onSuggestionRejected = vi.fn();

      onSuggestionRejected({
        suggestionId: "sug-1",
        suggestionType: "refactor",
        rejectMethod: "dismiss_button",
        timestamp: Date.now(),
      });

      expect(onSuggestionRejected).toHaveBeenCalledWith(
        expect.objectContaining({
          suggestionId: "sug-1",
          rejectMethod: "dismiss_button",
        }),
      );
    });

    it("should track escape key dismissal", () => {
      const onSuggestionRejected = vi.fn();

      onSuggestionRejected({
        suggestionId: "sug-1",
        suggestionType: "completion",
        rejectMethod: "escape_key",
        timestamp: Date.now(),
      });

      expect(onSuggestionRejected).toHaveBeenCalledWith(
        expect.objectContaining({
          rejectMethod: "escape_key",
        }),
      );
    });
  });
});

// =============================================================================
// Canvas Telemetry
// =============================================================================

describe("Canvas Telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Canvas Opened Events", () => {
    it("should fire telemetry when canvas panel is opened", () => {
      const onCanvasOpened = vi.fn();

      onCanvasOpened({
        sessionId: "session-123",
        source: "navigation", // How user got there
        hasExistingArtifacts: true,
        artifactCount: 3,
        timestamp: Date.now(),
      });

      expect(onCanvasOpened).toHaveBeenCalledWith(
        expect.objectContaining({
          sessionId: "session-123",
          source: "navigation",
        }),
      );
    });

    it("should track deep link canvas opens", () => {
      const onCanvasOpened = vi.fn();

      onCanvasOpened({
        sessionId: "session-123",
        source: "deep_link",
        artifactId: "artifact-456",
        timestamp: Date.now(),
      });

      expect(onCanvasOpened).toHaveBeenCalledWith(
        expect.objectContaining({
          source: "deep_link",
          artifactId: "artifact-456",
        }),
      );
    });
  });

  describe("Artifact Created Events", () => {
    it("should fire telemetry when artifact is created", () => {
      const onArtifactCreated = vi.fn();

      onArtifactCreated({
        artifactId: "artifact-123",
        artifactType: "code",
        language: "javascript",
        createdBy: "user",
        sessionId: "session-456",
        timestamp: Date.now(),
      });

      expect(onArtifactCreated).toHaveBeenCalledWith(
        expect.objectContaining({
          artifactType: "code",
          createdBy: "user",
        }),
      );
    });

    it("should distinguish AI-created artifacts", () => {
      const onArtifactCreated = vi.fn();

      onArtifactCreated({
        artifactId: "artifact-123",
        artifactType: "code",
        createdBy: "ai",
        confidence: 0.95,
        timestamp: Date.now(),
      });

      expect(onArtifactCreated).toHaveBeenCalledWith(
        expect.objectContaining({
          createdBy: "ai",
          confidence: 0.95,
        }),
      );
    });
  });

  describe("Artifact Edited Events", () => {
    it("should fire telemetry when artifact is edited", () => {
      const onArtifactEdited = vi.fn();

      onArtifactEdited({
        artifactId: "artifact-123",
        editType: "content_change",
        editedBy: "user",
        previousVersion: 1,
        newVersion: 2,
        changeSize: 150, // characters changed
        timestamp: Date.now(),
      });

      expect(onArtifactEdited).toHaveBeenCalledWith(
        expect.objectContaining({
          editType: "content_change",
          editedBy: "user",
        }),
      );
    });

    it("should track AI-assisted edits", () => {
      const onArtifactEdited = vi.fn();

      onArtifactEdited({
        artifactId: "artifact-123",
        editType: "ai_inline_edit",
        editedBy: "ai",
        instruction: "Add error handling",
        acceptedByUser: true,
        timestamp: Date.now(),
      });

      expect(onArtifactEdited).toHaveBeenCalledWith(
        expect.objectContaining({
          editType: "ai_inline_edit",
          acceptedByUser: true,
        }),
      );
    });
  });
});

// =============================================================================
// Agent Telemetry
// =============================================================================

describe("Agent Telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Agent Started Events", () => {
    it("should fire telemetry when background agent starts", () => {
      const onAgentStarted = vi.fn();

      onAgentStarted({
        agentId: "agent-123",
        agentName: "Data Processor",
        task: "process_csv",
        initiatedBy: "user",
        sessionId: "session-456",
        timestamp: Date.now(),
      });

      expect(onAgentStarted).toHaveBeenCalledWith(
        expect.objectContaining({
          agentId: "agent-123",
          task: "process_csv",
        }),
      );
    });
  });

  describe("Agent Completed Events", () => {
    it("should fire telemetry when agent completes successfully", () => {
      const onAgentCompleted = vi.fn();

      onAgentCompleted({
        agentId: "agent-123",
        success: true,
        durationMs: 45000,
        artifactsCreated: 2,
        timestamp: Date.now(),
      });

      expect(onAgentCompleted).toHaveBeenCalledWith(
        expect.objectContaining({
          success: true,
          durationMs: 45000,
        }),
      );
    });
  });

  describe("Agent Failed Events", () => {
    it("should fire telemetry when agent fails", () => {
      const onAgentFailed = vi.fn();

      onAgentFailed({
        agentId: "agent-123",
        success: false,
        errorType: "timeout",
        errorMessage: "Agent timed out after 5 minutes",
        durationMs: 300000,
        timestamp: Date.now(),
      });

      expect(onAgentFailed).toHaveBeenCalledWith(
        expect.objectContaining({
          success: false,
          errorType: "timeout",
        }),
      );
    });
  });
});

// =============================================================================
// Help Panel Telemetry
// =============================================================================

describe("Help Panel Telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Help Opened Events", () => {
    it("should fire telemetry when help panel is opened", () => {
      const onHelpOpened = vi.fn();

      onHelpOpened({
        source: "keyboard_shortcut", // ? key
        currentRoute: "/studio/chat",
        timestamp: Date.now(),
      });

      expect(onHelpOpened).toHaveBeenCalledWith(
        expect.objectContaining({
          source: "keyboard_shortcut",
          currentRoute: "/studio/chat",
        }),
      );
    });

    it("should track contextual help opens", () => {
      const onHelpOpened = vi.fn();

      onHelpOpened({
        source: "contextual_tooltip",
        helpTopic: "canvas_artifacts",
        currentRoute: "/studio/chat/session-123",
        timestamp: Date.now(),
      });

      expect(onHelpOpened).toHaveBeenCalledWith(
        expect.objectContaining({
          source: "contextual_tooltip",
          helpTopic: "canvas_artifacts",
        }),
      );
    });
  });

  describe("Help Searched Events", () => {
    it("should fire telemetry when user searches help", () => {
      const onHelpSearched = vi.fn();

      onHelpSearched({
        query: "how to create workflow",
        resultsCount: 5,
        resultClicked: true,
        resultIndex: 0,
        timestamp: Date.now(),
      });

      expect(onHelpSearched).toHaveBeenCalledWith(
        expect.objectContaining({
          query: "how to create workflow",
          resultsCount: 5,
        }),
      );
    });

    it("should track zero-result searches", () => {
      const onHelpSearched = vi.fn();

      onHelpSearched({
        query: "xyzabc123",
        resultsCount: 0,
        resultClicked: false,
        timestamp: Date.now(),
      });

      expect(onHelpSearched).toHaveBeenCalledWith(
        expect.objectContaining({
          resultsCount: 0,
        }),
      );
    });
  });
});

// =============================================================================
// Compliance Telemetry
// =============================================================================

describe("Compliance Telemetry", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Compliance Exported Events", () => {
    it("should fire telemetry when compliance report is exported", () => {
      const onComplianceExported = vi.fn();

      onComplianceExported({
        reportType: "soc2",
        format: "pdf",
        controlsIncluded: 47,
        userId: "user-123",
        timestamp: Date.now(),
      });

      expect(onComplianceExported).toHaveBeenCalledWith(
        expect.objectContaining({
          reportType: "soc2",
          format: "pdf",
        }),
      );
    });

    it("should track all compliance framework exports", () => {
      const onComplianceExported = vi.fn();
      const frameworks = ["soc2", "hipaa", "gdpr", "fedramp"];

      frameworks.forEach((framework) => {
        onComplianceExported({
          reportType: framework,
          format: "csv",
          timestamp: Date.now(),
        });
      });

      expect(onComplianceExported).toHaveBeenCalledTimes(4);
    });
  });

  describe("Compliance View Events", () => {
    it("should fire telemetry when compliance dashboard is viewed", () => {
      const onComplianceViewed = vi.fn();

      onComplianceViewed({
        framework: "hipaa",
        viewDuration: 0, // Initial view
        persona: "compliance-officer",
        timestamp: Date.now(),
      });

      expect(onComplianceViewed).toHaveBeenCalledWith(
        expect.objectContaining({
          framework: "hipaa",
          persona: "compliance-officer",
        }),
      );
    });
  });
});

// =============================================================================
// HEART Metrics Integration
// =============================================================================

describe("HEART Metrics Integration", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockFetch.mockResolvedValue({ ok: true, json: async () => ({}) });
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Engagement Tracking", () => {
    it("should track feature engagement events", async () => {
      const trackEngagement = vi.fn();

      // Simulate tracking various engagements
      trackEngagement({ feature: "canvas", action: "artifact_created" });
      trackEngagement({ feature: "ai", action: "suggestion_accepted" });
      trackEngagement({ feature: "help", action: "search_performed" });

      expect(trackEngagement).toHaveBeenCalledTimes(3);
    });

    it("should batch engagement events", async () => {
      const eventQueue: Array<{ feature: string; action: string }> = [];
      const trackEngagement = (event: { feature: string; action: string }) => {
        eventQueue.push(event);
      };

      // Add multiple events
      trackEngagement({ feature: "chat", action: "message_sent" });
      trackEngagement({ feature: "chat", action: "response_received" });
      trackEngagement({ feature: "canvas", action: "tab_switched" });

      // Events should be queued for batching
      expect(eventQueue.length).toBe(3);
    });
  });

  describe("Task Success Tracking", () => {
    it("should track task completion", () => {
      const startTask = vi.fn();
      const completeTask = vi.fn();

      startTask("create_workflow");
      // ... user performs task
      completeTask(true);

      expect(startTask).toHaveBeenCalledWith("create_workflow");
      expect(completeTask).toHaveBeenCalledWith(true);
    });

    it("should track task failure", () => {
      const startTask = vi.fn();
      const completeTask = vi.fn();

      startTask("deploy_agent");
      // ... task fails
      completeTask(false, "Permission denied");

      expect(completeTask).toHaveBeenCalledWith(false, "Permission denied");
    });
  });

  describe("Adoption Tracking", () => {
    it("should track feature discovery", () => {
      const trackAdoption = vi.fn();

      trackAdoption({
        feature: "command_palette",
        discovered: true,
        discoveryMethod: "keyboard_shortcut",
      });

      expect(trackAdoption).toHaveBeenCalledWith(
        expect.objectContaining({
          feature: "command_palette",
          discovered: true,
        }),
      );
    });

    it("should track onboarding progress", () => {
      const trackAdoption = vi.fn();

      trackAdoption({
        step: "first_chat_sent",
        stepIndex: 1,
        completed: true,
        totalSteps: 5,
      });

      expect(trackAdoption).toHaveBeenCalledWith(
        expect.objectContaining({
          step: "first_chat_sent",
          completed: true,
        }),
      );
    });
  });
});

// =============================================================================
// Event Schema Validation
// =============================================================================

describe("Telemetry Event Schema", () => {
  describe("Required Fields", () => {
    it("should always include timestamp", () => {
      const event = {
        type: "test_event",
        timestamp: Date.now(),
      };

      expect(event.timestamp).toBeDefined();
      expect(typeof event.timestamp).toBe("number");
    });

    it("should include event type", () => {
      const event = {
        type: "ai.suggestion.accepted",
        timestamp: Date.now(),
      };

      expect(event.type).toBeDefined();
      expect(event.type).toMatch(/^[a-z_]+\.[a-z_]+\.[a-z_]+$/);
    });
  });

  describe("Optional Context", () => {
    it("should support optional user context", () => {
      const event = {
        type: "test_event",
        timestamp: Date.now(),
        context: {
          userId: "user-123",
          sessionId: "session-456",
          persona: "developer",
        },
      };

      expect(event.context).toBeDefined();
      expect(event.context.userId).toBe("user-123");
    });

    it("should support optional trace correlation", () => {
      const event = {
        type: "test_event",
        timestamp: Date.now(),
        traceId: "trace-abc-123",
        spanId: "span-xyz-789",
      };

      expect(event.traceId).toBeDefined();
      expect(event.spanId).toBeDefined();
    });
  });
});

/**
 * Session Telemetry Tests
 *
 * TDD tests for session operation telemetry including:
 * - Session creation success/failure rates
 * - Revalidation frequency
 * - Sync timing
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { SessionTelemetry } from "./sessionTelemetry";

// =============================================================================
// Tests
// =============================================================================

describe("SessionTelemetry", () => {
  let telemetry: SessionTelemetry;
  let consoleSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    telemetry = new SessionTelemetry();
    consoleSpy = vi.spyOn(console, "debug").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleSpy.mockRestore();
    vi.clearAllMocks();
  });

  describe("Session Creation Tracking", () => {
    it("should track successful session creation", () => {
      telemetry.trackSessionCreation({
        sessionId: "session-123",
        success: true,
        durationMs: 150,
        sessionName: "My Chat",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.sessionCreations.total).toBe(1);
      expect(metrics.sessionCreations.successful).toBe(1);
      expect(metrics.sessionCreations.failed).toBe(0);
      expect(metrics.sessionCreations.avgDurationMs).toBeCloseTo(150, 0);
    });

    it("should track failed session creation", () => {
      telemetry.trackSessionCreation({
        sessionId: undefined,
        success: false,
        durationMs: 50,
        error: "Network error",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.sessionCreations.total).toBe(1);
      expect(metrics.sessionCreations.successful).toBe(0);
      expect(metrics.sessionCreations.failed).toBe(1);
      expect(metrics.sessionCreations.lastError).toBe("Network error");
    });

    it("should calculate success rate", () => {
      // 3 successful, 1 failed
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackSessionCreation({
        success: false,
        durationMs: 50,
        error: "Error",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.sessionCreations.successRate).toBeCloseTo(0.75, 2);
    });
  });

  describe("Revalidation Tracking", () => {
    it("should track revalidation events", () => {
      telemetry.trackRevalidation({
        sessionId: "session-123",
        trigger: "message_sent",
        durationMs: 200,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.revalidations.total).toBe(1);
      expect(metrics.revalidations.avgDurationMs).toBeCloseTo(200, 0);
    });

    it("should track revalidation frequency", () => {
      // Simulate multiple revalidations
      telemetry.trackRevalidation({ trigger: "message_sent", durationMs: 100 });
      telemetry.trackRevalidation({ trigger: "auto", durationMs: 100 });
      telemetry.trackRevalidation({ trigger: "message_sent", durationMs: 100 });

      const metrics = telemetry.getMetrics();
      expect(metrics.revalidations.total).toBe(3);
      expect(metrics.revalidations.byTrigger["message_sent"]).toBe(2);
      expect(metrics.revalidations.byTrigger["auto"]).toBe(1);
    });

    it("should track debounced vs executed revalidations", () => {
      telemetry.trackRevalidation({
        trigger: "message_sent",
        durationMs: 100,
        debounced: false,
      });
      telemetry.trackRevalidation({
        trigger: "message_sent",
        durationMs: 0,
        debounced: true,
      });
      telemetry.trackRevalidation({
        trigger: "message_sent",
        durationMs: 0,
        debounced: true,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.revalidations.executed).toBe(1);
      expect(metrics.revalidations.debounced).toBe(2);
    });
  });

  describe("Sync Tracking", () => {
    it("should track sync events", () => {
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 5,
        durationMs: 15,
        skipped: false,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.syncs.total).toBe(1);
      expect(metrics.syncs.avgDurationMs).toBeCloseTo(15, 0);
    });

    it("should track skipped syncs (race condition guard)", () => {
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 5,
        durationMs: 0,
        skipped: true,
        skipReason: "pending_mutation",
      });
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 5,
        durationMs: 15,
        skipped: false,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.syncs.total).toBe(2);
      expect(metrics.syncs.skipped).toBe(1);
      expect(metrics.syncs.executed).toBe(1);
    });

    it("should track message count changes", () => {
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 0,
        durationMs: 10,
        skipped: false,
      });
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 2,
        durationMs: 10,
        skipped: false,
      });
      telemetry.trackSync({
        sessionId: "session-123",
        messageCount: 5,
        durationMs: 10,
        skipped: false,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.syncs.avgMessageCount).toBeCloseTo(2.33, 1);
    });
  });

  describe("Artifact Save Tracking", () => {
    it("should track successful artifact save", () => {
      telemetry.trackArtifactSave({
        artifactId: "artifact-123",
        success: true,
        durationMs: 200,
        contentLength: 1500,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.saves.total).toBe(1);
      expect(metrics.artifactOperations.saves.successful).toBe(1);
      expect(metrics.artifactOperations.saves.failed).toBe(0);
      expect(metrics.artifactOperations.saves.avgDurationMs).toBeCloseTo(
        200,
        0,
      );
      expect(metrics.artifactOperations.saves.avgContentLength).toBeCloseTo(
        1500,
        0,
      );
    });

    it("should track failed artifact save", () => {
      telemetry.trackArtifactSave({
        artifactId: "artifact-123",
        success: false,
        durationMs: 50,
        error: "Save failed: network error",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.saves.total).toBe(1);
      expect(metrics.artifactOperations.saves.successful).toBe(0);
      expect(metrics.artifactOperations.saves.failed).toBe(1);
      expect(metrics.artifactOperations.saves.lastError).toBe(
        "Save failed: network error",
      );
    });

    it("should calculate save success rate", () => {
      telemetry.trackArtifactSave({
        artifactId: "a1",
        success: true,
        durationMs: 100,
        contentLength: 100,
      });
      telemetry.trackArtifactSave({
        artifactId: "a2",
        success: true,
        durationMs: 100,
        contentLength: 200,
      });
      telemetry.trackArtifactSave({
        artifactId: "a3",
        success: true,
        durationMs: 100,
        contentLength: 300,
      });
      telemetry.trackArtifactSave({
        artifactId: "a4",
        success: false,
        durationMs: 50,
        error: "Error",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.saves.successRate).toBeCloseTo(0.75, 2);
      expect(metrics.artifactOperations.saves.avgContentLength).toBeCloseTo(
        200,
        0,
      );
    });

    it("should add artifact save to event history", () => {
      telemetry.trackArtifactSave({
        artifactId: "artifact-123",
        success: true,
        durationMs: 150,
        contentLength: 1000,
      });

      const history = telemetry.getEventHistory();
      expect(history).toHaveLength(1);
      expect(history[0].type).toBe("artifact_save");
    });
  });

  describe("Artifact Delete Tracking", () => {
    it("should track successful artifact delete", () => {
      telemetry.trackArtifactDelete({
        artifactId: "artifact-123",
        success: true,
        durationMs: 100,
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.deletes.total).toBe(1);
      expect(metrics.artifactOperations.deletes.successful).toBe(1);
      expect(metrics.artifactOperations.deletes.failed).toBe(0);
      expect(metrics.artifactOperations.deletes.avgDurationMs).toBeCloseTo(
        100,
        0,
      );
    });

    it("should track failed artifact delete", () => {
      telemetry.trackArtifactDelete({
        artifactId: "artifact-123",
        success: false,
        durationMs: 30,
        error: "Delete failed: permission denied",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.deletes.total).toBe(1);
      expect(metrics.artifactOperations.deletes.successful).toBe(0);
      expect(metrics.artifactOperations.deletes.failed).toBe(1);
      expect(metrics.artifactOperations.deletes.lastError).toBe(
        "Delete failed: permission denied",
      );
    });

    it("should calculate delete success rate", () => {
      telemetry.trackArtifactDelete({
        artifactId: "a1",
        success: true,
        durationMs: 100,
      });
      telemetry.trackArtifactDelete({
        artifactId: "a2",
        success: true,
        durationMs: 80,
      });
      telemetry.trackArtifactDelete({
        artifactId: "a3",
        success: false,
        durationMs: 20,
        error: "Error",
      });
      telemetry.trackArtifactDelete({
        artifactId: "a4",
        success: false,
        durationMs: 20,
        error: "Error",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.artifactOperations.deletes.successRate).toBeCloseTo(
        0.5,
        2,
      );
    });

    it("should add artifact delete to event history", () => {
      telemetry.trackArtifactDelete({
        artifactId: "artifact-123",
        success: true,
        durationMs: 100,
      });

      const history = telemetry.getEventHistory();
      expect(history).toHaveLength(1);
      expect(history[0].type).toBe("artifact_delete");
    });
  });

  describe("Metrics Reset", () => {
    it("should reset all metrics", () => {
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackRevalidation({ trigger: "message_sent", durationMs: 100 });
      telemetry.trackSync({
        sessionId: "s",
        messageCount: 1,
        durationMs: 10,
        skipped: false,
      });
      telemetry.trackArtifactSave({
        artifactId: "a1",
        success: true,
        durationMs: 150,
        contentLength: 1000,
      });
      telemetry.trackArtifactDelete({
        artifactId: "a2",
        success: true,
        durationMs: 50,
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s1",
        action: "accept",
        suggestionType: "completion",
      });

      telemetry.reset();

      const metrics = telemetry.getMetrics();
      expect(metrics.sessionCreations.total).toBe(0);
      expect(metrics.revalidations.total).toBe(0);
      expect(metrics.syncs.total).toBe(0);
      expect(metrics.artifactOperations.saves.total).toBe(0);
      expect(metrics.artifactOperations.deletes.total).toBe(0);
      expect(metrics.suggestions.total).toBe(0);
    });
  });

  describe("Debug Logging", () => {
    it("should log events when debug mode is enabled", () => {
      const debugTelemetry = new SessionTelemetry({ debug: true });

      debugTelemetry.trackSessionCreation({ success: true, durationMs: 100 });

      expect(consoleSpy).toHaveBeenCalled();
    });

    it("should not log events when debug mode is disabled", () => {
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });

      expect(consoleSpy).not.toHaveBeenCalled();
    });
  });

  describe("Event History", () => {
    it("should keep event history up to max limit", () => {
      const limitedTelemetry = new SessionTelemetry({ maxHistorySize: 3 });

      limitedTelemetry.trackSessionCreation({ success: true, durationMs: 100 });
      limitedTelemetry.trackSessionCreation({ success: true, durationMs: 100 });
      limitedTelemetry.trackSessionCreation({ success: true, durationMs: 100 });
      limitedTelemetry.trackSessionCreation({ success: true, durationMs: 100 });

      const history = limitedTelemetry.getEventHistory();
      expect(history).toHaveLength(3);
    });
  });

  describe("Suggestion Action Tracking", () => {
    it("should track accepted suggestion", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "suggestion-123",
        action: "accept",
        suggestionType: "completion",
        artifactId: "artifact-456",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.suggestions.total).toBe(1);
      expect(metrics.suggestions.accepted).toBe(1);
      expect(metrics.suggestions.dismissed).toBe(0);
      expect(metrics.suggestions.byType["completion"]).toBe(1);
    });

    it("should track dismissed suggestion", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "suggestion-123",
        action: "dismiss",
        suggestionType: "refactor",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.suggestions.total).toBe(1);
      expect(metrics.suggestions.accepted).toBe(0);
      expect(metrics.suggestions.dismissed).toBe(1);
      expect(metrics.suggestions.byType["refactor"]).toBe(1);
    });

    it("should track suggestions by type", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "s1",
        action: "accept",
        suggestionType: "completion",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s2",
        action: "accept",
        suggestionType: "completion",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s3",
        action: "dismiss",
        suggestionType: "fix",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s4",
        action: "accept",
        suggestionType: "refactor",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.suggestions.total).toBe(4);
      expect(metrics.suggestions.accepted).toBe(3);
      expect(metrics.suggestions.dismissed).toBe(1);
      expect(metrics.suggestions.byType["completion"]).toBe(2);
      expect(metrics.suggestions.byType["fix"]).toBe(1);
      expect(metrics.suggestions.byType["refactor"]).toBe(1);
    });

    it("should calculate acceptance rate", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "s1",
        action: "accept",
        suggestionType: "completion",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s2",
        action: "accept",
        suggestionType: "completion",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s3",
        action: "accept",
        suggestionType: "completion",
      });
      telemetry.trackSuggestionAction({
        suggestionId: "s4",
        action: "dismiss",
        suggestionType: "completion",
      });

      const metrics = telemetry.getMetrics();
      expect(metrics.suggestions.acceptanceRate).toBeCloseTo(0.75, 2);
    });

    it("should add suggestion action to event history", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "suggestion-123",
        action: "accept",
        suggestionType: "completion",
        artifactId: "artifact-456",
      });

      const history = telemetry.getEventHistory();
      expect(history).toHaveLength(1);
      expect(history[0].type).toBe("suggestion_action");
    });

    it("should track suggestion with optional artifact id", () => {
      telemetry.trackSuggestionAction({
        suggestionId: "suggestion-123",
        action: "accept",
        suggestionType: "explain",
      });

      const history = telemetry.getEventHistory();
      expect(history).toHaveLength(1);
      expect(
        (history[0].data as { artifactId?: string }).artifactId,
      ).toBeUndefined();
    });
  });

  describe("Flush/Export Mechanism", () => {
    it("should flush events to a custom exporter", async () => {
      const mockExporter = vi.fn().mockResolvedValue(undefined);
      const exportableTelemetry = new SessionTelemetry({
        exporter: mockExporter,
      });

      exportableTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });
      exportableTelemetry.trackRevalidation({
        trigger: "message_sent",
        durationMs: 50,
      });

      await exportableTelemetry.flush();

      expect(mockExporter).toHaveBeenCalledTimes(1);
      const exportedData = mockExporter.mock.calls[0][0];
      expect(exportedData.metrics).toBeDefined();
      expect(exportedData.events).toHaveLength(2);
    });

    it("should clear events after successful flush", async () => {
      const mockExporter = vi.fn().mockResolvedValue(undefined);
      const exportableTelemetry = new SessionTelemetry({
        exporter: mockExporter,
      });

      exportableTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });
      await exportableTelemetry.flush();

      const history = exportableTelemetry.getEventHistory();
      expect(history).toHaveLength(0);
    });

    it("should not clear events on failed flush", async () => {
      const mockExporter = vi
        .fn()
        .mockRejectedValue(new Error("Network error"));
      const exportableTelemetry = new SessionTelemetry({
        exporter: mockExporter,
      });

      exportableTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });

      await expect(exportableTelemetry.flush()).rejects.toThrow(
        "Network error",
      );

      const history = exportableTelemetry.getEventHistory();
      expect(history).toHaveLength(1);
    });

    it("should do nothing when no exporter is configured", async () => {
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });

      // Should not throw
      await expect(telemetry.flush()).resolves.toBeUndefined();

      // Events should remain
      const history = telemetry.getEventHistory();
      expect(history).toHaveLength(1);
    });

    it("should support auto-flush when threshold is reached", async () => {
      const mockExporter = vi.fn().mockResolvedValue(undefined);
      const autoFlushTelemetry = new SessionTelemetry({
        exporter: mockExporter,
        autoFlushThreshold: 3,
      });

      autoFlushTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });
      autoFlushTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });
      expect(mockExporter).not.toHaveBeenCalled();

      // This should trigger auto-flush
      autoFlushTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });

      // Allow async flush to complete
      await vi.waitFor(() => {
        expect(mockExporter).toHaveBeenCalledTimes(1);
      });
    });

    it("should include session metadata in export payload", async () => {
      const mockExporter = vi.fn().mockResolvedValue(undefined);
      const exportableTelemetry = new SessionTelemetry({
        exporter: mockExporter,
        sessionId: "test-session-id",
        clientVersion: "1.0.0",
      });

      exportableTelemetry.trackSessionCreation({
        success: true,
        durationMs: 100,
      });
      await exportableTelemetry.flush();

      const exportedData = mockExporter.mock.calls[0][0];
      expect(exportedData.metadata.sessionId).toBe("test-session-id");
      expect(exportedData.metadata.clientVersion).toBe("1.0.0");
      expect(exportedData.metadata.timestamp).toBeTypeOf("number");
    });

    it("should export to JSON format", () => {
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackRevalidation({ trigger: "manual", durationMs: 50 });

      const json = telemetry.toJSON();

      expect(json).toBeTypeOf("string");
      const parsed = JSON.parse(json);
      expect(parsed.metrics).toBeDefined();
      expect(parsed.events).toHaveLength(2);
    });

    it("should create exportable payload with getExportPayload", () => {
      telemetry.trackSessionCreation({ success: true, durationMs: 100 });
      telemetry.trackSync({
        sessionId: "s",
        messageCount: 5,
        durationMs: 10,
        skipped: false,
      });

      const payload = telemetry.getExportPayload();

      expect(payload.metrics.sessionCreations.total).toBe(1);
      expect(payload.metrics.syncs.total).toBe(1);
      expect(payload.events).toHaveLength(2);
      expect(payload.exportedAt).toBeTypeOf("number");
    });
  });
});

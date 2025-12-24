/**
 * Session Telemetry
 *
 * Provides telemetry tracking for session operations:
 * - Session creation success/failure rates
 * - Revalidation frequency and timing
 * - Sync timing and skip rates
 *
 * Usage:
 * ```tsx
 * import { sessionTelemetry } from "../utils/sessionTelemetry";
 *
 * // Track session creation
 * const startTime = Date.now();
 * try {
 *   const session = await createSession();
 *   sessionTelemetry.trackSessionCreation({
 *     sessionId: session.id,
 *     success: true,
 *     durationMs: Date.now() - startTime,
 *   });
 * } catch (error) {
 *   sessionTelemetry.trackSessionCreation({
 *     success: false,
 *     durationMs: Date.now() - startTime,
 *     error: error.message,
 *   });
 * }
 * ```
 */

import { devLogger } from "./devLogger";

// =============================================================================
// Types
// =============================================================================

export interface SessionCreationEvent {
  sessionId?: string;
  sessionName?: string;
  success: boolean;
  durationMs: number;
  error?: string;
}

export interface RevalidationEvent {
  sessionId?: string;
  trigger: "message_sent" | "auto" | "manual" | string;
  durationMs: number;
  debounced?: boolean;
}

export interface SyncEvent {
  sessionId: string;
  messageCount: number;
  durationMs: number;
  skipped: boolean;
  skipReason?: "pending_mutation" | "no_loader_data" | string;
}

export interface ArtifactSaveEvent {
  artifactId: string;
  success: boolean;
  durationMs: number;
  error?: string;
  contentLength?: number;
}

export interface ArtifactDeleteEvent {
  artifactId: string;
  success: boolean;
  durationMs: number;
  error?: string;
}

export interface SuggestionActionEvent {
  suggestionId: string;
  action: "accept" | "dismiss";
  suggestionType: string;
  artifactId?: string;
}

export interface CanvasActionEvent {
  artifactId: string;
  action: "review" | "comment" | "fix" | "explain" | "test" | "port" | string;
  contentType?: string;
  language?: string;
  sessionId?: string;
  success: boolean;
  durationMs: number;
  error?: string;
}

export interface TelemetryEvent {
  type:
    | "session_creation"
    | "revalidation"
    | "sync"
    | "artifact_save"
    | "artifact_delete"
    | "suggestion_action"
    | "canvas_action";
  timestamp: number;
  data:
    | SessionCreationEvent
    | RevalidationEvent
    | SyncEvent
    | ArtifactSaveEvent
    | ArtifactDeleteEvent
    | SuggestionActionEvent
    | CanvasActionEvent;
}

export interface SessionTelemetryMetrics {
  sessionCreations: {
    total: number;
    successful: number;
    failed: number;
    successRate: number;
    avgDurationMs: number;
    lastError?: string;
  };
  revalidations: {
    total: number;
    executed: number;
    debounced: number;
    avgDurationMs: number;
    byTrigger: Record<string, number>;
  };
  syncs: {
    total: number;
    executed: number;
    skipped: number;
    avgDurationMs: number;
    avgMessageCount: number;
  };
  artifactOperations: {
    saves: {
      total: number;
      successful: number;
      failed: number;
      successRate: number;
      avgDurationMs: number;
      avgContentLength: number;
      lastError?: string;
    };
    deletes: {
      total: number;
      successful: number;
      failed: number;
      successRate: number;
      avgDurationMs: number;
      lastError?: string;
    };
  };
  suggestions: {
    total: number;
    accepted: number;
    dismissed: number;
    acceptanceRate: number;
    byType: Record<string, number>;
  };
  canvasActions: {
    total: number;
    successful: number;
    failed: number;
    successRate: number;
    avgDurationMs: number;
    byAction: Record<string, number>;
    lastError?: string;
  };
}

/**
 * Telemetry export payload
 */
export interface TelemetryExportPayload {
  metrics: SessionTelemetryMetrics;
  events: TelemetryEvent[];
  metadata: {
    sessionId?: string;
    clientVersion?: string;
    timestamp: number;
  };
  exportedAt: number;
}

/**
 * Telemetry exporter function type
 */
export type TelemetryExporter = (
  payload: TelemetryExportPayload,
) => Promise<void>;

interface SessionTelemetryOptions {
  debug?: boolean;
  maxHistorySize?: number;
  /** Custom exporter function for sending telemetry to a backend */
  exporter?: TelemetryExporter;
  /** Auto-flush threshold (number of events to trigger auto-flush) */
  autoFlushThreshold?: number;
  /** Session identifier for export metadata */
  sessionId?: string;
  /** Client version for export metadata */
  clientVersion?: string;
}

// =============================================================================
// Implementation
// =============================================================================

export class SessionTelemetry {
  private options: {
    debug: boolean;
    maxHistorySize: number;
    exporter?: TelemetryExporter;
    autoFlushThreshold?: number;
    sessionId?: string;
    clientVersion?: string;
  };
  private eventHistory: TelemetryEvent[] = [];

  // Session creation metrics
  private sessionCreationTotal = 0;
  private sessionCreationSuccessful = 0;
  private sessionCreationFailed = 0;
  private sessionCreationDurations: number[] = [];
  private sessionCreationLastError?: string;

  // Revalidation metrics
  private revalidationTotal = 0;
  private revalidationExecuted = 0;
  private revalidationDebounced = 0;
  private revalidationDurations: number[] = [];
  private revalidationByTrigger: Record<string, number> = {};

  // Sync metrics
  private syncTotal = 0;
  private syncExecuted = 0;
  private syncSkipped = 0;
  private syncDurations: number[] = [];
  private syncMessageCounts: number[] = [];

  // Artifact save metrics
  private artifactSaveTotal = 0;
  private artifactSaveSuccessful = 0;
  private artifactSaveFailed = 0;
  private artifactSaveDurations: number[] = [];
  private artifactSaveContentLengths: number[] = [];
  private artifactSaveLastError?: string;

  // Artifact delete metrics
  private artifactDeleteTotal = 0;
  private artifactDeleteSuccessful = 0;
  private artifactDeleteFailed = 0;
  private artifactDeleteDurations: number[] = [];
  private artifactDeleteLastError?: string;

  // Suggestion action metrics
  private suggestionTotal = 0;
  private suggestionAccepted = 0;
  private suggestionDismissed = 0;
  private suggestionByType: Record<string, number> = {};

  // Canvas action metrics
  private canvasActionTotal = 0;
  private canvasActionSuccessful = 0;
  private canvasActionFailed = 0;
  private canvasActionDurations: number[] = [];
  private canvasActionByType: Record<string, number> = {};
  private canvasActionLastError?: string;

  constructor(options: SessionTelemetryOptions = {}) {
    this.options = {
      debug: options.debug ?? false,
      maxHistorySize: options.maxHistorySize ?? 100,
      exporter: options.exporter,
      autoFlushThreshold: options.autoFlushThreshold,
      sessionId: options.sessionId,
      clientVersion: options.clientVersion,
    };
  }

  /**
   * Track session creation event
   */
  trackSessionCreation(event: SessionCreationEvent): void {
    this.sessionCreationTotal++;

    if (event.success) {
      this.sessionCreationSuccessful++;
    } else {
      this.sessionCreationFailed++;
      if (event.error) {
        this.sessionCreationLastError = event.error;
      }
    }

    this.sessionCreationDurations.push(event.durationMs);
    this.addToHistory("session_creation", event);
    this.log("Session creation tracked", event);
  }

  /**
   * Track revalidation event
   */
  trackRevalidation(event: RevalidationEvent): void {
    this.revalidationTotal++;

    if (event.debounced) {
      this.revalidationDebounced++;
    } else {
      this.revalidationExecuted++;
      this.revalidationDurations.push(event.durationMs);
    }

    this.revalidationByTrigger[event.trigger] =
      (this.revalidationByTrigger[event.trigger] || 0) + 1;

    this.addToHistory("revalidation", event);
    this.log("Revalidation tracked", event);
  }

  /**
   * Track sync event
   */
  trackSync(event: SyncEvent): void {
    this.syncTotal++;

    if (event.skipped) {
      this.syncSkipped++;
    } else {
      this.syncExecuted++;
      this.syncDurations.push(event.durationMs);
    }

    this.syncMessageCounts.push(event.messageCount);
    this.addToHistory("sync", event);
    this.log("Sync tracked", event);
  }

  /**
   * Track artifact save event
   */
  trackArtifactSave(event: ArtifactSaveEvent): void {
    this.artifactSaveTotal++;

    if (event.success) {
      this.artifactSaveSuccessful++;
    } else {
      this.artifactSaveFailed++;
      if (event.error) {
        this.artifactSaveLastError = event.error;
      }
    }

    this.artifactSaveDurations.push(event.durationMs);
    if (event.contentLength !== undefined) {
      this.artifactSaveContentLengths.push(event.contentLength);
    }

    this.addToHistory("artifact_save", event);
    this.log("Artifact save tracked", event);
  }

  /**
   * Track artifact delete event
   */
  trackArtifactDelete(event: ArtifactDeleteEvent): void {
    this.artifactDeleteTotal++;

    if (event.success) {
      this.artifactDeleteSuccessful++;
    } else {
      this.artifactDeleteFailed++;
      if (event.error) {
        this.artifactDeleteLastError = event.error;
      }
    }

    this.artifactDeleteDurations.push(event.durationMs);
    this.addToHistory("artifact_delete", event);
    this.log("Artifact delete tracked", event);
  }

  /**
   * Track suggestion action event (accept/dismiss)
   */
  trackSuggestionAction(event: SuggestionActionEvent): void {
    this.suggestionTotal++;

    if (event.action === "accept") {
      this.suggestionAccepted++;
    } else {
      this.suggestionDismissed++;
    }

    this.suggestionByType[event.suggestionType] =
      (this.suggestionByType[event.suggestionType] || 0) + 1;

    this.addToHistory("suggestion_action", event);
    this.log("Suggestion action tracked", event);
  }

  /**
   * Track canvas action event (review, comment, fix, etc.)
   */
  trackCanvasAction(event: CanvasActionEvent): void {
    this.canvasActionTotal++;

    if (event.success) {
      this.canvasActionSuccessful++;
    } else {
      this.canvasActionFailed++;
      if (event.error) {
        this.canvasActionLastError = event.error;
      }
    }

    this.canvasActionDurations.push(event.durationMs);
    this.canvasActionByType[event.action] =
      (this.canvasActionByType[event.action] || 0) + 1;

    this.addToHistory("canvas_action", event);
    this.log("Canvas action tracked", event);
  }

  /**
   * Get current metrics
   */
  getMetrics(): SessionTelemetryMetrics {
    return {
      sessionCreations: {
        total: this.sessionCreationTotal,
        successful: this.sessionCreationSuccessful,
        failed: this.sessionCreationFailed,
        successRate:
          this.sessionCreationTotal > 0
            ? this.sessionCreationSuccessful / this.sessionCreationTotal
            : 0,
        avgDurationMs: this.average(this.sessionCreationDurations),
        lastError: this.sessionCreationLastError,
      },
      revalidations: {
        total: this.revalidationTotal,
        executed: this.revalidationExecuted,
        debounced: this.revalidationDebounced,
        avgDurationMs: this.average(this.revalidationDurations),
        byTrigger: { ...this.revalidationByTrigger },
      },
      syncs: {
        total: this.syncTotal,
        executed: this.syncExecuted,
        skipped: this.syncSkipped,
        avgDurationMs: this.average(this.syncDurations),
        avgMessageCount: this.average(this.syncMessageCounts),
      },
      artifactOperations: {
        saves: {
          total: this.artifactSaveTotal,
          successful: this.artifactSaveSuccessful,
          failed: this.artifactSaveFailed,
          successRate:
            this.artifactSaveTotal > 0
              ? this.artifactSaveSuccessful / this.artifactSaveTotal
              : 0,
          avgDurationMs: this.average(this.artifactSaveDurations),
          avgContentLength: this.average(this.artifactSaveContentLengths),
          lastError: this.artifactSaveLastError,
        },
        deletes: {
          total: this.artifactDeleteTotal,
          successful: this.artifactDeleteSuccessful,
          failed: this.artifactDeleteFailed,
          successRate:
            this.artifactDeleteTotal > 0
              ? this.artifactDeleteSuccessful / this.artifactDeleteTotal
              : 0,
          avgDurationMs: this.average(this.artifactDeleteDurations),
          lastError: this.artifactDeleteLastError,
        },
      },
      suggestions: {
        total: this.suggestionTotal,
        accepted: this.suggestionAccepted,
        dismissed: this.suggestionDismissed,
        acceptanceRate:
          this.suggestionTotal > 0
            ? this.suggestionAccepted / this.suggestionTotal
            : 0,
        byType: { ...this.suggestionByType },
      },
      canvasActions: {
        total: this.canvasActionTotal,
        successful: this.canvasActionSuccessful,
        failed: this.canvasActionFailed,
        successRate:
          this.canvasActionTotal > 0
            ? this.canvasActionSuccessful / this.canvasActionTotal
            : 0,
        avgDurationMs: this.average(this.canvasActionDurations),
        byAction: { ...this.canvasActionByType },
        lastError: this.canvasActionLastError,
      },
    };
  }

  /**
   * Get event history
   */
  getEventHistory(): TelemetryEvent[] {
    return [...this.eventHistory];
  }

  /**
   * Reset all metrics
   */
  reset(): void {
    this.sessionCreationTotal = 0;
    this.sessionCreationSuccessful = 0;
    this.sessionCreationFailed = 0;
    this.sessionCreationDurations = [];
    this.sessionCreationLastError = undefined;

    this.revalidationTotal = 0;
    this.revalidationExecuted = 0;
    this.revalidationDebounced = 0;
    this.revalidationDurations = [];
    this.revalidationByTrigger = {};

    this.syncTotal = 0;
    this.syncExecuted = 0;
    this.syncSkipped = 0;
    this.syncDurations = [];
    this.syncMessageCounts = [];

    this.artifactSaveTotal = 0;
    this.artifactSaveSuccessful = 0;
    this.artifactSaveFailed = 0;
    this.artifactSaveDurations = [];
    this.artifactSaveContentLengths = [];
    this.artifactSaveLastError = undefined;

    this.artifactDeleteTotal = 0;
    this.artifactDeleteSuccessful = 0;
    this.artifactDeleteFailed = 0;
    this.artifactDeleteDurations = [];
    this.artifactDeleteLastError = undefined;

    this.suggestionTotal = 0;
    this.suggestionAccepted = 0;
    this.suggestionDismissed = 0;
    this.suggestionByType = {};

    this.canvasActionTotal = 0;
    this.canvasActionSuccessful = 0;
    this.canvasActionFailed = 0;
    this.canvasActionDurations = [];
    this.canvasActionByType = {};
    this.canvasActionLastError = undefined;

    this.eventHistory = [];
  }

  /**
   * Get exportable payload containing metrics and events
   */
  getExportPayload(): TelemetryExportPayload {
    return {
      metrics: this.getMetrics(),
      events: this.getEventHistory(),
      metadata: {
        sessionId: this.options.sessionId,
        clientVersion: this.options.clientVersion,
        timestamp: Date.now(),
      },
      exportedAt: Date.now(),
    };
  }

  /**
   * Export telemetry as JSON string
   */
  toJSON(): string {
    return JSON.stringify(this.getExportPayload());
  }

  /**
   * Flush events to the configured exporter
   * Clears event history on successful flush
   */
  async flush(): Promise<void> {
    // If no exporter configured, do nothing
    if (!this.options.exporter) {
      return;
    }

    const payload = this.getExportPayload();

    // Call exporter - if it throws, events are preserved
    await this.options.exporter(payload);

    // Clear event history on successful flush
    this.eventHistory = [];
  }

  /**
   * Calculate average of an array of numbers
   */
  private average(arr: number[]): number {
    if (arr.length === 0) return 0;
    return arr.reduce((a, b) => a + b, 0) / arr.length;
  }

  /**
   * Add event to history with size limit and auto-flush support
   */
  private addToHistory(
    type: TelemetryEvent["type"],
    data:
      | SessionCreationEvent
      | RevalidationEvent
      | SyncEvent
      | ArtifactSaveEvent
      | ArtifactDeleteEvent
      | SuggestionActionEvent
      | CanvasActionEvent,
  ): void {
    this.eventHistory.push({
      type,
      timestamp: Date.now(),
      data,
    });

    // Trim history if over limit
    while (this.eventHistory.length > this.options.maxHistorySize) {
      this.eventHistory.shift();
    }

    // Auto-flush if threshold reached
    if (
      this.options.autoFlushThreshold &&
      this.options.exporter &&
      this.eventHistory.length >= this.options.autoFlushThreshold
    ) {
      // Fire and forget - don't block event tracking
      this.flush().catch((error) => {
        this.log("Auto-flush failed", error);
      });
    }
  }

  /**
   * Log event if debug mode is enabled
   */
  private log(message: string, data: unknown): void {
    if (this.options.debug) {
      devLogger.debug(`[SessionTelemetry] ${message}`, data);
    }
  }
}

// =============================================================================
// Singleton Instance
// =============================================================================

/**
 * Global session telemetry instance
 */
export const sessionTelemetry = new SessionTelemetry({
  debug: process.env.NODE_ENV === "development",
});

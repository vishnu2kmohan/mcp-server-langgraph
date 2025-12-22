/**
 * HeartAggregator
 *
 * Sprint 4 - Phase 3.2: HEART Tracker Enhancement
 *
 * Standalone module for HEART event aggregation and batching.
 * Extracted from useHeartMetricsTracker for reusability.
 *
 * Features:
 * - Event queuing with timestamps
 * - Auto-flush on interval (default 30s) or max batch size (default 50)
 * - Session context attachment to events
 * - Statistics tracking
 * - Pause/resume functionality
 *
 * @example
 * ```typescript
 * const aggregator = new HeartAggregator({
 *   flushIntervalMs: 30000,
 *   maxBatchSize: 50,
 * });
 *
 * // Set session context
 * aggregator.setSessionContext({ sessionId: "123", persona: "admin" });
 *
 * // Queue events
 * aggregator.queueEvent("engagement", { feature: "chat", action: "send" });
 *
 * // Manual flush
 * await aggregator.flush();
 *
 * // Get statistics
 * console.log(aggregator.getStats());
 * ```
 */

import { devLogger } from "../utils/devLogger";

const logger = devLogger.withPrefix("[HeartAggregator]");

// =============================================================================
// Types
// =============================================================================

/**
 * Queued event structure
 */
export interface QueuedEvent {
  event_type: string;
  payload: Record<string, unknown>;
  timestamp: number;
}

/**
 * Session context attached to events
 */
export interface SessionContext {
  sessionId?: string;
  persona?: string;
  username?: string;
  [key: string]: unknown;
}

/**
 * Aggregator configuration
 */
export interface HeartAggregatorConfig {
  /** Flush interval in milliseconds (default: 30000) */
  flushIntervalMs?: number;
  /** Maximum batch size before auto-flush (default: 50) */
  maxBatchSize?: number;
  /** Batch endpoint URL (default: /api/v1/metrics/heart/batch) */
  batchEndpoint?: string;
  /** Whether aggregator is enabled (default: true) */
  enabled?: boolean;
}

/**
 * Required configuration with all fields
 */
interface RequiredConfig {
  flushIntervalMs: number;
  maxBatchSize: number;
  batchEndpoint: string;
  enabled: boolean;
}

/**
 * Aggregator statistics
 */
export interface AggregatorStats {
  /** Total events queued */
  totalQueued: number;
  /** Total events successfully flushed */
  totalFlushed: number;
  /** Number of successful flush operations */
  flushCount: number;
  /** Number of failed flush attempts */
  failedFlushes: number;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_FLUSH_INTERVAL_MS = 30000;
const DEFAULT_MAX_BATCH_SIZE = 50;
const DEFAULT_BATCH_ENDPOINT = "/api/v1/metrics/heart/batch";

// =============================================================================
// HeartAggregator Class
// =============================================================================

/**
 * HEART event aggregator with batching support
 */
export class HeartAggregator {
  private config: RequiredConfig;
  private queue: QueuedEvent[] = [];
  private sessionContext: SessionContext = {};
  private sessionStartTime: number = Date.now();
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private isPaused: boolean = false;
  private stats: AggregatorStats = {
    totalQueued: 0,
    totalFlushed: 0,
    flushCount: 0,
    failedFlushes: 0,
  };

  constructor(config: HeartAggregatorConfig = {}) {
    this.config = {
      flushIntervalMs: config.flushIntervalMs ?? DEFAULT_FLUSH_INTERVAL_MS,
      maxBatchSize: config.maxBatchSize ?? DEFAULT_MAX_BATCH_SIZE,
      batchEndpoint: config.batchEndpoint ?? DEFAULT_BATCH_ENDPOINT,
      enabled: config.enabled ?? true,
    };

    if (this.config.enabled) {
      this.startFlushTimer();
    }
  }

  // ===========================================================================
  // Configuration
  // ===========================================================================

  /**
   * Get current configuration
   */
  getConfig(): RequiredConfig {
    return { ...this.config };
  }

  // ===========================================================================
  // Event Queuing
  // ===========================================================================

  /**
   * Queue an event for batching
   */
  queueEvent(eventType: string, payload: Record<string, unknown>): void {
    if (!this.config.enabled) {
      return;
    }

    const event: QueuedEvent = {
      event_type: eventType,
      payload: { ...payload, ...this.sessionContext },
      timestamp: Date.now(),
    };

    this.queue.push(event);
    this.stats.totalQueued++;

    // Auto-flush if max batch size reached
    if (this.queue.length >= this.config.maxBatchSize) {
      void this.flush();
    }
  }

  /**
   * Get number of pending events
   */
  getPendingCount(): number {
    return this.queue.length;
  }

  /**
   * Get copy of pending events (for debugging/testing)
   */
  getPendingEvents(): QueuedEvent[] {
    return [...this.queue];
  }

  // ===========================================================================
  // Flush Operations
  // ===========================================================================

  /**
   * Flush all pending events to backend
   */
  async flush(): Promise<void> {
    if (this.queue.length === 0) {
      return;
    }

    const events = [...this.queue];
    this.queue = [];

    const sessionDuration = Date.now() - this.sessionStartTime;

    try {
      const response = await fetch(this.config.batchEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          events,
          session_duration: sessionDuration,
        }),
      });

      if (response.ok) {
        this.stats.totalFlushed += events.length;
        this.stats.flushCount++;
      } else {
        this.stats.failedFlushes++;
        logger.warn(`Batch flush failed with status ${response.status}`);
      }
    } catch (error) {
      this.stats.failedFlushes++;
      logger.warn("Batch flush failed", error);
    }
  }

  // ===========================================================================
  // Timer Control
  // ===========================================================================

  /**
   * Start the auto-flush timer
   */
  private startFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
    }

    this.flushTimer = setInterval(() => {
      if (!this.isPaused && this.queue.length > 0) {
        void this.flush();
      }
    }, this.config.flushIntervalMs);
  }

  /**
   * Stop the auto-flush timer
   */
  private stopFlushTimer(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /**
   * Pause auto-flushing
   */
  pause(): void {
    this.isPaused = true;
  }

  /**
   * Resume auto-flushing
   */
  resume(): void {
    this.isPaused = false;
    if (this.config.enabled && !this.flushTimer) {
      this.startFlushTimer();
    }
  }

  // ===========================================================================
  // Session Context
  // ===========================================================================

  /**
   * Set session start time for duration calculation
   */
  setSessionStartTime(timestamp: number): void {
    this.sessionStartTime = timestamp;
  }

  /**
   * Set session context to attach to all events
   */
  setSessionContext(context: Partial<SessionContext>): void {
    this.sessionContext = { ...this.sessionContext, ...context };
  }

  /**
   * Get current session context
   */
  getSessionContext(): SessionContext {
    return { ...this.sessionContext };
  }

  /**
   * Clear session context
   */
  clearSessionContext(): void {
    this.sessionContext = {};
  }

  // ===========================================================================
  // Statistics
  // ===========================================================================

  /**
   * Get aggregator statistics
   */
  getStats(): AggregatorStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats = {
      totalQueued: 0,
      totalFlushed: 0,
      flushCount: 0,
      failedFlushes: 0,
    };
  }

  // ===========================================================================
  // Enable/Disable
  // ===========================================================================

  /**
   * Enable the aggregator
   */
  enable(): void {
    this.config.enabled = true;
    this.startFlushTimer();
  }

  /**
   * Disable the aggregator and flush pending events
   */
  async disable(): Promise<void> {
    this.config.enabled = false;
    this.stopFlushTimer();
    await this.flush();
  }

  // ===========================================================================
  // Cleanup
  // ===========================================================================

  /**
   * Destroy the aggregator
   * @param flushPending Whether to flush pending events before destroy
   */
  async destroy(flushPending: boolean = false): Promise<void> {
    if (flushPending && this.queue.length > 0) {
      await this.flush();
    }

    this.stopFlushTimer();
    this.queue = [];
    this.sessionContext = {};
  }
}

export default HeartAggregator;

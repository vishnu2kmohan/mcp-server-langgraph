/**
 * errorReporter
 *
 * Sprint 3 - Phase 2.4: Error Reporting Pipeline
 *
 * Utility for reporting errors to backend telemetry.
 * Features:
 * - Posts errors to /api/v1/errors/report
 * - Includes stack traces, user context, session info
 * - Rate limiting (max 10 reports/minute by default)
 * - Batch mode for high-volume scenarios
 * - Integration with ClassifiedError types
 *
 * @example
 * ```tsx
 * const reporter = new ErrorReporter();
 *
 * try {
 *   await riskyOperation();
 * } catch (error) {
 *   await reporter.report(error, {
 *     userContext: { userId: 'user-123', persona: 'alice-builder' },
 *     customContext: { component: 'ChatPage', action: 'sendMessage' },
 *   });
 * }
 * ```
 */

import type { ClassifiedError, ErrorCategory } from "../errors/ErrorTypes";

// =============================================================================
// Types
// =============================================================================

/**
 * User context for error reports
 */
export interface ErrorUserContext {
  userId?: string;
  persona?: string;
  sessionId?: string;
}

/**
 * Browser environment info
 */
export interface BrowserInfo {
  userAgent?: string;
  url?: string;
  referrer?: string;
  language?: string;
  screenSize?: string;
}

/**
 * Error report payload
 */
export interface ErrorReport {
  /** Unique report ID (generated client-side) */
  id: string;
  /** Error message */
  message: string;
  /** Stack trace if available */
  stack?: string;
  /** Error category */
  category: ErrorCategory;
  /** Error code */
  code?: string;
  /** HTTP status code if applicable */
  statusCode?: number;
  /** Whether error is recoverable */
  recoverable?: boolean;
  /** Timestamp when error occurred */
  timestamp: string;
  /** User context */
  userContext?: ErrorUserContext;
  /** Browser info */
  browserInfo: BrowserInfo;
  /** Custom context */
  customContext?: Record<string, unknown>;
}

/**
 * Report creation options
 */
export interface CreateReportOptions {
  userContext?: ErrorUserContext;
  customContext?: Record<string, unknown>;
}

/**
 * ErrorReporter configuration
 */
export interface ErrorReporterConfig {
  /** API endpoint for single reports (default: /api/v1/errors/report) */
  endpoint?: string;
  /** API endpoint for batch reports */
  batchEndpoint?: string;
  /** Maximum reports per minute (default: 10) */
  maxReportsPerMinute?: number;
  /** Whether reporting is enabled (default: true) */
  enabled?: boolean;
  /** Use batch mode (default: false) */
  batchMode?: boolean;
  /** Batch interval in ms (default: 5000) */
  batchInterval?: number;
  /** Maximum batch size (default: 50) */
  maxBatchSize?: number;
}

/**
 * Report result
 */
export interface ReportResult {
  success: boolean;
  reportId?: string;
  error?: Error;
  rateLimited?: boolean;
  disabled?: boolean;
}

/**
 * Reporter statistics
 */
export interface ReporterStats {
  totalReported: number;
  rateLimited: number;
  failed: number;
  queued: number;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_ENDPOINT = "/api/v1/errors/report";
const DEFAULT_BATCH_ENDPOINT = "/api/v1/errors/report/batch";
const DEFAULT_MAX_REPORTS_PER_MINUTE = 10;
const DEFAULT_BATCH_INTERVAL = 5000;
const DEFAULT_MAX_BATCH_SIZE = 50;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Generate unique ID
 */
function generateId(): string {
  return `err-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`;
}

/**
 * Get browser info
 */
function getBrowserInfo(): BrowserInfo {
  if (typeof window === "undefined") {
    return { url: "" };
  }

  return {
    userAgent: navigator.userAgent,
    url: window.location.href,
    referrer: document.referrer || undefined,
    language: navigator.language,
    screenSize: `${window.screen.width}x${window.screen.height}`,
  };
}

/**
 * Check if value is a ClassifiedError
 */
function isClassifiedError(error: unknown): error is ClassifiedError {
  return (
    typeof error === "object" &&
    error !== null &&
    "category" in error &&
    "message" in error
  );
}

// =============================================================================
// createErrorReport
// =============================================================================

/**
 * Create an error report from an Error or ClassifiedError
 */
export function createErrorReport(
  error: Error | ClassifiedError,
  options: CreateReportOptions = {}
): ErrorReport {
  const { userContext, customContext } = options;

  if (isClassifiedError(error)) {
    // Extract stack from originalError if it's an Error instance
    const originalStack =
      error.originalError instanceof Error
        ? error.originalError.stack
        : undefined;

    // Convert "maybe" to undefined for boolean compatibility
    const isRecoverable =
      error.recoverable === "maybe" ? undefined : error.recoverable;

    return {
      id: generateId(),
      message: error.message,
      stack: originalStack,
      category: error.category,
      code: error.code,
      statusCode: error.statusCode,
      recoverable: isRecoverable,
      timestamp: new Date().toISOString(),
      userContext,
      browserInfo: getBrowserInfo(),
      customContext,
    };
  }

  // Plain Error
  return {
    id: generateId(),
    message: error.message,
    stack: error.stack,
    category: "unknown",
    timestamp: new Date().toISOString(),
    userContext,
    browserInfo: getBrowserInfo(),
    customContext,
  };
}

// =============================================================================
// ErrorReporter Class
// =============================================================================

/**
 * Error reporter for sending errors to backend telemetry
 */
export class ErrorReporter {
  private readonly config: Required<ErrorReporterConfig>;
  private reportTimestamps: number[] = [];
  private queue: ErrorReport[] = [];
  private batchTimer: ReturnType<typeof setInterval> | null = null;
  private stats: ReporterStats = {
    totalReported: 0,
    rateLimited: 0,
    failed: 0,
    queued: 0,
  };

  constructor(config: ErrorReporterConfig = {}) {
    this.config = {
      endpoint: config.endpoint ?? DEFAULT_ENDPOINT,
      batchEndpoint: config.batchEndpoint ?? DEFAULT_BATCH_ENDPOINT,
      maxReportsPerMinute: config.maxReportsPerMinute ?? DEFAULT_MAX_REPORTS_PER_MINUTE,
      enabled: config.enabled ?? true,
      batchMode: config.batchMode ?? false,
      batchInterval: config.batchInterval ?? DEFAULT_BATCH_INTERVAL,
      maxBatchSize: config.maxBatchSize ?? DEFAULT_MAX_BATCH_SIZE,
    };

    // Start batch timer if in batch mode
    if (this.config.batchMode) {
      this.startBatchTimer();
    }
  }

  /**
   * Report an error
   */
  async report(
    error: Error | ClassifiedError,
    options: CreateReportOptions = {}
  ): Promise<ReportResult> {
    // Check if disabled
    if (!this.config.enabled) {
      return { success: false, disabled: true };
    }

    // Check rate limit
    if (this.isRateLimited()) {
      this.stats.rateLimited++;
      return { success: false, rateLimited: true };
    }

    const report = createErrorReport(error, options);

    // Batch mode: queue the report
    if (this.config.batchMode) {
      this.queue.push(report);
      this.stats.queued++;

      // Flush if queue is full
      if (this.queue.length >= this.config.maxBatchSize) {
        await this.flush();
      }

      return { success: true, reportId: report.id };
    }

    // Immediate mode: send now
    return this.sendReport(report);
  }

  /**
   * Send single report to backend
   */
  private async sendReport(report: ErrorReport): Promise<ReportResult> {
    try {
      this.recordReportTimestamp();

      const response = await fetch(this.config.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(report),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = (await response.json()) as { reportId?: string };
      this.stats.totalReported++;

      return {
        success: true,
        reportId: data.reportId ?? report.id,
      };
    } catch (err) {
      this.stats.failed++;
      return {
        success: false,
        error: err instanceof Error ? err : new Error(String(err)),
      };
    }
  }

  /**
   * Flush batch queue
   */
  async flush(): Promise<void> {
    if (this.queue.length === 0) {
      return;
    }

    const reports = [...this.queue];
    this.queue = [];
    this.stats.queued = 0;

    try {
      const response = await fetch(this.config.batchEndpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reports }),
      });

      if (response.ok) {
        this.stats.totalReported += reports.length;
      } else {
        this.stats.failed += reports.length;
      }
    } catch {
      this.stats.failed += reports.length;
    }
  }

  /**
   * Check if rate limited
   */
  private isRateLimited(): boolean {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove timestamps older than 1 minute
    this.reportTimestamps = this.reportTimestamps.filter((ts) => ts > oneMinuteAgo);

    return this.reportTimestamps.length >= this.config.maxReportsPerMinute;
  }

  /**
   * Record a report timestamp for rate limiting
   */
  private recordReportTimestamp(): void {
    this.reportTimestamps.push(Date.now());
  }

  /**
   * Start batch timer
   */
  private startBatchTimer(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
    }

    this.batchTimer = setInterval(() => {
      void this.flush();
    }, this.config.batchInterval);
  }

  /**
   * Stop batch timer
   */
  private stopBatchTimer(): void {
    if (this.batchTimer) {
      clearInterval(this.batchTimer);
      this.batchTimer = null;
    }
  }

  /**
   * Enable reporting
   */
  enable(): void {
    this.config.enabled = true;
    if (this.config.batchMode) {
      this.startBatchTimer();
    }
  }

  /**
   * Disable reporting
   */
  disable(): void {
    this.config.enabled = false;
    this.stopBatchTimer();
  }

  /**
   * Get queue size (for batch mode)
   */
  getQueueSize(): number {
    return this.queue.length;
  }

  /**
   * Get statistics
   */
  getStats(): ReporterStats {
    return { ...this.stats };
  }

  /**
   * Reset statistics
   */
  resetStats(): void {
    this.stats = {
      totalReported: 0,
      rateLimited: 0,
      failed: 0,
      queued: 0,
    };
  }

  /**
   * Cleanup
   */
  destroy(): void {
    this.stopBatchTimer();
    this.queue = [];
  }
}

// =============================================================================
// Singleton Export
// =============================================================================

/**
 * Default error reporter instance
 */
export const errorReporter = new ErrorReporter();

export default ErrorReporter;

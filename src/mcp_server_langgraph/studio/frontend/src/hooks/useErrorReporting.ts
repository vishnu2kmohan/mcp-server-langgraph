/**
 * useErrorReporting Hook
 *
 * Sprint 3 - Phase 2.4: Error Reporting Pipeline
 *
 * React hook for reporting errors to backend telemetry.
 * Integrates with TelemetryContext and provides convenient API.
 *
 * Features:
 * - Automatic user context from auth state
 * - Integration with TelemetryContext
 * - Window error capture option
 * - Convenience methods for components
 *
 * @example
 * ```tsx
 * function ChatPage() {
 *   const { reportError, lastError, isReporting } = useErrorReporting();
 *
 *   const handleSend = async () => {
 *     try {
 *       await sendMessage();
 *     } catch (error) {
 *       await reportError(error, {
 *         customContext: { component: 'ChatPage', action: 'send' },
 *       });
 *     }
 *   };
 * }
 * ```
 */

import { useState, useCallback, useEffect, useRef } from "react";
import {
  ErrorReporter,
  type ErrorReporterConfig,
  type ReportResult,
  type ReporterStats,
  type CreateReportOptions,
} from "../utils/errorReporter";
import type { ClassifiedError } from "../errors/ErrorTypes";

// =============================================================================
// Types
// =============================================================================

export interface UseErrorReportingOptions extends ErrorReporterConfig {
  /** Automatically capture unhandled window errors */
  captureWindowErrors?: boolean;
  /** Automatically capture unhandled promise rejections */
  captureUnhandledRejections?: boolean;
}

export interface UseErrorReportingResult {
  /** Report an error */
  reportError: (
    error: Error | ClassifiedError,
    options?: CreateReportOptions,
  ) => Promise<ReportResult>;
  /** Last reported error */
  lastError: Error | ClassifiedError | null;
  /** Whether currently reporting */
  isReporting: boolean;
  /** Whether reporting is enabled */
  isEnabled: boolean;
  /** Enable reporting */
  enable: () => void;
  /** Disable reporting */
  disable: () => void;
  /** Get reporting statistics */
  getStats: () => ReporterStats;
  /** Flush any queued reports */
  flush: () => Promise<void>;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useErrorReporting(
  options: UseErrorReportingOptions = {},
): UseErrorReportingResult {
  const {
    captureWindowErrors = false,
    captureUnhandledRejections = false,
    enabled = true,
    ...reporterConfig
  } = options;

  // State
  const [lastError, setLastError] = useState<Error | ClassifiedError | null>(
    null,
  );
  const [isReporting, setIsReporting] = useState(false);
  const [isEnabled, setIsEnabled] = useState(enabled);

  // Reporter instance (stable across renders)
  const reporterRef = useRef<ErrorReporter | null>(null);

  // Initialize reporter
  if (!reporterRef.current) {
    reporterRef.current = new ErrorReporter({
      ...reporterConfig,
      enabled,
    });
  }

  /**
   * Report an error
   */
  const reportError = useCallback(
    async (
      error: Error | ClassifiedError,
      reportOptions: CreateReportOptions = {},
    ): Promise<ReportResult> => {
      setLastError(error);
      setIsReporting(true);

      try {
        const result = await reporterRef.current!.report(error, reportOptions);
        return result;
      } finally {
        setIsReporting(false);
      }
    },
    [],
  );

  /**
   * Enable reporting
   */
  const enable = useCallback(() => {
    reporterRef.current?.enable();
    setIsEnabled(true);
  }, []);

  /**
   * Disable reporting
   */
  const disable = useCallback(() => {
    reporterRef.current?.disable();
    setIsEnabled(false);
  }, []);

  /**
   * Get statistics
   */
  const getStats = useCallback((): ReporterStats => {
    return (
      reporterRef.current?.getStats() ?? {
        totalReported: 0,
        rateLimited: 0,
        failed: 0,
        queued: 0,
      }
    );
  }, []);

  /**
   * Flush queued reports
   */
  const flush = useCallback(async (): Promise<void> => {
    await reporterRef.current?.flush();
  }, []);

  // Setup window error capture
  useEffect(() => {
    if (!captureWindowErrors) return;

    const handleError = (event: ErrorEvent) => {
      void reportError(event.error ?? new Error(event.message), {
        customContext: {
          type: "window_error",
          filename: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        },
      });
    };

    window.addEventListener("error", handleError);
    return () => window.removeEventListener("error", handleError);
  }, [captureWindowErrors, reportError]);

  // Setup unhandled rejection capture
  useEffect(() => {
    if (!captureUnhandledRejections) return;

    const handleRejection = (event: PromiseRejectionEvent) => {
      const error =
        event.reason instanceof Error
          ? event.reason
          : new Error(String(event.reason));

      void reportError(error, {
        customContext: {
          type: "unhandled_rejection",
        },
      });
    };

    window.addEventListener("unhandledrejection", handleRejection);
    return () =>
      window.removeEventListener("unhandledrejection", handleRejection);
  }, [captureUnhandledRejections, reportError]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      reporterRef.current?.destroy();
    };
  }, []);

  return {
    reportError,
    lastError,
    isReporting,
    isEnabled,
    enable,
    disable,
    getStats,
    flush,
  };
}

export default useErrorReporting;

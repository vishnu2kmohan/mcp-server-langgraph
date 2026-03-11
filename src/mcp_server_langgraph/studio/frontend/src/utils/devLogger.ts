/**
 * Development Logger
 *
 * Provides conditional console logging that only runs in development mode.
 * Prevents console spam in production while keeping useful debug info in dev.
 *
 * Usage:
 * ```tsx
 * import { devLogger } from "../utils/devLogger";
 *
 * // Simple usage
 * devLogger.warn("Something might be wrong", { data });
 *
 * // With prefix for context
 * const logger = devLogger.withPrefix("[SessionSync]");
 * logger.debug("Syncing session", sessionId);
 * ```
 */

// =============================================================================
// Types
// =============================================================================

/**
 * Log levels from least to most severe
 */
export enum DevLogLevel {
  DEBUG = 0,
  LOG = 1,
  WARN = 2,
  ERROR = 3,
}

interface DevLoggerOptions {
  /** Minimum log level to display */
  minLevel?: DevLogLevel;
  /** Prefix to prepend to all messages */
  prefix?: string;
  /**
   * Whether to suppress debug/log level messages in test mode.
   * When true, only WARN and ERROR will be logged during tests.
   * This reduces noise in test output while keeping important messages visible.
   * Default: true
   */
  suppressInTests?: boolean;
}

// =============================================================================
// Implementation
// =============================================================================

/**
 * Check if we're in test mode (vitest/jest)
 * Returns true when running in test environment
 */
export function isTestMode(): boolean {
  // Vitest sets import.meta.env.MODE to 'test'
  // Also check for process.env.NODE_ENV in case of SSR/node context
  return (
    import.meta.env.MODE === "test" ||
    (typeof process !== "undefined" && process.env?.NODE_ENV === "test")
  );
}

/**
 * Check if we're in development mode
 * Returns true in development or test environments
 *
 * Uses Vite's native import.meta.env.DEV for reliable detection.
 * In production builds, this is statically replaced with `false`,
 * allowing dead code elimination.
 */
export function isDevMode(): boolean {
  // Use Vite's native env detection (more reliable than process.env.NODE_ENV)
  // import.meta.env.DEV is true in dev, false in production builds
  return import.meta.env.DEV;
}

/**
 * Create a development logger with optional configuration
 */
function createDevLogger(options: DevLoggerOptions = {}) {
  // Default suppressInTests to false for backwards compatibility
  // Component loggers (created via withPrefix) should set suppressInTests: true
  // to reduce noise in test output
  const {
    minLevel = DevLogLevel.DEBUG,
    prefix = "",
    suppressInTests = false,
  } = options;

  const shouldLog = (level: DevLogLevel): boolean => {
    if (!isDevMode()) return false;

    // In test mode, optionally suppress debug/log level messages
    // to reduce noise in test output
    if (suppressInTests && isTestMode() && level < DevLogLevel.WARN) {
      return false;
    }

    return level >= minLevel;
  };

  const formatMessage = (message: string): string => {
    return prefix ? `${prefix} ${message}` : message;
  };

  return {
    /**
     * Log debug message (only in development)
     */
    debug: (message: string, ...args: unknown[]) => {
      if (shouldLog(DevLogLevel.DEBUG)) {
        console.debug(formatMessage(message), ...args);
      }
    },

    /**
     * Log info message (only in development)
     */
    log: (message: string, ...args: unknown[]) => {
      if (shouldLog(DevLogLevel.LOG)) {
        console.log(formatMessage(message), ...args);
      }
    },

    /**
     * Log warning message (only in development)
     */
    warn: (message: string, ...args: unknown[]) => {
      if (shouldLog(DevLogLevel.WARN)) {
        console.warn(formatMessage(message), ...args);
      }
    },

    /**
     * Log error message (only in development)
     */
    error: (message: string, ...args: unknown[]) => {
      if (shouldLog(DevLogLevel.ERROR)) {
        console.error(formatMessage(message), ...args);
      }
    },

    /**
     * Log a structured metric (counter/histogram) via console.debug.
     * Uses the same suppression rules as debug-level logging.
     */
    metric: (name: string, value: number, tags?: Record<string, string>) => {
      if (shouldLog(DevLogLevel.DEBUG)) {
        const label = formatMessage(`[metric] ${name}`);
        if (tags) {
          console.debug(label, value, tags);
        } else {
          console.debug(label, value);
        }
      }
    },

    /**
     * Create a new logger with a prefix
     *
     * Note: Component loggers (those with a prefix) automatically suppress
     * debug/log level messages in tests to reduce test output noise.
     * Use .withTestOutput() to override this behavior when debugging.
     */
    withPrefix: (newPrefix: string) => {
      return createDevLogger({
        minLevel,
        prefix: prefix ? `${prefix} ${newPrefix}` : newPrefix,
        // Component loggers suppress debug/log in tests by default
        // to reduce noise in test output
        suppressInTests: true,
      });
    },

    /**
     * Create a new logger with a minimum log level
     */
    withMinLevel: (newMinLevel: DevLogLevel) => {
      return createDevLogger({
        minLevel: newMinLevel,
        prefix,
        suppressInTests,
      });
    },

    /**
     * Create a new logger that shows all messages even in tests
     * Useful for debugging test failures
     */
    withTestOutput: () => {
      return createDevLogger({
        minLevel,
        prefix,
        suppressInTests: false,
      });
    },
  };
}

// =============================================================================
// Export
// =============================================================================

/**
 * Default development logger instance
 */
export const devLogger = createDevLogger();

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
}

// =============================================================================
// Implementation
// =============================================================================

/**
 * Check if we're in development mode
 * Returns true in development or test environments
 */
export function isDevMode(): boolean {
  const nodeEnv = process.env.NODE_ENV;
  return nodeEnv === "development" || nodeEnv === "test";
}

/**
 * Create a development logger with optional configuration
 */
function createDevLogger(options: DevLoggerOptions = {}) {
  const { minLevel = DevLogLevel.DEBUG, prefix = "" } = options;

  const shouldLog = (level: DevLogLevel): boolean => {
    return isDevMode() && level >= minLevel;
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
     * Create a new logger with a prefix
     */
    withPrefix: (newPrefix: string) => {
      return createDevLogger({
        minLevel,
        prefix: prefix ? `${prefix} ${newPrefix}` : newPrefix,
      });
    },

    /**
     * Create a new logger with a minimum log level
     */
    withMinLevel: (newMinLevel: DevLogLevel) => {
      return createDevLogger({
        minLevel: newMinLevel,
        prefix,
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

/**
 * Development Logger Tests
 *
 * TDD tests for conditional console logging that only runs in development.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { devLogger, DevLogLevel, isDevMode } from "./devLogger";

describe("devLogger", () => {
  let consoleSpies: {
    debug: ReturnType<typeof vi.spyOn>;
    log: ReturnType<typeof vi.spyOn>;
    warn: ReturnType<typeof vi.spyOn>;
    error: ReturnType<typeof vi.spyOn>;
  };

  beforeEach(() => {
    consoleSpies = {
      debug: vi.spyOn(console, "debug").mockImplementation(() => {}),
      log: vi.spyOn(console, "log").mockImplementation(() => {}),
      warn: vi.spyOn(console, "warn").mockImplementation(() => {}),
      error: vi.spyOn(console, "error").mockImplementation(() => {}),
    };
  });

  afterEach(() => {
    consoleSpies.debug.mockRestore();
    consoleSpies.log.mockRestore();
    consoleSpies.warn.mockRestore();
    consoleSpies.error.mockRestore();
    vi.clearAllMocks();
  });

  describe("isDevMode", () => {
    it("should return true in test environment", () => {
      // In vitest, NODE_ENV is 'test' which should behave like development
      expect(isDevMode()).toBe(true);
    });
  });

  describe("logging methods", () => {
    it("should log debug messages in development", () => {
      devLogger.debug("Test debug message", { data: 123 });
      expect(consoleSpies.debug).toHaveBeenCalledWith("Test debug message", {
        data: 123,
      });
    });

    it("should log info messages in development", () => {
      devLogger.log("Test log message");
      expect(consoleSpies.log).toHaveBeenCalledWith("Test log message");
    });

    it("should log warning messages in development", () => {
      devLogger.warn("Test warning", { error: "something" });
      expect(consoleSpies.warn).toHaveBeenCalledWith("Test warning", {
        error: "something",
      });
    });

    it("should log error messages in development", () => {
      devLogger.error("Test error", new Error("Test"));
      expect(consoleSpies.error).toHaveBeenCalled();
    });
  });

  describe("prefixed logger", () => {
    it("should create a logger with a prefix", () => {
      const logger = devLogger.withPrefix("[SessionSync]");
      logger.warn("Something happened");
      expect(consoleSpies.warn).toHaveBeenCalledWith(
        "[SessionSync] Something happened",
      );
    });

    it("should pass additional arguments with prefix (using withTestOutput)", () => {
      // Note: withPrefix() now suppresses debug/log in tests by default
      // Use withTestOutput() to verify logging behavior in tests
      const logger = devLogger.withPrefix("[API]").withTestOutput();
      logger.debug("Request", { url: "/test" });
      expect(consoleSpies.debug).toHaveBeenCalledWith("[API] Request", {
        url: "/test",
      });
    });

    it("should suppress debug/log in tests with withPrefix by default", () => {
      const logger = devLogger.withPrefix("[API]");
      logger.debug("Debug message");
      logger.log("Log message");
      logger.warn("Warning message"); // Warnings should still log
      logger.error("Error message"); // Errors should still log

      expect(consoleSpies.debug).not.toHaveBeenCalled();
      expect(consoleSpies.log).not.toHaveBeenCalled();
      expect(consoleSpies.warn).toHaveBeenCalledWith("[API] Warning message");
      expect(consoleSpies.error).toHaveBeenCalledWith("[API] Error message");
    });

    it("should allow enabling test output with withTestOutput()", () => {
      const logger = devLogger.withPrefix("[Test]").withTestOutput();
      logger.debug("Debug visible");
      logger.log("Log visible");

      expect(consoleSpies.debug).toHaveBeenCalledWith("[Test] Debug visible");
      expect(consoleSpies.log).toHaveBeenCalledWith("[Test] Log visible");
    });
  });

  describe("level filtering", () => {
    it("should support min level configuration", () => {
      const warnOnlyLogger = devLogger.withMinLevel(DevLogLevel.WARN);

      warnOnlyLogger.debug("Debug message");
      warnOnlyLogger.log("Log message");
      warnOnlyLogger.warn("Warning message");
      warnOnlyLogger.error("Error message");

      expect(consoleSpies.debug).not.toHaveBeenCalled();
      expect(consoleSpies.log).not.toHaveBeenCalled();
      expect(consoleSpies.warn).toHaveBeenCalledWith("Warning message");
      expect(consoleSpies.error).toHaveBeenCalledWith("Error message");
    });

    it("should filter log messages below min level", () => {
      const errorOnlyLogger = devLogger.withMinLevel(DevLogLevel.ERROR);

      errorOnlyLogger.debug("Debug");
      errorOnlyLogger.log("Log");
      errorOnlyLogger.warn("Warn");

      expect(consoleSpies.debug).not.toHaveBeenCalled();
      expect(consoleSpies.log).not.toHaveBeenCalled();
      expect(consoleSpies.warn).not.toHaveBeenCalled();
    });

    it("should allow log level exactly at min level", () => {
      const logOnlyLogger = devLogger.withMinLevel(DevLogLevel.LOG);

      logOnlyLogger.debug("Debug"); // Below LOG
      logOnlyLogger.log("Log"); // Exactly LOG

      expect(consoleSpies.debug).not.toHaveBeenCalled();
      expect(consoleSpies.log).toHaveBeenCalledWith("Log");
    });
  });

  describe("chained prefixes", () => {
    it("should chain prefixes correctly", () => {
      const logger1 = devLogger.withPrefix("[Module]");
      const logger2 = logger1.withPrefix("[SubModule]");

      logger2.warn("Nested message");

      expect(consoleSpies.warn).toHaveBeenCalledWith(
        "[Module] [SubModule] Nested message",
      );
    });

    it("should handle withMinLevel after withPrefix", () => {
      const logger = devLogger
        .withPrefix("[Test]")
        .withMinLevel(DevLogLevel.WARN);

      logger.debug("Debug");
      logger.warn("Warning");

      expect(consoleSpies.debug).not.toHaveBeenCalled();
      expect(consoleSpies.warn).toHaveBeenCalledWith("[Test] Warning");
    });
  });

  describe("messages without prefix", () => {
    it("should log without prefix for base logger", () => {
      devLogger.log("Plain message");

      expect(consoleSpies.log).toHaveBeenCalledWith("Plain message");
    });
  });
});

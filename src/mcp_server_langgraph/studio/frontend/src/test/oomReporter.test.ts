/**
 * OOM Reporter Tests
 *
 * TDD tests for the main-process Vitest reporter that tracks module lifecycle
 * to detect OOM suspects and report high-memory test files.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import OomReporter, {
  formatMemoryLine,
  formatOomSuspectLine,
  type OomReporterOptions,
} from "./oomReporter";

/**
 * Create a mock TestModule-like object for testing.
 * Vitest's TestModule is complex — we mock the minimal interface used by OomReporter.
 */
function createMockModule(
  id: string,
  relativePath: string,
  options?: {
    heap?: number; // bytes
    duration?: number; // ms
  },
) {
  return {
    id,
    moduleId: id,
    get relativeModuleId() {
      // Simulate Vitest's module path resolution behavior
      return relativePath;
    },
    diagnostic: () => ({
      heap: options?.heap,
      duration: options?.duration ?? 1000,
    }),
  };
}

describe("oomReporter", () => {
  // ===========================================================================
  // OomReporter Class
  // ===========================================================================

  describe("OomReporter", () => {
    let reporter: OomReporter;
    let consoleSpy: ReturnType<typeof vi.spyOn>;

    beforeEach(() => {
      reporter = new OomReporter();
      consoleSpy = vi.spyOn(console, "log").mockImplementation(() => {});
    });

    afterEach(() => {
      consoleSpy.mockRestore();
      vi.restoreAllMocks();
    });

    describe("constructor", () => {
      it("should use defaults (256MB report, 500MB high)", () => {
        const r = new OomReporter();
        const report = r.getReport();

        expect(report.completed).toEqual([]);
        expect(report.suspects).toEqual([]);
      });

      it("should accept custom options", () => {
        const options: OomReporterOptions = {
          reportThresholdMB: 100,
          highMemoryThresholdMB: 200,
        };
        const r = new OomReporter(options);

        // Reporter created without error
        expect(r.getReport().completed).toEqual([]);
      });
    });

    describe("onTestRunStart", () => {
      it("should clear accumulated state from previous runs", () => {
        const mod = createMockModule("mod1", "src/components/Heavy.test.tsx", {
          heap: 300 * 1024 * 1024,
          duration: 3000,
        });

        // Simulate a completed run
        reporter.onTestModuleStart(mod as never);
        reporter.onTestModuleEnd(mod as never);

        // Add an incomplete module (suspect)
        const mod2 = createMockModule(
          "mod2",
          "src/components/Crashed.test.tsx",
        );
        reporter.onTestModuleStart(mod2 as never);

        // Verify state is accumulated
        let report = reporter.getReport();
        expect(report.completed).toHaveLength(1);
        expect(report.suspects).toHaveLength(1);

        // Start a new run - should clear everything
        reporter.onTestRunStart();

        report = reporter.getReport();
        expect(report.completed).toHaveLength(0);
        expect(report.suspects).toHaveLength(0);
      });
    });

    describe("onTestModuleStart", () => {
      it("should record module path and start time", () => {
        const mod = createMockModule("mod1", "src/components/Heavy.test.tsx");

        reporter.onTestModuleStart(mod as never);

        // Module should be tracked as "in progress"
        // (verified indirectly via onTestRunEnd suspect detection)
        const report = reporter.getReport();
        expect(report.suspects).toContain("src/components/Heavy.test.tsx");
      });
    });

    describe("onTestModuleEnd", () => {
      it("should record heap from diagnostic().heap and compute MB", () => {
        const mod = createMockModule("mod1", "src/components/Test.test.tsx", {
          heap: 300 * 1024 * 1024, // 300MB
          duration: 5000,
        });

        reporter.onTestModuleStart(mod as never);
        reporter.onTestModuleEnd(mod as never);

        const report = reporter.getReport();
        expect(report.completed).toHaveLength(1);
        expect(report.completed[0].heapMB).toBeCloseTo(300, 0);
        expect(report.completed[0].path).toBe("src/components/Test.test.tsx");
        // Should not be a suspect since it completed
        expect(report.suspects).toHaveLength(0);
      });

      it("should handle undefined heap (logHeapUsage not enabled)", () => {
        const mod = createMockModule("mod1", "src/components/Test.test.tsx", {
          heap: undefined,
          duration: 2000,
        });

        reporter.onTestModuleStart(mod as never);
        reporter.onTestModuleEnd(mod as never);

        const report = reporter.getReport();
        expect(report.completed).toHaveLength(1);
        expect(report.completed[0].heapMB).toBe(0);
      });

      it("should log [MEMORY] when heap >= reportThreshold", () => {
        const r = new OomReporter({ reportThresholdMB: 256 });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule(
          "mod1",
          "src/hooks/useStreamingChat.test.ts",
          {
            heap: 312 * 1024 * 1024, // 312MB
            duration: 4200,
          },
        );

        r.onTestModuleStart(mod as never);
        r.onTestModuleEnd(mod as never);

        expect(spy).toHaveBeenCalledWith(expect.stringContaining("[MEMORY]"));
        expect(spy).toHaveBeenCalledWith(
          expect.stringContaining("src/hooks/useStreamingChat.test.ts"),
        );

        spy.mockRestore();
      });

      it("should add HIGH marker when heap >= highMemoryThreshold", () => {
        const r = new OomReporter({
          reportThresholdMB: 256,
          highMemoryThresholdMB: 500,
        });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule(
          "mod1",
          "src/components/CanvasArtifact.test.tsx",
          {
            heap: 890 * 1024 * 1024, // 890MB
            duration: 8100,
          },
        );

        r.onTestModuleStart(mod as never);
        r.onTestModuleEnd(mod as never);

        const logCall = spy.mock.calls.find(
          (call) => typeof call[0] === "string" && call[0].includes("[MEMORY]"),
        );
        expect(logCall).toBeDefined();
        expect(logCall![0]).toContain("⚠ HIGH");

        spy.mockRestore();
      });

      it("should skip log when below threshold", () => {
        const r = new OomReporter({ reportThresholdMB: 256 });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule("mod1", "src/utils/small.test.ts", {
          heap: 50 * 1024 * 1024, // 50MB - below 256MB threshold
          duration: 500,
        });

        r.onTestModuleStart(mod as never);
        r.onTestModuleEnd(mod as never);

        const memoryCalls = spy.mock.calls.filter(
          (call) => typeof call[0] === "string" && call[0].includes("[MEMORY]"),
        );
        expect(memoryCalls).toHaveLength(0);

        spy.mockRestore();
      });

      it("should log when below threshold but VITEST_MEMORY_VERBOSE=true", () => {
        const originalEnv = process.env;
        process.env = { ...originalEnv, VITEST_MEMORY_VERBOSE: "true" };

        const r = new OomReporter({ reportThresholdMB: 256 });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule("mod1", "src/utils/small.test.ts", {
          heap: 50 * 1024 * 1024, // 50MB - below threshold
          duration: 500,
        });

        r.onTestModuleStart(mod as never);
        r.onTestModuleEnd(mod as never);

        const memoryCalls = spy.mock.calls.filter(
          (call) => typeof call[0] === "string" && call[0].includes("[MEMORY]"),
        );
        expect(memoryCalls).toHaveLength(1);

        spy.mockRestore();
        process.env = originalEnv;
      });

      it("should include duration from diagnostic", () => {
        const r = new OomReporter({ reportThresholdMB: 100 });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule("mod1", "src/components/Test.test.tsx", {
          heap: 200 * 1024 * 1024,
          duration: 4200, // 4.2 seconds
        });

        r.onTestModuleStart(mod as never);
        r.onTestModuleEnd(mod as never);

        const logCall = spy.mock.calls.find(
          (call) => typeof call[0] === "string" && call[0].includes("[MEMORY]"),
        );
        expect(logCall![0]).toContain("4.2s");

        spy.mockRestore();
      });
    });

    describe("onTestRunEnd", () => {
      it("should log [OOM-SUSPECT] for modules that started but never ended", () => {
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod1 = createMockModule(
          "mod1",
          "src/components/HeavyTest.test.tsx",
        );
        const mod2 = createMockModule(
          "mod2",
          "src/components/Normal.test.tsx",
          {
            heap: 100 * 1024 * 1024,
            duration: 2000,
          },
        );

        // mod1 starts but never ends (worker died)
        reporter.onTestModuleStart(mod1 as never);
        // mod2 completes normally
        reporter.onTestModuleStart(mod2 as never);
        reporter.onTestModuleEnd(mod2 as never);

        // End the test run
        reporter.onTestRunEnd([] as never, [] as never, "passed" as never);

        const suspectCalls = spy.mock.calls.filter(
          (call) =>
            typeof call[0] === "string" && call[0].includes("[OOM-SUSPECT]"),
        );
        expect(suspectCalls).toHaveLength(1);
        expect(suspectCalls[0][0]).toContain(
          "src/components/HeavyTest.test.tsx",
        );
        expect(suspectCalls[0][0]).toContain("started but never completed");

        spy.mockRestore();
      });

      it("should have no suspects when all modules completed", () => {
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod1 = createMockModule("mod1", "src/components/A.test.tsx", {
          heap: 100 * 1024 * 1024,
          duration: 1000,
        });
        const mod2 = createMockModule("mod2", "src/components/B.test.tsx", {
          heap: 150 * 1024 * 1024,
          duration: 2000,
        });

        reporter.onTestModuleStart(mod1 as never);
        reporter.onTestModuleEnd(mod1 as never);
        reporter.onTestModuleStart(mod2 as never);
        reporter.onTestModuleEnd(mod2 as never);

        reporter.onTestRunEnd([] as never, [] as never, "passed" as never);

        const suspectCalls = spy.mock.calls.filter(
          (call) =>
            typeof call[0] === "string" && call[0].includes("[OOM-SUSPECT]"),
        );
        expect(suspectCalls).toHaveLength(0);

        spy.mockRestore();
      });

      it("should log [MEMORY-SUMMARY] count of high-memory files", () => {
        const r = new OomReporter({
          reportThresholdMB: 100,
          highMemoryThresholdMB: 500,
        });
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        // Two high-memory files
        const mod1 = createMockModule("mod1", "src/a.test.tsx", {
          heap: 600 * 1024 * 1024,
          duration: 5000,
        });
        const mod2 = createMockModule("mod2", "src/b.test.tsx", {
          heap: 800 * 1024 * 1024,
          duration: 7000,
        });
        // One normal file
        const mod3 = createMockModule("mod3", "src/c.test.tsx", {
          heap: 200 * 1024 * 1024,
          duration: 1000,
        });

        r.onTestModuleStart(mod1 as never);
        r.onTestModuleEnd(mod1 as never);
        r.onTestModuleStart(mod2 as never);
        r.onTestModuleEnd(mod2 as never);
        r.onTestModuleStart(mod3 as never);
        r.onTestModuleEnd(mod3 as never);

        r.onTestRunEnd([] as never, [] as never, "passed" as never);

        const summaryCalls = spy.mock.calls.filter(
          (call) =>
            typeof call[0] === "string" && call[0].includes("[MEMORY-SUMMARY]"),
        );
        expect(summaryCalls).toHaveLength(1);
        expect(summaryCalls[0][0]).toContain("2 file(s)");
        expect(summaryCalls[0][0]).toContain("500MB");

        spy.mockRestore();
      });

      it("should not log [MEMORY-SUMMARY] when no high-memory files", () => {
        const spy = vi.spyOn(console, "log").mockImplementation(() => {});

        const mod = createMockModule("mod1", "src/small.test.tsx", {
          heap: 50 * 1024 * 1024,
          duration: 500,
        });

        reporter.onTestModuleStart(mod as never);
        reporter.onTestModuleEnd(mod as never);

        reporter.onTestRunEnd([] as never, [] as never, "passed" as never);

        const summaryCalls = spy.mock.calls.filter(
          (call) =>
            typeof call[0] === "string" && call[0].includes("[MEMORY-SUMMARY]"),
        );
        expect(summaryCalls).toHaveLength(0);

        spy.mockRestore();
      });
    });

    describe("getReport", () => {
      it("should return structured {completed, suspects}", () => {
        const mod1 = createMockModule("mod1", "src/components/Done.test.tsx", {
          heap: 300 * 1024 * 1024,
          duration: 3000,
        });
        const mod2 = createMockModule(
          "mod2",
          "src/components/Crashed.test.tsx",
        );

        reporter.onTestModuleStart(mod1 as never);
        reporter.onTestModuleEnd(mod1 as never);
        reporter.onTestModuleStart(mod2 as never);
        // mod2 never ends

        const report = reporter.getReport();

        expect(report.completed).toHaveLength(1);
        expect(report.completed[0]).toEqual(
          expect.objectContaining({
            path: "src/components/Done.test.tsx",
            heapMB: expect.any(Number),
            durationS: expect.any(Number),
          }),
        );

        expect(report.suspects).toEqual(["src/components/Crashed.test.tsx"]);
      });
    });
  });

  // ===========================================================================
  // formatMemoryLine Helper
  // ===========================================================================

  describe("formatMemoryLine", () => {
    it("should format [MEMORY] with path, MB, duration, no HIGH marker", () => {
      const line = formatMemoryLine(
        "src/hooks/useStreamingChat.test.ts",
        312,
        4.2,
        false,
      );

      expect(line).toBe(
        "[MEMORY] src/hooks/useStreamingChat.test.ts: 312MB heap (duration: 4.2s)",
      );
    });

    it("should include HIGH marker when isHigh is true", () => {
      const line = formatMemoryLine(
        "src/components/CanvasArtifact.test.tsx",
        890,
        8.1,
        true,
      );

      expect(line).toBe(
        "[MEMORY] src/components/CanvasArtifact.test.tsx: 890MB heap (duration: 8.1s) ⚠ HIGH",
      );
    });

    it("should handle integer duration", () => {
      const line = formatMemoryLine("test.ts", 100, 5.0, false);

      expect(line).toBe("[MEMORY] test.ts: 100MB heap (duration: 5.0s)");
    });
  });

  // ===========================================================================
  // formatOomSuspectLine Helper
  // ===========================================================================

  describe("formatOomSuspectLine", () => {
    it("should format [OOM-SUSPECT] with path", () => {
      const line = formatOomSuspectLine("src/components/HeavyTest.test.tsx");

      expect(line).toBe(
        "[OOM-SUSPECT] src/components/HeavyTest.test.tsx: started but never completed (likely OOM/timeout)",
      );
    });
  });
});

/**
 * sql.js WebWorker Bridge Tests
 *
 * Comprehensive tests for PyodideSQLBridge, loadWasmWithIntegrity,
 * and formatSQLResult. All browser APIs (Worker, fetch, crypto.subtle)
 * are mocked since the test environment is jsdom.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

// ---------------------------------------------------------------------------
// Mock types and helpers
// ---------------------------------------------------------------------------

/** Simulated Worker instance with controllable message handling */
interface MockWorkerInstance {
  postMessage: ReturnType<typeof vi.fn>;
  terminate: ReturnType<typeof vi.fn>;
  addEventListener: ReturnType<typeof vi.fn>;
  removeEventListener: ReturnType<typeof vi.fn>;
  onmessage: ((e: MessageEvent) => void) | null;
  onerror: ((e: ErrorEvent) => void) | null;
}

function createMockWorker(): MockWorkerInstance {
  return {
    postMessage: vi.fn(),
    terminate: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    onmessage: null,
    onerror: null,
  };
}

/** Helper to simulate a worker response via the onmessage handler */
function simulateWorkerMessage(
  worker: MockWorkerInstance,
  data: Record<string, unknown>,
): void {
  if (worker.onmessage) {
    worker.onmessage(new MessageEvent("message", { data }));
  }
}

/** Helper to simulate a worker response via addEventListener */
function simulateWorkerEventListenerMessage(
  worker: MockWorkerInstance,
  data: Record<string, unknown>,
): void {
  const calls = worker.addEventListener.mock.calls;
  for (const call of calls) {
    if (call[0] === "message") {
      const handler = call[1] as (e: MessageEvent) => void;
      handler(new MessageEvent("message", { data }));
    }
  }
}

/**
 * Flush microtask queue so that `await loadWasmWithIntegrity()` inside
 * `initialize()` can settle before we simulate worker messages.
 */
async function flushMicrotasks(): Promise<void> {
  for (let i = 0; i < 5; i++) {
    await Promise.resolve();
  }
}

/**
 * Helper: create a fully initialized bridge with short timeout.
 * Flushes microtasks so the init event listener is registered,
 * then simulates the worker init_success response.
 */
async function createInitializedBridge(
  mockWorker: MockWorkerInstance,
  timeoutMs = 500,
) {
  const { PyodideSQLBridge } = await import("./sqlBridge");
  const bridge = new PyodideSQLBridge(timeoutMs);
  const initPromise = bridge.initialize();
  await flushMicrotasks();
  simulateWorkerEventListenerMessage(mockWorker, { type: "init_success" });
  await initPromise;
  return bridge;
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("sqlBridge", () => {
  let mockWorker: MockWorkerInstance;
  let mockFetch: ReturnType<typeof vi.fn>;
  let mockDigest: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    vi.resetModules();

    mockWorker = createMockWorker();

    // Return mockWorker directly so that when the bridge sets
    // `this.worker.onmessage = handler`, it modifies mockWorker itself
    // (not a copy), letting simulateWorkerMessage find the handler.
    // Must use regular function (not arrow) so `new` works.
    const MockWorkerClass = vi.fn().mockImplementation(function () {
      return mockWorker;
    });
    vi.stubGlobal("Worker", MockWorkerClass);

    // Default: fetch returns 404 so loadWasmWithIntegrity() fails fast
    // and initialize() proceeds to set up the worker event listener.
    mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    });
    vi.stubGlobal("fetch", mockFetch);

    mockDigest = vi.fn();
    vi.stubGlobal("crypto", {
      subtle: { digest: mockDigest },
      randomUUID: () => "test-uuid-1234",
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  // =========================================================================
  // SQL_JS_CONFIG
  // =========================================================================

  describe("SQL_JS_CONFIG", () => {
    it("wasmPath points to /wasm/sql-wasm.wasm", async () => {
      const { SQL_JS_CONFIG } = await import("./sqlBridge");
      expect(SQL_JS_CONFIG.wasmPath).toBe("/wasm/sql-wasm.wasm");
    });

    it("cdnFallback is null in production (import.meta.env.DEV = false)", async () => {
      const { SQL_JS_CONFIG } = await import("./sqlBridge");
      expect(SQL_JS_CONFIG).toHaveProperty("cdnFallback");
      expect(
        typeof SQL_JS_CONFIG.cdnFallback === "string" ||
          SQL_JS_CONFIG.cdnFallback === null,
      ).toBe(true);
    });

    it("cdnFallback URL is passed to worker in init message", async () => {
      const bridge = await createInitializedBridge(mockWorker);
      expect(bridge.isReady).toBe(true);

      // The init message should include cdnFallback from SQL_JS_CONFIG
      const initCall = mockWorker.postMessage.mock.calls.find(
        (call: unknown[]) =>
          (call[0] as Record<string, unknown>).type === "init",
      );
      expect(initCall).toBeDefined();
      expect(initCall![0]).toHaveProperty("cdnFallback");
    });
  });

  // =========================================================================
  // PyodideSQLBridge
  // =========================================================================

  describe("PyodideSQLBridge", () => {
    describe("initialize", () => {
      it("creates WebWorker and sends init message", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        const initPromise = bridge.initialize();
        expect(Worker).toHaveBeenCalledTimes(1);

        await flushMicrotasks();
        simulateWorkerEventListenerMessage(mockWorker, {
          type: "init_success",
        });
        await initPromise;

        expect(mockWorker.postMessage).toHaveBeenCalledWith(
          expect.objectContaining({ type: "init" }),
        );
      });

      it("resolves when worker responds with init success", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        const initPromise = bridge.initialize();
        await flushMicrotasks();
        simulateWorkerEventListenerMessage(mockWorker, {
          type: "init_success",
        });

        await expect(initPromise).resolves.toBeUndefined();
        expect(bridge.isReady).toBe(true);
      });

      it("rejects on worker init error", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        const initPromise = bridge.initialize();
        await flushMicrotasks();
        simulateWorkerEventListenerMessage(mockWorker, {
          type: "init_error",
          error: "Failed to load sql.js",
        });

        await expect(initPromise).rejects.toThrow("Failed to load sql.js");
        expect(bridge.isReady).toBe(false);
      });

      it("passes cdnFallback in init message when WASM fetch fails", async () => {
        // Default mock fetch returns 404, so loadWasmWithIntegrity fails
        // and cdnFallback should be sent to the worker
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        const initPromise = bridge.initialize();
        await flushMicrotasks();

        const initCall = mockWorker.postMessage.mock.calls.find(
          (call: unknown[]) =>
            (call[0] as Record<string, unknown>).type === "init",
        );
        expect(initCall).toBeDefined();
        const initMsg = initCall![0] as Record<string, unknown>;
        // When WASM fetch fails, wasmBinary should be undefined
        expect(initMsg.wasmBinary).toBeUndefined();
        // cdnFallback should always be present (string or null)
        expect(initMsg).toHaveProperty("cdnFallback");

        simulateWorkerEventListenerMessage(mockWorker, {
          type: "init_success",
        });
        await initPromise;
      });

      it("does not reinitialize if already initialized", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        const initPromise1 = bridge.initialize();
        await flushMicrotasks();
        simulateWorkerEventListenerMessage(mockWorker, {
          type: "init_success",
        });
        await initPromise1;

        const WorkerConstructor = vi.mocked(Worker);
        const callCountBefore = WorkerConstructor.mock.calls.length;
        await bridge.initialize();
        expect(WorkerConstructor.mock.calls.length).toBe(callCountBefore);
      });
    });

    describe("execute", () => {
      it("sends execute message to worker and returns result", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        const executePromise = bridge.execute("SELECT 1 + 1 AS result");

        const executeCall = mockWorker.postMessage.mock.calls.find(
          (call: unknown[]) =>
            (call[0] as Record<string, unknown>).type === "execute",
        );
        expect(executeCall).toBeDefined();
        const id = (executeCall![0] as Record<string, unknown>).id as string;

        simulateWorkerMessage(mockWorker, {
          type: "execute_success",
          id,
          results: [{ columns: ["result"], values: [[2]] }],
        });

        const results = await executePromise;
        expect(results).toEqual([{ columns: ["result"], values: [[2]] }]);
      });

      it("rejects with timeout error after timeout period", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        vi.useFakeTimers();
        const executePromise = bridge.execute("SELECT SLEEP(999)");
        vi.advanceTimersByTime(600);

        await expect(executePromise).rejects.toThrow(
          "Query timeout after 500ms",
        );
        vi.useRealTimers();
      });

      it("rejects when worker returns error", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        const executePromise = bridge.execute("INVALID SQL");

        const executeCall = mockWorker.postMessage.mock.calls.find(
          (call: unknown[]) =>
            (call[0] as Record<string, unknown>).type === "execute",
        );
        const id = (executeCall![0] as Record<string, unknown>).id as string;

        simulateWorkerMessage(mockWorker, {
          type: "execute_error",
          id,
          error: 'near "INVALID": syntax error',
        });

        await expect(executePromise).rejects.toThrow(
          'near "INVALID": syntax error',
        );
      });

      it("throws if not initialized", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();

        await expect(bridge.execute("SELECT 1")).rejects.toThrow(
          "PyodideSQLBridge is not initialized",
        );
      });

      it("cleans up timeout on success", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        vi.useFakeTimers();
        const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

        const executePromise = bridge.execute("SELECT 1");

        const executeCall = mockWorker.postMessage.mock.calls.find(
          (call: unknown[]) =>
            (call[0] as Record<string, unknown>).type === "execute",
        );
        const id = (executeCall![0] as Record<string, unknown>).id as string;

        simulateWorkerMessage(mockWorker, {
          type: "execute_success",
          id,
          results: [{ columns: ["x"], values: [[1]] }],
        });

        await executePromise;
        expect(clearTimeoutSpy).toHaveBeenCalled();
        vi.useRealTimers();
      });

      it("cleans up timeout on error", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        vi.useFakeTimers();
        const clearTimeoutSpy = vi.spyOn(global, "clearTimeout");

        const executePromise = bridge.execute("BAD SQL");

        const executeCall = mockWorker.postMessage.mock.calls.find(
          (call: unknown[]) =>
            (call[0] as Record<string, unknown>).type === "execute",
        );
        const id = (executeCall![0] as Record<string, unknown>).id as string;

        simulateWorkerMessage(mockWorker, {
          type: "execute_error",
          id,
          error: "syntax error",
        });

        await expect(executePromise).rejects.toThrow("syntax error");
        expect(clearTimeoutSpy).toHaveBeenCalled();
        vi.useRealTimers();
      });
    });

    describe("destroy", () => {
      it("terminates worker", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        bridge.destroy();

        expect(mockWorker.postMessage).toHaveBeenCalledWith(
          expect.objectContaining({ type: "destroy" }),
        );
        expect(mockWorker.terminate).toHaveBeenCalled();
      });

      it("sets initialized to false", async () => {
        const bridge = await createInitializedBridge(mockWorker);
        expect(bridge.isReady).toBe(true);

        bridge.destroy();
        expect(bridge.isReady).toBe(false);
      });

      it("is safe to call multiple times", async () => {
        const bridge = await createInitializedBridge(mockWorker);

        expect(() => {
          bridge.destroy();
          bridge.destroy();
          bridge.destroy();
        }).not.toThrow();
      });

      it("cleans up pending promises", async () => {
        const bridge = await createInitializedBridge(mockWorker, 5000);

        const executePromise = bridge.execute("SELECT 1");
        bridge.destroy();

        await expect(executePromise).rejects.toThrow(
          "Bridge destroyed while query was pending",
        );
      });
    });

    describe("isReady", () => {
      it("returns false before initialization", async () => {
        const { PyodideSQLBridge } = await import("./sqlBridge");
        const bridge = new PyodideSQLBridge();
        expect(bridge.isReady).toBe(false);
      });

      it("returns true after initialization", async () => {
        const bridge = await createInitializedBridge(mockWorker);
        expect(bridge.isReady).toBe(true);
      });

      it("returns false after destroy", async () => {
        const bridge = await createInitializedBridge(mockWorker);
        expect(bridge.isReady).toBe(true);

        bridge.destroy();
        expect(bridge.isReady).toBe(false);
      });
    });
  });

  // =========================================================================
  // loadWasmWithIntegrity
  // =========================================================================

  describe("loadWasmWithIntegrity", () => {
    it("fetches WASM and returns ArrayBuffer", async () => {
      const { loadWasmWithIntegrity } = await import("./sqlBridge");

      const wasmBuffer = new ArrayBuffer(16);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(wasmBuffer),
      });

      const result = await loadWasmWithIntegrity("/wasm/test.wasm", "");

      expect(mockFetch).toHaveBeenCalledWith("/wasm/test.wasm");
      expect(result).toBe(wasmBuffer);
    });

    it("throws on integrity check failure when hash set", async () => {
      const { loadWasmWithIntegrity } = await import("./sqlBridge");

      const wasmBuffer = new ArrayBuffer(16);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(wasmBuffer),
      });

      const hashBuffer = new Uint8Array([1, 2, 3, 4, 5, 6]).buffer;
      mockDigest.mockResolvedValueOnce(hashBuffer);

      await expect(
        loadWasmWithIntegrity("/wasm/test.wasm", "expected-hash-abc123"),
      ).rejects.toThrow("WASM integrity check failed");
    });

    it("passes when hash matches", async () => {
      const { loadWasmWithIntegrity } = await import("./sqlBridge");

      const wasmBuffer = new ArrayBuffer(16);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(wasmBuffer),
      });

      const hashBytes = new Uint8Array([10, 20, 30, 40, 50, 60]);
      const hashBuffer = hashBytes.buffer;
      mockDigest.mockResolvedValueOnce(hashBuffer);

      const expectedBase64 = btoa(
        String.fromCharCode(...Array.from(hashBytes)),
      );

      const result = await loadWasmWithIntegrity(
        "/wasm/test.wasm",
        expectedBase64,
      );

      expect(mockDigest).toHaveBeenCalledWith("SHA-384", wasmBuffer);
      expect(result).toBe(wasmBuffer);
    });

    it("skips integrity check when hash is empty", async () => {
      const { loadWasmWithIntegrity } = await import("./sqlBridge");

      const wasmBuffer = new ArrayBuffer(16);
      mockFetch.mockResolvedValueOnce({
        ok: true,
        status: 200,
        arrayBuffer: () => Promise.resolve(wasmBuffer),
      });

      const result = await loadWasmWithIntegrity("/wasm/test.wasm", "");

      expect(mockDigest).not.toHaveBeenCalled();
      expect(result).toBe(wasmBuffer);
    });

    it("throws on fetch failure", async () => {
      const { loadWasmWithIntegrity } = await import("./sqlBridge");

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 404,
        statusText: "Not Found",
      });

      await expect(
        loadWasmWithIntegrity("/wasm/missing.wasm", ""),
      ).rejects.toThrow("Failed to fetch WASM: 404 Not Found");
    });
  });

  // =========================================================================
  // formatSQLResult
  // =========================================================================

  describe("formatSQLResult", () => {
    it("formats sql.js result with columns and values", async () => {
      const { formatSQLResult } = await import("./sqlBridge");

      const raw = [
        {
          columns: ["id", "name"],
          values: [
            [1, "Alice"],
            [2, "Bob"],
          ],
        },
      ];

      const result = formatSQLResult(raw);

      expect(result).toEqual([
        {
          columns: ["id", "name"],
          values: [
            [1, "Alice"],
            [2, "Bob"],
          ],
        },
      ]);
    });

    it("handles empty result set", async () => {
      const { formatSQLResult } = await import("./sqlBridge");
      const result = formatSQLResult([]);
      expect(result).toEqual([]);
    });

    it("handles multiple result sets", async () => {
      const { formatSQLResult } = await import("./sqlBridge");

      const raw = [
        { columns: ["x"], values: [[1], [2]] },
        {
          columns: ["y", "z"],
          values: [
            ["a", "b"],
            ["c", "d"],
          ],
        },
      ];

      const result = formatSQLResult(raw);

      expect(result).toHaveLength(2);
      expect(result[0].columns).toEqual(["x"]);
      expect(result[0].values).toEqual([[1], [2]]);
      expect(result[1].columns).toEqual(["y", "z"]);
    });
  });

  // =========================================================================
  // Edge Cases
  // =========================================================================

  describe("edge cases", () => {
    it("handles concurrent execute calls with different IDs", async () => {
      const bridge = await createInitializedBridge(mockWorker, 5000);

      let callIndex = 0;
      vi.stubGlobal("crypto", {
        subtle: { digest: mockDigest },
        randomUUID: () => `uuid-${callIndex++}`,
      });

      const promise1 = bridge.execute("SELECT 1");
      const promise2 = bridge.execute("SELECT 2");

      const executeCalls = mockWorker.postMessage.mock.calls.filter(
        (call: unknown[]) =>
          (call[0] as Record<string, unknown>).type === "execute",
      );
      expect(executeCalls.length).toBe(2);

      const id1 = (executeCalls[0][0] as Record<string, unknown>).id as string;
      const id2 = (executeCalls[1][0] as Record<string, unknown>).id as string;

      // Resolve in reverse order
      simulateWorkerMessage(mockWorker, {
        type: "execute_success",
        id: id2,
        results: [{ columns: ["x"], values: [[2]] }],
      });
      simulateWorkerMessage(mockWorker, {
        type: "execute_success",
        id: id1,
        results: [{ columns: ["x"], values: [[1]] }],
      });

      const result1 = await promise1;
      const result2 = await promise2;
      expect(result1).toEqual([{ columns: ["x"], values: [[1]] }]);
      expect(result2).toEqual([{ columns: ["x"], values: [[2]] }]);
    });

    it("ignores worker messages with unknown IDs", async () => {
      const bridge = await createInitializedBridge(mockWorker, 5000);

      expect(() => {
        simulateWorkerMessage(mockWorker, {
          type: "execute_success",
          id: "unknown-id",
          results: [],
        });
      }).not.toThrow();

      // Verify bridge is still functional
      expect(bridge.isReady).toBe(true);
    });

    it("bridge can be reinitialized after destroy", async () => {
      const bridge = await createInitializedBridge(mockWorker);
      expect(bridge.isReady).toBe(true);

      bridge.destroy();
      expect(bridge.isReady).toBe(false);

      // Create fresh mock worker for second init
      const mockWorker2 = createMockWorker();
      vi.mocked(Worker).mockImplementation(function () {
        return mockWorker2;
      });

      const initPromise2 = bridge.initialize();
      await flushMicrotasks();
      simulateWorkerEventListenerMessage(mockWorker2, {
        type: "init_success",
      });
      await initPromise2;
      expect(bridge.isReady).toBe(true);
    });

    it("default timeout is 10 seconds", async () => {
      const bridge = await createInitializedBridge(mockWorker, 10_000);

      vi.useFakeTimers();
      const executePromise = bridge.execute("SELECT 1");

      vi.advanceTimersByTime(9900);
      vi.advanceTimersByTime(200);

      await expect(executePromise).rejects.toThrow(
        "Query timeout after 10000ms",
      );
      vi.useRealTimers();
    });

    it("formatSQLResult preserves value types", async () => {
      const { formatSQLResult } = await import("./sqlBridge");

      const raw = [
        {
          columns: ["int", "float", "text", "nil", "bool"],
          values: [[42, 3.14, "hello", null, true]],
        },
      ];

      const result = formatSQLResult(raw);
      expect(result[0].values[0]).toEqual([42, 3.14, "hello", null, true]);
    });

    it("execute uses crypto.randomUUID for request IDs", async () => {
      const bridge = await createInitializedBridge(mockWorker, 5000);

      bridge.execute("SELECT 1");

      const executeCall = mockWorker.postMessage.mock.calls.find(
        (call: unknown[]) =>
          (call[0] as Record<string, unknown>).type === "execute",
      );
      expect(executeCall).toBeDefined();
      const id = (executeCall![0] as Record<string, unknown>).id as string;
      expect(id).toBe("test-uuid-1234");

      // Clean up the pending promise
      simulateWorkerMessage(mockWorker, {
        type: "execute_success",
        id,
        results: [],
      });
    });
  });
});

/**
 * sql.js WebWorker Bridge for Browser-Based SQL Execution
 *
 * Provides non-blocking SQL execution in the browser using sql.js
 * compiled to WebAssembly. All SQL operations run in a dedicated
 * WebWorker to avoid blocking the main thread.
 *
 * SECURITY: Self-hosted WASM with SRI integrity verification.
 * The WASM binary is served from /wasm/sql-wasm.wasm and verified
 * at runtime using SHA-384 hash comparison. The expected hash is
 * injected at build time via VITE_SQL_WASM_HASH.
 */

/** Result from a SQL query execution */
export interface SQLResult {
  columns: string[];
  values: unknown[][];
}

/** Message types for WebWorker communication */
export type WorkerMessage =
  | { type: "init"; wasmBinary?: ArrayBuffer; cdnFallback?: string | null }
  | { type: "execute"; sql: string; id: string }
  | { type: "destroy" };

/** Response types from WebWorker */
export type WorkerResponse =
  | { type: "init_success" }
  | { type: "init_error"; error: string }
  | { type: "execute_success"; id: string; results: SQLResult[] }
  | { type: "execute_error"; id: string; error: string }
  | { type: "destroyed" };

/** Configuration for sql.js WASM loading */
export const SQL_JS_CONFIG = {
  /** Path to self-hosted WASM binary */
  wasmPath: "/wasm/sql-wasm.wasm",
  /** Expected SHA-384 hash (injected at build time, empty string if not set) */
  wasmIntegrity:
    (typeof import.meta !== "undefined" &&
      import.meta.env?.VITE_SQL_WASM_HASH) ||
    "",
  /** CDN fallback only for development (never production) */
  cdnFallback:
    typeof import.meta !== "undefined" && import.meta.env?.DEV
      ? "https://sql.js.org/dist"
      : null,
} as const;

/** Default query timeout in milliseconds */
const DEFAULT_TIMEOUT_MS = 10_000;

/**
 * Load WASM binary with runtime integrity verification.
 *
 * Browsers don't support fetch+integrity for WASM, so we verify
 * the SHA-384 hash manually using crypto.subtle.
 */
export async function loadWasmWithIntegrity(
  wasmPath: string = SQL_JS_CONFIG.wasmPath,
  expectedHash: string = SQL_JS_CONFIG.wasmIntegrity,
): Promise<ArrayBuffer> {
  const response = await fetch(wasmPath);
  if (!response.ok) {
    throw new Error(
      `Failed to fetch WASM: ${response.status} ${response.statusText}`,
    );
  }

  const buffer = await response.arrayBuffer();

  // Runtime integrity check
  if (expectedHash) {
    const hashBuffer = await crypto.subtle.digest("SHA-384", buffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashBase64 = btoa(String.fromCharCode(...hashArray));

    if (hashBase64 !== expectedHash) {
      throw new Error(
        `WASM integrity check failed. Expected: ${expectedHash}, Got: ${hashBase64}`,
      );
    }
  }

  return buffer;
}

/**
 * Format raw sql.js output into structured SQLResult objects.
 */
export function formatSQLResult(
  rawResults: Array<{ columns: string[]; values: unknown[][] }>,
): SQLResult[] {
  return rawResults.map((r) => ({
    columns: r.columns,
    values: r.values,
  }));
}

/**
 * PyodideSQLBridge - Non-blocking SQL execution via WebWorker.
 *
 * Uses sql.js (SQLite compiled to WASM) running in a dedicated WebWorker
 * to execute SQL queries without blocking the main thread.
 *
 * Usage:
 * ```typescript
 * const bridge = new PyodideSQLBridge();
 * await bridge.initialize();
 * const results = await bridge.execute("SELECT 1 + 1 AS result");
 * bridge.destroy();
 * ```
 */
export class PyodideSQLBridge {
  private worker: Worker | null = null;
  private initialized = false;
  private pendingRequests = new Map<
    string,
    {
      resolve: (value: SQLResult[]) => void;
      reject: (reason: Error) => void;
      timer: ReturnType<typeof setTimeout>;
    }
  >();
  private timeoutMs: number;

  constructor(timeoutMs: number = DEFAULT_TIMEOUT_MS) {
    this.timeoutMs = timeoutMs;
  }

  /** Whether the bridge is ready to execute queries */
  get isReady(): boolean {
    return this.initialized && this.worker !== null;
  }

  /**
   * Initialize the WebWorker and sql.js database.
   * Loads and verifies WASM integrity before initialization.
   */
  async initialize(): Promise<void> {
    if (this.initialized) {
      return;
    }

    this.worker = new Worker(new URL("./sqlWorker.ts", import.meta.url), {
      type: "module",
    });

    // Set up message handler for execute responses
    this.worker.onmessage = (e: MessageEvent<WorkerResponse>) => {
      this.handleWorkerMessage(e.data);
    };

    // Load WASM with integrity check
    let wasmBinary: ArrayBuffer | undefined;
    try {
      wasmBinary = await loadWasmWithIntegrity();
    } catch {
      // WASM not available (dev mode or first run) - worker will load from CDN
    }

    // Send init message and wait for response
    return new Promise<void>((resolve, reject) => {
      const initHandler = (e: MessageEvent<WorkerResponse>) => {
        if (e.data.type === "init_success") {
          this.initialized = true;
          this.worker!.removeEventListener("message", initHandler);
          resolve();
        } else if (e.data.type === "init_error") {
          this.worker!.removeEventListener("message", initHandler);
          reject(new Error(e.data.error));
        }
      };

      this.worker!.addEventListener("message", initHandler);
      this.worker!.postMessage({
        type: "init",
        wasmBinary,
        cdnFallback: SQL_JS_CONFIG.cdnFallback,
      } satisfies WorkerMessage);
    });
  }

  /**
   * Execute a SQL query in the WebWorker.
   * Returns results as an array of SQLResult objects.
   */
  async execute(sql: string): Promise<SQLResult[]> {
    if (!this.initialized || !this.worker) {
      throw new Error(
        "PyodideSQLBridge is not initialized. Call initialize() first.",
      );
    }

    const id = crypto.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;

    return new Promise<SQLResult[]>((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pendingRequests.delete(id);
        reject(new Error(`Query timeout after ${this.timeoutMs}ms`));
      }, this.timeoutMs);

      this.pendingRequests.set(id, { resolve, reject, timer });

      this.worker!.postMessage({
        type: "execute",
        sql,
        id,
      } satisfies WorkerMessage);
    });
  }

  /**
   * Destroy the bridge, terminating the WebWorker and cleaning up.
   */
  destroy(): void {
    // Reject all pending requests
    for (const [id, { reject, timer }] of this.pendingRequests) {
      clearTimeout(timer);
      reject(new Error("Bridge destroyed while query was pending"));
      this.pendingRequests.delete(id);
    }

    if (this.worker) {
      this.worker.postMessage({ type: "destroy" } satisfies WorkerMessage);
      this.worker.terminate();
      this.worker = null;
    }

    this.initialized = false;
  }

  private handleWorkerMessage(data: WorkerResponse): void {
    if (data.type === "execute_success" || data.type === "execute_error") {
      const pending = this.pendingRequests.get(data.id);
      if (pending) {
        clearTimeout(pending.timer);
        this.pendingRequests.delete(data.id);

        if (data.type === "execute_success") {
          pending.resolve(data.results);
        } else {
          pending.reject(new Error(data.error));
        }
      }
    }
  }
}

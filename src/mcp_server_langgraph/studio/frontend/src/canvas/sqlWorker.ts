/**
 * SQL WebWorker - Non-blocking sql.js execution
 *
 * Handles initialization and query execution in a dedicated worker thread.
 * Communication with the main thread uses structured messages.
 */

// sql.js types (loaded dynamically)
interface SqlJsDatabase {
  exec(sql: string): Array<{ columns: string[]; values: unknown[][] }>;
  close(): void;
}

interface SqlJsStatic {
  Database: new () => SqlJsDatabase;
}

let db: SqlJsDatabase | null = null;

/**
 * Initialize sql.js with WASM binary (preferred) or CDN fallback.
 *
 * Loading strategy:
 * 1. Use pre-loaded wasmBinary if provided (local-first)
 * 2. Fall back to CDN if cdnFallback URL is provided (dev only)
 * 3. Fail with clear error if neither is available
 */
async function initDatabase(
  wasmBinary?: ArrayBuffer,
  cdnFallback?: string | null,
): Promise<void> {
  const initSqlJs = (await import("sql.js")).default;

  let initConfig:
    | { wasmBinary: ArrayBuffer }
    | { locateFile: (file: string) => string };

  if (wasmBinary) {
    initConfig = { wasmBinary };
  } else if (cdnFallback) {
    initConfig = {
      locateFile: (file: string) => `${cdnFallback}/${file}`,
    };
  } else {
    throw new Error(
      "sql.js WASM binary not available. " +
        "Ensure /wasm/sql-wasm.wasm is present or enable CDN fallback in development.",
    );
  }

  const SQL: SqlJsStatic = await initSqlJs(initConfig);
  db = new SQL.Database();
}

/**
 * Execute SQL against the in-memory database.
 */
function executeSQL(sql: string, id: string): void {
  if (!db) {
    self.postMessage({
      type: "execute_error",
      id,
      error: "Database not initialized",
    });
    return;
  }

  try {
    const results = db.exec(sql);
    self.postMessage({
      type: "execute_success",
      id,
      results: results.map((r) => ({
        columns: r.columns,
        values: r.values,
      })),
    });
  } catch (error) {
    self.postMessage({
      type: "execute_error",
      id,
      error: error instanceof Error ? error.message : String(error),
    });
  }
}

// Message handler
self.onmessage = async (e: MessageEvent) => {
  const { type } = e.data;

  switch (type) {
    case "init":
      try {
        await initDatabase(e.data.wasmBinary, e.data.cdnFallback);
        self.postMessage({ type: "init_success" });
      } catch (error) {
        self.postMessage({
          type: "init_error",
          error: error instanceof Error ? error.message : String(error),
        });
      }
      break;

    case "execute":
      executeSQL(e.data.sql, e.data.id);
      break;

    case "destroy":
      if (db) {
        db.close();
        db = null;
      }
      self.postMessage({ type: "destroyed" });
      break;
  }
};

/**
 * Type declarations for sql.js
 *
 * sql.js is a WebAssembly-based SQLite implementation.
 * Used by sqlWorker.ts for in-browser SQL execution.
 */

declare module "sql.js" {
  export interface SqlJsDatabase {
    exec(sql: string): Array<{ columns: string[]; values: unknown[][] }>;
    close(): void;
    run(sql: string): void;
  }

  export interface SqlJsStatic {
    Database: new (data?: ArrayBuffer | null) => SqlJsDatabase;
  }

  export interface InitSqlJsOptions {
    wasmBinary?: ArrayBuffer;
    locateFile?: (file: string) => string;
  }

  export default function initSqlJs(
    options?: InitSqlJsOptions,
  ): Promise<SqlJsStatic>;
}

/**
 * Handler Ordering Meta-Test
 *
 * This meta-test validates that all MSW handler files follow the correct ordering pattern:
 * Static paths MUST be defined BEFORE parameterized paths to avoid routing conflicts.
 *
 * MSW matches handlers in order of definition. If a parameterized path like /api/v1/foo/:id
 * is defined before a static path like /api/v1/foo/bar, the static path will never match
 * because :id will capture "bar" as the id parameter.
 *
 * This test reads handler files and validates the ordering programmatically.
 */

import { describe, it, expect, afterEach } from "vitest";
import * as fs from "fs";
import * as path from "path";

// Path to handlers directory
const HANDLERS_DIR = path.resolve(__dirname);
const MAIN_HANDLERS_FILE = path.resolve(__dirname, "../handlers.ts");

interface HandlerInfo {
  method: string;
  path: string;
  line: number;
  hasParam: boolean;
  basePrefix: string;
}

/**
 * Extract handler definitions from a TypeScript file
 */
function extractHandlers(filePath: string): HandlerInfo[] {
  const content = fs.readFileSync(filePath, "utf-8");
  const lines = content.split("\n");
  const handlers: HandlerInfo[] = [];

  // Pattern to match http.get/post/etc calls
  const handlerPattern =
    /http\.(get|post|put|patch|delete)\s*\(\s*["'`]([^"'`]+)["'`]/gi;

  lines.forEach((line, index) => {
    let match;
    handlerPattern.lastIndex = 0; // Reset regex state

    while ((match = handlerPattern.exec(line)) !== null) {
      const method = match[1].toLowerCase();
      const handlerPath = match[2];

      // Check if path contains parameters
      const hasParam = handlerPath.includes(":");

      // Extract base prefix (path before first param or full path if no param)
      const paramIndex = handlerPath.indexOf(":");
      const basePrefix =
        paramIndex > 0
          ? handlerPath.substring(
              0,
              handlerPath.lastIndexOf("/", paramIndex) + 1,
            )
          : handlerPath;

      handlers.push({
        method,
        path: handlerPath,
        line: index + 1,
        hasParam,
        basePrefix,
      });
    }
  });

  return handlers;
}

/**
 * Check if a static path could be accidentally matched by a parameterized path.
 *
 * A conflict occurs when:
 * - /api/v1/foo/:id is defined before /api/v1/foo/bar
 * - Because :id would match "bar"
 *
 * NOT a conflict:
 * - /api/v1/foo/:id before /api/v1/foo/:id/sub (sub-resource, different depth)
 * - /api/v1/foo/:id before /api/v1/foo/:id/test (extends the param path)
 */
function wouldConflict(paramPath: string, staticPath: string): boolean {
  // Count path segments
  const paramSegments = paramPath.split("/").filter(Boolean);
  const staticSegments = staticPath.split("/").filter(Boolean);

  // If static path has more segments, it's a sub-resource, not a conflict
  // e.g., /foo/:id (3 segments) vs /foo/:id/test (4 segments) - no conflict
  if (staticSegments.length !== paramSegments.length) {
    return false;
  }

  // Check if the parameterized path pattern would match the static path
  // by comparing segment by segment
  for (let i = 0; i < paramSegments.length; i++) {
    const paramSeg = paramSegments[i];
    const staticSeg = staticSegments[i];

    // If param segment starts with :, it's a wildcard that would match any static segment
    if (paramSeg.startsWith(":")) {
      // This segment would match - continue checking
      continue;
    }

    // If segments don't match exactly, no conflict
    if (paramSeg !== staticSeg) {
      return false;
    }
  }

  // All non-param segments match, so the parameterized path would capture the static path
  return true;
}

/**
 * Find ordering violations across all handlers
 * Now checks all handlers regardless of grouping
 */
function findOrderingViolations(
  handlers: HandlerInfo[],
): Array<{ static: HandlerInfo; parameterized: HandlerInfo }> {
  const violations: Array<{ static: HandlerInfo; parameterized: HandlerInfo }> =
    [];

  for (let i = 0; i < handlers.length; i++) {
    const current = handlers[i];

    // If current handler has a parameter, check if any later handlers are static
    // that could be matched by this parameterized handler (same method only)
    if (current.hasParam) {
      for (let j = i + 1; j < handlers.length; j++) {
        const later = handlers[j];

        // Only compare same HTTP methods
        if (
          later.method === current.method &&
          !later.hasParam &&
          wouldConflict(current.path, later.path)
        ) {
          violations.push({ static: later, parameterized: current });
        }
      }
    }
  }

  return violations;
}

/**
 * Validate handler ordering in a file
 */
function validateHandlerOrdering(filePath: string): {
  valid: boolean;
  violations: string[];
} {
  const handlers = extractHandlers(filePath);
  const foundViolations = findOrderingViolations(handlers);
  const violations: string[] = [];

  for (const violation of foundViolations) {
    violations.push(
      `Line ${violation.parameterized.line}: ${violation.parameterized.method.toUpperCase()} "${violation.parameterized.path}" ` +
        `is defined BEFORE static path "${violation.static.path}" (line ${violation.static.line}). ` +
        `The static path will never match!`,
    );
  }

  return { valid: violations.length === 0, violations };
}

describe("Handler Ordering Meta-Tests", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });
  describe("Main handlers.ts", () => {
    it("should have static paths defined before parameterized paths", () => {
      const result = validateHandlerOrdering(MAIN_HANDLERS_FILE);

      if (!result.valid) {
        console.error("Handler ordering violations found:");
        result.violations.forEach((v) => console.error(`  - ${v}`));
      }

      expect(result.valid).toBe(true);
      expect(result.violations).toEqual([]);
    });

    it("should define connection static paths before :id", () => {
      const handlers = extractHandlers(MAIN_HANDLERS_FILE);

      // Find connection handlers
      const connectionHandlers = handlers.filter((h) =>
        h.path.includes("/connections"),
      );

      // Find the :id handler (GET method, exactly 4 segments: api/v1/connections/:id)
      const idHandler = connectionHandlers.find(
        (h) => h.path === "/api/v1/connections/:id" && h.method === "get",
      );

      // Find static handlers at the same depth that should come before
      // These are paths like /api/v1/connections/templates (4 segments, no params)
      // NOT paths like /api/v1/connections/:id/test (5 segments, sub-resource)
      const staticHandlersAtSameDepth = connectionHandlers.filter((h) => {
        if (h.hasParam) return false;
        const segments = h.path.split("/").filter(Boolean);
        // Same depth as /api/v1/connections/:id (4 segments)
        return (
          segments.length === 4 &&
          h.path.startsWith("/api/v1/connections/") &&
          h.path !== "/api/v1/connections"
        );
      });

      if (idHandler) {
        for (const staticHandler of staticHandlersAtSameDepth) {
          expect(staticHandler.line).toBeLessThan(idHandler.line);
        }
      }
    });

    it("should define workflow static paths before :id", () => {
      const handlers = extractHandlers(MAIN_HANDLERS_FILE);

      // Find workflow handlers
      const workflowHandlers = handlers.filter((h) =>
        h.path.includes("/workflows"),
      );

      // Find the :id handler
      const idHandler = workflowHandlers.find(
        (h) => h.path === "/api/v1/workflows/:id",
      );

      // Find shared-with-me handler
      const sharedHandler = workflowHandlers.find(
        (h) => h.path === "/api/v1/workflows/shared-with-me",
      );

      if (idHandler && sharedHandler) {
        expect(sharedHandler.line).toBeLessThan(idHandler.line);
      }
    });

    it("should define session static paths before :sessionId", () => {
      const handlers = extractHandlers(MAIN_HANDLERS_FILE);

      // Find session handlers
      const sessionHandlers = handlers.filter((h) =>
        h.path.includes("/sessions"),
      );

      // Find the :sessionId handler
      const idHandler = sessionHandlers.find(
        (h) => h.path === "/api/v1/sessions/:sessionId",
      );

      // Find generate-title handler
      const generateTitleHandler = sessionHandlers.find(
        (h) => h.path === "/api/v1/sessions/generate-title",
      );

      if (idHandler && generateTitleHandler) {
        expect(generateTitleHandler.line).toBeLessThan(idHandler.line);
      }
    });
  });

  describe("Handler files in handlers/ directory", () => {
    const handlerFiles = fs
      .readdirSync(HANDLERS_DIR)
      .filter((f) => f.endsWith("Handlers.ts") && !f.endsWith(".test.ts"));

    for (const file of handlerFiles) {
      it(`${file} should have correct handler ordering`, () => {
        const filePath = path.join(HANDLERS_DIR, file);
        const result = validateHandlerOrdering(filePath);

        if (!result.valid) {
          console.error(`Handler ordering violations in ${file}:`);
          result.violations.forEach((v) => console.error(`  - ${v}`));
        }

        expect(result.valid).toBe(true);
        expect(result.violations).toEqual([]);
      });
    }
  });

  describe("Validation utilities", () => {
    it("should detect parameterized paths correctly", () => {
      const testContent = `
        http.get("/api/v1/foo/:id", () => {});
        http.get("/api/v1/foo/bar", () => {});
        http.post("/api/v1/baz/:userId/items", () => {});
      `;

      // Write temp file
      const tempFile = path.join(HANDLERS_DIR, "_temp_test_handlers.ts");
      fs.writeFileSync(tempFile, testContent);

      try {
        const handlers = extractHandlers(tempFile);

        expect(handlers[0].hasParam).toBe(true);
        expect(handlers[0].path).toBe("/api/v1/foo/:id");

        expect(handlers[1].hasParam).toBe(false);
        expect(handlers[1].path).toBe("/api/v1/foo/bar");

        expect(handlers[2].hasParam).toBe(true);
        expect(handlers[2].path).toBe("/api/v1/baz/:userId/items");
      } finally {
        fs.unlinkSync(tempFile);
      }
    });

    it("should detect ordering violations", () => {
      // Test the wouldConflict function directly
      // /api/v1/items/:id would match /api/v1/items/special (same depth, param matches static)
      expect(wouldConflict("/api/v1/items/:id", "/api/v1/items/special")).toBe(
        true,
      );

      // /api/v1/items/:id would NOT match /api/v1/items/:id/test (different depth)
      expect(wouldConflict("/api/v1/items/:id", "/api/v1/items/:id/test")).toBe(
        false,
      );

      // /api/v1/items/:id would NOT match /api/v1/other/special (different prefix)
      expect(wouldConflict("/api/v1/items/:id", "/api/v1/other/special")).toBe(
        false,
      );

      // Now test the full validation with a file
      const testContent = [
        'http.get("/api/v1/items/:id", () => {});',
        'http.get("/api/v1/items/special", () => {});',
      ].join("\n");

      const tempFile = path.join(HANDLERS_DIR, "_temp_violation_handlers.ts");
      fs.writeFileSync(tempFile, testContent);

      try {
        const handlers = extractHandlers(tempFile);
        expect(handlers.length).toBe(2);
        expect(handlers[0].path).toBe("/api/v1/items/:id");
        expect(handlers[1].path).toBe("/api/v1/items/special");

        const result = validateHandlerOrdering(tempFile);

        expect(result.valid).toBe(false);
        expect(result.violations.length).toBe(1);
        expect(result.violations[0]).toContain("/api/v1/items/special");
      } finally {
        fs.unlinkSync(tempFile);
      }
    });

    it("should pass when ordering is correct", () => {
      const testContent = `
        http.get("/api/v1/items/special", () => {});
        http.get("/api/v1/items/:id", () => {});
      `;

      // Write temp file
      const tempFile = path.join(HANDLERS_DIR, "_temp_correct_handlers.ts");
      fs.writeFileSync(tempFile, testContent);

      try {
        const result = validateHandlerOrdering(tempFile);

        expect(result.valid).toBe(true);
        expect(result.violations).toEqual([]);
      } finally {
        fs.unlinkSync(tempFile);
      }
    });
  });
});

#!/usr/bin/env npx ts-node
/**
 * Audit Script: API Mock Format Analysis
 *
 * Scans MSW handlers and test fixtures to identify:
 * 1. MSW handlers returning camelCase (should be snake_case)
 * 2. Test fixtures using camelCase API responses (should be snake_case)
 * 3. Missing transformSnakeToCamel calls in hooks using authenticatedFetch
 *
 * Usage: npx ts-node scripts/audit-api-mocks.ts
 */

import * as fs from "fs";
import * as path from "path";
import { glob } from "glob";

interface AuditResult {
  file: string;
  line: number;
  issue: string;
  snippet: string;
}

const results: AuditResult[] = [];

// Common snake_case patterns that should appear in API responses
const SNAKE_CASE_PATTERNS = [
  "current_step",
  "node_id",
  "node_name",
  "start_time",
  "end_time",
  "input_schema",
  "created_at",
  "updated_at",
  "session_id",
  "workflow_id",
  "user_id",
  "trace_id",
  "span_id",
  "raw_output",
  "current_node",
  "show_after_ms",
  "target_element",
];

// camelCase equivalents that indicate non-transformed mock data
const CAMEL_CASE_PATTERNS = [
  "currentStep",
  "nodeId",
  "nodeName",
  "startTime",
  "endTime",
  "inputSchema",
  "createdAt",
  "updatedAt",
  "sessionId",
  "workflowId",
  "userId",
  "traceId",
  "spanId",
  "rawOutput",
  "currentNode",
  "showAfterMs",
  "targetElement",
];

function analyzeFile(filePath: string, content: string): void {
  const lines = content.split("\n");
  const relativePath = path.relative(process.cwd(), filePath);

  // Check for MSW handlers
  if (filePath.includes("/mocks/") && filePath.includes("Handler")) {
    // Look for HttpResponse.json with camelCase keys
    lines.forEach((line, index) => {
      for (const pattern of CAMEL_CASE_PATTERNS) {
        // Match property assignments like `nodeId:` or `"nodeId":`
        const regex = new RegExp(`["']?${pattern}["']?\\s*:`);
        if (regex.test(line)) {
          results.push({
            file: relativePath,
            line: index + 1,
            issue: `MSW handler returns camelCase '${pattern}' - should be snake_case`,
            snippet: line.trim().substring(0, 80),
          });
        }
      }
    });
  }

  // Check for test fixtures in test files
  if (filePath.includes(".test.") || filePath.includes("__tests__")) {
    // Look for mock API response objects with camelCase
    let inMockResponse = false;
    let braceDepth = 0;

    lines.forEach((line, index) => {
      // Detect mock response patterns
      if (
        line.includes("mockResolvedValue") ||
        line.includes("Promise.resolve") ||
        line.includes("json:") ||
        line.includes("HttpResponse.json")
      ) {
        inMockResponse = true;
        braceDepth = 0;
      }

      if (inMockResponse) {
        braceDepth += (line.match(/{/g) || []).length;
        braceDepth -= (line.match(/}/g) || []).length;

        for (const pattern of CAMEL_CASE_PATTERNS) {
          const regex = new RegExp(`["']?${pattern}["']?\\s*:`);
          if (regex.test(line)) {
            results.push({
              file: relativePath,
              line: index + 1,
              issue: `Test fixture uses camelCase '${pattern}' in mock API response - should be snake_case`,
              snippet: line.trim().substring(0, 80),
            });
          }
        }

        if (braceDepth <= 0) {
          inMockResponse = false;
        }
      }
    });
  }

  // Check for hooks using authenticatedFetch without transformation
  if (filePath.includes("/hooks/") && !filePath.includes(".test.")) {
    const hasAuthenticatedFetch = content.includes("authenticatedFetch");
    const hasTransform =
      content.includes("transformSnakeToCamel") ||
      content.includes("transformResponse");

    if (hasAuthenticatedFetch && !hasTransform) {
      // Check if it's actually fetching data (not just a POST without response)
      if (
        content.includes("response.json()") ||
        content.includes("await response.json()")
      ) {
        results.push({
          file: relativePath,
          line: 1,
          issue:
            "Hook uses authenticatedFetch but missing transformSnakeToCamel",
          snippet: "Uses response.json() without transformation",
        });
      }
    }
  }
}

async function main(): Promise<void> {
  console.log("🔍 Auditing API mock formats...\n");

  // Find all relevant files
  const patterns = [
    "src/mocks/**/*.ts",
    "src/**/*.test.ts",
    "src/**/*.test.tsx",
    "src/hooks/*.ts",
    "src/components/**/hooks/*.ts",
  ];

  let allFiles: string[] = [];
  for (const pattern of patterns) {
    const files = await glob(pattern, { ignore: ["node_modules/**"] });
    allFiles = [...allFiles, ...files];
  }

  // Deduplicate
  allFiles = [...new Set(allFiles)];

  console.log(`Found ${allFiles.length} files to analyze\n`);

  // Analyze each file
  for (const file of allFiles) {
    try {
      const content = fs.readFileSync(file, "utf-8");
      analyzeFile(file, content);
    } catch (err) {
      console.error(`Error reading ${file}:`, err);
    }
  }

  // Group results by category
  const mswIssues = results.filter((r) => r.issue.includes("MSW handler"));
  const fixtureIssues = results.filter((r) => r.issue.includes("Test fixture"));
  const hookIssues = results.filter((r) =>
    r.issue.includes("authenticatedFetch"),
  );

  // Print summary
  console.log("=" .repeat(80));
  console.log("AUDIT SUMMARY");
  console.log("=".repeat(80));

  console.log(`\n📦 MSW Handlers with camelCase: ${mswIssues.length}`);
  if (mswIssues.length > 0) {
    const uniqueFiles = [...new Set(mswIssues.map((r) => r.file))];
    uniqueFiles.forEach((f) => console.log(`   - ${f}`));
  }

  console.log(`\n🧪 Test Fixtures with camelCase: ${fixtureIssues.length}`);
  if (fixtureIssues.length > 0) {
    const uniqueFiles = [...new Set(fixtureIssues.map((r) => r.file))];
    uniqueFiles.slice(0, 20).forEach((f) => console.log(`   - ${f}`));
    if (uniqueFiles.length > 20) {
      console.log(`   ... and ${uniqueFiles.length - 20} more files`);
    }
  }

  console.log(`\n🔗 Hooks missing transformation: ${hookIssues.length}`);
  if (hookIssues.length > 0) {
    hookIssues.forEach((r) => console.log(`   - ${r.file}`));
  }

  console.log("\n" + "=".repeat(80));
  console.log(`TOTAL ISSUES: ${results.length}`);
  console.log("=".repeat(80));

  // Write detailed results to file
  const reportPath = "scripts/api-mock-audit-report.json";
  fs.writeFileSync(
    reportPath,
    JSON.stringify(
      {
        summary: {
          mswHandlers: mswIssues.length,
          testFixtures: fixtureIssues.length,
          hooks: hookIssues.length,
          total: results.length,
        },
        mswHandlerFiles: [...new Set(mswIssues.map((r) => r.file))],
        testFixtureFiles: [...new Set(fixtureIssues.map((r) => r.file))],
        hookFiles: [...new Set(hookIssues.map((r) => r.file))],
        details: results,
      },
      null,
      2,
    ),
  );
  console.log(`\n📝 Detailed report written to: ${reportPath}`);
}

main().catch(console.error);

/**
 * Persona Fixtures for E2E Tests
 *
 * Provides persona-specific test fixtures with:
 * - Visible modules from PersonaVariants
 * - Theme configuration for UI verification
 * - Accessibility testing with @axe-core/playwright
 *
 * Usage:
 * ```typescript
 * import { test, expect, checkA11y } from '../fixtures/persona-fixtures';
 *
 * test.describe('Admin Journey', () => {
 *   test.use({ persona: 'admin' });
 *
 *   test('should have accessible dashboard', async ({ page, visibleModules }) => {
 *     await page.goto('/studio/admin');
 *     await checkA11y(page);
 *   });
 * });
 * ```
 */

import { test as base, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

// =============================================================================
// Persona Configuration (mirrors PersonaVariants.ts)
// =============================================================================

export type PersonaId =
  | "admin"
  | "security-admin"
  | "auditor"
  | "alice-builder"
  | "alice-analyst"
  | "alice-devops"
  | "compliance-officer"
  | "bob";

export type ModuleId =
  | "projects"
  | "chat"
  | "workflows"
  | "agents"
  | "mcp"
  | "vectors"
  | "connections"
  | "files"
  | "traces"
  | "observability"
  | "cost"
  | "admin"
  | "audit"
  | "compliance"
  | "help"
  | "settings";

/**
 * Visible modules per persona (mirrors PersonaVariants.ts)
 */
export const PERSONA_VISIBLE_MODULES: Record<PersonaId, ModuleId[]> = {
  admin: [
    "projects",
    "chat",
    "workflows",
    "agents",
    "mcp",
    "vectors",
    "files",
    "traces",
    "observability",
    "cost",
    "admin",
    "audit",
    "compliance",
    "settings",
    "help",
  ],
  "security-admin": ["admin", "audit", "compliance", "settings", "help"],
  auditor: ["audit", "compliance", "help"],
  "alice-builder": [
    "projects",
    "chat",
    "workflows",
    "agents",
    "mcp",
    "vectors",
    "files",
    "traces",
    "cost",
    "settings",
    "help",
  ],
  "alice-analyst": [
    "projects",
    "chat",
    "traces",
    "observability",
    "cost",
    "settings",
    "help",
  ],
  "alice-devops": [
    "projects",
    "chat",
    "agents",
    "mcp",
    "connections",
    "traces",
    "settings",
    "help",
  ],
  "compliance-officer": ["audit", "compliance", "help"],
  bob: ["projects", "chat", "workflows", "help"],
};

/**
 * Default view per persona
 */
export const PERSONA_DEFAULT_VIEW: Record<PersonaId, string> = {
  admin: "/studio/admin",
  "security-admin": "/studio/compliance",
  auditor: "/studio/audit",
  "alice-builder": "/studio/chat",
  "alice-analyst": "/studio/observability",
  "alice-devops": "/studio/connections",
  "compliance-officer": "/studio/compliance",
  bob: "/studio/chat",
};

/**
 * Theme accent colors per persona (for visual verification)
 */
export const PERSONA_THEME_ACCENT: Record<PersonaId, string> = {
  admin: "red",
  "security-admin": "orange",
  auditor: "yellow",
  "alice-builder": "blue",
  "alice-analyst": "purple",
  "alice-devops": "cyan",
  "compliance-officer": "teal",
  bob: "green",
};

// =============================================================================
// Accessibility Testing Utilities
// =============================================================================

/**
 * WCAG tags for accessibility testing
 */
export const WCAG_TAGS = [
  "wcag2a",
  "wcag2aa",
  "wcag21a",
  "wcag21aa",
  "wcag22aa",
] as const;

export interface A11yCheckResult {
  violations: Array<{
    id: string;
    impact: "minor" | "moderate" | "serious" | "critical";
    description: string;
    helpUrl: string;
    nodes: Array<{ html: string; failureSummary: string }>;
  }>;
  passes: number;
  incomplete: number;
}

/**
 * Check accessibility violations on current page
 *
 * @param page - Playwright page
 * @param options - Optional configuration
 * @returns A11y check result
 */
export async function checkA11y(
  page: Page,
  options: {
    /** Include specific element selectors only */
    include?: string[];
    /** Exclude specific element selectors */
    exclude?: string[];
    /** Disable specific rules */
    disableRules?: string[];
    /** Use stricter AAA tags */
    strict?: boolean;
  } = {}
): Promise<A11yCheckResult> {
  let builder = new AxeBuilder({ page }).withTags([...WCAG_TAGS]);

  if (options.strict) {
    builder = builder.withTags([...WCAG_TAGS, "wcag2aaa"]);
  }

  if (options.include?.length) {
    builder = builder.include(options.include);
  }

  if (options.exclude?.length) {
    builder = builder.exclude(options.exclude);
  }

  if (options.disableRules?.length) {
    builder = builder.disableRules(options.disableRules);
  }

  const results = await builder.analyze();

  return {
    violations: results.violations.map((v) => ({
      id: v.id,
      impact: v.impact as "minor" | "moderate" | "serious" | "critical",
      description: v.description,
      helpUrl: v.helpUrl,
      nodes: v.nodes.map((n) => ({
        html: n.html,
        failureSummary: n.failureSummary || "",
      })),
    })),
    passes: results.passes.length,
    incomplete: results.incomplete.length,
  };
}

/**
 * Assert no accessibility violations
 *
 * @param page - Playwright page
 * @param options - Optional configuration
 */
export async function expectNoA11yViolations(
  page: Page,
  options: Parameters<typeof checkA11y>[1] = {}
): Promise<void> {
  const result = await checkA11y(page, options);

  if (result.violations.length > 0) {
    const violationMessages = result.violations
      .map((v) => {
        const nodeInfo = v.nodes
          .slice(0, 3) // Show max 3 nodes
          .map((n) => `    - ${n.html.slice(0, 100)}`)
          .join("\n");
        return `  [${v.impact}] ${v.id}: ${v.description}\n${nodeInfo}`;
      })
      .join("\n\n");

    throw new Error(
      `Found ${result.violations.length} accessibility violations:\n\n${violationMessages}`
    );
  }
}

// =============================================================================
// Persona Test Fixtures
// =============================================================================

export interface PersonaFixtures {
  /** Current persona ID */
  persona: PersonaId;
  /** Visible modules for current persona */
  visibleModules: ModuleId[];
  /** Default view URL for current persona */
  defaultView: string;
  /** Theme accent color for current persona */
  themeAccent: string;
}

/**
 * Extended test with persona fixtures
 */
export const test = base.extend<PersonaFixtures>({
  // Default persona (can be overridden with test.use())
  persona: ["admin", { option: true }],

  // Derived from persona
  visibleModules: async ({ persona }, use) => {
    await use(PERSONA_VISIBLE_MODULES[persona] || []);
  },

  defaultView: async ({ persona }, use) => {
    await use(PERSONA_DEFAULT_VIEW[persona] || "/studio/chat");
  },

  themeAccent: async ({ persona }, use) => {
    await use(PERSONA_THEME_ACCENT[persona] || "blue");
  },
});

export { expect } from "@playwright/test";

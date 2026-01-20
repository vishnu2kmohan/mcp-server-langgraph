// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from '@eslint/js';
import globals from 'globals';
import reactPlugin from 'eslint-plugin-react';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

/**
 * IMPORTANT: RTK Query + useEffect Infinite Loop Pattern
 *
 * The react-hooks/exhaustive-deps rule warns about missing dependencies in useEffect.
 * However, with RTK Query mutations, adding the callback to deps causes INFINITE LOOPS:
 *
 * DANGEROUS PATTERN (causes infinite loop):
 * ```typescript
 * const [mutation] = useSomeMutation();
 *
 * const fetchData = useCallback(async () => {
 *   await mutation({ ... }).unwrap();
 * }, [mutation]);  // mutation changes on every render!
 *
 * useEffect(() => {
 *   fetchData();
 * }, [fetchData]);  // fetchData changes → re-runs → infinite loop!
 * ```
 *
 * SAFE PATTERN (use ref to prevent re-runs):
 * ```typescript
 * const hasFetchedRef = useRef(false);
 *
 * useEffect(() => {
 *   if (!hasFetchedRef.current) {
 *     hasFetchedRef.current = true;
 *     fetchData();
 *   }
 *   // eslint-disable-next-line react-hooks/exhaustive-deps
 * }, [enabled, sessionId]);  // Omit fetchData, use ref guard
 * ```
 *
 * When you see eslint-disable for exhaustive-deps, check for this pattern.
 * See: useSessionIntelligence.ts for correct implementation examples.
 */

export default tseslint.config({ ignores: ['dist', 'node_modules'] }, {
  extends: [js.configs.recommended, ...tseslint.configs.recommended],
  files: ['**/*.{ts,tsx}'],
  languageOptions: {
    ecmaVersion: 2020,
    globals: globals.browser,
  },
  plugins: {
    react: reactPlugin,
    'react-hooks': reactHooks,
    'react-refresh': reactRefresh,
  },
  rules: {
    ...reactHooks.configs.recommended.rules,
    'react-refresh/only-export-components': [
      'warn',
      { allowConstantExport: true },
    ],
    '@typescript-eslint/no-unused-vars': [
      'error',
      {
        argsIgnorePattern: '^_',
        varsIgnorePattern: '^_',
        destructuredArrayIgnorePattern: '^_',
      },
    ],
    // Design System: Enforce UI component usage over raw HTML elements
    // Use <Button> from components/UI instead of raw <button>
    // This catches design system bypass and ensures consistent styling
    // UPGRADED to 'error' (2026-01-11): All design system components available.
    // Button, Input, Checkbox, RadioGroup, Select, Textarea, FileInput, Toggle, Slider.
    // Exceptions configured via file-level overrides below.
    'react/forbid-elements': [
      'error',
      {
        forbid: [
          {
            element: 'button',
            message:
              'Use <Button> from @/components/UI instead of raw <button>. Import: import { Button } from "@/components/UI";',
          },
          {
            element: 'input',
            message:
              'Use <Input>, <Checkbox>, or <RadioGroup> from @/components/UI. For search, use <SearchInput>. For file uploads, use type="file" with sr-only class.',
          },
          {
            element: 'select',
            message:
              'Use design system dropdown/select components from @/components/UI instead of raw <select>.',
          },
          {
            element: 'textarea',
            message:
              'Use design system text area components from @/components/UI instead of raw <textarea>.',
          },
        ],
      },
    ],
    'no-restricted-globals': [
      'error',
      {
        name: 'localStorage',
        message:
          'Use the storage utility from utils/storage.ts instead. Import { storage } for get/set/remove or { getAuthToken, setAuthTokens, clearAuthTokens } for auth tokens.',
      },
      {
        name: 'sessionStorage',
        message:
          'Use the storage utility from utils/storage.ts instead for consistent storage abstraction.',
      },
    ],
    // Note: buildWebSocketUrl now requires all 3 parameters (TypeScript enforced as of 2024-12)
    // This rule is no longer needed since TypeScript will error on missing params.
    // Keeping as documentation of the pattern that led to this change.
    // See: websocketAuthContract.test.ts for the contract tests that validate auth requirements.

    // Block imports of deprecated buildWebSocketUrl from config/api.ts
    // Use the new version from utils/websocket.ts which has required auth parameter
    // Also enforce design system import patterns
    'no-restricted-imports': [
      'error',
      {
        patterns: [
          {
            group: ['**/config/api'],
            importNames: ['buildWebSocketUrl'],
            message:
              'buildWebSocketUrl from config/api.ts is deprecated. Import from utils/websocket.ts instead: import { buildWebSocketUrl } from "../utils/websocket"',
          },
          // Design System: Enforce barrel imports for UI components
          // Import from "@/components/UI" instead of direct file imports
          {
            group: [
              '**/components/UI/Button',
              '**/components/UI/Badge',
              '**/components/UI/Card',
              '**/components/UI/Dialog',
              '**/components/UI/Skeleton',
              '**/components/UI/SearchInput',
              '**/components/UI/Pagination',
            ],
            message:
              'Import from "@/components/UI" barrel instead of direct file imports. Example: import { Button, Badge } from "@/components/UI";',
          },
          // Design System: Use cn() utility instead of clsx/classnames
          // cn() is the standard class merging utility in this codebase
          {
            group: ['clsx', 'classnames'],
            message:
              'Use cn() from "@/utils/cn" for class merging instead of clsx/classnames.',
          },
        ],
      },
    ],

    // Catch common snake_case API field patterns in new code
    // This helps prevent regressions after the camelCase API transformation
    // See ADR-0091 for the complete API transformation strategy
    // ADR-0091 Phase 4: Upgraded from 'warn' to 'error' for strict enforcement
    'no-restricted-syntax': [
      'error',
      {
        selector:
          "MemberExpression[property.name=/^(alert_id|started_at|ended_at|created_at|updated_at|user_id|session_id|trace_id|span_id|workflow_id|project_id|organization_id|remediation_id|recommendation_id|step_number|risk_level|total_cost|total_tokens|prompt_tokens|completion_tokens|request_count|next_cursor|prev_cursor|has_next|has_prev|auth_type|api_key|default_level|feature_flag|task_categories|version_number|graph_json|source_text|commit_message|created_by|prompt_version|prompt_model|head_version_id|node_count|edge_count|message_count|owner_id|connection_type|tool_count|max_tokens|request_id|per_page|total_pages)$/]",
        message:
          'Use camelCase field names (e.g., alertId, startedAt, userId). API responses are now transformed via RTK Query transformResponse. See ADR-0091.',
      },
      // Design System: Enforce semantic colors over raw Tailwind colors
      // Mappings:
      //   violet-* / purple-* -> insight-* (AI features)
      //   indigo-* / blue-* / sky-* -> primary-* (Primary actions)
      //   emerald-* / green-* / lime-* -> success-* (Success states)
      //   red-* / rose-* -> error-* (Error states)
      //   amber-* / yellow-* -> warning-* (Warning states)
      //   cyan-* / teal-* -> info-* (Informational)
      //   gray-* / slate-* / zinc-* / stone-* -> neutral-* (General UI)
      //   orange-* -> grafana-* (Observability brand)
      //   pink-* / fuchsia-* -> error-* or insight-* depending on context
      // Exceptions: NodePalette.tsx, TraceCanvas.tsx (categorical colors), tokens.ts, charts
      // See: docs-internal/frontend/STYLE.md and scripts/migrate-raw-colors.sh
      {
        selector:
          "Literal[value=/\\b(text|bg|border|ring|divide|outline|shadow|from|to|via|hover:text|hover:bg|hover:border|focus:ring|focus:border|active:bg|dark:text|dark:bg|dark:border)-(red|green|blue|yellow|amber|purple|orange|cyan|violet|indigo|emerald|rose|teal|sky|pink|fuchsia|lime)-\\d+/]",
        message:
          'Use semantic colors instead of raw Tailwind colors. Mappings: red/rose->error-*, green/emerald/lime->success-*, yellow/amber->warning-*, blue/indigo/sky->primary-*, violet/purple->insight-*, cyan/teal->info-*, orange->grafana-*. See docs-internal/frontend/STYLE.md',
      },
      // Design System: Enforce neutral-* over gray-*/slate-*/zinc-*/stone-*
      // This was historically "warn" due to high usage count, but migration is now complete.
      // Upgraded to error for new code (2026-01-12)
      {
        selector:
          "Literal[value=/\\b(text|bg|border|ring|divide|hover:bg|hover:text|hover:border|dark:text|dark:bg|dark:border)-(gray|slate|zinc|stone)-\\d+/]",
        message:
          'Use neutral-* instead of gray-*/slate-*/zinc-*/stone-* for semantic consistency. See docs-internal/frontend/STYLE.md',
      },
      // WCAG 2.2 AA Contrast: Catch low-contrast dark mode text patterns
      // neutral-400 fails contrast in dark mode (4.03:1 on dark-1 background)
      // Use neutral-300 or lighter for WCAG AA compliance (4.5:1 minimum)
      // Added 2026-01-13 after comprehensive accessibility audit
      {
        selector:
          "Literal[value=/dark:text-neutral-400/]",
        message:
          'dark:text-neutral-400 fails WCAG 2.2 AA contrast (4.03:1 < 4.5:1 required). Use dark:text-neutral-300 or lighter. See ContrastAccessibility.test.tsx for safe patterns.',
      },
      // WCAG 2.2 AA Contrast: Low-opacity background patterns
      // NOTE: Regex selector disabled - esquery can't parse forward slashes in patterns.
      // Opacity values /20 and /30 often result in insufficient contrast.
      // Use /40 minimum for dark mode backgrounds, /50 for badges.
      // Enforcement: ContrastAccessibility.test.tsx validates these patterns at test time.
      // Theme Consistency: Prefer Radix semantic colors over legacy Tailwind patterns
      // With Radix Colors v3.0.0+, bg-neutral-1/2/3 auto-switch via .dark class selector.
      // This is more maintainable than explicit bg-white dark:bg-neutral-900 patterns.
      // Radix 1-12 scale: 1-2 backgrounds, 3-5 interactive, 6-8 borders, 9-10 solid, 11-12 text
      // Updated 2026-01-14 to reflect Radix v3.0.0 best practices
      {
        selector:
          "Literal[value=/bg-white\\s+dark:bg-neutral-900/]",
        message:
          'Use bg-neutral-1 instead of bg-white dark:bg-neutral-900. Radix Colors v3.0.0+ auto-switches via .dark class. See docs-internal/frontend/STYLE.md#radix-colors',
      },
      {
        selector:
          "Literal[value=/bg-neutral-50\\s+dark:bg-neutral-800/]",
        message:
          'Use bg-neutral-2 instead of bg-neutral-50 dark:bg-neutral-800. Radix Colors v3.0.0+ auto-switches via .dark class. See docs-internal/frontend/STYLE.md#radix-colors',
      },
      // Radix Colors: Prevent legacy neutral-100 to neutral-900 patterns
      // Use Radix 1-12 scale instead:
      //   Text: 900/800→12, 700/600→11, 500→10, 400/300→9
      //   BG:   900→2, 800→3, 700→4, 600/500→5, 400/300/200→3-4, 100/50→1-2
      //   Border: 800/700→7, 600/500/400→6, 300/200/100→5
      // Migration: scripts/migrate-legacy-neutrals.py
      // Added 2026-01-14 to prevent regression after comprehensive migration
      {
        selector:
          "Literal[value=/\\b(text|bg|border|hover:bg|hover:text|focus:bg|focus:border|ring|divide)-neutral-(100|200|300|400|500|600|700|800|900|950)\\b/]",
        message:
          'Use Radix neutral-1 to neutral-12 scale instead of legacy neutral-100 to neutral-900. Text: 900→12, 700→11, 500→10, 400→9. BG: 900→2, 800→3, 700→4. Border: 700→7, 500→6, 300→5. Run: python scripts/migrate-legacy-neutrals.py',
      },
      // Radix Colors: Prevent redundant dark: prefix patterns
      // Radix v3.0.0+ uses .dark class selector - colors auto-switch
      // dark:bg-* and dark:text-* with neutral-1 to neutral-12 are redundant
      {
        selector:
          "Literal[value=/dark:(bg|text|border|hover:bg|hover:text)-neutral-\\d+/]",
        message:
          'Radix Colors v3.0.0+ auto-switches via .dark class selector - no dark: prefix needed. Use bg-neutral-X directly. See docs-internal/frontend/STYLE.md#radix-colors',
      },
      // ============================================================================
      // Design System: Sizing Token Enforcement
      // Added 2026-01-14 for consistent sizing across the codebase
      // See docs-internal/frontend/STYLE.md#sizing-decisions for exemptions
      // ============================================================================
      // Catch arbitrary height values - use Tailwind spacing scale instead
      // Exemptions: vh/vw units, calc(), WCAG touch targets (32px/44px),
      //             workflow nodes (180px), container heights (300-600px)
      {
        selector:
          "Literal[value=/\\bh-\\[(?!calc\\()(?!\\d+vh)(?!300px|400px|500px|600px)\\d+(?!vh)/]",
        message:
          'Use design token heights (h-8, h-10, h-12, etc.) instead of arbitrary h-[Xpx]. Exempted: h-[calc(...)], h-[Xvh], h-[300-600px] containers. See docs-internal/frontend/STYLE.md#sizing-decisions',
      },
      // Catch arbitrary width values - use Tailwind width utilities instead
      // Exemptions: vw units, calc(), percentages, workflow nodes (180px)
      {
        selector:
          "Literal[value=/\\bw-\\[(?!calc\\()(?!\\d+vw)(?!\\d+%)(?!180px)\\d+/]",
        message:
          'Use design token widths (w-full, w-64, max-w-xs, etc.) instead of arbitrary w-[Xpx]. Exempted: w-[calc(...)], w-[Xvw], w-[X%], w-[180px] nodes. See docs-internal/frontend/STYLE.md#sizing-decisions',
      },
      // Catch non-standard size props - use sm/md/lg/xl
      {
        selector:
          "Literal[value=/size=[\"'](?:small|medium|large|xs|xxl|tiny|huge|mini|micro|massive)[\"']/i]",
        message:
          'Use standard size prop values: "sm", "md", "lg", "xl", or "icon". Not: small, medium, large, xs, xxl.',
      },
      // ============================================================================
      // Design System: Spacing Token Enforcement
      // Added 2026-01-14 for consistent spacing (4px base unit scale)
      // ============================================================================
      // Catch arbitrary padding values - use Tailwind spacing scale
      // Exemptions: vh/vw units for viewport-relative positioning
      {
        selector:
          "Literal[value=/\\bp[trblxy]?-\\[(?!\\d+vh)(?!\\d+vw)\\d+/]",
        message:
          'Use design token padding (p-4, p-6, px-3, etc.) instead of arbitrary p-[Xpx]. Scale: 1=4px, 2=8px, 3=12px, 4=16px, 5=20px, 6=24px. Exempted: p-[Xvh/vw].',
      },
      // Catch arbitrary margin values
      {
        selector:
          "Literal[value=/\\bm[trblxy]?-\\[(?!\\d+vh)(?!\\d+vw)\\d+/]",
        message:
          'Use design token margin (m-4, mt-2, mx-auto, etc.) instead of arbitrary m-[Xpx]. Exempted: m-[Xvh/vw].',
      },
      // Catch arbitrary gap values
      {
        selector:
          "Literal[value=/\\bgap(?:-[xy])?-\\[\\d+/]",
        message:
          'Use design token gap (gap-2, gap-4, gap-6, etc.) instead of arbitrary gap-[Xpx].',
      },
      // ============================================================================
      // Design System: Z-Index Token Enforcement
      // Tokens: z-0, z-10 (tooltip), z-50 (dropdown), z-55 (command palette),
      //         z-60 (modal), z-65 (notification), z-70 (system alert), z-75 (toast)
      // Added 2026-01-14 for consistent stacking context
      // ============================================================================
      // Catch arbitrary z-index values
      {
        selector:
          "Literal[value=/\\bz-\\[\\d+\\]/]",
        message:
          'Use design token z-index (z-10, z-50, z-55, z-60, z-65, z-70, z-75) instead of arbitrary z-[X]. See tailwind.config.ts for z-index scale.',
      },
      // Catch non-token z-index values (z-20, z-30, z-40, z-100, etc.)
      {
        selector:
          "Literal[value=/\\bz-(?:20|30|40|100|999|\\d{3,})\\b/]",
        message:
          'Use design token z-index. Available: z-0, z-10 (tooltip), z-50 (dropdown), z-55 (cmd palette), z-60 (modal), z-65 (notification), z-70 (alert), z-75 (toast).',
      },
      // ============================================================================
      // Design System: Animation Duration Token Enforcement
      // Tokens: duration-75, duration-100, duration-150, duration-200,
      //         duration-300, duration-500, duration-700, duration-1000
      // Added 2026-01-14 for consistent motion timing
      // ============================================================================
      // Catch arbitrary duration values
      {
        selector:
          "Literal[value=/\\bduration-\\[[^\\]]+\\]/]",
        message:
          'Use design token durations (duration-150, duration-300, duration-500) instead of arbitrary duration-[Xms]. See design-system/animation-tokens.ts.',
      },
      // Catch arbitrary delay values
      {
        selector:
          "Literal[value=/\\bdelay-\\[[^\\]]+\\]/]",
        message:
          'Use design token delays (delay-75, delay-100, delay-150, etc.) instead of arbitrary delay-[Xms].',
      },
      // ============================================================================
      // Design System: Inline Style Enforcement
      // Added 2026-01-15 to catch inline style props and <style> blocks
      // ============================================================================
      // Catch inline style objects - prefer Tailwind classes
      // Exemptions: Dynamic values (transforms, animations), third-party libs
      {
        selector:
          "JSXAttribute[name.name='style'][value.type='JSXExpressionContainer']",
        message:
          'Avoid inline style={{...}} props. Use Tailwind utility classes instead. Exemptions: dynamic transforms, third-party lib integration, canvas/SVG positioning.',
      },
      // Catch <style> JSX elements - these bypass the design system
      {
        selector:
          "JSXElement[openingElement.name.name='style']",
        message:
          'Avoid <style> blocks. Migrate CSS to Tailwind utility classes or design system components. See ConnectionTemplateSelector migration as reference.',
      },
      // ============================================================================
      // Design System: Inline Badge Pattern Detection
      // Catches common inline badge styling patterns to promote Badge component adoption
      // Added 2026-01-15 to reduce inline badge patterns (120 files identified in audit)
      // ============================================================================
      // Detect common inline badge class patterns: px-2 py-0.5 rounded (compact pill)
      {
        selector:
          "Literal[value=/px-2\\s+py-0\\.5\\s+.*rounded/]",
        message:
          'Use <Badge size="sm"> from @/components/UI instead of inline badge styling (px-2 py-0.5 rounded). Import: import { Badge } from "@/components/UI";',
      },
      // Detect common inline badge class patterns: px-2 py-1 rounded (standard pill)
      {
        selector:
          "Literal[value=/px-2\\s+py-1\\s+.*rounded/]",
        message:
          'Use <Badge> from @/components/UI instead of inline badge styling (px-2 py-1 rounded). Import: import { Badge } from "@/components/UI";',
      },
      // Detect inline badge with text-xs sizing pattern
      {
        selector:
          "Literal[value=/text-xs\\s+.*px-\\d+\\s+py-\\d+.*rounded|rounded.*text-xs\\s+px-\\d+\\s+py-\\d+/]",
        message:
          'Use <Badge> from @/components/UI instead of inline text-xs badge styling. Badge has size="sm" for compact badges.',
      },
      // Detect inline badge-full (pill) pattern
      {
        selector:
          "Literal[value=/px-\\d+\\s+py-\\d+(\\.\\d+)?\\s+.*rounded-full/]",
        message:
          'Use <Badge rounded="full"> from @/components/UI instead of inline pill styling (rounded-full). Import: import { Badge } from "@/components/UI";',
      },
    ],
  },
}, // Override for storage utility - it legitimately needs direct localStorage access
{
  files: ['**/utils/storage.ts'],
  rules: {
    'no-restricted-globals': 'off',
  },
}, // Override for test files - they need to set up localStorage for testing
{
  files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
  rules: {
    'no-restricted-globals': 'off',
    // Tests may intentionally test buildWebSocketUrl with various argument counts
    'no-restricted-syntax': 'off',
  },
}, // Override for api.ts and its tests - they define/test the deprecated function
{
  files: ['**/config/api.ts', '**/config/api.test.ts'],
  rules: {
    'no-restricted-imports': 'off',
  },
}, // Override for websocket utility - it defines buildWebSocketUrl and uses it internally
{
  files: ['**/utils/websocket.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for API transforms - they legitimately work with snake_case fields
{
  files: ['**/api/transforms.ts', '**/api/transforms.test.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for API index - query params must use snake_case for backend
{
  files: ['**/api/index.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for mock handlers - they simulate snake_case API responses
{
  files: ['**/mocks/**/*.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for WebSocket hooks - they process raw API data before transformation
{
  files: ['**/hooks/use*WebSocket.ts', '**/hooks/useStreamingChat.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for HITL types - they define API-compatible snake_case types
{
  files: ['**/types/hitl.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for apiTransforms - it works with snake_case conversions
{
  files: ['**/utils/apiTransforms.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for Intelligence hooks - they work with AI API responses
{
  files: ['**/hooks/use*Intelligence.ts', '**/hooks/useStudioAI.ts', '**/hooks/useAIOrchestratorStatus.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for router loaders - they process API responses
{
  files: ['**/router/loaders/*.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for store slices - they store API data
{
  files: ['**/store/slices/*.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for HITL dialogs hook - processes API data before transformation
{
  files: ['**/hooks/useHITLDialogs.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Override for HITL dialog components - they are API boundary components that:
// 1. Consume API contract types (snake_case) directly as props
// 2. Build API-compatible response objects to send back to backend
// These are tightly coupled with the HITL WebSocket/hook layer
// ADR-0091 Phase 6.1: RemediationApprovalDialog now clean, removed from override
{
  files: [
    '**/components/Admin/AgentApprovalDialog.tsx',
    '**/components/Admin/ClarificationDialog.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // ADR-0091 Phase 6.1 (2026-01-06): Admin alert/remediation components are now clean
// Removed override for: AIRecommendationCard, AdminDashboard, AgentApprovalAuditLog,
// AlertDetailPanel, AlertGroupsPanel, AlertsPanel, BatchApprovalPanel
// All now use camelCase via RTK Query transforms
// ADR-0091 Phase 6: Component overrides for snake_case property access
// RTK Query transformResponse is applied to core endpoints.
// These overrides remain until component code is updated to use camelCase property access.
// Track progress in ADR-0091 Phase 6 section.
//
// COMPLETED (overrides removed - 2026-01-05):
// - Agents/*.tsx - All camelCase ✓
// - MCP/*.tsx - All camelCase ✓
// - Observability/*.tsx - All camelCase ✓
// - PlanEditor/*.tsx - All camelCase ✓
// - Analytics/*.tsx - All camelCase ✓
// - Connection/*.tsx - All camelCase ✓
// - DevTools/**/*.tsx, *.ts - All camelCase ✓
// - Workflow/*.tsx - All camelCase ✓
// - Project/*.tsx - All camelCase ✓
// - SessionNav.tsx - All camelCase ✓
// - Chat/SaveAsWorkflowButton.tsx - All camelCase ✓
// - Cost/*.tsx - All camelCase ✓
// - Insights/*.tsx - All camelCase ✓
// - Session/*.tsx - All camelCase ✓
// - conversation/*.tsx - All camelCase ✓
{
  files: [
    // API Boundary Components - intentionally use snake_case at system boundaries:
    // - Feature flag names (backend-defined, e.g., "kb_focus", "mobile_drawer")
    // - API request bodies (e.g., refresh_token in logout request)
    // - External API params (e.g., Keycloak post_logout_redirect_uri)
    // - JWT token fields in tests (Keycloak standard: preferred_username, realm_access)
    '**/layout/*.tsx',
    '**/pages/*.tsx', // Pages access raw API responses before transformation
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // ADR-0091 Status:
// - Phase 5: COMPLETE (transform functions)
// - Phase 6: COMPLETE (16 component directories migrated to camelCase)
// - Phase 10: COMPLETE (HITL dialog components migrated to camelCase)
// - Remaining overrides: layout/*.tsx (UserMenuDropdown), pages/*.tsx (API boundary)

// ============================================================================
// Design System: Overrides for forbid-elements rule
// These files legitimately need raw HTML elements
// ============================================================================

// UI primitive components define the design system - they must use raw elements
// Also allow CVA variant exports alongside components (react-refresh warning)
{
  files: ['**/components/UI/**/*.tsx'],
  rules: {
    'react/forbid-elements': 'off',
    'no-restricted-imports': 'off', // UI components may have internal imports
    'react-refresh/only-export-components': 'off', // CVA variants are exported with components
  },
}, // Page components may use direct UI imports to avoid Rollup circular dependency warnings
// when the page and UI barrel end up in different chunks
{
  files: ['**/pages/**/*.tsx'],
  rules: {
    'no-restricted-imports': 'off',
  },
}, // Canvas and ReactFlow components need native event handlers
{
  files: ['**/canvas/**/*.tsx', '**/reactflow/**/*.tsx', '**/Workflow/**/*.tsx'],
  rules: {
    'react/forbid-elements': 'off',
    'react-refresh/only-export-components': 'off', // Canvas exports helper functions
  },
}, // Form components that wrap raw inputs
{
  files: ['**/components/Chat/**/*.tsx', '**/conversation/**/*.tsx'],
  rules: {
    'react/forbid-elements': [
      'warn',
      {
        forbid: [
          // Allow textarea and input in chat (ChatInputForm uses them legitimately)
          // But still warn about button and select
          {
            element: 'button',
            message:
              'Use <Button> from @/components/UI instead of raw <button>.',
          },
          {
            element: 'select',
            message:
              'Use design system dropdown/select components from @/components/UI.',
          },
        ],
      },
    ],
  },
}, // Files with legitimate raw input usage (file uploads, range sliders, dynamic forms, custom radio)
{
  files: [
    '**/components/Common/FileDropZone.tsx', // File upload
    '**/components/Chat/ExportButton.tsx', // File download checkbox
    '**/components/Settings/SettingsPanel.tsx', // Range sliders
    '**/components/DevTools/TimelineBar.tsx', // Range slider
    '**/pages/AgentsPage.tsx', // Range slider for thinking budget
    '**/generative/InteractiveForm.tsx', // Dynamic form generator
    '**/components/Feedback/SUSSurvey.tsx', // Custom rating scale radio buttons
    '**/components/Admin/RemediationApprovalDialog.tsx', // Custom card-style radio buttons
  ],
  rules: {
    'react/forbid-elements': 'off',
  },
}, // Test files may need to test raw elements
{
  files: ['**/*.test.tsx', '**/*.spec.tsx'],
  rules: {
    'react/forbid-elements': 'off',
  },
}, // Storybook stories may render examples
{
  files: ['**/*.stories.tsx'],
  rules: {
    'react/forbid-elements': 'off',
  },
},

// ============================================================================
// Design System: Overrides for semantic color enforcement
// These files legitimately use raw Tailwind colors for categorical/visualization purposes
// ============================================================================

// Categorical node type colors - intentionally distinct from semantic status colors
{
  files: [
    '**/components/Workflow/NodePalette.tsx',     // Node type colors (start, end, llm, tool, condition)
    '**/components/Trace/TraceCanvas.tsx',        // Trace visualization colors
    '**/components/Trace/TraceNode.tsx',          // Trace node colors
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Chart and visualization components - programmatic SVG/canvas colors
{
  files: [
    '**/components/Artifacts/ChartArtifact.tsx',
    '**/components/Artifacts/VegaLiteArtifact.tsx',
    '**/components/Chat/InteractiveChart.tsx',
    '**/components/Chat/InteractiveMermaidDiagram.tsx',
    '**/canvas/**/*.tsx',
    '**/generative/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Design tokens - defines the raw-to-semantic mappings
{
  files: ['**/utils/tokens.ts', '**/utils/colors.ts', '**/types/design-tokens.ts'],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Connection template selector - template category colors
{
  files: ['**/components/Connection/ConnectionTemplateSelector.tsx'],
  rules: {
    'no-restricted-syntax': 'off',
  },
},

// ============================================================================
// Design System: Overrides for sizing/spacing token enforcement
// These files legitimately use arbitrary values documented in STYLE.md
// Added 2026-01-14 alongside ESLint sizing/spacing rules
// ============================================================================

// DevTools tabs - contain legitimate fixed-width dropdowns, panels, and log layouts
{
  files: [
    '**/components/DevTools/**/*.tsx',
    '**/components/DevTools/**/*.ts',
  ],
  rules: {
    // DevTools legitimately use: min-w-[120px] dropdowns, fixed panel heights
    'no-restricted-syntax': 'off',
  },
}, // Dialog/Modal components - use viewport-relative and fixed sizing
{
  files: [
    '**/components/Common/**/*.tsx',
    '**/components/Export/**/*.tsx',
    '**/components/MCP/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Admin dashboard components - tables with fixed column widths
{
  files: [
    '**/components/Admin/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Layout components - use viewport-relative sizing for responsive design
{
  files: [
    '**/layout/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Canvas and workflow - fixed node sizes, panel dimensions
{
  files: [
    '**/canvas/**/*.tsx',
    '**/components/Workflow/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Chat components - input constraints, message bubble widths
{
  files: [
    '**/components/Chat/**/*.tsx',
    '**/conversation/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Session/Project components - list item sizing
{
  files: [
    '**/components/Session/**/*.tsx',
    '**/components/Project/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Observability/Insights - chart containers, metric cards
{
  files: [
    '**/components/Observability/**/*.tsx',
    '**/components/Insights/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // AI features - suggestions, command palettes with fixed positioning
{
  files: [
    '**/ai/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Generative components - dynamic content rendering
{
  files: [
    '**/generative/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Help/Onboarding - tour overlays, help panels
{
  files: [
    '**/help/**/*.tsx',
    '**/components/Help/**/*.tsx',
    '**/components/Onboarding/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Settings - form layouts, sliders
{
  files: [
    '**/components/Settings/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Compliance - dashboard layouts
{
  files: [
    '**/compliance/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Persona/Router - guard components with layout logic
{
  files: [
    '**/persona/**/*.tsx',
    '**/router/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
},

// ============================================================================
// Design System: Inline Style Overrides
// These files legitimately use inline styles for dynamic values
// Added 2026-01-15 alongside ESLint inline style rule
// ============================================================================

// Artifact components - render third-party content with dynamic styles
{
  files: [
    '**/components/Artifacts/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Analytics components - dynamic data-driven colors and visualizations
{
  files: [
    '**/components/Analytics/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Cost components - dynamic budget bars and forecast charts
{
  files: [
    '**/components/Cost/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Error components - dynamic error state visualizations
{
  files: [
    '**/components/ErrorBoundary/**/*.tsx',
    '**/components/ErrorRecovery/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Feedback components - dynamic survey/rating visualizations
{
  files: [
    '**/components/Feedback/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Motion components - CSS animations requiring dynamic styles
{
  files: [
    '**/components/Motion/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Components with legitimate inline badge patterns (to be migrated to Badge component)
// These are existing patterns that will be refactored in a separate migration
{
  files: [
    '**/components/Agents/**/*.tsx',
    '**/components/Context/**/*.tsx',
    '**/components/DecisionTrace/**/*.tsx',
    '**/components/Error/**/*.tsx',
    '**/components/PlanEditor/**/*.tsx',
    '**/components/PlanSearch/**/*.tsx',
    '**/components/Status/**/*.tsx',
    '**/components/TemplateSelector/**/*.tsx',
    '**/components/WebSocketMetrics/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // Nudge/spotlight components - calculated positions for overlays
{
  files: [
    '**/components/Nudge/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // UI primitive components - may need dynamic styles for positioning
{
  files: [
    '**/components/UI/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, // DevTools panel - telemetry viewer and debug tools
{
  files: [
    '**/devtools/**/*.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
    'react/forbid-elements': 'off', // DevTools use raw elements for debugging
  },
}, // Storybook stories - documentation and examples may use inline styles
{
  files: [
    '**/*.stories.tsx',
  ],
  rules: {
    'no-restricted-syntax': 'off',
  },
}, storybook.configs["flat/recommended"]);

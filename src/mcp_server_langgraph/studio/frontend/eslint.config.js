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
      // Use error-*, success-*, warning-*, primary-* instead of red-*, green-*, yellow-*, blue-*
      // Use insight-* instead of purple-*, grafana-* instead of orange-*, info-* instead of cyan-*
      // Use neutral-* instead of gray-* (recommended but not enforced due to 4000+ usages)
      // See plan: ~/.claude/plans/playful-toasting-emerson.md
      {
        selector:
          "Literal[value=/\\b(text|bg|border|ring|hover:text|hover:bg|hover:border|focus:ring)-(red|green|blue|yellow|amber|purple|orange|cyan)-\\d+/]",
        message:
          'Use semantic colors (error-*, success-*, warning-*, primary-*, insight-*, grafana-*, info-*) instead of raw colors (red-*, green-*, blue-*, yellow-*, amber-*, purple-*, orange-*, cyan-*). See src/utils/colors.ts for utilities.',
      },
      // Design System: Suggest neutral-* instead of gray-* for new code
      // Note: This is informational only (4000+ existing usages). Migration is tracked in plan.
      // New code should prefer neutral-* for consistency with other semantic colors.
      // {
      //   selector:
      //     "Literal[value=/\\b(text|bg|border|divide)-(gray)-\\d+/]",
      //   message:
      //     'Consider using neutral-* instead of gray-* for semantic consistency. See src/utils/colors.ts for NEUTRAL_COLORS utilities.',
      // },
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
}, storybook.configs["flat/recommended"]);

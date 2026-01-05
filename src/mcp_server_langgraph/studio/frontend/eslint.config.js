import js from '@eslint/js';
import globals from 'globals';
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

export default tseslint.config(
  { ignores: ['dist', 'node_modules'] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ['**/*.{ts,tsx}'],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
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
          ],
        },
      ],

      // Catch common snake_case API field patterns in new code
      // This helps prevent regressions after the camelCase API transformation
      // See ADR-0091 for the complete API transformation strategy
      'no-restricted-syntax': [
        'warn',
        {
          selector:
            "MemberExpression[property.name=/^(alert_id|started_at|ended_at|created_at|updated_at|user_id|session_id|trace_id|span_id|workflow_id|project_id|organization_id|remediation_id|recommendation_id|step_number|risk_level|total_cost|total_tokens|prompt_tokens|completion_tokens|request_count|next_cursor|prev_cursor|has_next|has_prev|auth_type|api_key|default_level|feature_flag|task_categories|version_number|graph_json|source_text|commit_message|created_by|prompt_version|prompt_model|head_version_id|node_count|edge_count|message_count|owner_id|connection_type|tool_count|max_tokens|request_id|per_page|total_pages)$/]",
          message:
            'Use camelCase field names (e.g., alertId, startedAt, userId). API responses are now transformed via RTK Query transformResponse. See ADR-0091.',
        },
      ],
    },
  },
  // Override for storage utility - it legitimately needs direct localStorage access
  {
    files: ['**/utils/storage.ts'],
    rules: {
      'no-restricted-globals': 'off',
    },
  },
  // Override for test files - they need to set up localStorage for testing
  {
    files: ['**/*.test.ts', '**/*.test.tsx', '**/*.spec.ts', '**/*.spec.tsx'],
    rules: {
      'no-restricted-globals': 'off',
      // Tests may intentionally test buildWebSocketUrl with various argument counts
      'no-restricted-syntax': 'off',
    },
  },
  // Override for api.ts and its tests - they define/test the deprecated function
  {
    files: ['**/config/api.ts', '**/config/api.test.ts'],
    rules: {
      'no-restricted-imports': 'off',
    },
  },
  // Override for websocket utility - it defines buildWebSocketUrl and uses it internally
  {
    files: ['**/utils/websocket.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for API transforms - they legitimately work with snake_case fields
  {
    files: ['**/api/transforms.ts', '**/api/transforms.test.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for API index - query params must use snake_case for backend
  {
    files: ['**/api/index.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for mock handlers - they simulate snake_case API responses
  {
    files: ['**/mocks/**/*.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for WebSocket hooks - they process raw API data before transformation
  {
    files: ['**/hooks/use*WebSocket.ts', '**/hooks/useStreamingChat.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for HITL types - they define API-compatible snake_case types
  {
    files: ['**/types/hitl.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for apiTransforms - it works with snake_case conversions
  {
    files: ['**/utils/apiTransforms.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for Intelligence hooks - they work with AI API responses
  {
    files: ['**/hooks/use*Intelligence.ts', '**/hooks/useStudioAI.ts', '**/hooks/useAIOrchestratorStatus.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for router loaders - they process API responses
  {
    files: ['**/router/loaders/*.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for store slices - they store API data
  {
    files: ['**/store/slices/*.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for HITL dialogs hook - processes API data before transformation
  {
    files: ['**/hooks/useHITLDialogs.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for HITL dialog components - they are API boundary components that:
  // 1. Consume API contract types (snake_case) directly as props
  // 2. Build API-compatible response objects to send back to backend
  // These are tightly coupled with the HITL WebSocket/hook layer
  {
    files: [
      '**/components/Admin/AgentApprovalDialog.tsx',
      '**/components/Admin/ClarificationDialog.tsx',
      '**/components/Admin/RemediationApprovalDialog.tsx',
    ],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for Admin alert/remediation components - API boundary layer
  // These components directly consume backend Alert, Recommendation, Remediation types
  // Full camelCase migration requires RTK Query transformResponse (tracked in ADR-0091 Phase 5)
  {
    files: [
      '**/components/Admin/AIRecommendationCard.tsx',
      '**/components/Admin/AdminDashboard.tsx',
      '**/components/Admin/AgentApprovalAuditLog.tsx',
      '**/components/Admin/AlertDetailPanel.tsx',
      '**/components/Admin/AlertGroupsPanel.tsx',
      '**/components/Admin/AlertsPanel.tsx',
      '**/components/Admin/BatchApprovalPanel.tsx',
    ],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // Override for components that consume API data - pending Phase 5 migration
  // These consume backend types directly (Agents, Workflow, Session, Project, MCP, Cost, Observability)
  // Full camelCase migration requires RTK Query transformResponse (tracked in ADR-0091 Phase 5)
  {
    files: [
      '**/components/Agents/*.tsx',
      '**/components/Chat/SaveAsWorkflowButton.tsx',
      '**/components/Connection/*.tsx',
      '**/components/Cost/*.tsx',
      '**/components/DevTools/**/*.tsx',
      '**/components/DevTools/**/*.ts',
      '**/components/Insights/*.tsx',
      '**/components/MCP/*.tsx',
      '**/components/Observability/*.tsx',
      '**/components/PlanEditor/*.tsx',
      '**/components/Project/*.tsx',
      '**/components/Session/*.tsx',
      '**/components/Workflow/*.tsx',
      '**/conversation/*.tsx',
      '**/layout/*.tsx',
      '**/pages/*.tsx',
    ],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
  // ADR-0091 Phase 4 Complete: Targeted overrides for API boundary components
  // Phase 5 will add RTK Query transformResponse to migrate from snake_case to camelCase
  // See ADR-0091 for full migration tracking
);

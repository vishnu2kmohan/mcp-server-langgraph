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
      // Enforce explicit includeAuthToken parameter in buildWebSocketUrl calls
      // Backend endpoints with require_auth=True need the token, defaulting to false causes auth failures
      'no-restricted-syntax': [
        'warn',
        {
          selector: 'CallExpression[callee.name="buildWebSocketUrl"][arguments.length<3]',
          message:
            'buildWebSocketUrl should explicitly set includeAuthToken (3rd param). Most endpoints require auth (require_auth=True in ws_router.py). Use buildWebSocketUrl(endpoint, params, true) for authenticated endpoints.',
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
  // Override for websocket utility - it defines buildWebSocketUrl and uses it internally
  {
    files: ['**/utils/websocket.ts'],
    rules: {
      'no-restricted-syntax': 'off',
    },
  },
);

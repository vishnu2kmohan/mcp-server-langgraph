import js from '@eslint/js';
import globals from 'globals';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

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
    },
  },
);

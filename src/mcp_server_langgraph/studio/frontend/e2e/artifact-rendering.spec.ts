/**
 * Interactive Artifact Rendering E2E Tests
 *
 * Tests the interactive artifact rendering functionality including:
 * - Mermaid diagram rendering
 * - Chart rendering
 * - SVG with zoom/pan
 * - Sandpack execution for JSX/TSX/MDX
 * - Feature flag toggle behavior
 *
 * IMPORTANT: E2E tests run with BACKEND_ENABLED=true by default.
 * This ensures tests validate against the real backend API.
 *
 * To run these tests:
 * 1. Start test infrastructure: `make test-infra-up-build`
 * 2. Run tests: `npm run test:e2e -- --grep "Artifact Rendering"`
 */

import { test, expect } from './fixtures/auth';

// Backend integration is enabled by default for E2E tests.
const backendEnabled = process.env.BACKEND_ENABLED !== 'false';

test.describe('Interactive Artifact Rendering', () => {
  test.beforeEach(async ({ alicePage }) => {
    // Navigate to chat page
    await alicePage.goto('/chat');
    await alicePage.waitForLoadState('networkidle');
  });

  test.describe('Mermaid Diagrams', () => {
    test('should render mermaid diagram from assistant response', async ({ alicePage }) => {
      // This test requires a chat session with a mermaid diagram response
      // Skip if backend is not enabled
      test.skip(!backendEnabled, 'Requires backend for message streaming');

      // TODO: Send a message that triggers mermaid diagram response
      // TODO: Verify the diagram SVG is rendered
      // TODO: Verify interactivity (zoom, pan)
    });
  });

  test.describe('Charts', () => {
    test('should render interactive chart from chart code block', async ({ alicePage }) => {
      test.skip(!backendEnabled, 'Requires backend for message streaming');

      // TODO: Send a message that triggers chart response
      // TODO: Verify chart container is rendered
      // TODO: Verify chart title and data
    });
  });

  test.describe('Sandpack Execution', () => {
    test('should show Run button for executable code blocks', async ({ alicePage }) => {
      test.skip(!backendEnabled, 'Requires backend for message streaming');

      // TODO: Send a message that triggers JSX/TSX code response
      // TODO: Verify Run button is visible
      // TODO: Click Run button and verify Sandpack preview loads
    });

    test('should not auto-execute code blocks', async ({ alicePage }) => {
      test.skip(!backendEnabled, 'Requires backend for message streaming');

      // TODO: Verify Sandpack preview is NOT visible until Run is clicked
      // This validates the security-conscious opt-in behavior
    });
  });

  test.describe('Feature Flag', () => {
    test('should fall back to plain code when interactive_artifacts flag is false', async ({ alicePage }) => {
      // This test requires mocking the feature flags API
      test.skip(!backendEnabled, 'Requires backend with feature flag control');

      // TODO: Mock feature flags API to return interactive_artifacts: false
      // TODO: Verify mermaid/chart blocks render as plain code
    });
  });
});
